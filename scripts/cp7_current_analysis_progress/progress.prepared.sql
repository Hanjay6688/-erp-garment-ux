-- D17-18 opt-in read-only telemetry. Existing request/status/capture bodies
-- and producer seals are unchanged. This endpoint does not run a unit.
create function public.erp_cp7_get_frozen_analysis_progress_v1(p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;again jsonb;allowed boolean;s jsonb;op jsonb;fin jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 allowed:=cp7_analysis_stage.report_finance_access(a,false);
 -- The status and row metadata share one SQL snapshot. Only the caller's
 -- request is read; the existing actor/request unique key bounds this read.
 select cp7_analysis_stage.status(j.id),
  jsonb_build_object('created_at',j.created_at,'last_activity_at',j.updated_at,
   'finished_at',case when j.state in('DONE','FAILED')then j.updated_at end,
   'worker_observation','NOT_EXPOSED'),
  case when allowed and j.reference->>'finance_sidecar_mode'='STAGED'then
   jsonb_build_object('capture_id',c.id,'created_at',c.created_at,'last_activity_at',c.updated_at,
    'finished_at',c.finished_at,'unit_attempts',c.unit_attempts,'report_ms',c.report_ms,
    'worker_observation',case when exists(
     select 1 from pg_catalog.pg_locks l
     where l.locktype='advisory'and l.granted and l.mode='ExclusiveLock'and l.objsubid=1
      and l.database=(select d.oid from pg_catalog.pg_database d where d.datname=current_database())
      and l.classid=((pg_catalog.hashtextextended('CP7:FINANCE_CAPTURE_STEP:'||c.id::text,0)>>32)&4294967295)::oid
      and l.objid=(pg_catalog.hashtextextended('CP7:FINANCE_CAPTURE_STEP:'||c.id::text,0)&4294967295)::oid
    )then'LOCK_HELD'else'NO_LOCK_OBSERVED'end)
  end into s,op,fin
 from cp7_analysis_stage.jobs j
 left join cp7_finance_capture.captures c on allowed and c.owner_kind='STAGED_ANALYSIS'and c.owner_id=j.id and c.actor=j.actor
 where j.actor=(a->>'actor')::uuid and j.request_id=p_request
  and j.reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v2';
 if s is null then raise exception 'CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
 if allowed and s?'finance_capture'and(fin->>'capture_id'is null
  or fin->>'capture_id'is distinct from s#>>'{finance_capture,capture,capture_id}')then
  raise exception 'CP7_ANALYSIS_FINANCE_CAPTURE_CHANGED';end if;
 -- Current ACL is checked again after reading metadata, including a change
 -- to finance access that might not change the general actor identity.
 again:=cp7_schedule_native.access_now(false);
 if again is distinct from a or cp7_analysis_stage.report_finance_access(again,false)is distinct from allowed then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.frozen-analysis-progress.v1','policy_id','D17-18-20261026',
  'observed_at',clock_timestamp(),'status',s,'operational',op,'finance',fin,'production_go',false);
end $$;
alter function public.erp_cp7_get_frozen_analysis_progress_v1(uuid)owner to cp7_capture;
revoke all on function public.erp_cp7_get_frozen_analysis_progress_v1(uuid)from public,anon,authenticated,service_role,postgres;
grant execute on function public.erp_cp7_get_frozen_analysis_progress_v1(uuid)to authenticated;
