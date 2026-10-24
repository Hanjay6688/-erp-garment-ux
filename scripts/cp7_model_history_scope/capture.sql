create function cp7_model_history_scope.capture(p_target text,p_query jsonb,p_with_inputs boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;q jsonb;summary jsonb;result jsonb;producer text;hash text;
begin
 if p_target is null or p_target!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or p_with_inputs is null then raise exception 'CP7_MODEL_HISTORY_SCOPE_QUERY';end if;
 q:=cp7_planning.history_query(p_query);
 if(q->>'through_date')::date-(q->>'from_date')::date>365 then raise exception 'CP7_MODEL_HISTORY_SCOPE_QUERY';end if;
 c:=cp7_model_history_scope.raw(split_part(p_target,':',1)::uuid);
 select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')into producer
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where p.prokind='f'and(n.nspname in('cp7_model_history_scope','cp7_demand','cp7_wip','cp7_history_reference')
  or n.nspname='cp7_planning'and p.proname in('history_query','history_events','history_availability','utc')
  or n.nspname='cp7_reorder_inputs'and p.proname in('current_stock','stock_summary')
  or n.nspname='cp7_analysis_stage'and p.proname in('history_stock','bounds'));
 c:=c||jsonb_build_object('target_key',p_target,'producer_hash',producer,
  'stock_reference',cp7_history_reference.stock_digest(c->'facts'->'products',(c->>'captured_at')::timestamptz));
 hash:=cp7_model_history_scope.identity(c);
 if p_with_inputs then
  if c->>'status'='INCOMPLETE'then summary:=cp7_reorder_inputs.stock_summary(c->'facts'->'products',(c->>'captured_at')::timestamptz,q);end if;
  result:=cp7_model_history_scope.build(c,q,summary);
 end if;
 return jsonb_build_object('contract_version','cp7.scoped-history-inputs.v1','scope','SINGLE_CURRENT_PHYSICAL_ROOT',
  'target_key',p_target,'query',q,'captured_at',c->'captured_at','source_hash',hash,'producer_hash',producer,
  'raw_capture_status',c->'status','raw_status_overridden',false,'source',c,'result',result,
  'actual_capture_persisted',false,'model_caller_integrated',false,'production_go',false);
end $$;
