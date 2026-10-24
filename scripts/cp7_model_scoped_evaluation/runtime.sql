-- Scoped immutable evaluations retain the reviewed v2 policy/assessment kernel.
-- Separate v3 table/FK/request namespace; no old history or model is rewritten.
create schema cp7_model_scoped_evaluation authorization cp7_capture;
revoke all on schema cp7_model_scoped_evaluation from public,anon,authenticated,service_role;
create table cp7_model_scoped_evaluation.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 payload jsonb not null,query jsonb not null,
 history_run_id uuid not null references cp7_model_history_runtime.runs(id),
 captured_at timestamptz not null,registry_id text not null references cp7_model_native.registry(id),
 input jsonb not null,result jsonb not null,dependency_hash text not null,
 unique(actor,request_id)
);
alter table cp7_model_scoped_evaluation.runs owner to cp7_capture;
alter table cp7_model_scoped_evaluation.runs enable row level security;
create policy no_access on cp7_model_scoped_evaluation.runs for all to public using(false)with check(false);
revoke all on cp7_model_scoped_evaluation.runs from public,anon,authenticated,service_role;
create trigger immutable_run before update or delete on cp7_model_scoped_evaluation.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_model_scoped_evaluation.engine()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select md5(cp7_model_scoped_dataset.engine()||':'||
  string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text))
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.prokind='f'and
 (n.nspname='cp7_model_scoped_evaluation'or n.nspname='public'and
  p.proname in('erp_cp7_capture_model_evaluation_v3','erp_cp7_read_model_evaluation_v3'))
$$;

create function cp7_model_scoped_evaluation.dataset(q jsonb,p_actor uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare d jsonb;engine text;
begin
 engine:=cp7_model_scoped_evaluation.engine();
 d:=cp7_model_scoped_dataset.dataset(q,p_actor);
 if d->>'contract_version'is distinct from'cp7.native-model-dataset.v2'
  or d->>'source_hash'is distinct from encode(pg_catalog.sha256(convert_to((d-'source_hash')::text,'UTF8')),'hex')
  or d->>'engine_hash'is distinct from cp7_model_scoped_dataset.engine()
  or engine is distinct from cp7_model_scoped_evaluation.engine()then
  raise exception 'CP7_SCOPED_EVALUATION_DATASET_BINDING';end if;
 -- Verify the original bound dataset before extending its engine identity.
 -- The same v2 assessment contract consumes unchanged observations and policy.
 d:=(d-'source_hash')||jsonb_build_object('engine_hash',engine);
 return d||jsonb_build_object('source_hash',encode(pg_catalog.sha256(convert_to(d::text,'UTF8')),'hex'));
end $$;

create function cp7_model_scoped_evaluation.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;run cp7_model_scoped_evaluation.runs%rowtype;history jsonb;after_history jsonb;
 policy_source jsonb;engine text;checked timestamptz;guard jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();
 select *into run from cp7_model_scoped_evaluation.runs r where r.id=p_run and r.actor=(a->>'actor')::uuid;
 if run.id is null then raise exception using errcode='42501',message='CP7_SCOPED_EVALUATION_RUN_UNAVAILABLE';end if;
 if run.query is distinct from cp7_model_native.query(run.payload)
  or run.input->'query'is distinct from run.query
  or run.input->>'history_run_id'is distinct from run.history_run_id::text
  or run.input->>'registry_id'is distinct from run.registry_id
  or run.input->>'source_hash'is distinct from run.dependency_hash
  or run.dependency_hash is distinct from encode(pg_catalog.sha256(convert_to((run.input-'source_hash')::text,'UTF8')),'hex')then
  raise exception 'CP7_SCOPED_EVALUATION_STORED_BINDING';end if;
 history:=cp7_model_history_runtime.serve(run.history_run_id);checked:=clock_timestamp();
 policy_source:=cp7_model_policy.source_at(checked);engine:=cp7_model_scoped_evaluation.engine();
 guard:=cp7_model_registry_adapter.current_guard(run.input,run.result,
  jsonb_build_object('run_id',history->'run_id','source_state',history->'current_guard'->'source_state'),
  policy_source,engine,checked);
 after_history:=cp7_model_history_runtime.serve(run.history_run_id);
 if after_history-'current_guard'is distinct from history-'current_guard'
  or (after_history->'current_guard')-'checked_at'is distinct from (history->'current_guard')-'checked_at'
  or cp7_model_scoped_evaluation.engine()is distinct from engine
  or cp7_model_policy.source_at(clock_timestamp())is distinct from policy_source
  or(clock_timestamp()at time zone'Asia/Jakarta')::date is distinct from(checked at time zone'Asia/Jakarta')::date then
  raise exception using errcode='40001',message='CP7_SCOPED_EVALUATION_CHANGED_DURING_READ';end if;
 if cp7_private.access_now()is distinct from a then
  raise exception using errcode='42501',message='CP7_SCOPED_EVALUATION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.scoped-model-run.v3','run_id',run.id,'request_id',run.request_id,
  'actor_scope_id',run.actor,'captured_at',cp7_planning.utc(run.captured_at),'query',run.query,
  'assessment',run.result,'current_guard',guard,'history_scope','SINGLE_CURRENT_PHYSICAL_ROOT',
  'forecast_applied',false,'production_go',false);
