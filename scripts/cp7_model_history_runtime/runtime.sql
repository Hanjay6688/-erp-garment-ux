-- Opt-in candidate. The scoped source must be installed separately; existing
-- global history/model tables, public callers and default bundle are unchanged.
create schema cp7_model_history_runtime authorization cp7_capture;
revoke all on schema cp7_model_history_runtime from public,anon,authenticated,service_role;

create table cp7_model_history_runtime.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 payload jsonb not null,query jsonb not null,captured_at timestamptz not null,
 access_at_capture jsonb not null,source jsonb not null,result jsonb not null,
 dependency_hash text not null,engine_hash text not null,unique(actor,request_id)
);
alter table cp7_model_history_runtime.runs owner to cp7_capture;
alter table cp7_model_history_runtime.runs enable row level security;
create policy no_access on cp7_model_history_runtime.runs for all to public using(false)with check(false);
revoke all on cp7_model_history_runtime.runs from public,anon,authenticated,service_role;
create trigger immutable_run before update or delete on cp7_model_history_runtime.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_model_history_runtime.query(p jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare q jsonb;target_value text;
begin
 perform cp7_wip.fields(p,array['target_key','from_date','through_date','group_mode']);
 target_value:=p->>'target_key';
 if jsonb_typeof(p->'target_key')is distinct from'string' or target_value!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then
  raise exception 'CP7_MODEL_HISTORY_QUERY';end if;
 q:=cp7_planning.history_query(p-'target_key');
 if(q->>'through_date')::date-(q->>'from_date')::date>365 then raise exception 'CP7_MODEL_HISTORY_QUERY';end if;
 return q||jsonb_build_object('target_key',target_value);
end $$;

create function cp7_model_history_runtime.engine()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.prokind='f'and
 (n.nspname='cp7_model_history_runtime' or n.nspname='public'and p.proname in('erp_cp7_capture_model_history_v1','erp_cp7_read_model_history_v1'))
$$;

create function cp7_model_history_runtime.live(q jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare current_source jsonb;refusal text;
begin
 current_source:=cp7_model_history_scope.capture(q->>'target_key',q-'target_key',false);
 return jsonb_build_object('state','AVAILABLE','source_hash',current_source->'source_hash',
  'reason',null,'producer_hash',current_source->'producer_hash');
exception when raise_exception then
 get stacked diagnostics refusal=message_text;
 -- A missing or now-ambiguous target/non-stock source retires an archive.
 -- Other errors (including authority, SQL, timeout and engine faults) escape.
 if refusal not in('CP7_MODEL_HISTORY_SCOPE_TARGET','CP7_MODEL_HISTORY_SCOPE_NON_STOCK_INCOMPLETE',
  'CP7_MODEL_HISTORY_SCOPE_STOCK_BOUND','CP7_HISTORY_REFERENCE_ROOTS')then raise;end if;
 return jsonb_build_object('state','UNAVAILABLE','source_hash',null,'reason',refusal,'producer_hash',null);
end $$;

create function cp7_model_history_runtime.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;run cp7_model_history_runtime.runs%rowtype;live jsonb;checked timestamptz;
 engine text;source_state text;reason text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();
 select *into run from cp7_model_history_runtime.runs r where r.id=p_run and r.actor=(a->>'actor')::uuid;
 if run.id is null then raise exception using errcode='42501',message='CP7_MODEL_HISTORY_RUN_UNAVAILABLE';end if;
 if run.source->>'source_hash'is distinct from run.dependency_hash
  or run.source->'query'is distinct from run.query-'target_key'
  or run.source->'target_key'is distinct from run.query->'target_key'
  or run.result->>'source_hash'is distinct from run.dependency_hash
  or run.result->'target_key'is distinct from run.query->'target_key'
  or run.result->'captured_at'is distinct from run.source->'captured_at'
  or run.result->>'scope'is distinct from'SINGLE_CURRENT_PHYSICAL_ROOT'then
  raise exception 'CP7_MODEL_HISTORY_STORED_BINDING';end if;
 live:=cp7_model_history_runtime.live(run.query);engine:=cp7_model_history_runtime.engine();
 if cp7_model_history_runtime.live(run.query)is distinct from live
  or cp7_model_history_runtime.engine()is distinct from engine then
  raise exception using errcode='40001',message='CP7_MODEL_HISTORY_CHANGED_DURING_READ';end if;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_HISTORY_ACCESS_CHANGED';end if;
 checked:=clock_timestamp();
 source_state:=case when live->>'state'='AVAILABLE'and live->>'source_hash'=run.dependency_hash and engine=run.engine_hash then'UNCHANGED'else'ARCHIVED_STALE'end;
 reason:=case when live->>'state'<>'AVAILABLE'then'CURRENT_SCOPED_SOURCE_UNAVAILABLE'
  when live->>'source_hash'<>run.dependency_hash then'CURRENT_SCOPED_SOURCE_CHANGED'
  when engine<>run.engine_hash then'HISTORY_RUNTIME_ENGINE_CHANGED'else'CURRENT_SCOPED_SOURCE_AND_ENGINE'end;
 return jsonb_build_object('contract_version','cp7.scoped-history-run.v1','run_id',run.id,
  'request_id',run.request_id,'actor_scope_id',run.actor,'captured_at',cp7_planning.utc(run.captured_at),
  'query',run.query,'history',run.result,'source_hash',run.dependency_hash,
  'current_guard',jsonb_build_object('source_state',source_state,'reason',reason,
   'checked_at',cp7_planning.utc(checked),'live_source_hash',live->'source_hash','engine_hash',engine),
  'model_caller_integrated',false,'production_go',false);
end $$;

create function cp7_model_history_runtime.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;run cp7_model_history_runtime.runs%rowtype;c jsonb;engine text;answer jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();q:=cp7_model_history_runtime.query(p_query);
 if p_request is null then raise exception 'CP7_MODEL_HISTORY_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_HISTORY_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:MODEL:HISTORY:V1:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_HISTORY_ACCESS_CHANGED';end if;
 select *into run from cp7_model_history_runtime.runs r where r.actor=(a->>'actor')::uuid and r.request_id=p_request;
 if found then
  if run.payload is distinct from p_query then raise exception 'CP7_MODEL_HISTORY_REQUEST_CHANGED';end if;
  return cp7_model_history_runtime.serve(run.id);
 end if;
 engine:=cp7_model_history_runtime.engine();
 c:=cp7_model_history_scope.capture(q->>'target_key',q-'target_key',true);
 if cp7_model_history_runtime.live(q)->>'source_hash'is distinct from c->>'source_hash'
  or cp7_model_history_runtime.engine()is distinct from engine then
  raise exception using errcode='40001',message='CP7_MODEL_HISTORY_SOURCE_CHANGED';end if;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MODEL_HISTORY_ACCESS_CHANGED';end if;
 insert into cp7_model_history_runtime.runs(actor,request_id,payload,query,captured_at,access_at_capture,source,result,dependency_hash,engine_hash)
 values((a->>'actor')::uuid,p_request,p_query,q,(c->>'captured_at')::timestamptz,a,c-'result',c->'result',c->>'source_hash',engine)
 returning *into run;
 answer:=cp7_model_history_runtime.serve(run.id);
 if answer->'current_guard'->>'source_state'is distinct from'UNCHANGED'then
  raise exception using errcode='40001',message='CP7_MODEL_HISTORY_SOURCE_CHANGED';end if;
 return answer;
end $$;

create function public.erp_cp7_capture_model_history_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'set statement_timeout='8s'as $$
 select cp7_model_history_runtime.capture(p_query,p_request)
$$;
create function public.erp_cp7_read_model_history_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'set statement_timeout='8s'as $$
 select cp7_model_history_runtime.serve(p_run)
$$;
alter function cp7_model_history_runtime.query(jsonb)owner to cp7_capture;
alter function cp7_model_history_runtime.engine()owner to cp7_capture;
alter function cp7_model_history_runtime.live(jsonb)owner to cp7_capture;
alter function cp7_model_history_runtime.serve(uuid)owner to cp7_capture;
alter function cp7_model_history_runtime.capture(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_capture_model_history_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_model_history_v1(uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_model_history_runtime from public,anon,authenticated,service_role;
revoke all on function public.erp_cp7_capture_model_history_v1(jsonb,uuid),public.erp_cp7_read_model_history_v1(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_model_history_v1(jsonb,uuid),public.erp_cp7_read_model_history_v1(uuid)to authenticated;
