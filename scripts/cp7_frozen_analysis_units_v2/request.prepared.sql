create function cp7_frozen_analysis_units_v2.request(p_query jsonb,p_request uuid)returns jsonb
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
  if jq<>q then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
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
