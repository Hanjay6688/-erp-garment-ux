"""Native owner-report reuse and current financial authority on saved analysis."""
from concurrent.futures import ThreadPoolExecutor
import json,time,uuid
import psycopg
import cp7_finance_cases as finance

def cases(cur,today,parent):
 auth,b=parent.auth,parent.b
 def same_source():
  parent.setup(cur,today);before=b.boundary.snapshot(cur);e=parent.capture(cur,today);parent.checked(e)
  f=e['financial_source'];assert f is not None
  auth.actor(cur);native=cur.execute('select public.erp_cp7_get_finance_report_v1(%s)',(json.dumps(f['dates']),)).fetchone()[0];b.api.admin(cur)
  assert f['report']['snapshot']==native['snapshot']and f['report']['close_preflight']==native['close_preflight']
  assert f['report']['captured_at']==e['analysis']['snapshot']['effective_as_of']
  assert cur.execute('select encode(pg_catalog.sha256(convert_to(jsonb_build_object(\'report\',%s::jsonb-\'captured_at\',\'book_signature\',%s::text)::text,\'UTF8\')),\'hex\')',(json.dumps(f['report']),f['book_signature'])).fetchone()[0]==f['source_hash']
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',accepted_native_owner_report_identical_no_second_money_or_HPP_engine=True,one_source_clock=True,no_business_DML=True)
 def ops_redaction():
  parent.setup(cur,today);subject,role=auth.custom_actor(cur)
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.reports.view')",(role,))
  e=parent.capture(cur,today,subject=subject);parent.checked(e)
  assert e['financial_source']is None and not any(m['value']['unit']=='IDR'for m in e['analysis']['metrics'])
  return dict(status='PASS',custom_four_Ops_plus_report_permission_still_preserves_native_owner_admin_boundary=True,no_financial_operands_or_facts=True)
 def current_rights(preflight=False):
  parent.setup(cur,today);key=uuid.uuid4();e=parent.capture(cur,today,key);assert e['financial_source']is not None
  if preflight:assert e['financial_source']['report']['close_preflight']is not None
  role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(auth.base.OPERATOR_AUTH,)).fetchone()[0]
  permission='finance.period_close.manage'if preflight else'finance.reports.view'
  cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,permission))
  # Operational access remains sufficient for a fresh operational-only run;
  # neither the cached UUID nor its original protected archive may leak money.
  auth.refused(cur,lambda:parent.capture(cur,today,key),'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
  auth.refused(cur,lambda:parent.read(cur,e['run_id']),'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
  fresh=parent.capture(cur,today);parent.checked(fresh)
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
  subject=parent.auth.base.OPERATOR_AUTH;key=uuid.uuid4()
  with tools.connect()as conn,conn.cursor()as cur:
   parent.setup(cur,today);e=parent.capture(cur,today,key);assert e['financial_source']is not None
   role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(subject,)).fetchone()[0];conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=parent.capture(cur,today,key);conn.commit();return r
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
  owner=http.login('OWNER','p15-analysis-financial-owner')
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
