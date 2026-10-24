-- Private prototype: collect current server-owned model references once per
-- source, not a full global history scan for every product. No caller replaced.
create schema cp7_model_target_source authorization cp7_capture;
revoke all on schema cp7_model_target_source from public,anon,authenticated,service_role;

create function cp7_model_target_source.engine()returns text
language sql stable security invoker set search_path=''as $$
 select md5(string_agg(pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text))
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_model_target_source'
$$;

create function cp7_model_target_source.selection(p_targets text[],p_actor uuid,p_at timestamptz)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(jsonb_build_object('target_key',t.target,'run_id',r.id)order by t.target collate"C"),'[]')
 from unnest(p_targets)t(target)left join lateral(
  select x.id from cp7_model_registry_adapter.runs x
  where x.actor=p_actor and x.query->>'target_key'=t.target and x.captured_at<=p_at
  order by x.captured_at desc,x.id desc limit 1
 )r on true
$$;

create function cp7_model_target_source.capture(p_targets text[],p_known timestamptz)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;v_actor uuid;selected jsonb;entry jsonb;run cp7_model_registry_adapter.runs%rowtype;
 history cp7_planning.history_runs%rowtype;live jsonb;after_live jsonb;live_hash text;engine text;
 policy jsonb;source_engine text;checked timestamptz;guard jsonb;rows jsonb[]:='{}';row_value jsonb;source jsonb;hash text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();v_actor:=(a->>'actor')::uuid;checked:=clock_timestamp();
 if p_known is null or p_known>checked or p_targets is null or cardinality(p_targets)>5000
  or exists(select 1 from unnest(p_targets)t where t is null or t!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
  or cardinality(p_targets)<>(select count(distinct t)from unnest(p_targets)t)then raise exception 'CP7_MODEL_TARGET_SOURCE_QUERY';end if;
 selected:=cp7_model_target_source.selection(p_targets,v_actor,p_known);
 if selected is distinct from cp7_model_target_source.selection(p_targets,v_actor,checked)then
  raise exception 'CP7_MODEL_TARGET_NEWER_EVALUATION_REQUIRES_NEW_CAPTURE';end if;
 policy:=cp7_model_policy.source_at(checked);engine:=cp7_model_registry_adapter.engine();source_engine:=cp7_model_target_source.engine();
 -- Match the exact existing Native v2 reader: a 1000-product history source.
 -- An INCOMPLETE source retires the model; it is never treated as empty/zero.
 -- Dense Native history capture/consumption requires a separately qualified
 -- bounded adapter and is not claimed by this private prototype.
 if exists(select 1 from jsonb_array_elements(selected)x where x->'run_id'<>'null'::jsonb)then
  live:=cp7_planning.history_source();
  live_hash:=encode(extensions.digest(convert_to((live->'facts')::text,'UTF8'),'sha256'),'hex');
 end if;
 for entry in select value from jsonb_array_elements(selected)loop
  row_value:=jsonb_build_object('target_key',entry->'target_key','run_id',entry->'run_id',
   'state','BASELINE_REQUIRED','reason','NO_OWN_MODEL_EVALUATION','history_run_id',null,'history_query',null,
   'model_source_hash',null,'captured_at',null,'forecast_from_date',null,'selected_model',null,'forecast',null);
  if entry->'run_id'<>'null'::jsonb then
   select *into run from cp7_model_registry_adapter.runs r where r.id=(entry->>'run_id')::uuid and r.actor=v_actor;
   select *into history from cp7_planning.history_runs h where h.id=run.history_run_id and h.actor=v_actor;
   if run.id is null or history.id is null or run.query->'target_key'is distinct from entry->'target_key'
    or run.input->'history_run_id'is distinct from to_jsonb(history.id)
    or run.input->>'history_source_hash'is distinct from history.dependency_hash
    or run.dependency_hash is distinct from run.input->>'source_hash'then raise exception 'CP7_MODEL_TARGET_STORED_BINDING';end if;
   guard:=cp7_model_registry_adapter.current_guard(run.input,run.result,
    jsonb_build_object('run_id',history.id,'source_state',case when live->>'status'='COMPLETE'
     and live_hash=history.dependency_hash then'UNCHANGED'else'ARCHIVED_STALE'end),policy,engine,checked);
   row_value:=row_value||jsonb_build_object('state',guard->'state','reason',guard->'reason',
    'history_run_id',history.id,'history_query',history.query,'model_source_hash',run.dependency_hash,
    'captured_at',cp7_planning.utc(run.captured_at),'forecast_from_date',run.result->'activation'->'forecast_from_date',
    'selected_model',case when guard->>'state'='ELIGIBLE'then run.result->'activation'->'selected_model'else'null'::jsonb end,
    'forecast',case when guard->>'state'='ELIGIBLE'then run.result->'activation'->'forecast'else'null'::jsonb end);
  end if;
  rows:=array_append(rows,row_value);
 end loop;
 -- Re-read both source and current authority before returning. Clock values
 -- are not hashed into source identity, so identical state can be reused.
 if live is not null then
  after_live:=cp7_planning.history_source();
  if after_live->'status'is distinct from live->'status'or after_live->'facts'is distinct from live->'facts'then
   raise exception 'CP7_MODEL_TARGET_HISTORY_CHANGED_DURING_CAPTURE';end if;
 end if;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_TARGET_ACCESS_CHANGED';end if;
 checked:=clock_timestamp();
 if selected is distinct from cp7_model_target_source.selection(p_targets,v_actor,checked)
  or policy is distinct from cp7_model_policy.source_at(checked)or engine is distinct from cp7_model_registry_adapter.engine()
  or source_engine is distinct from cp7_model_target_source.engine()
  or(p_known at time zone'Asia/Jakarta')::date<>(checked at time zone'Asia/Jakarta')::date then
  raise exception 'CP7_MODEL_TARGET_AUTHORITY_CHANGED_DURING_CAPTURE';end if;
 source:=jsonb_build_object('contract_version','cp7.model-target-source.v1','actor_scope_id',v_actor,
  'access_epoch',encode(extensions.digest(convert_to(a::text,'UTF8'),'sha256'),'hex'),
  'business_date',(checked at time zone'Asia/Jakarta')::date::text,'policy_source',policy,'engine_hash',engine,'consumer_engine_hash',source_engine,
  'live_history_source_hash',live_hash,'rows',to_jsonb(rows));
 hash:=encode(extensions.digest(convert_to(source::text,'UTF8'),'sha256'),'hex');
 return source||jsonb_build_object('source_hash',hash,'known_as_of',cp7_planning.utc(p_known),
  'checked_at',cp7_planning.utc(checked),'private_prototype',true,'caller_replaced',false,
  'forecast_applied',false,'production_go',false);
end $$;

alter function cp7_model_target_source.engine()owner to cp7_capture;
alter function cp7_model_target_source.selection(text[],uuid,timestamp with time zone)owner to cp7_capture;
alter function cp7_model_target_source.capture(text[],timestamp with time zone)owner to cp7_capture;
revoke all on all functions in schema cp7_model_target_source from public,anon,authenticated,service_role;
