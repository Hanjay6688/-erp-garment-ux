-- Private candidate consumer. Public/default/staged callers are unchanged.
create schema cp7_model_target_consumer_v2 authorization cp7_capture;
revoke all on schema cp7_model_target_consumer_v2 from public,anon,authenticated,service_role;

create function cp7_model_target_consumer_v2.rows(c jsonb,history_rows jsonb,current_stock jsonb,hash text,context jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare s jsonb:=c->'model_target_source';identity jsonb;models jsonb;products jsonb;base_rows jsonb;
 row_value jsonb;m jsonb;resolution jsonb;projection jsonb;target jsonb;provenance jsonb;vector jsonb;
 result_rows jsonb[]:='{}';reason text;at timestamptz;business_day date;key text;selection_by_target jsonb;selection_row jsonb;
 scoped_products jsonb;physical_rows jsonb;physical_by_target jsonb;runtime_value text;
begin
 -- The original resolver retains profile validation, manual/own/analog order,
 -- exact observed PCS/day totals, UNKNOWN and the shared baseline kernel.
 base_rows:=cp7_product_analog_consumer.baseline_rows(c,history_rows,current_stock,hash,context);
 perform cp7_wip.fields(s,array['contract_version','actor_scope_id','access_epoch','business_date','policy_source',
  'engine_hash','scoped_engine_hash','history_engine_hash','producer_hash','selection','consumer_engine_hash','live_history_source_hash','rows','source_hash','known_as_of','checked_at',
  'private_prototype','caller_replaced','forecast_applied','production_go']);
 if s->>'contract_version'is distinct from'cp7.model-target-source.v2'
  or s->'private_prototype'is distinct from'true'::jsonb or s->'caller_replaced'is distinct from'false'::jsonb
  or s->'forecast_applied'is distinct from'false'::jsonb or s->'production_go'is distinct from'false'::jsonb then
  raise exception 'CP7_MODEL_CONSUMER_SOURCE_CONTRACT';end if;
 identity:=s-'source_hash'-'known_as_of'-'checked_at'-'private_prototype'-'caller_replaced'-'forecast_applied'-'production_go';
 if encode(extensions.digest(convert_to(identity::text,'UTF8'),'sha256'),'hex')is distinct from s->>'source_hash'then
  raise exception 'CP7_MODEL_CONSUMER_SOURCE_DIGEST';end if;
 at:=cp7_demand.instant(c->'captured_at');business_day:=(at at time zone'Asia/Jakarta')::date;
 if at is distinct from cp7_demand.instant(s->'known_as_of')or cp7_demand.instant(s->'checked_at')<at
  or business_day is distinct from cp7_demand.day(s->'business_date')then raise exception 'CP7_MODEL_CONSUMER_SOURCE_CLOCK';end if;
 perform cp7_demand.items(s->'rows',5000);
 select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into models from jsonb_array_elements(s->'rows')x;
 select coalesce(jsonb_object_agg((x->>'root_id')||':'||(x->>'size_id'),true),'{}')into products from jsonb_array_elements(c->'facts'->'products')x;
 if(select count(*)from jsonb_each(models))<>jsonb_array_length(s->'rows')
  or(select count(*)from jsonb_each(products))<>jsonb_array_length(c->'facts'->'products')
  or(select count(*)from jsonb_each(models))<>(select count(*)from jsonb_each(products))
  or exists(select 1 from jsonb_each(models)x where not products?x.key)then raise exception 'CP7_MODEL_CONSUMER_SOURCE_SCOPE';end if;
 -- The source must match the global captured boundary before a model can
 -- consume it. Global and single-root histories retain distinct identities.
 if s->'selection'='null'::jsonb then
  if exists(select 1 from jsonb_each(models)x where x.value->'run_id'is distinct from'null'::jsonb
   or x.value->>'reason'is distinct from'MODEL_CURRENT_ACCESS_REQUIRED')then
   raise exception 'CP7_MODEL_CONSUMER_SELECTION_BINDING';end if;
 else
  perform cp7_demand.items(s->'selection',5000);
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into selection_by_target from jsonb_array_elements(s->'selection')x;
  if jsonb_array_length(s->'selection')<>(select count(*)from jsonb_each(models))
   or jsonb_array_length(s->'selection')<>(select count(*)from jsonb_each(selection_by_target))then
   raise exception 'CP7_MODEL_CONSUMER_SELECTION_BINDING';end if;
  for m in select value from jsonb_each(models)loop
   selection_row:=selection_by_target->(m->>'target_key');
   if selection_row is null or selection_row->'run_id'is distinct from m->'run_id'
    or selection_row->'runtime'is distinct from m->'runtime'
    or selection_row->'read_method'is distinct from m->'read_method'
    or selection_row->'captured_at'is distinct from m->'captured_at'then
    raise exception 'CP7_MODEL_CONSUMER_SELECTION_BINDING';end if;
  end loop;
 end if;
 if exists(select 1 from jsonb_each(models)x where x.value->>'state'='ELIGIBLE'and x.value->>'runtime'='GLOBAL_V2')and
  (c->>'status'is distinct from'COMPLETE'or encode(extensions.digest(convert_to((c->'facts')::text,'UTF8'),'sha256'),'hex')is distinct from s->>'live_history_source_hash')then
  raise exception 'CP7_MODEL_CONSUMER_PHYSICAL_SOURCE_MISMATCH';end if;
 select coalesce(jsonb_agg(p order by p->>'id'),'[]')into scoped_products from jsonb_array_elements(c->'facts'->'products')p
  where models->((p->>'root_id')||':'||(p->>'size_id'))->>'runtime'='SCOPED_V3'
   and models->((p->>'root_id')||':'||(p->>'size_id'))->>'state'='ELIGIBLE';
 if jsonb_array_length(scoped_products)>0 then
  perform cp7_demand.items(c->'model_target_stock_references',5000);
  physical_rows:=cp7_model_target_source_v2.physical_rows(c,5000,c->'model_target_stock_references',s->>'producer_hash');
  select coalesce(jsonb_object_agg(x->>'target_key',x->'reference'->'scoped_source_hash'),'{}')into physical_by_target from jsonb_array_elements(physical_rows)x;
  if exists(select 1 from jsonb_each(models)x where x.value->>'state'='ELIGIBLE'and x.value->>'runtime'='SCOPED_V3'
   and(x.value->'history_source_hash'is distinct from x.value->'physical_source_hash'
    or x.value->'physical_source_hash'is distinct from physical_by_target->x.key))then
   raise exception 'CP7_MODEL_CONSUMER_PHYSICAL_SOURCE_MISMATCH';end if;
 end if;
 for row_value in select value from jsonb_array_elements(base_rows)loop
  key:=row_value->>'target_key';m:=models->key;target:=row_value->'target';reason:=null;projection:=null;
  if m is null or m->'target_key'is distinct from row_value->'target_key'then raise exception 'CP7_MODEL_CONSUMER_TARGET_BINDING';end if;
  perform cp7_wip.fields(m,array['target_key','run_id','runtime','read_method','state','reason','history_run_id','history_scope',
   'history_query','history_source_hash','physical_source_hash','model_source_hash','captured_at','forecast_from_date','selected_model','forecast']);
  runtime_value:=m->>'runtime';
  if m->>'state'is null or m->>'state'not in('BASELINE_REQUIRED','ELIGIBLE')or m->>'reason'is null then
   raise exception 'CP7_MODEL_CONSUMER_RUNTIME_BINDING';end if;
  if m->'run_id'='null'::jsonb then
   if m->>'state'<>'BASELINE_REQUIRED'or exists(select 1 from jsonb_each(m)x
    where x.key not in('target_key','state','reason')and x.value<>'null'::jsonb)then
    raise exception 'CP7_MODEL_CONSUMER_RUNTIME_BINDING';end if;
  else
   perform(m->>'run_id')::uuid;perform(m->>'history_run_id')::uuid;
   if runtime_value is null or runtime_value not in('GLOBAL_V2','SCOPED_V3')
    or m->>'read_method'is distinct from(case runtime_value when'GLOBAL_V2'then'erp_cp7_read_model_evaluation_v2'else'erp_cp7_read_model_evaluation_v3'end)
    or m->>'history_scope'is distinct from(case runtime_value when'GLOBAL_V2'then'GLOBAL_CURRENT_PHYSICAL_ROOTS'else'SINGLE_CURRENT_PHYSICAL_ROOT'end)
    or m->>'model_source_hash'is null or m->>'model_source_hash'!~'^[0-9a-f]{64}$'
    or m->>'history_source_hash'is null or m->>'history_source_hash'!~'^[0-9a-f]{64}$'
    or m->>'physical_source_hash'is null or m->>'physical_source_hash'!~'^[0-9a-f]{64}$'
    or cp7_demand.instant(m->'captured_at')>at then raise exception 'CP7_MODEL_CONSUMER_RUNTIME_BINDING';end if;
  end if;
  if row_value->'demand_estimate'->>'basis'='SELECTED_MANUAL_ASSUMPTION'then reason:='EXPLICIT_MANUAL_DEMAND_RETAINS_PRIORITY';
  elsif row_value->'demand_estimate'->>'basis'is distinct from'OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'then
   reason:='OWN_HISTORY_MINIMUM_REQUIRED_BEFORE_MODEL';
  elsif m->>'state'is distinct from'ELIGIBLE'then reason:=m->>'reason';
  elsif m->'history_query'is distinct from context->'query'then reason:='MODEL_HISTORY_QUERY_DIFFERS_FROM_TARGET';
  else
   if m->'forecast'->>'status'is distinct from'ELIGIBLE'
    or m->'forecast'->'method'is distinct from m->'selected_model'->'method'
    or m->'forecast'->'params'is distinct from m->'selected_model'->'params'
    or cp7_demand.instant(m->'captured_at')>at then raise exception 'CP7_MODEL_CONSUMER_VECTOR_BINDING';end if;
   vector:=jsonb_build_object('contract_version','cp7.model-target-vector.v1',
    'forecast_from_date',m->'forecast_from_date','forecasts',m->'forecast'->'forecasts');
   projection:=cp7_model_target_projection.project(target->'inputs',vector,business_day);
   if projection->'baseline'is distinct from target then raise exception 'CP7_MODEL_CONSUMER_BASELINE_CHANGED';end if;
   reason:=projection->>'reason';
  end if;
  if reason is null then raise exception 'CP7_MODEL_CONSUMER_MISSING_REASON';end if;
  resolution:=jsonb_build_object('contract_version','cp7.model-target-resolution.v2',
   'state',case when projection->>'state'='ARITHMETIC_CANDIDATE'then'MODEL_PROJECTED'else'BASELINE_RETAINED'end,
   'reason',reason,'source_hash',s->'source_hash','actor_scope_id',s->'actor_scope_id','access_epoch',s->'access_epoch',
   'run_id',m->'run_id','runtime',m->'runtime','read_method',m->'read_method',
   'history_scope',m->'history_scope','history_source_hash',m->'history_source_hash','physical_source_hash',m->'physical_source_hash','history_run_id',m->'history_run_id','history_query',m->'history_query',
   'model_source_hash',m->'model_source_hash','captured_at',m->'captured_at',
   'policy_source',s->'policy_source','engine_hash',case when runtime_value='SCOPED_V3'then s->'scoped_engine_hash'else s->'engine_hash'end,
   'global_engine_hash',s->'engine_hash','scoped_engine_hash',s->'scoped_engine_hash','history_engine_hash',s->'history_engine_hash','consumer_engine_hash',s->'consumer_engine_hash',
   'forecast_from_date',m->'forecast_from_date','selected_model',m->'selected_model',
   'forecast',case when projection->>'state'='ARITHMETIC_CANDIDATE'then m->'forecast'else'null'::jsonb end,
   'baseline_target',target,'forecast_applied',projection->>'state'='ARITHMETIC_CANDIDATE',
   'production_go',false);
  -- Coalesce SQL NULL for all baseline-only paths; never expose an unknown
  -- boolean as a false authority signal.
  resolution:=resolution||jsonb_build_object('forecast_applied',coalesce(projection->>'state'='ARITHMETIC_CANDIDATE',false));
  if resolution->>'state'='MODEL_PROJECTED'then
   target:=target||(projection->'projected')||jsonb_build_object('reason',reason,
    'model_input',resolution,'forecast_applied',true);
  end if;
  provenance:=(row_value->'demand_provenance')||jsonb_build_object('contract_version','cp7.target-demand-provenance.v3',
   'target_pcs',target->'target_pcs','reorder_point_pcs',target->'reorder_point_pcs','model',resolution);
  -- Demand estimate/own totals remain historical operands, never rewritten
  -- into average forecast values or pretended observed sales.
  result_rows:=array_append(result_rows,row_value||jsonb_build_object('target',target,
   'model_resolution',resolution,'demand_provenance',provenance));
 end loop;
 return to_jsonb(result_rows);
end $$;

alter function cp7_model_target_consumer_v2.rows(jsonb,jsonb,jsonb,text,jsonb)owner to cp7_capture;
revoke all on function cp7_model_target_consumer_v2.rows(jsonb,jsonb,jsonb,text,jsonb)from public,anon,authenticated,service_role;
