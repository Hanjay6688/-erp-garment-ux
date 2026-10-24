create or replace function cp7_product_analog_consumer.baseline_rows(c jsonb,history_rows jsonb,current_stock jsonb,hash text,context jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare h jsonb:=jsonb_build_object('current_stock',current_stock);r jsonb;cfg jsonb;p jsonb;stock jsonb;estimate jsonb;target jsonb;manual jsonb;own jsonb;
 refs jsonb;profile_refs jsonb;total numeric;sd numeric;policy jsonb;state text;rows jsonb[]:='{}';root text;
 profiles jsonb;profiles_repeated jsonb;stocks jsonb;stocks_repeated jsonb;policies jsonb;resolution jsonb;all_refs jsonb;
begin
 if context->>'contract_version'is distinct from'cp7.analog-consumer-context.v1'
  or context->'captured_at'is distinct from c->'captured_at'then raise exception 'CP7_ANALOG_CONSUMER_CONTEXT';end if;
 for r in select x.value from jsonb_array_elements(history_rows)with ordinality x(value,o)order by x.o loop
  if context->'histories'->(r->>'target_key')is distinct from r then raise exception 'CP7_ANALOG_CONSUMER_ROW_CONTEXT';end if;
  root:=split_part(r->>'target_key',':',1);
  if profiles is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into profiles,profiles_repeated
    from(select x->>'root_id' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'profiles')with ordinality a(x,o)
     where x->>'root_id'is not null group by 1)f;
  end if;
  if profiles_repeated?root then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  p:=profiles->root;
  if stocks is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into stocks,stocks_repeated
    from(select x->>'target_key' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(h->'current_stock')with ordinality a(x,o)
     where x->>'target_key'is not null group by 1)f;
  end if;
  if stocks_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  stock:=stocks->(r->>'target_key');
  refs:=r->'refs';cfg:=case when p->>'quality'='SELECTED_ASSUMPTION'then p->'config'else null end;
  profile_refs:=case when cfg is null then '[]'::jsonb else jsonb_build_array(jsonb_build_object('kind','PLANNING_PROFILE','id',p->>'profile_id','revision',p->>'revision'))end;
  select coalesce(sum((value->>'gross_observed_pcs')::numeric),0),stddev_samp((value->>'gross_observed_pcs')::numeric)into total,sd from jsonb_array_elements(r->'days')where value->>'state'='AVAILABLE';
  own:=jsonb_build_object('available_total_pcs',total::text,'available_days',(r->>'available_days')::text,'capture_complete',true,'refs',refs);
  manual:=case when cfg->>'mean_mode'='SELECTED_MANUAL'then jsonb_build_object('daily_pcs',cfg->'daily_pcs',
   'assumption_id',p->>'profile_id','selected',true,'refs',profile_refs)else null end;
  resolution:=null;all_refs:=refs||profile_refs;
  -- Resolve fallback only after the existing manual/own priority is known.
  if manual is null and cfg is not null and cp7_wip.pcs(own->'available_days')<cp7_wip.pcs(cfg->'minimum_available_days')
   and context->'choices'->(r->>'target_key')->>'state'is distinct from'UNREVIEWED'then
   resolution:=cp7_product_analog_consumer.resolve(context,r->>'target_key',p);
   if resolution->>'state'='READY'then all_refs:=cp7_product_analog_consumer.refs(all_refs||(resolution->'refs'));end if;
  end if;
  estimate:=cp7_demand.estimate(jsonb_build_object('contract_version','cp7.demand-estimate-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','target_key',r->>'target_key','size_id',r->>'size_id',
   'minimum_own_available_days',coalesce(cfg->'minimum_available_days','"1"'::jsonb),
   'own',case when cfg is null then null else own end,'analog',resolution->'analog','manual',manual,'refs',all_refs));
  target:=cp7_baseline.target(jsonb_build_object('contract_version','cp7.target-input.v2','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','mode',coalesce(cfg->>'buffer_mode','DAYS'),
   'daily_total_pcs',case when estimate->>'basis'='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'then own->'available_total_pcs'when estimate->>'basis'='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'then resolution->'scaled_total_pcs'else estimate->'daily_pcs'end,
   'counted_days',case when estimate->>'basis'='OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'then own->'available_days'when estimate->>'basis'='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'then resolution->'available_days'else'"1"'::jsonb end,
   'daily_sd',case when cfg->>'buffer_mode'='STATISTICAL'then case when estimate->>'basis'='REVIEWED_ANALOG_SAME_PHYSICAL_SIZE_ASSUMPTION'then resolution->>'scaled_daily_sd'else sd::text end end,'service_level',case when cfg->>'buffer_mode'='STATISTICAL'then cfg->>'service_level'end,'lead_days',cfg->'lead_days','review_days',cfg->'review_days','buffer_days',cfg->'buffer_days',
   'refs',all_refs));
  if policies is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}')into policies
    from(select m.k,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'production_policies'->'rows')with ordinality a(x,o)
     cross join lateral(select e#>>'{}' k from jsonb_array_elements(case when jsonb_typeof(x->'members')='array'then x->'members'end)e
       where jsonb_typeof(e)='string'
      union select jsonb_object_keys(case when jsonb_typeof(x->'members')='object'then x->'members'end)
      union select x->'members'#>>'{}' where jsonb_typeof(x->'members')='string')m group by 1)f;
  end if;
  policy:=policies->root;
  state:=case when policy->'policy'->>'quality'='KNOWN'then policy->'policy'->>'state'else null end;
  rows:=array_append(rows,jsonb_build_object('target_key',r->>'target_key','size_id',r->>'size_id',
   'sku',stock->>'sku','product_name',stock->>'product_name','available_fg_pcs',stock->>'native_available_pcs',
   'profile',p,'demand_estimate',estimate,'target',target,'production_policy',policy,
   'start_new_pcs',case when state in('PAUSED','STOPPED')then '0'else null end,
   'final_gap_pcs',null,'supply_state','UNKNOWN','capacity_state','UNKNOWN','timeline_state','UNKNOWN',
   'reason',case when state in('PAUSED','STOPPED')then 'PRODUCTION_DISABLED_EXISTING_STOCK_STILL_SELLABLE'
    when state is null then 'PRODUCTION_POLICY_UNREVIEWED_OR_IDENTITY_UNAVAILABLE'
    else 'AUTHORITATIVE_WIP_MATCHING_CALENDAR_CAPACITY_NOT_CAPTURED'end,
   'refs',all_refs,'demand_provenance',cp7_product_analog_consumer.provenance(c,context->'query',r,estimate,resolution,target))||case when resolution is null then'{}'::jsonb else jsonb_build_object('analog_resolution',resolution)end);
 end loop;
 return to_jsonb(rows);
end $$;

create or replace function cp7_reorder_inputs.points(v jsonb,defaults jsonb,leads jsonb,manuals jsonb)returns jsonb
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
   'target',kernel,'demand_basis',row_value->'demand_estimate'->'basis',
   'analog_resolution',row_value->'analog_resolution',
   'demand_provenance',(row_value->'demand_provenance')||jsonb_build_object(
    'basis',case when profile->>'quality'='UNREVIEWED'and counted>=14 then'OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'else coalesce(row_value->'demand_estimate'->>'basis','UNKNOWN')end,
    'daily_total_pcs',kernel->'inputs'->'daily_total_pcs','counted_days',kernel->'inputs'->'counted_days',
    'daily_sd',kernel->'inputs'->'daily_sd','target_pcs',kernel->'target_pcs','reorder_point_pcs',kernel->'reorder_point_pcs'),
   'manual_state',manual_state,'manual_reference',manual_row,
   'supply_alignment',case when source_kind='PLANNING_PROFILE'and point_basis='FORMULA'and reason is null then'NATIVE_TARGET'else'NEEDS_EXPLICIT_BINDING'end));
 end loop;
 if (select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'history')
  or (select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'products')then raise exception 'CP7_REORDER_HISTORY_SCOPE_MISMATCH';end if;
 selection_hash:=encode(extensions.digest(convert_to(jsonb_build_object('native_source',v->'source_hash',
  'query',v->'query','defaults',defaults,'leads',leads,'manuals',manuals,'compiler','reorder-points-1')::text,'UTF8'),'sha256'),'hex');
 return jsonb_build_object('contract_version','cp7.reorder-native-points.v1','captured_at',v->'captured_at','query',v->'query',
  'native_source_hash',v->'source_hash','selection_hash',selection_hash,'rows',to_jsonb(output_rows),'apply_enabled',false,'production_go',false);
