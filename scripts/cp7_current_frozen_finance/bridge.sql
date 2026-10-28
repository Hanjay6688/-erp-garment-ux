create schema cp7_current_frozen_finance authorization cp7_capture;
revoke all on schema cp7_current_frozen_finance from public,anon,authenticated,service_role;
create or replace function cp7_frozen_analysis_units_v2.request(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;jid uuid;jq jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();snap pg_snapshot;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 if jid is not null then
  select x.query into jq from cp7_analysis_stage.jobs x where x.id=jid;
  if not exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid
   and x.reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v2')then
   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if jq<>q or exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid
   and coalesce(x.reference->>'finance_sidecar_mode','DEFERRED')<>'DEFERRED')then
   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
  return cp7_analysis_stage.status(jid);
 end if;
 if exists(select 1 from cp7_analysis_native.runs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)
  or exists(select 1 from cp7_analysis_jobs.jobs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)then
  raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';
 end if;
 -- One statement: the reference and the snapshot it was read in (all of
 -- source_within is stable, so it reads in this statement's snapshot). A
 -- transaction that already wrote has rows the snapshot cannot place, so its
 -- mark is null and changes are then judged by recording time alone.
 select cp7_frozen_analysis_units_v2.source(q,true),
  case when pg_current_xact_id_if_assigned()is null then pg_current_snapshot()end into c,snap;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 -- More planned products than the job's declared capacity: refused here with
 -- the declared code, before any job or reference is kept (independent audit
 -- Fable F-AN-01: it used to become a FAILED job at unit 0 under another code).
 if jsonb_array_length(coalesce(c->'facts'->'products','[]'::jsonb))>(b->>'job_targets')::integer then
  raise exception using message='CP7_ANALYSIS_STAGED_TARGET_LIMIT',
   detail=jsonb_build_object('targets_limit',b->'job_targets','refused_at','REQUEST')::text;
 end if;
 jid:=cp7_analysis_stage.create_job((a->>'actor')::uuid,p_request,q,a,c);
 insert into cp7_analysis_stage.capture_marks(job_id,source_snapshot)values(jid,snap);
 return cp7_analysis_stage.status(jid);
end $$;
create or replace function cp7_frozen_analysis_units_v2.producer_hash()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.frozen-analysis-unit-producer.v2',
  'capsule',cp7_frozen_analysis_v2.producer_hash(),'adapter',(
   select string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),E'\n'order by p.oid::regprocedure::text)
   from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where p.prokind='f'and(n.nspname in('cp7_frozen_analysis_units_v2','cp7_current_frozen_finance')or p.oid=any(array[
    'cp7_analysis_stage.run_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units)'::regprocedure,
    'cp7_analysis_stage.run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb)'::regprocedure,
    'cp7_supply_native.fingerprint(jsonb)'::regprocedure,
    'cp7_analysis_stage.analysis_skeleton(jsonb,jsonb,uuid,jsonb,jsonb,jsonb,jsonb,jsonb,boolean,text)'::regprocedure,
    'cp7_schedule_staged_review.workspace(uuid)'::regprocedure,
    'cp7_schedule_staged_review.save(jsonb,uuid)'::regprocedure]))))::text,'UTF8'),'sha256'),'hex')
