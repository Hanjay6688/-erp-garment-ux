-- Immutable v2 evaluations use a distinct table and request namespace from v1.
-- Policy/gate/adapter must already be installed by this opt-in stage composition.
create table cp7_model_registry_adapter.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 payload jsonb not null,query jsonb not null,history_run_id uuid not null references cp7_planning.history_runs(id),
 captured_at timestamptz not null,registry_id text not null references cp7_model_native.registry(id),
 input jsonb not null,result jsonb not null,dependency_hash text not null,
 unique(actor,request_id)
);
alter table cp7_model_registry_adapter.runs owner to cp7_capture;
alter table cp7_model_registry_adapter.runs enable row level security;
create policy no_access on cp7_model_registry_adapter.runs for all to public using(false)with check(false);
revoke all on cp7_model_registry_adapter.runs from public,anon,authenticated,service_role;
create trigger immutable_run before update or delete on cp7_model_registry_adapter.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_model_registry_adapter.current_guard(d jsonb,r jsonb,history jsonb,policy_source jsonb,p_engine text,p_checked timestamptz)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare history_current boolean;engine_current boolean;policy_current boolean;origin_current boolean;reason text;
begin
 if d->>'contract_version'is distinct from'cp7.native-model-dataset.v2'
  or r->>'contract_version'is distinct from'cp7.native-model-assessment.v2'
  or r->'source_hash'is distinct from d->'source_hash'or r->'engine_hash'is distinct from d->'engine_hash'
  or history->'run_id'is distinct from d->'history_run_id'
  or history->>'source_state'is null or history->>'source_state'not in('UNCHANGED','ARCHIVED_STALE')
  or p_checked is null or p_engine is null then raise exception 'CP7_MODEL_V2_GUARD_BINDING';end if;
 history_current:=history->>'source_state'='UNCHANGED';engine_current:=p_engine=d->>'engine_hash';
 policy_current:=coalesce(policy_source,'null'::jsonb)is not distinct from d->'policy_source';
 origin_current:=cp7_demand.day(d->'through_date')+1=(p_checked at time zone'Asia/Jakarta')::date
  and r->'activation'->>'forecast_from_date'=(p_checked at time zone'Asia/Jakarta')::date::text;
 if p_checked<cp7_demand.instant(r->'activation'->'known_as_of')then reason:='CURRENT_CLOCK_PRECEDES_EVALUATION';
 elsif not history_current then reason:='NATIVE_HISTORY_SOURCE_CHANGED';
 elsif not engine_current then reason:='MODEL_ENGINE_CHANGED';
 elsif not policy_current then reason:='ACTIVATION_POLICY_CHANGED';
 elsif not origin_current then reason:='MODEL_FORECAST_ORIGIN_NOT_CURRENT';
 elsif r->'activation'->>'state'is distinct from'ELIGIBLE'then reason:=r->'activation'->>'reason';
 end if;
 if reason is null and r->'activation'->>'state'is distinct from'ELIGIBLE'then raise exception 'CP7_MODEL_V2_MISSING_ADMISSION_REASON';end if;
 return jsonb_build_object('contract_version','cp7.native-model-current-guard.v2',
  'state',case when reason is null then'ELIGIBLE'else'BASELINE_REQUIRED'end,
  'reason',coalesce(reason,'CURRENT_NATIVE_SOURCE_POLICY_ENGINE_AND_DATED_ADMISSION'),
  'source_state',case when history_current and engine_current and policy_current and origin_current then'UNCHANGED'else'ARCHIVED_STALE'end,
  'history_unchanged',history_current,'engine_unchanged',engine_current,'policy_unchanged',policy_current,
  'forecast_origin_current',origin_current,'checked_at',cp7_planning.utc(p_checked),'forecast_applied',false,'production_go',false);
end $$;

