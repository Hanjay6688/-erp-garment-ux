-- Private source-only prototype. No public caller, selection or owner policy.
create schema cp7_product_analog_stage authorization cp7_capture;
revoke all on schema cp7_product_analog_stage from public,anon,authenticated,service_role;
create function cp7_product_analog_stage.candidates(c jsonb,p_target text,p_offset integer,p_limit integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare prepared jsonb;target_product jsonb;selected_profile jsonb;history_map jsonb;
 envelope jsonb;minimum_days numeric;matching_count integer;candidate_count integer;suggested_count integer;page_rows jsonb;
begin
 if p_offset is null or p_offset<0 or p_offset>5000 or p_limit is null or p_limit not between 1 and 100 then
  raise exception 'CP7_PRODUCT_ANALOG_PAGE';end if;
 prepared:=cp7_bounded_analysis_stage.require_inputs(c,c->'bounded_query');
 envelope:=jsonb_build_object('contract_version','cp7.product-analog-candidates.prototype.v1',
  'target_key',p_target,'source_captured_at',c->'captured_at','query',c->'bounded_query',
  'history_hash',prepared->'history_hash','source_hash',prepared->'source_hash',
  'selected',false,'reviewed',false,'forecast_applied',false,'production_go',false);
 perform cp7_wip.key(to_jsonb(p_target));
 select count(*),(jsonb_agg(product))->0 into matching_count,target_product
  from jsonb_array_elements(c->'facts'->'products')product
  where(product->>'root_id')||':'||(product->>'size_id')=p_target;
 if matching_count<>1 then raise exception 'CP7_PRODUCT_ANALOG_TARGET';end if;
 select count(*),(jsonb_agg(profile))->0 into matching_count,selected_profile
  from jsonb_array_elements(c->'profiles')profile where profile->'root_id'=target_product->'root_id';
 if matching_count>1 then raise exception 'CP7_PRODUCT_ANALOG_PROFILE_AMBIGUOUS';end if;
 if matching_count=0 or selected_profile->>'quality'is distinct from'SELECTED_ASSUMPTION'then
  return envelope||jsonb_build_object('contract_version','cp7.product-analog-candidates.prototype.v1',
   'target_key',p_target,'state','PLANNING_CONFIG_REQUIRED','candidates','[]'::jsonb,
   'total',0,'suggested',0,'offset',p_offset,'limit',p_limit,'selected',false,'reviewed',false,'production_go',false);
 end if;
 minimum_days:=cp7_wip.pcs(selected_profile#>'{config,minimum_available_days}');
 if minimum_days<1 then raise exception 'CP7_PRODUCT_ANALOG_MINIMUM_DAYS';end if;
 select jsonb_object_agg(history_row->>'target_key',history_row)into history_map
  from jsonb_array_elements(prepared->'history')history_row;
 with product_history as materialized(
  select product,history_map->((product->>'root_id')||':'||(product->>'size_id'))observed
  from jsonb_array_elements(c->'facts'->'products')product
  where product->'size_id'=target_product->'size_id'
   and(product->>'root_id')||':'||(product->>'size_id')<>p_target
 ),eligible as materialized(
  select product,observed,
   product->>'model_id'is not null and product->'model_id'=target_product->'model_id'same_model,
   product->>'brand_id'is not null and product->'brand_id'=target_product->'brand_id'same_brand
  from product_history where cp7_wip.pcs(to_jsonb(observed->>'available_days'))>=minimum_days
   and observed->>'available_sales_mean'is not null
 ),ranked as materialized(
  select product->>'sku'sku,product->>'root_id'root_key,same_model,same_brand,
   jsonb_build_object('target_key',(product->>'root_id')||':'||(product->>'size_id'),
    'root_id',product->'root_id','size_id',product->'size_id','sku',product->'sku',
    'product_name',product->'product_name','is_active',product->'is_active',
    'available_days',observed->'available_days','observed_available_daily_mean',observed->'available_sales_mean',
    'stockout_days',observed->'stockout_days','unknown_days',observed->'unknown_days',
    'reasons',jsonb_build_array('SAME_PHYSICAL_SIZE')||case when same_model then'"SAME_CAPTURED_MODEL"'::jsonb else'[]'::jsonb end
      ||case when same_brand then'"SAME_CAPTURED_BRAND"'::jsonb else'[]'::jsonb end,
    'suggested',same_model or same_brand,'manual_similarity_reason_required',not(same_model or same_brand),
    'selected',false,'reviewed',false,'refs',observed->'refs')row_value
  from eligible
 )select (select count(*)from ranked),(select count(*)from ranked where same_model or same_brand),
  coalesce((select jsonb_agg(limited.row_value order by limited.same_model desc,limited.same_brand desc,limited.sku collate"C",limited.root_key collate"C")
   from(select*from ranked order by same_model desc,same_brand desc,sku collate"C",root_key collate"C" offset p_offset limit p_limit)limited),'[]')
 into candidate_count,suggested_count,page_rows;
 return envelope||jsonb_build_object('contract_version','cp7.product-analog-candidates.prototype.v1',
  'target_key',p_target,'source_captured_at',c->'captured_at','query',c->'bounded_query',
  'history_hash',prepared->'history_hash','source_hash',prepared->'source_hash',
  'profile_id',selected_profile->'profile_id','profile_revision',selected_profile->'revision',
  'minimum_available_days',minimum_days::text,'total',candidate_count,'suggested',suggested_count,
  'offset',p_offset,'limit',p_limit,'candidates',page_rows,
  'state',case when candidate_count=0 then'INSUFFICIENT_REVIEWABLE_HISTORY'when suggested_count=0 then'MANUAL_CHOICE_REQUIRES_SIMILARITY_REASON'else'REVIEW_REQUIRED'end,
  'selected',false,'reviewed',false,'forecast_applied',false,'production_go',false);
end $$;
alter function cp7_product_analog_stage.candidates(jsonb,text,integer,integer)owner to cp7_capture;
revoke all on function cp7_product_analog_stage.candidates(jsonb,text,integer,integer)from public,anon,authenticated,service_role;
