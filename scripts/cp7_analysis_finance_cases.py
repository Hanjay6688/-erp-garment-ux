"""Native owner-report reuse and current financial authority on saved analysis."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import json,time,uuid
import psycopg
import cp7_finance_cases as finance

def admin_actor(cur,parent):
 subject,_=parent.auth.custom_actor(cur)
 role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
 cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
 for permission in ('master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view','finance.reports.view','finance.period_close.manage'):
  cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
 return subject,role

def cases(cur,today,parent):
 auth,b=parent.auth,parent.b
 def same_source():
  parent.setup(cur,today);before=b.boundary.snapshot(cur);e=parent.capture(cur,today);parent.checked(e)
  f=e['financial_source'];assert f is not None
  auth.actor(cur);native=cur.execute('select public.erp_cp7_get_finance_report_v1(%s)',(json.dumps(f['dates']),)).fetchone()[0];b.api.admin(cur)
  fingerprint=lambda report,book:cur.execute('select cp7_analysis_native.financial_fingerprint(%s::jsonb,%s)',(json.dumps(report),book)).fetchone()[0]
  assert fingerprint(native,f['book_signature'])==f['source_hash']
  for section in('performance','financial_position','basis'):
   assert f['report']['snapshot'][section]==native['snapshot'][section]
  assert datetime.fromisoformat(f['report']['captured_at'])==datetime.fromisoformat(e['analysis']['snapshot']['effective_as_of'])
  # A pure perturbation of the actual Native report proves set-order stability,
  # not another Native event. Keep every raw archived member and duplicate.
  permuted=deepcopy(f['report']);checks=permuted['snapshot']['data_confidence']
  for key in('failed_checks','blockers'):
   if isinstance(checks.get(key),list):checks[key].reverse()
  if isinstance(permuted['close_preflight'],dict):
   for key in('blockers','info'):
    if isinstance(permuted['close_preflight'].get(key),list):permuted['close_preflight'][key].reverse()
  permuted['captured_at']='2000-01-01T00:00:00+00:00'
  assert fingerprint(permuted,f['book_signature'])==f['source_hash']
  changed=deepcopy(permuted);changed['snapshot']['financial_position']['cash']=str(Decimal(changed['snapshot']['financial_position']['cash'])+1)
  assert fingerprint(changed,f['book_signature'])!=f['source_hash']
  if checks.get('failed_checks'):
   duplicated=deepcopy(permuted);duplicated['snapshot']['data_confidence']['failed_checks'].append(deepcopy(checks['failed_checks'][0]))
   assert fingerprint(duplicated,f['book_signature'])!=f['source_hash']
   changed=deepcopy(permuted);changed['snapshot']['data_confidence']['failed_checks'][0]['details']='Changed Native check meaning'
   assert fingerprint(changed,f['book_signature'])!=f['source_hash']
  assert fingerprint(permuted,'changed-book-provenance')!=f['source_hash']
  # Same business state must survive physical SQL plan changes. These are
  # session-only reader perturbations, not a Native event or a fixture fact.
  reads=0
  try:
   for plan in('force_custom_plan','force_generic_plan'):
    cur.execute("select set_config('plan_cache_mode',%s,true)",(plan,))
    for scan in('on','off'):
     cur.execute("select set_config('enable_seqscan',%s,true)",(scan,))
     for aggregate in('on','off'):
      cur.execute("select set_config('enable_hashagg',%s,true)",(aggregate,))
      for _ in range(5):
       current=parent.read(cur,e['run_id']);reads+=1
       assert current['source_state']=='UNCHANGED'and current['analysis']==e['analysis']and current['financial_source']==e['financial_source'],('P14_FINANCIAL_READER_SOURCE_UNSTABLE',plan,scan,aggregate,reads,current['source_state'])
  except Exception:
   from cp7_plan_native_cases import source_diagnostic
   diagnostic=source_diagnostic(cur,e['run_id']);path=Path(__file__).resolve().parents[1]/'cp6-proof/t3/P14_FINANCIAL_STABILITY_SOURCE_DIAGNOSTIC.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(dict(plan=plan,scan=scan,aggregate=aggregate,reads=reads,source=diagnostic),indent=2,default=str)+'\n')
   raise
  finally:
   for name,value in(('plan_cache_mode','auto'),('enable_seqscan','on'),('enable_hashagg','on')):cur.execute('select set_config(%s,%s,true)',(name,value))
  assert reads==40 and b.boundary.snapshot(cur)==before
  # Pure clock counterfixtures on the actual stored Native source. They do
  # not manufacture Native production events or alter the forty live reads.
  from zoneinfo import ZoneInfo
  c=cur.execute('select facts from cp7_analysis_native.runs where id=%s',(e['run_id'],)).fetchone()[0]
  schedule_hash=lambda source:cur.execute('select cp7_schedule_native.fingerprint(%s::jsonb)',(json.dumps(source),)).fetchone()[0]
  captured=datetime.fromisoformat(c['captured_at']);windows=c['schedule']['config']['windows']
  start=datetime.fromisoformat(min(windows,key=lambda w:datetime.fromisoformat(w['starts_at']))['starts_at'])
  assert start>captured+timedelta(minutes=2),'P14_FUTURE_CALENDAR_CONTROL_REQUIRED'
  def at(instant):
   changed=deepcopy(c);changed['captured_at']=instant.isoformat();changed['planning_time_bucket']=instant.replace(second=0,microsecond=0).isoformat();return changed
  later=captured+timedelta(minutes=1)
  if captured.astimezone(ZoneInfo('Asia/Jakarta')).date()==later.astimezone(ZoneInfo('Asia/Jakarta')).date():
   assert schedule_hash(at(later))==schedule_hash(c),'FUTURE_WINDOW_FALSE_CLOCK_EXPIRY'
  else:assert schedule_hash(at(later))!=schedule_hash(c),'BUSINESS_DAY_EXPIRY_LOST'
  assert schedule_hash(at(start+timedelta(minutes=1)))!=schedule_hash(at(start+timedelta(minutes=2))),'ACTIVE_WINDOW_CLOCK_GUARD_LOST'
  assert schedule_hash(at(captured+timedelta(days=1)))!=schedule_hash(c),'BUSINESS_DAY_CLOCK_GUARD_LOST'
  horizon=datetime.fromisoformat(c['schedule']['config']['through_at'])
  assert schedule_hash(at(horizon-timedelta(seconds=1)))!=schedule_hash(at(horizon+timedelta(seconds=1))),'HORIZON_CLOCK_GUARD_LOST'
  return dict(status='PASS',actual_Owner_financial_Original_40_public_reads_under_different_SQL_plans=True,accepted_native_owner_report_identical_no_second_money_or_HPP_engine=True,one_source_clock=True,no_business_DML=True,unordered_Native_checks_multiset_hash_stable=True,actual_report_pure_permutation_not_Native_event=True,money_check_content_duplicate_and_book_provenance_changes_detected=True,pure_actual_Native_clock_counterfixtures_not_business_events=True,future_window_clock_stable_active_window_business_day_and_horizon_expire=True)
 def ops_redaction():
  parent.setup(cur,today);subject,role=auth.custom_actor(cur)
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.reports.view')",(role,))
  e=parent.capture(cur,today,subject=subject);parent.checked(e)
  assert e['financial_source']is None and not any(m['value']['unit']=='IDR'for m in e['analysis']['metrics'])
  return dict(status='PASS',custom_four_Ops_plus_report_permission_still_preserves_native_owner_admin_boundary=True,no_financial_operands_or_facts=True)
 def current_rights(preflight=False):
  parent.setup(cur,today);subject,role=admin_actor(cur,parent);key=uuid.uuid4();e=parent.capture(cur,today,key,subject);assert e['financial_source']is not None
  if preflight:assert e['financial_source']['report']['close_preflight']is not None
  permission='finance.period_close.manage'if preflight else'finance.reports.view'
  cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,permission))
  # Operational access remains sufficient for a fresh operational-only run;
  # neither the cached UUID nor its original protected archive may leak money.
  auth.refused(cur,lambda:parent.capture(cur,today,key,subject),'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
  auth.refused(cur,lambda:parent.read(cur,e['run_id'],subject),'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
  fresh=parent.capture(cur,today,subject=subject);parent.checked(fresh)
  if preflight:assert fresh['financial_source']['report']['close_preflight']is None
  else:assert fresh['financial_source']is None
  return dict(status='PASS',revoked_permission=permission,four_operational_permissions_retained=True,current_financial_authority_before_cached_UUID_and_original_read=True)
 def journal_stales():
  f=parent.previous.baseline.history.fixture(cur,today,qty=24,stock=100)
  e=parent.capture(cur,today);old=e['financial_source'];assert old is not None
  parent.previous.baseline.history.sales.fg.post_sale(cur,f['draft'])
  reread=parent.read(cur,e['run_id']);assert reread['source_state']=='ARCHIVED_STALE'and reread['analysis']==e['analysis']and reread['financial_source']==old
  fresh=parent.capture(cur,today);parent.checked(fresh);assert fresh['financial_source']['source_hash']!=old['source_hash']
  native=finance.read(cur,today);assert fresh['financial_source']['report']['snapshot']['financial_position']==native['snapshot']['financial_position']
  parent.previous.baseline.history.sales.native(cur,'select erp.reverse_sale(%s,%s)',(f['sale'],'P15 native inverse provenance control'))
  inverse=parent.capture(cur,today);parent.checked(inverse)
  assert inverse['financial_source']['report']['snapshot']['financial_position']==old['report']['snapshot']['financial_position']
  assert inverse['financial_source']['book_signature']!=old['book_signature']and parent.read(cur,e['run_id'])['source_state']=='ARCHIVED_STALE'
  return dict(status='PASS',actual_native_sale_journal_stales_financial_source=True,original_money_and_readiness_immutable=True,current_balance_matches_existing_owner_report=True,neutral_post_inverse_keeps_provenance_change_visible=True)
 return [('P15_NATIVE_ANALYSIS_FINANCE_'+n,fn)for n,fn in [('SAME_SOURCE',same_source),('OWNER_BOUNDARY',ops_redaction),('CURRENT_REPORT_AUTH',current_rights),('CURRENT_PREFLIGHT_AUTH',lambda:current_rights(True)),('JOURNAL_STALE',journal_stales)]]

def races(tools,today,parent):
 def revoke_waiting():
  key=uuid.uuid4()
  with tools.connect()as conn,conn.cursor()as cur:
   parent.setup(cur,today);subject,role=admin_actor(cur,parent);e=parent.capture(cur,today,key,subject);assert e['financial_source']is not None;conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=parent.capture(cur,today,key,subject);conn.commit();return r
     except psycopg.Error as ex:conn.rollback();return str(ex)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_capture_analysis_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P15_REAL_FINANCIAL_CAPTURE_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(30)
  assert isinstance(result,str)and any(code in result for code in('CP7_ANALYSIS_ACCESS_CHANGED','CP7_ANALYSIS_FINANCE_ACCESS_DENIED')),result
  return dict(status='PASS',financial_permission_revoked_after_observed_native_capture_lock_wait=True,cached_financial_body_not_returned=True)
 return [('P15_ANALYSIS_FINANCE_LOCK_CURRENT_AUTH',revoke_waiting)]

def http_cases(http,today,parent):
 def current_finance():
  owner=http.login('ADMIN','p15-analysis-financial-admin')
  with http.connect()as conn,conn.cursor()as c:parent.setup(c,today);conn.commit()
  args=dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4()));e=owner.rpc('erp_cp7_capture_analysis_v1',args);assert e['status']==200,e;parent.checked(e['body']);assert e['body']['financial_source']is not None
  with http.connect()as conn,conn.cursor()as c:
   role=c.execute('select role_id from erp.app_users where auth_user_id=%s',(owner.auth_user_id,)).fetchone()[0]
   c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(role,));conn.commit()
  assert owner.rpc('erp_cp7_capture_analysis_v1',args)['status']==403
  assert owner.rpc('erp_cp7_read_analysis_v1',dict(p_run=e['body']['run_id']))['status']==403
  fresh=owner.rpc('erp_cp7_capture_analysis_v1',dict(args,p_request=str(uuid.uuid4())));assert fresh['status']==200,fresh;parent.checked(fresh['body']);assert fresh['body']['financial_source']is None
  return dict(status='PASS',real_Auth_financial_permission_only_revoked=True,cached_archive403_fresh_operational200_no_money=True)
 return [('P15_ANALYSIS_FINANCE_HTTP_CURRENT_AUTH',current_finance)]