$$;
create function cp7_current_frozen_finance.source(p_query jsonb,p_with_capsule boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare q jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();stock jsonb;summary jsonb;producer text;
begin
 if p_with_capsule is null then raise exception 'CP7_BOUNDED_ANALYSIS_CAPTURE_MODE';end if;
 q:=cp7_planning.history_query(p_query);
 c:=cp7_bounded_analysis_stage.analysis_source((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED','finance_sidecar_mode','STAGED');
 perform cp7_frozen_analysis_v2.admit(c,q,(b->>'job_targets')::integer);
 stock:=cp7_history_reference_binary_v2.stock_digest(c->'facts'->'products',(c->>'captured_at')::timestamptz);
 producer:=cp7_frozen_analysis_units_v2.producer_hash();
 if not p_with_capsule then return cp7_frozen_analysis_v2.reference(c,q,stock,producer);end if;
 if c->>'status'='INCOMPLETE'then
  summary:=cp7_reorder_inputs.stock_summary(c->'facts'->'products',(c->>'captured_at')::timestamptz,q);
 end if;
 return cp7_frozen_analysis_v2.seal(c,q,stock,summary,producer,(b->>'job_targets')::integer);
end $$;
alter function cp7_current_frozen_finance.source(jsonb,boolean) owner to cp7_capture;
revoke all on function cp7_current_frozen_finance.source(jsonb,boolean) from public,anon,authenticated,service_role;
create function cp7_current_frozen_finance.request_finance(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;jid uuid;jq jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();snap pg_snapshot;finance_mode text;stored_mode text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_query?'finance_mode'and(jsonb_typeof(p_query->'finance_mode')is distinct from'string'or p_query->>'finance_mode'not in('STAGED','DEFERRED'))then
  raise exception 'CP7_ANALYSIS_FINANCE_MODE';end if;
 finance_mode:=coalesce(p_query->>'finance_mode','DEFERRED');q:=cp7_planning.history_query(p_query-'finance_mode');
 if finance_mode='STAGED'and not cp7_analysis_stage.report_finance_access(a,false)then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;
 if p_query->'finance_mode'is distinct from'"STAGED"'::jsonb then
  raise exception 'CP7_BOUNDED_FINANCE_EXPLICIT_STAGED_REQUIRED';end if;
 if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(false)is distinct from a
  or not cp7_analysis_stage.report_finance_access(a,false)then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 if jid is not null then
  select x.query,coalesce(x.reference->>'finance_sidecar_mode','DEFERRED')into jq,stored_mode from cp7_analysis_stage.jobs x where x.id=jid;
  if not exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid
   and x.reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v2')then
   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if jq<>q or stored_mode<>finance_mode then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if cp7_schedule_native.access_now(false)is distinct from a
  or not cp7_analysis_stage.report_finance_access(a,false)then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;
  return cp7_analysis_stage.status(jid);
 end if;
 if exists(select 1 from cp7_analysis_native.runs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)
  or exists(select 1 from cp7_analysis_jobs.jobs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)then
  raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';
 end if;
 -- One statement: the reference and the snapshot it was read in (all of
 -- source_within is stable, so it reads in this statement's snapshot). A
 -- transaction that already wrote has rows the snapshot cannot place, so its
 -- mark is null and changes are then judged by recording time alone.
 select cp7_current_frozen_finance.source(q,true),
  case when pg_current_xact_id_if_assigned()is null then pg_current_snapshot()end into c,snap;
 if cp7_schedule_native.access_now(false)is distinct from a
  or not cp7_analysis_stage.report_finance_access(a,false)then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;
 -- More planned products than the job's declared capacity: refused here with
 -- the declared code, before any job or reference is kept (independent audit
 -- Fable F-AN-01: it used to become a FAILED job at unit 0 under another code).
 if jsonb_array_length(coalesce(c->'facts'->'products','[]'::jsonb))>(b->>'job_targets')::integer then
  raise exception using message='CP7_ANALYSIS_STAGED_TARGET_LIMIT',
   detail=jsonb_build_object('targets_limit',b->'job_targets','refused_at','REQUEST')::text;
 end if;
 jid:=cp7_analysis_stage.create_job((a->>'actor')::uuid,p_request,q,a,c);
 if finance_mode='STAGED'then
  perform cp7_finance_capture.start('STAGED_ANALYSIS',jid,q,(c->>'captured_at')::timestamptz);
  if cp7_schedule_native.access_now(false)is distinct from a or not cp7_analysis_stage.report_finance_access(a,false)then
   raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;
 end if;
 insert into cp7_analysis_stage.capture_marks(job_id,source_snapshot)values(jid,snap);
 return cp7_analysis_stage.status(jid);
end $$;
alter function cp7_current_frozen_finance.request_finance(jsonb,uuid) owner to cp7_capture;
revoke all on function cp7_current_frozen_finance.request_finance(jsonb,uuid) from public,anon,authenticated,service_role;
