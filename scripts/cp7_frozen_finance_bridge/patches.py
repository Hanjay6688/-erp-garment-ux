"""Counted frozen-v2 caller changes; A's financial functions remain untouched."""
from cp7_analysis_finance_bridge.patches import once

REQUEST='cp7_frozen_analysis_units_v2.request(jsonb,uuid)'
STATUS='cp7_analysis_stage.status(uuid)'
SIGNATURES=(REQUEST,STATUS)


def patched(originals):
 if set(originals)!=set(SIGNATURES):raise ValueError('FROZEN_FINANCE_SIGNATURE_SET_CHANGED')
 request=originals[REQUEST]
 request=once(request,'snap pg_snapshot;', 'snap pg_snapshot;finance_mode text;stored_mode text;',REQUEST)
 request=once(request,'a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);',"""a:=cp7_schedule_native.access_now(false);
 if p_query?'finance_mode'and(jsonb_typeof(p_query->'finance_mode')is distinct from'string'or p_query->>'finance_mode'not in('STAGED','DEFERRED'))then
  raise exception 'CP7_ANALYSIS_FINANCE_MODE';end if;
 finance_mode:=coalesce(p_query->>'finance_mode','DEFERRED');q:=cp7_planning.history_query(p_query-'finance_mode');
 if finance_mode='STAGED'and not cp7_analysis_stage.report_finance_access(a,false)then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;""",REQUEST)
 request=once(request," jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);", """ if cp7_schedule_native.access_now(false)is distinct from a or(finance_mode='STAGED'and not cp7_analysis_stage.report_finance_access(a,false))then
  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);""",REQUEST)
 request=once(request,'select x.query into jq from cp7_analysis_stage.jobs x where x.id=jid;',
  "select x.query,coalesce(x.reference->>'finance_sidecar_mode','DEFERRED')into jq,stored_mode from cp7_analysis_stage.jobs x where x.id=jid;",REQUEST)
 request=once(request,"if jq<>q then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;",
  "if jq<>q or stored_mode<>finance_mode then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;",REQUEST)
 request=once(request," jid:=cp7_analysis_stage.create_job((a->>'actor')::uuid,p_request,q,a,c);", """ if finance_mode='STAGED'then c:=c||jsonb_build_object('finance_sidecar_mode','STAGED');end if;
 jid:=cp7_analysis_stage.create_job((a->>'actor')::uuid,p_request,q,a,c);
 if finance_mode='STAGED'then
  perform cp7_finance_capture.start('STAGED_ANALYSIS',jid,q,(c->>'captured_at')::timestamptz);
  if cp7_schedule_native.access_now(false)is distinct from a or not cp7_analysis_stage.report_finance_access(a,false)then
   raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;
 end if;""",REQUEST)
 status=once(originals[STATUS],"'apply_enabled',false,'production_go',false)",
  "'apply_enabled',false,'production_go',false)||case when j.reference->>'finance_sidecar_mode'='STAGED'then jsonb_build_object('finance_capture',cp7_analysis_finance.status(j.id))else'{}'::jsonb end",STATUS)
 return{REQUEST:request,STATUS:status}