end $$;

create function cp7_model_scoped_evaluation.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;run cp7_model_scoped_evaluation.runs%rowtype;d jsonb;assessment jsonb;
 history jsonb;after_history jsonb;policy_source jsonb;captured timestamptz;context jsonb;answer jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();q:=cp7_model_native.query(p_query);
 if p_request is null then raise exception 'CP7_SCOPED_EVALUATION_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_private.access_now()is distinct from a then
  raise exception using errcode='42501',message='CP7_SCOPED_EVALUATION_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:MODEL:EVALUATION:V3:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_private.access_now()is distinct from a then
  raise exception using errcode='42501',message='CP7_SCOPED_EVALUATION_ACCESS_CHANGED';end if;
 select *into run from cp7_model_scoped_evaluation.runs r where r.actor=(a->>'actor')::uuid and r.request_id=p_request;
 if found then
  if run.payload is distinct from p_query then raise exception 'CP7_SCOPED_EVALUATION_REQUEST_CHANGED';end if;
  return cp7_model_scoped_evaluation.serve(run.id);
 end if;
 history:=cp7_model_history_runtime.serve((q->>'history_run_id')::uuid);
 if history->'current_guard'->>'source_state'is distinct from'UNCHANGED'then
  raise exception 'CP7_SCOPED_EVALUATION_HISTORY_STALE';end if;
 d:=cp7_model_scoped_evaluation.dataset(q,(a->>'actor')::uuid);captured:=clock_timestamp();
 policy_source:=cp7_model_policy.source_at(captured);
 context:=jsonb_build_object('target_key',d->'target_key','size_id',d->'size_id','source_hash',d->'source_hash',
  'engine_hash',d->'engine_hash','known_as_of',cp7_planning.utc(captured),'horizon_days',q->'horizon_days',
  'forecast_from_date',(captured at time zone'Asia/Jakarta')::date::text);
 assessment:=cp7_model_registry_adapter.assess(d,context,policy_source);
 insert into cp7_model_scoped_evaluation.runs(actor,request_id,payload,query,history_run_id,captured_at,registry_id,input,result,dependency_hash)
 values((a->>'actor')::uuid,p_request,p_query,q,(q->>'history_run_id')::uuid,captured,
  d->>'registry_id',d,assessment,d->>'source_hash')returning *into run;
 answer:=cp7_model_scoped_evaluation.serve(run.id);
 after_history:=cp7_model_history_runtime.serve(run.history_run_id);
 if after_history->'current_guard'->>'source_state'is distinct from'UNCHANGED'
  or after_history-'current_guard'is distinct from history-'current_guard'
  or d->>'engine_hash'is distinct from cp7_model_scoped_evaluation.engine()
  or cp7_model_policy.source_at(clock_timestamp())is distinct from policy_source
  or(clock_timestamp()at time zone'Asia/Jakarta')::date is distinct from(captured at time zone'Asia/Jakarta')::date then
  raise exception using errcode='40001',message='CP7_SCOPED_EVALUATION_SOURCE_CHANGED';end if;
 if cp7_private.access_now()is distinct from a then
  raise exception using errcode='42501',message='CP7_SCOPED_EVALUATION_ACCESS_CHANGED';end if;
 return answer;
end $$;

create function public.erp_cp7_capture_model_evaluation_v3(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'set statement_timeout='8s'as $$
 select cp7_model_scoped_evaluation.capture(p_query,p_request)
$$;
create function public.erp_cp7_read_model_evaluation_v3(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'set statement_timeout='8s'as $$
 select cp7_model_scoped_evaluation.serve(p_run)
$$;
alter function cp7_model_scoped_evaluation.engine()owner to cp7_capture;
alter function cp7_model_scoped_evaluation.dataset(jsonb,uuid)owner to cp7_capture;
alter function cp7_model_scoped_evaluation.serve(uuid)owner to cp7_capture;
alter function cp7_model_scoped_evaluation.capture(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_capture_model_evaluation_v3(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_model_evaluation_v3(uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_model_scoped_evaluation from public,anon,authenticated,service_role;
revoke all on function public.erp_cp7_capture_model_evaluation_v3(jsonb,uuid),public.erp_cp7_read_model_evaluation_v3(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_model_evaluation_v3(jsonb,uuid),public.erp_cp7_read_model_evaluation_v3(uuid)to authenticated;
