-- ROP reads the lead result of the same target kernel. Reviewed Native
-- profiles win, including explicit manual demand and known zero. Products
-- without a profile keep the existing statistical/14-day rule, now from
-- the SAME Native available-day history, with a separately proven lead.
-- Default-only ROP does not claim a reviewed full production target.
create function cp7_reorder_inputs.points(v jsonb,defaults jsonb,leads jsonb,manuals jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare row_value jsonb;hist jsonb;profile jsonb;config jsonb;kernel jsonb;lead_row jsonb;manual_row jsonb;
 by_history jsonb;by_product jsonb;product jsonb;by_lead jsonb:='{}';by_manual jsonb:='{}';seen jsonb:='{}';item jsonb;key text;root text;
 total numeric;counted numeric;sd numeric;mean_value numeric;lead_days numeric;point text;formula_point text;
 source_kind text;reason text;point_basis text;manual_state text;checked timestamptz;window_days integer;
 output_rows jsonb[]:='{}';selection_hash text;
begin
 perform cp7_wip.fields(v,array['contract_version','captured_at','query','source_hash','history_hash','target_engine','products','history','current_stock','targets','apply_enabled','production_go']);
 perform cp7_wip.fields(defaults,array['service_level','window_days']);
 if v->>'contract_version'is distinct from'cp7.reorder-native-inputs.v1'
  or v->>'target_engine'is distinct from'EXISTING_NATIVE_STAGED_BASELINE'
  or v->'apply_enabled'is distinct from'false'::jsonb or v->'production_go'is distinct from'false'::jsonb
  or defaults->>'service_level'is null or defaults->>'service_level'not in('0.90','0.95','0.99')
  or jsonb_typeof(defaults->'service_level')is distinct from'string'
  or jsonb_typeof(defaults->'window_days')is distinct from'string'or defaults->>'window_days'!~'^[0-9]{2,3}$'then
  raise exception 'CP7_REORDER_INPUT_POLICY';end if;
 checked:=cp7_demand.instant(v->'captured_at');window_days:=(defaults->>'window_days')::integer;
 if window_days not between 14 and 365
  or v->'query'->>'from_date'is distinct from((checked at time zone'Asia/Jakarta')::date-window_days)::text
  or v->'query'->>'through_date'is distinct from((checked at time zone'Asia/Jakarta')::date-1)::text then
  raise exception 'CP7_REORDER_INPUT_PERIOD';end if;
 perform cp7_wip.fields(v->'query',array['from_date','through_date','group_mode']);
 if v->'query'->>'group_mode'is distinct from'AS_SOLD'then raise exception 'CP7_REORDER_INPUT_GROUP_MODE';end if;
 perform cp7_demand.items(v->'targets',5000);perform cp7_demand.items(v->'history',5000);
 perform cp7_demand.items(v->'products',5000);
 perform cp7_demand.items(leads,5000);perform cp7_demand.items(manuals,5000);
 for item in select value from jsonb_array_elements(leads)loop
  perform cp7_wip.fields(item,array['model_id','lead_days','lot_count','group_count']);key:=cp7_wip.key(item->'model_id');
  if by_lead?key then raise exception 'CP7_REORDER_LEAD_DUPLICATE';end if;
  perform cp7_wip.pcs(item->'lot_count');perform cp7_wip.pcs(item->'group_count');
  if cp7_wip.pcs(item->'group_count')>cp7_wip.pcs(item->'lot_count')then raise exception 'CP7_REORDER_LEAD_COUNTS';end if;
  if item->'lead_days'<>'null'::jsonb then
   perform cp7_demand.decimal(item->'lead_days');
   if cp7_wip.pcs(item->'group_count')<3 then raise exception 'CP7_REORDER_LEAD_UNPROVEN';end if;
  end if;
  by_lead:=by_lead||jsonb_build_object(key,item);
 end loop;
 for item in select value from jsonb_array_elements(manuals)loop
  perform cp7_wip.fields(item,array['root_id','product_version_id','size_id','revision','reorder_point_pcs']);
  key:=cp7_wip.key(item->'root_id');perform cp7_wip.key(item->'product_version_id');perform cp7_wip.key(item->'size_id');perform cp7_wip.pcs(item->'revision');
  if by_manual?key then raise exception 'CP7_REORDER_MANUAL_DUPLICATE';end if;
  if item->'reorder_point_pcs'<>'null'::jsonb and cp7_wip.pcs(item->'reorder_point_pcs')>10000000 then raise exception 'CP7_REORDER_MANUAL_RANGE';end if;
  by_manual:=by_manual||jsonb_build_object(key,item);
 end loop;
 select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into by_history from jsonb_array_elements(v->'history')x;
 if (select count(*)from jsonb_each(by_history))<>jsonb_array_length(v->'history')then raise exception 'CP7_REORDER_HISTORY_DUPLICATE';end if;
 select coalesce(jsonb_object_agg(x->>'root_id',x),'{}')into by_product from jsonb_array_elements(v->'products')x;
 if (select count(*)from jsonb_each(by_product))<>jsonb_array_length(v->'products')then raise exception 'CP7_REORDER_PRODUCT_DUPLICATE';end if;
 for row_value in select value from jsonb_array_elements(v->'targets')loop
  key:=cp7_wip.key(row_value->'target_key');root:=split_part(key,':',1);hist:=by_history->key;
  if seen?key or hist is null or row_value->>'size_id'is distinct from hist->>'size_id'then raise exception 'CP7_REORDER_TARGET_HISTORY_BINDING';end if;
  seen:=seen||jsonb_build_object(key,true);profile:=row_value->'profile';config:=profile->'config';product:=by_product->root;
  if jsonb_typeof(profile)is distinct from'object'or profile->>'root_id'is distinct from root then raise exception 'CP7_REORDER_TARGET_PROFILE_BINDING';end if;
  if product is null or product->>'id'is distinct from profile->>'product_version_id'or product->>'size_id'is distinct from row_value->>'size_id'then raise exception 'CP7_REORDER_TARGET_PRODUCT_BINDING';end if;
  lead_row:=by_lead->(product->>'model_id');manual_row:=by_manual->root;
  select coalesce(sum((day->>'gross_observed_pcs')::numeric),0),count(*),stddev_samp((day->>'gross_observed_pcs')::numeric)
   into total,counted,sd from jsonb_array_elements(hist->'days')day where day->>'state'='AVAILABLE';
  if counted is distinct from(hist->>'available_days')::numeric then raise exception 'CP7_REORDER_AVAILABLE_DAY_BINDING';end if;
  mean_value:=case when counted>0 then total/counted end;lead_days:=null;reason:=null;
  if profile->>'quality'='SELECTED_ASSUMPTION'then
   -- Keep the exact Native target, not a rounded mean or a second lead rule.
   kernel:=row_value->'target';source_kind:='PLANNING_PROFILE';
   if kernel->'inputs'->>'contract_version'is distinct from'cp7.target-input.v2'then raise exception 'CP7_REORDER_TARGET_KERNEL_BINDING';end if;
   if kernel->'inputs'->'lead_days'<>'null'::jsonb then lead_days:=cp7_demand.decimal(kernel->'inputs'->'lead_days');end if;
   mean_value:=case when kernel->'inputs'->'daily_total_pcs'<>'null'::jsonb and kernel->'inputs'->'counted_days'<>'null'::jsonb
    then cp7_demand.decimal(kernel->'inputs'->'daily_total_pcs')/nullif(cp7_wip.pcs(kernel->'inputs'->'counted_days'),0)end;
   reason:=case when kernel->>'status'is distinct from'SCENARIO'then kernel->>'reason'end;
  elsif profile->>'quality'='UNREVIEWED'then
   source_kind:='NATIVE_HISTORY_WITH_EXISTING_DEFAULTS';
   if lead_row->'lead_days'<>'null'::jsonb then lead_days:=cp7_demand.decimal(lead_row->'lead_days');end if;
   kernel:=cp7_baseline.target(jsonb_build_object('contract_version','cp7.target-input.v2','snapshot_id',v->'source_hash',
    'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','mode','STATISTICAL','daily_total_pcs',case when counted>=14 then total::text end,
    'counted_days',case when counted>=14 then counted::text end,'daily_sd',case when counted>=14 then sd::text end,
    'lead_days',lead_days::text,'review_days','0','buffer_days',null,'service_level',defaults->'service_level','refs',hist->'refs'));
   reason:=case when counted<14 then'FEWER_THAN_14_NATIVE_AVAILABLE_DAYS'when lead_days is null then'NO_PROVEN_LEAD_TIME'
    when kernel->>'status'is distinct from'SCENARIO'then kernel->>'reason'end;
  else
   source_kind:='PROFILE_UNAVAILABLE';kernel:=row_value->'target';reason:='PROFILE_IDENTITY_OR_VERSION_CHANGED';
  end if;
  formula_point:=case when reason is null then kernel->>'reorder_point_pcs'end;point:=formula_point;
  point_basis:=case when formula_point is not null then'FORMULA'else'UNKNOWN'end;manual_state:='NONE';
  if manual_row is not null then
   manual_state:=case when manual_row->'reorder_point_pcs'='null'::jsonb then'CLEARED'
    when manual_row->>'product_version_id'is distinct from profile->>'product_version_id'or manual_row->>'size_id'is distinct from row_value->>'size_id'then'STALE_IDENTITY'
    else'ACTIVE'end;
   if manual_state='ACTIVE'then point:=manual_row->>'reorder_point_pcs';point_basis:='MANUAL';reason:=null;
   elsif manual_state='STALE_IDENTITY'then point:=null;point_basis:='UNKNOWN';reason:='MANUAL_POINT_VERSION_CHANGED';end if;
  end if;
  output_rows:=array_append(output_rows,jsonb_build_object('target_key',key,'size_id',row_value->'size_id',
   'product_version_id',profile->'product_version_id','source_kind',source_kind,'point_basis',point_basis,'point_pcs',point,
   'formula_point_pcs',formula_point,'reason',reason,'daily_mean',mean_value::text,'available_days',counted::text,
   'available_total_pcs',total::text,'daily_sd',sd::text,'lead_days',lead_days::text,
   'lead_basis',case when lead_days is null then null when source_kind='PLANNING_PROFILE'then'PROFILE'else'MEASURED'end,
   'target',kernel,'manual_state',manual_state,'manual_reference',manual_row,
   'supply_alignment',case when source_kind='PLANNING_PROFILE'and point_basis='FORMULA'and reason is null then'NATIVE_TARGET'else'NEEDS_EXPLICIT_BINDING'end));
 end loop;
 if (select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'history')
  or (select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'products')then raise exception 'CP7_REORDER_HISTORY_SCOPE_MISMATCH';end if;
 selection_hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_source',v->'source_hash',
  'query',v->'query','defaults',defaults,'leads',leads,'manuals',manuals,'compiler','reorder-points-1')::text,'UTF8'),'sha256'),'hex');
 return jsonb_build_object('contract_version','cp7.reorder-native-points.v1','captured_at',v->'captured_at','query',v->'query',
  'native_source_hash',v->'source_hash','selection_hash',selection_hash,'rows',to_jsonb(output_rows),'apply_enabled',false,'production_go',false);
end $$;
alter function cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)from public,anon,authenticated,service_role;
