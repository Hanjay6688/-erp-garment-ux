-- B consumes A's official finance capture. No financial formula, Native DML,
-- public endpoint, scheduler or sealed operational-page mutation.
create schema cp7_analysis_finance authorization cp7_capture;
revoke all on schema cp7_analysis_finance from public,anon,authenticated,service_role;
create function cp7_analysis_finance.status(p_job uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;again jsonb;j cp7_analysis_stage.jobs%rowtype;s jsonb;f jsonb;v jsonb;dates jsonb;outcome jsonb;
begin
 a:=cp7_schedule_native.access_now(false);
 select *into j from cp7_analysis_stage.jobs x where x.id=p_job and x.actor=(a->>'actor')::uuid;
 if j.id is null then raise exception using errcode='42501',message='CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
 if coalesce(j.reference->>'finance_sidecar_mode','DEFERRED')<>'STAGED'then return null;end if;
 outcome:=jsonb_build_object('contract_version','cp7.analysis-finance-sidecar.v1','request_id',j.request_id,'job_id',j.id,
  'query',j.query,'reference',jsonb_build_object('captured_at',j.captured_at,'source_hash',j.source_hash),'production_go',false);
 -- status_of is a private compositional reader; check current financial
 -- permission before exposing even its progress, dates or capture identifier.
 if not cp7_analysis_stage.report_finance_access(a,false)then
  return outcome||jsonb_build_object('state','ACCESS_REVOKED','capture',null,'result',null);end if;
 s:=cp7_finance_capture.status_of('STAGED_ANALYSIS',j.id);
 dates:=jsonb_build_object('from',j.query->>'from_date','to',j.query->>'through_date','as_of',(j.captured_at at time zone'Asia/Jakarta')::date::text);
 if s is null or s->>'contract_version'is distinct from'cp7.finance-capture-status.v1'or s->>'owner_kind'is distinct from'STAGED_ANALYSIS'
  or s->>'owner_id'is distinct from j.id::text or s->'dates'is distinct from dates or coalesce(s->>'state','')not in('RUNNING','READY','FAILED')then
  raise exception 'CP7_ANALYSIS_FINANCE_CAPTURE_CHANGED';end if;
 if s->>'state'='READY'then
  f:=cp7_finance_capture.result((s->>'capture_id')::uuid);
  if f->>'contract_version'is distinct from'cp7.native-analysis-finance.v2'or f->'dates'is distinct from dates
   or f#>>'{capture,id}'is distinct from s->>'capture_id'
   or coalesce(f->>'source_hash','')!~'^[0-9a-f]{64}$'then raise exception 'CP7_ANALYSIS_FINANCE_CAPTURE_CHANGED';end if;
  -- The exact official overlay; the seed contains only sidecar metadata.
  -- No operational quantities or sealed Original are changed by this call.
  v:=cp7_analysis_native.finance_apply(jsonb_build_object('metrics','[]'::jsonb,'dependencies','[]'::jsonb,
    'generation_warnings','[]'::jsonb,'quality',jsonb_build_object('financial','NONE'),
    'snapshot',jsonb_build_object('fact_count',0),'financial_readiness','BLOCKED'),jsonb_build_object('financial_source',f));
  if v->'financial_readiness'is distinct from s->'readiness'then raise exception 'CP7_ANALYSIS_FINANCE_CAPTURE_CHANGED';end if;
  v:=jsonb_build_object('contract_version','cp7.analysis-finance-result.v1','capture_id',s->'capture_id',
   'source_hash',f->'source_hash','dates',f->'dates','report_read_at',s->'report_read_at','readiness',v->'financial_readiness',
   'metrics',v->'metrics','dependencies',v->'dependencies','warnings',v->'generation_warnings');
 end if;
 again:=cp7_schedule_native.access_now(false);
 if again is distinct from a or not cp7_analysis_stage.report_finance_access(again,false)then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;
 return outcome||jsonb_build_object('state',s->'state','capture',s,'result',v);
end $$;
alter function cp7_analysis_finance.status(uuid)owner to cp7_capture;
revoke all on function cp7_analysis_finance.status(uuid)from public,anon,authenticated,service_role;