end $$;

create or replace function cp7_product_analog_stage.read_candidates(p_request uuid,p_target text,p_offset integer,p_limit integer,p_access text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;jid uuid;j cp7_analysis_stage.jobs%rowtype;sealed jsonb;candidates jsonb;producer text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_access is distinct from encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 select *into j from cp7_analysis_stage.jobs where id=jid;
 if j.id is null or j.state is distinct from'DONE'then
  raise exception using errcode='42501',message='CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE';end if;
 sealed:=cp7_analysis_stage.page_set(j.run_id);
 if sealed->>'access_epoch'is distinct from p_access or sealed->>'request_id'is distinct from p_request::text
  or sealed->>'run_id'is distinct from j.run_id::text then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 if j.reference->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v1'
  or j.reference->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v1'then
  raise exception 'CP7_PRODUCT_ANALOG_BOUNDED_REQUIRED';end if;
 if j.query is distinct from j.reference->'bounded_query'
  or (j.reference->>'captured_at')::timestamptz is distinct from j.captured_at
  or (sealed#>>'{reference,captured_at}')::timestamptz is distinct from j.captured_at
  or sealed#>>'{reference,source_hash}'is distinct from j.source_hash then
  raise exception 'CP7_PRODUCT_ANALOG_REFERENCE_CHANGED';end if;
 candidates:=cp7_product_analog_stage.candidates(j.reference,p_target,p_offset,p_limit);
 producer:=cp7_bounded_analysis_stage.producer_hash();
 if producer is distinct from j.reference->>'bounded_producer_hash'then
  raise exception using errcode='40001',message='CP7_PRODUCT_ANALOG_PRODUCER_CHANGED';end if;
 if cp7_schedule_native.access_now(false)is distinct from a then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.product-analog-candidates-read.v2',
  'actor_scope_id',a->'actor','request_id',p_request,'run_id',j.run_id,'query',j.query,
  'reference',jsonb_build_object('captured_at',j.captured_at,'source_hash',j.source_hash),
  'identity_hash',sealed->'identity_hash','access_epoch',p_access,'producer_hash',producer,
  'source_state','CAPTURED_NOT_CHECKED','captured_source_only',true,
  'consumer_capability','REVIEWED_ANALOG_FOR_FRESH_CAPTURES',
  'target_demand',(select x->'demand_provenance'from jsonb_array_elements(j.reference#>'{bounded_history_inputs,inputs,targets}')x where x->>'target_key'=p_target),
  'result',candidates,'selected',false,'reviewed',false,'forecast_applied',false,'production_go',false);
end $$;

create or replace function cp7_reorder_caller.evaluate(v jsonb,supply jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare products jsonb;stocks jsonb;projections jsonb;seen jsonb;history_statistics jsonb;p jsonb;product jsonb;stock jsonb;
 projected jsonb;net jsonb;lead_net jsonb;kernel jsonb;config jsonb;hist jsonb;k text;root text;item jsonb;
 free numeric;point numeric;good numeric;base_position numeric;candidate numeric;conditional_position numeric;
 status text;reason text;state text;basis text;bound boolean;analysis_at timestamptz;lead numeric;review numeric;
 rows_out jsonb[]:='{}';metadata jsonb;row_value jsonb;
begin
 perform cp7_wip.fields(v,array['points','products','threshold_source_hash','input_path','history_statistics',
  'contract_version','captured_at','query','defaults','leads','manuals','current_stock','threshold_hash',
  'threshold_captured_at','context_hash','engine_hash','native_capture_status','cache_hit','live_ROP_caller_changed','apply_enabled','production_go']);
 if v->>'contract_version'is distinct from'cp7.reorder-reader-snapshot.v1'
  or v->'points'->'query'is distinct from v->'query'or v->'apply_enabled'is distinct from'false'::jsonb
  or v->'production_go'is distinct from'false'::jsonb then raise exception 'CP7_REORDER_EVALUATE_SNAPSHOT';end if;
 perform cp7_demand.instant(v->'captured_at');perform cp7_demand.instant(v->'threshold_captured_at');
 perform cp7_demand.items(v->'products',5000);perform cp7_demand.items(v->'current_stock',5000);
 perform cp7_demand.items(v->'points'->'rows',5000);
 perform cp7_wip.fields(supply,array['contract_version','checked_at','query','status','reason','job','projection','apply_enabled','production_go']);
 if supply->>'contract_version'is distinct from'cp7.reorder-supply-cache.v1'
  or supply->>'status'is null or supply->>'status'not in('UNKNOWN','SCENARIO','PARTIAL')
  or supply->'query'is distinct from v->'query'or supply->'apply_enabled'is distinct from'false'::jsonb
  or supply->'production_go'is distinct from'false'::jsonb then raise exception 'CP7_REORDER_EVALUATE_SUPPLY';end if;
 select coalesce(jsonb_object_agg(x->>'root_id',x),'{}')into products from jsonb_array_elements(v->'products')x;
 select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into stocks from jsonb_array_elements(v->'current_stock')x;
 if(select count(*)from jsonb_each(products))<>jsonb_array_length(v->'products')
  or(select count(*)from jsonb_each(stocks))<>jsonb_array_length(v->'current_stock')then raise exception 'CP7_REORDER_EVALUATE_DUPLICATE';end if;
 if supply->'projection'<>'null'::jsonb then
  if supply->'projection'->'query'is distinct from v->'query'then raise exception 'CP7_REORDER_EVALUATE_SUPPLY';end if;
  perform cp7_demand.items(supply->'projection'->'rows',5000);
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into projections from jsonb_array_elements(supply->'projection'->'rows')x;
  if(select count(*)from jsonb_each(projections))<>jsonb_array_length(supply->'projection'->'rows')then raise exception 'CP7_REORDER_EVALUATE_DUPLICATE';end if;
  if supply->'projection'->>'contract_version'is distinct from'cp7.reorder-supply.v1'
   or(select count(*)from jsonb_each(projections))<>jsonb_array_length(v->'points'->'rows')
   or exists(select 1 from jsonb_each(projections)x where not stocks?x.key)then
   raise exception 'CP7_REORDER_EVALUATE_SUPPLY_SCOPE';end if;
 end if;
 -- Build the validated identity set once, instead of copying a growing
 -- object for every target. Keep the same duplicate/scope refusal.
 select coalesce(jsonb_object_agg(cp7_wip.key(x->'target_key'),true),'{}')into seen
  from jsonb_array_elements(v->'points'->'rows')x;
 if(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'points'->'rows')then
  raise exception 'CP7_REORDER_EVALUATE_IDENTITY';end if;
 history_statistics:=v->'history_statistics';
 for p in select value from jsonb_array_elements(v->'points'->'rows')loop
  k:=cp7_wip.key(p->'target_key');root:=split_part(k,':',1);product:=products->root;stock:=stocks->k;
  if product is null or stock is null or product->'id'is distinct from p->'product_version_id'
   or product->'size_id'is distinct from p->'size_id'or stock->'size_id'is distinct from p->'size_id'
   or stock->>'root_id'is distinct from root then raise exception 'CP7_REORDER_EVALUATE_IDENTITY';end if;
  free:=cp7_wip.pcs(stock->'native_available_pcs');
  point:=null;if p->'point_pcs'<>'null'::jsonb then point:=cp7_wip.pcs(p->'point_pcs');end if;
  kernel:=p->'target';config:=kernel->'inputs';hist:=history_statistics->k;
  if hist is null then raise exception 'CP7_REORDER_EVALUATE_HISTORY';end if;
  good:=null;base_position:=null;candidate:=null;conditional_position:=null;analysis_at:=null;
  status:='UNKNOWN';reason:=coalesce(supply->>'reason','GLOBAL_ALLOCATION_UNAVAILABLE');net:=null;lead_net:=null;
  projected:=projections->k;lead:=null;review:=null;
  if p->'lead_days'<>'null'::jsonb then lead:=cp7_demand.decimal(p->'lead_days');end if;
  if config->'review_days'<>'null'::jsonb then review:=cp7_demand.decimal(config->'review_days');end if;
  bound:=false;
  if supply->>'status'in('SCENARIO','PARTIAL')and projected->>'status'='SCENARIO'
   and projected->'net'->'lead_net'->>'status'='SCENARIO'and lead is not null and review is not null
   and supply->'job'->>'state'='DONE'then
   net:=projected->'net';lead_net:=net->'lead_net';analysis_at:=cp7_demand.instant(supply->'job'->'captured_at');
   -- ROP manual replaces the trigger only. Reuse the Native L position,
   -- comparing it with that manual threshold; do not change the production
   -- target or call net() with a point above its own full target.
   bound:=projected->'size_id'=p->'size_id'and net->'inputs'->>'target_key'=k
    and net->'inputs'->'size_id'=p->'size_id'
    and net->'inputs'->'target_pcs'=kernel->'target_pcs'
    and net->'inputs'->'reorder_point_pcs'=p->'formula_point_pcs'
    and cp7_demand.instant(net->'inputs'->'lead_deadline')=analysis_at+lead*interval'1 day'
    and cp7_demand.instant(net->'inputs'->'deadline')=analysis_at+(lead+review)*interval'1 day'
    and(net->'inputs'->>'available_fg_pcs')::numeric=free
    and cp7_demand.instant(supply->'checked_at')>=cp7_demand.instant(v->'captured_at');
   if bound then
    good:=cp7_wip.pcs(lead_net->'directed_on_time_pcs')+cp7_wip.pcs(lead_net->'incoming_on_time_pcs');
    base_position:=free+good;
    if base_position is distinct from(net->>'lead_position_base_pcs')::numeric then raise exception 'CP7_REORDER_EVALUATE_POSITION';end if;
    if net->'lead_position_conditional_pcs'<>'null'::jsonb then
     conditional_position:=(net->>'lead_position_conditional_pcs')::numeric;candidate:=conditional_position-base_position;
     if candidate<0 then raise exception 'CP7_REORDER_EVALUATE_POSITION';end if;
    end if;
    status:='COMPLETE';reason:=null;
   else reason:='CURRENT_TARGET_STOCK_OR_HORIZON_CHANGED';end if;
  elsif projected is not null then reason:=coalesce(projected->>'reason',reason);end if;
  if status<>'COMPLETE'then net:=null;lead_net:=null;analysis_at:=null;end if;
  basis:=case when point is null then'NOT_ENOUGH_DATA'when p->>'point_basis'='MANUAL'then'MANUAL'else'FORMULA'end;
  state:=case when point is null or point=0 then'NO_POINT'
   when coalesce(base_position,free)<=point then'AT_OR_BELOW'else'ABOVE'end;
  metadata:=jsonb_build_object('contract_version','cp7.fg-reorder-projection.v2','target_demand',p->'demand_provenance',
   'threshold_source',p->'source_kind','threshold_checked_at',v->'threshold_captured_at','stock_checked_at',v->'captured_at',
   'analysis_at',case when analysis_at is not null then cp7_planning.utc(analysis_at)end,
   'lead_deadline',case when bound then net->'inputs'->'lead_deadline'else'null'::jsonb end,
   'target_deadline',case when bound then net->'inputs'->'deadline'else'null'::jsonb end,
   'base_position_pcs',base_position::text,'conditional_position_pcs',conditional_position::text,
   'candidate_pcs',candidate::text,'target_pcs',kernel->'target_pcs',
   'production_base_pcs',case when bound then net->'q_base_pcs'else'null'::jsonb end,
   'production_conditional_pcs',case when bound then net->'q_conditional_pcs'else'null'::jsonb end,
   'manual_state',p->'manual_state','manual_reference',p->'manual_reference',
   'raw_WIP_credited',false,'candidate_mutes_alert',false);
  row_value:=jsonb_build_object('contract_version','cp7.fg-reorder-row.v2','target_key',k,'root_id',root,
   'size_id',p->'size_id','model_id',product->'model_id','product_id',product->'id','sku',product->'sku',
   'product_name',product->'product_name','size_code',null,'free_pcs',free::text,'sales_pcs',p->'available_total_pcs',
   'counted_days',(p->>'available_days')::integer,'sale_days',(hist->>'sale_days')::integer,
   -- Display the demand input the Native target actually used. A selected
   -- manual demand profile must not be labelled with its historical mean.
   'daily_mean',((config->>'daily_total_pcs')::numeric/nullif((config->>'counted_days')::numeric,0))::text,
   'daily_sd',config->'daily_sd','lead_days',p->'lead_days','lead_basis',p->'lead_basis',
   'lead_lots',null,'lead_groups',null,'buffer_mode',config->'mode','buffer_days',config->'buffer_days',
   'service_level',case when config->>'mode'='STATISTICAL'then config->'service_level'else'null'::jsonb end,
   'z',case when config->>'mode'='STATISTICAL'then cp7_stock_formula.z((config->>'service_level')::numeric)::text end,
   'safety_pcs',kernel->'lead_safety_pcs','formula_point',p->'formula_point_pcs',
   'manual_point',case when p->>'manual_state'='ACTIVE'then p->'point_pcs'else'null'::jsonb end,
   'manual_revision',case when p->'manual_reference'<>'null'::jsonb then(p->'manual_reference'->>'revision')::integer end,
   'point',point::text,'basis',basis,'reason',case when point is null then p->'reason'else'null'::jsonb end,
   'wip_pcs',good::text,'wip_status',status,'wip_reason',reason,'state',state,'changed_at',v->'captured_at','projection',metadata);
  if product->'is_active'='true'::jsonb then rows_out:=array_append(rows_out,row_value);end if;
 end loop;
 if(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'products')
  or(select count(*)from jsonb_each(seen))<>jsonb_array_length(v->'current_stock')then raise exception 'CP7_REORDER_EVALUATE_SCOPE';end if;
 return jsonb_build_object('contract_version','cp7.fg-reorder-evaluation.v2','captured_at',v->'captured_at',
  'query',v->'query','rows',to_jsonb(rows_out),'live_ROP_caller_changed',false,'apply_enabled',false,'production_go',false);
end $$;