create function cp7_model_registry_adapter.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare access_value jsonb;run cp7_model_registry_adapter.runs%rowtype;history jsonb;policy_source jsonb;
 engine text;checked timestamptz;guard jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 access_value:=cp7_private.access_now();
 select *into run from cp7_model_registry_adapter.runs r where r.id=p_run and r.actor=(access_value->>'actor')::uuid;
 if run.id is null then raise exception using errcode='42501',message='CP7_MODEL_V2_RUN_UNAVAILABLE';end if;
 history:=cp7_planning.serve_history(run.history_run_id);checked:=clock_timestamp();
 policy_source:=cp7_model_policy.source_at(checked);engine:=cp7_model_registry_adapter.engine();
 guard:=cp7_model_registry_adapter.current_guard(run.input,run.result,history,policy_source,engine,checked);
 if cp7_private.access_now()is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_V2_ACCESS_CHANGED';end if;
 if cp7_model_policy.source_at(clock_timestamp())is distinct from policy_source then raise exception 'CP7_MODEL_V2_POLICY_CHANGED_DURING_READ';end if;
 -- Immutable assessment is returned verbatim. Only the separately named current
 -- guard is refreshed; reading never rewrites history or recalculates the model.
 return jsonb_build_object('contract_version','cp7.native-model-run.v2','run_id',run.id,'request_id',run.request_id,
  'actor_scope_id',run.actor,'captured_at',cp7_planning.utc(run.captured_at),'query',run.query,
  'assessment',run.result,'current_guard',guard,'forecast_applied',false,'production_go',false);
end $$;

create function cp7_model_registry_adapter.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare access_value jsonb;q jsonb;run cp7_model_registry_adapter.runs%rowtype;d jsonb;assessment jsonb;
 history jsonb;policy_source jsonb;captured timestamptz;context jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 access_value:=cp7_private.access_now();q:=cp7_model_native.query(p_query);
 if p_request is null then raise exception 'CP7_MODEL_V2_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_private.access_now()is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_V2_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:MODEL:EVALUATION:V2:'||(access_value->>'actor')||':'||p_request::text,0));
 if cp7_private.access_now()is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_V2_ACCESS_CHANGED';end if;
 select *into run from cp7_model_registry_adapter.runs r where r.actor=(access_value->>'actor')::uuid and r.request_id=p_request;
 if found then
  if run.payload is distinct from p_query then raise exception 'CP7_MODEL_V2_REQUEST_CHANGED';end if;
  return cp7_model_registry_adapter.serve(run.id);
 end if;
 history:=cp7_planning.serve_history((q->>'history_run_id')::uuid);
 if history->>'source_state'is distinct from'UNCHANGED'then raise exception 'CP7_MODEL_V2_HISTORY_STALE';end if;
 d:=cp7_model_registry_adapter.dataset(q,(access_value->>'actor')::uuid);captured:=clock_timestamp();
 policy_source:=cp7_model_policy.source_at(captured);
 context:=jsonb_build_object('target_key',d->'target_key','size_id',d->'size_id','source_hash',d->'source_hash',
  'engine_hash',d->'engine_hash','known_as_of',cp7_planning.utc(captured),'horizon_days',q->'horizon_days',
  'forecast_from_date',(captured at time zone'Asia/Jakarta')::date::text);
 assessment:=cp7_model_registry_adapter.assess(d,context,policy_source);
 insert into cp7_model_registry_adapter.runs(actor,request_id,payload,query,history_run_id,captured_at,registry_id,input,result,dependency_hash)
 values((access_value->>'actor')::uuid,p_request,p_query,q,(q->>'history_run_id')::uuid,captured,
  d->>'registry_id',d,assessment,d->>'source_hash')returning *into run;
 if cp7_private.access_now()is distinct from access_value then raise exception using errcode='42501',message='CP7_MODEL_V2_ACCESS_CHANGED';end if;
 return cp7_model_registry_adapter.serve(run.id);
end $$;

create function public.erp_cp7_capture_model_evaluation_v2(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'set statement_timeout='8s'as $$
 select cp7_model_registry_adapter.capture(p_query,p_request)
$$;
create function public.erp_cp7_read_model_evaluation_v2(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'set statement_timeout='8s'as $$
 select cp7_model_registry_adapter.serve(p_run)
$$;
alter function cp7_model_registry_adapter.current_guard(jsonb,jsonb,jsonb,jsonb,text,timestamp with time zone)owner to cp7_capture;
alter function cp7_model_registry_adapter.serve(uuid)owner to cp7_capture;
alter function cp7_model_registry_adapter.capture(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_capture_model_evaluation_v2(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_model_evaluation_v2(uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_model_registry_adapter from public,anon,authenticated,service_role;
revoke all on function public.erp_cp7_capture_model_evaluation_v2(jsonb,uuid),public.erp_cp7_read_model_evaluation_v2(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_model_evaluation_v2(jsonb,uuid),public.erp_cp7_read_model_evaluation_v2(uuid)to authenticated;
