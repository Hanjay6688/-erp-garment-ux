create function cp7_model_scoped_dataset.engine()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select md5(cp7_model_registry_adapter.engine()||':'||cp7_model_history_runtime.engine()||':'||
  string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text))
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='cp7_model_scoped_dataset'and p.prokind='f'
$$;

create function cp7_model_scoped_dataset.dataset(q jsonb,p_actor uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;before_history jsonb;after_history jsonb;d jsonb;policy_source jsonb;registry jsonb;
 engine text;answer jsonb;
begin
 a:=cp7_private.access_now();q:=cp7_model_native.query(q);
 if p_actor is distinct from(a->>'actor')::uuid then
  raise exception using errcode='42501',message='CP7_SCOPED_MODEL_ACTOR_CHANGED';end if;
 before_history:=cp7_model_history_runtime.serve((q->>'history_run_id')::uuid);
 if before_history->'current_guard'->>'source_state'is distinct from'UNCHANGED'then
  raise exception 'CP7_SCOPED_MODEL_HISTORY_STALE';end if;
 engine:=cp7_model_scoped_dataset.engine();
 d:=cp7_model_scoped_dataset.native_dataset(q,p_actor);
 policy_source:=cp7_model_policy.source_at(cp7_demand.instant(d->'known_as_of'));
 if policy_source is not null then
  select jsonb_build_object('id',r.id,'registered_at',cp7_planning.utc(r.registered_at),'configuration',r.configuration)
   into registry from cp7_model_native.registry r where r.id=policy_source->'policy'->>'registry_id';
  if registry is null then raise exception 'CP7_SCOPED_MODEL_POLICY_REGISTRY_UNAVAILABLE';end if;
 end if;
 -- Reuse the reviewed policy/assessment adapter. Only the source of immutable
 -- observations changes; there is no new policy, forecast or promotion rule.
 answer:=cp7_model_registry_adapter.bind(d,policy_source,registry,engine);
 after_history:=cp7_model_history_runtime.serve((q->>'history_run_id')::uuid);
 if after_history->'current_guard'->>'source_state'is distinct from'UNCHANGED'
  or after_history-'current_guard'is distinct from before_history-'current_guard'
  or engine is distinct from cp7_model_scoped_dataset.engine()then
  raise exception using errcode='40001',message='CP7_SCOPED_MODEL_SOURCE_CHANGED';end if;
 if cp7_private.access_now()is distinct from a then
  raise exception using errcode='42501',message='CP7_SCOPED_MODEL_ACCESS_CHANGED';end if;
 return answer;
end $$;

alter function cp7_model_scoped_dataset.native_dataset(jsonb,uuid)owner to cp7_capture;
alter function cp7_model_scoped_dataset.engine()owner to cp7_capture;
alter function cp7_model_scoped_dataset.dataset(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_model_scoped_dataset from public,anon,authenticated,service_role;
