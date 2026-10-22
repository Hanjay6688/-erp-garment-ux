"""Counted substitutions that wire the OW-12a finance capture into the installed staged report and server runner.

Business Report v2 (report-staged.sql) read the owner report and the whole-book provenance scan in ONE statement at
ACTUALS, which stops at the 8 s limit at factory scale. Its ACTUALS unit now takes the same figures from a staged
capture (cp7_finance_capture): one capture unit per step, the unit stored only when the capture is sealed. The status
names the capture's progress; the summary names the time the finance report was read. The runner learns the FINANCE
family. A DEFERRED report, every other unit, every refusal and the v1 report path stay byte-for-byte.
"""
RUN_UNIT='cp7_analysis_stage.report_run_unit(cp7_analysis_stage.report_jobs,jsonb)'
STEP='cp7_analysis_stage.report_step(uuid)'
STATUS='cp7_analysis_stage.report_status(uuid)'
SUMMARY='cp7_analysis_stage.report_summary_text(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,text)'
RUNNER='cp7_background.run_next()'
SIGNATURES=(RUN_UNIT,STEP,STATUS,SUMMARY,RUNNER)
STEPS={
 RUN_UNIT:(
  ('declare',
   " prior cp7_analysis_stage.report_publications%rowtype;sha text;hash text;pid uuid;n integer;expect integer;s record;preflight boolean;\n",
   " prior cp7_analysis_stage.report_publications%rowtype;sha text;hash text;pid uuid;n integer;expect integer;s record;preflight boolean;fc jsonb;\n"),
  ('actuals',
   "  select cp7_analysis_stage.report_actuals(j.analysis_job,j.period_query,j.finance='INCLUDED',clock_timestamp())into body;\n",
   "  -- OW-12a: the owner report comes from this job's staged finance capture (bounded steps), not one over-limit\n"
   "  -- statement; until the capture is sealed the unit stores nothing and the job stays at ACTUALS.\n"
   "  if j.finance='INCLUDED'then fc:=cp7_finance_capture.for_report(j.id,j.period_query);if fc is null then return null;end if;end if;\n"
   "  select cp7_analysis_stage.report_actuals(j.analysis_job,j.period_query,false,clock_timestamp())\n"
   "   ||case when j.finance='INCLUDED'then jsonb_build_object('finance',fc)else'{}'::jsonb end into body;\n"
   "  if j.finance='INCLUDED'and fc->'dates'->>'as_of'is distinct from body->>'report_date'then raise exception 'CP7_REPORT_V2_FINANCE_DATE_CHANGED';end if;\n"),
 ),
 STEP:(
  ('waiting',
   "    pid:=cp7_analysis_stage.report_run_unit(j,a);\n"
   "    update cp7_analysis_stage.report_jobs set units_done=units_done+1,unit_attempts=0,updated_at=clock_timestamp(),\n"
   "     publication_id=coalesce(pid,publication_id),state=case when units_done+1=unit_count then 'DONE'else 'RUNNING'end where id=j.id;\n",
   "    pid:=cp7_analysis_stage.report_run_unit(j,a);\n"
   "    if j.units_done=0 and j.finance='INCLUDED'and not exists(select 1 from cp7_analysis_stage.report_reads x where x.job_id=j.id and x.kind='ACTUALS')then\n"
   "     -- OW-12a: one finance capture unit ran; ACTUALS is not stored until the capture is sealed.\n"
   "     update cp7_analysis_stage.report_jobs set unit_attempts=0,updated_at=clock_timestamp()where id=j.id;\n"
   "    else\n"
   "    update cp7_analysis_stage.report_jobs set units_done=units_done+1,unit_attempts=0,updated_at=clock_timestamp(),\n"
   "     publication_id=coalesce(pid,publication_id),state=case when units_done+1=unit_count then 'DONE'else 'RUNNING'end where id=j.id;\n"
   "    end if;\n"),
 ),
 STATUS:(
  ('capture',
   "  'production_go',false)\n from cp7_analysis_stage.report_jobs j where j.id=p_job\n",
   "  'finance_capture',case when j.finance='INCLUDED'then cp7_finance_capture.status_of('STAGED_REPORT',j.id)end,\n"
   "  'production_go',false)\n from cp7_analysis_stage.report_jobs j where j.id=p_job\n"),
 ),
 SUMMARY:(
  ('read_time',
   "  lines:=array_append(lines,'Angka keuangan dan HPP dari laporan Native ERP untuk tanggal laporan '||(f->'dates'->>'as_of')||', dibaca '||read_at||\n",
   "  lines:=array_append(lines,'Angka keuangan dan HPP dari laporan Native ERP untuk tanggal laporan '||(f->'dates'->>'as_of')||', dibaca '||\n"
   "   coalesce(cp7_analysis_stage.report_wib((f->'report'->>'captured_at')::timestamptz),read_at)||\n"),
 ),
 RUNNER:(
  ('family',
   "  union all select 'REMINDER',cp7_background.reminder_pending_at()\n",
   "  union all select 'REMINDER',cp7_background.reminder_pending_at()\n"
   "  union all select 'FINANCE',min(updated_at)from cp7_finance_capture.captures where state='RUNNING'\n"),
  ('dispatch',
   "   when 'ANALYSIS'then cp7_background.analysis_next()else cp7_background.reminder_next()end;\n",
   "   when 'ANALYSIS'then cp7_background.analysis_next()when 'FINANCE'then cp7_finance_capture.run_next()else cp7_background.reminder_next()end;\n"),
 ),
}


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW12A_FINANCE_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW12A_FINANCE_DELTA_SET_CHANGED')
    out={}
    for signature in SIGNATURES:
        body=originals[signature]
        if 'cp7_finance_capture' in body:raise ValueError('OW12A_FINANCE_ALREADY_PATCHED: '+signature)
        for label,old,new in STEPS[signature]:body=once(body,old,new,signature+':'+label)
        out[signature]=body
    return out
