-- A warehouse-only reader must not learn model archives or activation policy.
create function cp7_model_target_source_v2.capture_for_reorder(c jsonb,p_limit integer)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare access_value jsonb;v_actor uuid;known timestamptz;checked timestamptz;targets jsonb;rows_value jsonb;
 identity jsonb;global_engine text;scoped_engine text;history_engine text;source_engine text;producer_hash text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 access_value:=cp7_stock_formula.access_now(false);v_actor:=auth.uid();
 if not exists(select 1 from unnest(array['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view'])p
  where erp.has_permission(p)is not true)then return cp7_model_target_source_v2.capture(c,p_limit);end if;
 known:=cp7_demand.instant(c->'captured_at');checked:=clock_timestamp();
 if v_actor is null or known>checked or(known at time zone'Asia/Jakarta')::date is distinct from(checked at time zone'Asia/Jakarta')::date then
  raise exception 'CP7_MODEL_TARGET_SOURCE_QUERY';end if;
 targets:=cp7_model_target_source_v2.non_stock_rows(c,p_limit);
 select coalesce(jsonb_agg(jsonb_build_object('target_key',x->'target_key','run_id',null,'runtime',null,'read_method',null,
  'state','BASELINE_REQUIRED','reason','MODEL_CURRENT_ACCESS_REQUIRED','history_run_id',null,'history_scope',null,
  'history_query',null,'history_source_hash',null,'physical_source_hash',null,'model_source_hash',null,'captured_at',null,
  'forecast_from_date',null,'selected_model',null,'forecast',null)order by x->>'target_key'collate"C"),'[]')into rows_value
 from jsonb_array_elements(targets)x;
 global_engine:=cp7_model_registry_adapter.engine();scoped_engine:=cp7_model_scoped_evaluation.engine();
 history_engine:=cp7_model_history_runtime.engine();source_engine:=cp7_model_target_source_v2.engine();producer_hash:=cp7_model_target_source_v2.producer();
 identity:=jsonb_build_object('contract_version','cp7.model-target-source.v2','actor_scope_id',v_actor,
  'access_epoch',encode(pg_catalog.sha256(convert_to(access_value::text,'UTF8')),'hex'),
  'business_date',(checked at time zone'Asia/Jakarta')::date::text,'policy_source',null,
  'engine_hash',global_engine,'scoped_engine_hash',scoped_engine,'history_engine_hash',history_engine,
  'consumer_engine_hash',source_engine,'producer_hash',producer_hash,'selection',null,
  'live_history_source_hash',null,'rows',rows_value);
 if access_value is distinct from cp7_stock_formula.access_now(false)or v_actor is distinct from auth.uid()
  or not exists(select 1 from unnest(array['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view'])p
   where erp.has_permission(p)is not true)then raise exception using errcode='42501',message='CP7_MODEL_TARGET_ACCESS_CHANGED';end if;
 checked:=clock_timestamp();
 if global_engine is distinct from cp7_model_registry_adapter.engine()or scoped_engine is distinct from cp7_model_scoped_evaluation.engine()
  or history_engine is distinct from cp7_model_history_runtime.engine()or source_engine is distinct from cp7_model_target_source_v2.engine()
  or producer_hash is distinct from cp7_model_target_source_v2.producer()
  or(known at time zone'Asia/Jakarta')::date is distinct from(checked at time zone'Asia/Jakarta')::date then
  raise exception using errcode='40001',message='CP7_MODEL_TARGET_AUTHORITY_CHANGED_DURING_CAPTURE';end if;
 return identity||jsonb_build_object('source_hash',encode(pg_catalog.sha256(convert_to(identity::text,'UTF8')),'hex'),
  'known_as_of',cp7_planning.utc(known),'checked_at',cp7_planning.utc(checked),
  'private_prototype',true,'caller_replaced',false,'forecast_applied',false,'production_go',false);
end $$;
alter function cp7_model_target_source_v2.capture_for_reorder(jsonb,integer)owner to cp7_capture;
revoke all on function cp7_model_target_source_v2.capture_for_reorder(jsonb,integer)from public,anon,authenticated,service_role;
