-- Private source with explicit evaluation namespaces and batched physical facts.
create function cp7_model_target_source_v2.producer()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(pg_catalog.sha256(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8')),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where p.prokind='f'and(n.nspname in('cp7_model_history_scope','cp7_demand','cp7_wip','cp7_history_reference')
  or n.nspname='cp7_planning'and p.proname in('history_query','history_events','history_availability','utc')
  or n.nspname='cp7_reorder_inputs'and p.proname in('current_stock','stock_summary')
  or n.nspname='cp7_analysis_stage'and p.proname in('history_stock','bounds'))
$$;

create function cp7_model_target_source_v2.engine()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(pg_catalog.sha256(convert_to(cp7_model_target_source.engine()||':'||
  string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8')),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.prokind='f'and
  n.nspname in('cp7_model_target_source_v2','cp7_model_evaluation_selection','cp7_model_target_binding','cp7_model_target_consumer_v2')
$$;

create function cp7_model_target_source_v2.capture(c jsonb,p_limit integer)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare access_value jsonb;v_actor uuid;known timestamptz;checked timestamptz;all_keys text[];scoped_keys text[];global_keys text[];
 selected jsonb;non_stock jsonb;selected_products jsonb;physical_rows jsonb;physical_by_target jsonb;
 live jsonb;live_products jsonb;live_rows jsonb;live_by_target jsonb;legacy_source jsonb;legacy_after jsonb;legacy_by_target jsonb;
 policy_value jsonb;global_engine text;scoped_engine text;history_engine text;source_engine text;producer_hash text;
 entry jsonb;row_value jsonb;guard jsonb;stored_model cp7_model_scoped_evaluation.runs%rowtype;
 stored_history cp7_model_history_runtime.runs%rowtype;legacy_history cp7_planning.history_runs%rowtype;
 source_state text;rows_out jsonb[]:='{}';identity jsonb;source_hash text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 access_value:=cp7_private.access_now();v_actor:=(access_value->>'actor')::uuid;
 known:=cp7_demand.instant(c->'captured_at');checked:=clock_timestamp();
 if known>checked or(known at time zone'Asia/Jakarta')::date is distinct from(checked at time zone'Asia/Jakarta')::date then
  raise exception 'CP7_MODEL_TARGET_SOURCE_QUERY';end if;
 non_stock:=cp7_model_target_source_v2.non_stock_rows(c,p_limit);
 select coalesce(array_agg(x->>'target_key'order by x->>'target_key'collate"C"),array[]::text[])into all_keys from jsonb_array_elements(non_stock)x;
 selected:=cp7_model_evaluation_selection.latest(all_keys,v_actor,known);
 if selected is distinct from cp7_model_evaluation_selection.latest(all_keys,v_actor,checked)then
  raise exception using errcode='40001',message='CP7_MODEL_TARGET_NEWER_EVALUATION_REQUIRES_NEW_CAPTURE';end if;
 select coalesce(array_agg(x->>'target_key'),array[]::text[])into scoped_keys from jsonb_array_elements(selected)x where x->>'runtime'='SCOPED_V3';
 select coalesce(array_agg(x->>'target_key'),array[]::text[])into global_keys from jsonb_array_elements(selected)x where x->>'runtime'='GLOBAL_V2';
 policy_value:=cp7_model_policy.source_at(checked);global_engine:=cp7_model_registry_adapter.engine();
 scoped_engine:=cp7_model_scoped_evaluation.engine();history_engine:=cp7_model_history_runtime.engine();
 source_engine:=cp7_model_target_source_v2.engine();producer_hash:=cp7_model_target_source_v2.producer();
 if cardinality(global_keys)>0 then
  legacy_source:=cp7_model_target_source.capture(global_keys,known);
  if legacy_source->>'actor_scope_id'is distinct from v_actor::text or legacy_source->'policy_source'is distinct from coalesce(policy_value,'null'::jsonb)
   or legacy_source->>'engine_hash'is distinct from global_engine then raise exception 'CP7_MODEL_TARGET_V2_PARENT_BINDING';end if;
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into legacy_by_target from jsonb_array_elements(legacy_source->'rows')x;
 end if;
 if cardinality(scoped_keys)>0 then
  select coalesce(jsonb_agg(p order by p->>'id'),'[]')into selected_products from jsonb_array_elements(c->'facts'->'products')p
   where(p->>'root_id')||':'||(p->>'size_id')=any(scoped_keys);
  physical_rows:=cp7_model_target_source_v2.physical_rows(c,p_limit,
   cp7_model_target_source_v2.stock_digests(selected_products,known),producer_hash);
  select coalesce(jsonb_object_agg(x->>'target_key',x->'reference'),'{}')into physical_by_target from jsonb_array_elements(physical_rows)x;
 end if;
 for entry in select value from jsonb_array_elements(selected)loop
  row_value:=jsonb_build_object('target_key',entry->'target_key','run_id',entry->'run_id',
   'runtime',entry->'runtime','read_method',entry->'read_method','state','BASELINE_REQUIRED','reason','NO_OWN_MODEL_EVALUATION',
   'history_run_id',null,'history_scope',null,'history_query',null,'history_source_hash',null,'physical_source_hash',null,
   'model_source_hash',null,'captured_at',null,'forecast_from_date',null,'selected_model',null,'forecast',null);
  if entry->>'runtime'='GLOBAL_V2'then
   if not legacy_by_target?(entry->>'target_key')then raise exception 'CP7_MODEL_TARGET_V2_PARENT_BINDING';end if;
   row_value:=row_value||(legacy_by_target->(entry->>'target_key'));
   if row_value->'run_id'is distinct from entry->'run_id'or row_value->'captured_at'is distinct from entry->'captured_at'then
    raise exception 'CP7_MODEL_TARGET_V2_PARENT_BINDING';end if;
   select *into legacy_history from cp7_planning.history_runs h where h.id=(row_value->>'history_run_id')::uuid and h.actor=v_actor;
   if legacy_history.id is null or legacy_history.query is distinct from row_value->'history_query'then
    raise exception 'CP7_MODEL_TARGET_V2_PARENT_BINDING';end if;
   row_value:=row_value||jsonb_build_object('history_scope','GLOBAL_CURRENT_PHYSICAL_ROOTS',
    'history_source_hash',legacy_history.dependency_hash,'physical_source_hash',legacy_source->'live_history_source_hash');
  elsif entry->>'runtime'='SCOPED_V3'then
   select *into stored_model from cp7_model_scoped_evaluation.runs r where r.id=(entry->>'run_id')::uuid and r.actor=v_actor;
   select *into stored_history from cp7_model_history_runtime.runs h where h.id=stored_model.history_run_id and h.actor=v_actor;
   if stored_model.id is null or stored_history.id is null
    or stored_model.query is distinct from cp7_model_native.query(stored_model.payload)
    or stored_model.query->'target_key'is distinct from entry->'target_key'
    or to_jsonb(cp7_planning.utc(stored_model.captured_at))is distinct from entry->'captured_at'
    or stored_model.input->'query'is distinct from stored_model.query
    or stored_model.input->>'history_run_id'is distinct from stored_model.history_run_id::text
    or stored_model.input->>'registry_id'is distinct from stored_model.registry_id
    or stored_model.input->>'history_source_hash'is distinct from stored_history.dependency_hash
    or stored_model.input->>'source_hash'is distinct from stored_model.dependency_hash
    or stored_model.dependency_hash is distinct from encode(pg_catalog.sha256(convert_to((stored_model.input-'source_hash')::text,'UTF8')),'hex')then
    raise exception 'CP7_SCOPED_EVALUATION_STORED_BINDING';end if;
   if stored_history.source->>'source_hash'is distinct from stored_history.dependency_hash
    or stored_history.source->'query'is distinct from stored_history.query-'target_key'
    or stored_history.source->'target_key'is distinct from stored_history.query->'target_key'
    or stored_history.query->'target_key'is distinct from entry->'target_key'
    or stored_history.result->>'source_hash'is distinct from stored_history.dependency_hash
    or stored_history.result->'target_key'is distinct from stored_history.query->'target_key'
    or stored_history.result->'captured_at'is distinct from stored_history.source->'captured_at'
    or stored_history.result->>'scope'is distinct from'SINGLE_CURRENT_PHYSICAL_ROOT'
    or cp7_model_history_scope.identity(stored_history.source->'source')is distinct from stored_history.dependency_hash then
    raise exception 'CP7_MODEL_HISTORY_STORED_BINDING';end if;
   if physical_by_target->(entry->>'target_key')is null then raise exception 'CP7_MODEL_TARGET_BINDING_TARGET_UNAVAILABLE';end if;
   source_state:=case when physical_by_target->(entry->>'target_key')->>'scoped_source_hash'=stored_history.dependency_hash
    and stored_history.engine_hash=history_engine then'UNCHANGED'else'ARCHIVED_STALE'end;
   guard:=cp7_model_registry_adapter.current_guard(stored_model.input,stored_model.result,
    jsonb_build_object('run_id',stored_history.id,'source_state',source_state),policy_value,scoped_engine,checked);
   row_value:=row_value||jsonb_build_object('state',guard->'state','reason',guard->'reason',
    'history_run_id',stored_history.id,'history_scope','SINGLE_CURRENT_PHYSICAL_ROOT','history_query',stored_history.query-'target_key',
    'history_source_hash',stored_history.dependency_hash,'physical_source_hash',physical_by_target->(entry->>'target_key')->'scoped_source_hash',
    'model_source_hash',stored_model.dependency_hash,'captured_at',cp7_planning.utc(stored_model.captured_at),
    'forecast_from_date',stored_model.result->'activation'->'forecast_from_date',
    'selected_model',case when guard->>'state'='ELIGIBLE'then stored_model.result->'activation'->'selected_model'else'null'::jsonb end,
    'forecast',case when guard->>'state'='ELIGIBLE'then stored_model.result->'activation'->'forecast'else'null'::jsonb end);
  elsif entry->'run_id'is distinct from'null'::jsonb then raise exception 'CP7_MODEL_SELECTION_RUNTIME';end if;
  rows_out:=array_append(rows_out,row_value);
 end loop;
 if cardinality(scoped_keys)>0 then
  live:=cp7_reorder_inputs.capture_history(p_limit);
  select coalesce(jsonb_agg(p order by p->>'id'),'[]')into live_products from jsonb_array_elements(live->'facts'->'products')p
   where(p->>'root_id')||':'||(p->>'size_id')=any(scoped_keys);
  if jsonb_array_length(live_products)<>cardinality(scoped_keys)then
   raise exception using errcode='40001',message='CP7_MODEL_TARGET_PHYSICAL_SOURCE_CHANGED_DURING_CAPTURE';end if;
  live_rows:=cp7_model_target_source_v2.physical_rows(live,p_limit,
   cp7_model_target_source_v2.stock_digests(live_products,(live->>'captured_at')::timestamptz),producer_hash);
  select coalesce(jsonb_object_agg(x->>'target_key',x->'reference'->'scoped_source_hash'),'{}')into live_by_target from jsonb_array_elements(live_rows)x;
  if live_by_target is distinct from(select coalesce(jsonb_object_agg(x->>'target_key',x->'reference'->'scoped_source_hash'),'{}')from jsonb_array_elements(physical_rows)x)then
   raise exception using errcode='40001',message='CP7_MODEL_TARGET_PHYSICAL_SOURCE_CHANGED_DURING_CAPTURE';end if;
  if legacy_source is not null then
   legacy_after:=cp7_model_target_source.capture(global_keys,known);
   if legacy_after->'source_hash'is distinct from legacy_source->'source_hash'then
    raise exception using errcode='40001',message='CP7_MODEL_TARGET_GLOBAL_SOURCE_CHANGED_DURING_CAPTURE';end if;
  end if;
 end if;
 if cp7_private.access_now()is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_TARGET_ACCESS_CHANGED';end if;
 checked:=clock_timestamp();
 if selected is distinct from cp7_model_evaluation_selection.latest(all_keys,v_actor,checked)
  or policy_value is distinct from cp7_model_policy.source_at(checked)
  or global_engine is distinct from cp7_model_registry_adapter.engine()
  or scoped_engine is distinct from cp7_model_scoped_evaluation.engine()
  or history_engine is distinct from cp7_model_history_runtime.engine()
  or source_engine is distinct from cp7_model_target_source_v2.engine()
  or producer_hash is distinct from cp7_model_target_source_v2.producer()
  or(known at time zone'Asia/Jakarta')::date is distinct from(checked at time zone'Asia/Jakarta')::date then
  raise exception using errcode='40001',message='CP7_MODEL_TARGET_AUTHORITY_CHANGED_DURING_CAPTURE';end if;
 identity:=jsonb_build_object('contract_version','cp7.model-target-source.v2','actor_scope_id',v_actor,
  'access_epoch',encode(pg_catalog.sha256(convert_to(access_value::text,'UTF8')),'hex'),
  'business_date',(checked at time zone'Asia/Jakarta')::date::text,'policy_source',policy_value,
  'engine_hash',global_engine,'scoped_engine_hash',scoped_engine,'history_engine_hash',history_engine,
  'consumer_engine_hash',source_engine,'producer_hash',producer_hash,'selection',selected,
  'live_history_source_hash',legacy_source->'live_history_source_hash','rows',to_jsonb(rows_out));
 source_hash:=encode(pg_catalog.sha256(convert_to(identity::text,'UTF8')),'hex');
 return identity||jsonb_build_object('source_hash',source_hash,'known_as_of',cp7_planning.utc(known),
  'checked_at',cp7_planning.utc(checked),'private_prototype',true,'caller_replaced',false,'forecast_applied',false,'production_go',false);
end $$;
alter function cp7_model_target_source_v2.producer()owner to cp7_capture;
alter function cp7_model_target_source_v2.engine()owner to cp7_capture;
alter function cp7_model_target_source_v2.capture(jsonb,integer)owner to cp7_capture;
revoke all on function cp7_model_target_source_v2.producer(),cp7_model_target_source_v2.engine(),cp7_model_target_source_v2.capture(jsonb,integer)from public,anon,authenticated,service_role;
