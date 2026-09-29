"""Native close/reopen invariants, immutable archives and exact recovery."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import copy,json,threading,time,uuid
import psycopg
import cp7_finance_cases as finance
import cp7_procurement_cases as receipt
b,auth,aw=finance.b,finance.auth,finance.aw

def read(cur,day,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_period_control_v1(%s)',(day,)).fetchone()[0];b.api.admin(cur);return r

def command(cur,action,payload,key=None,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_save_period_control_v1(%s,%s,%s)',(action,json.dumps(payload),key or uuid.uuid4())).fetchone()[0];b.api.admin(cur);return r

def intent(state,action='CLOSE',target=None):
 return dict(through=state['through'] if action=='CLOSE' else target,review_through=state['through'],review_token=state['review_token'],reason='P13 period reviewed against native ledger and completeness')

def ready(cur,today):
 f,_=aw.recost_fixture(cur,today,False);day=f['purchase_day']+timedelta(days=1);aw.quiet_seed(cur,f['purchase_day'],day)
 r=read(cur,day);assert r['preflight']['status']=='READY' and r['preflight']['date_allowed'],r
 return f,day,r

def filings(cur):return cur.execute("select coalesce(jsonb_agg(to_jsonb(f) order by f.filed_at,f.id),'[]') from erp.accounting_close_filings_v1 f").fetchone()[0]
def business(cur):
 return dict(accounts={k:str(v) for k,v in finance.cmd.accounts(cur).items()},material=cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(m) order by m.id)::text,'[]')) from erp.material_stock_movements m").fetchone()[0],fg=cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(m) order by m.id)::text,'[]')) from erp.fg_stock_movements m").fetchone()[0])
def late(cur,f,process=False):
 aw.chain.prior.post_purchase(cur,f['material'],aw.chain.production.at(f['purchase_day'],22),unit_price=12);b.api.admin(cur)
 if process:aw.chain.production.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');b.api.admin(cur)

def cases(cur,today):
 def lifecycle():
  f,day,initial=ready(cur,today);before=business(cur);old=filings(cur)
  r=command(cur,'CLOSE',intent(initial));assert r['closed_through']==str(day) and r['filing_id']
  first=filings(cur);assert len(first)==len(old)+1 and first[-1]['id']==r['filing_id'] and first[-1]['readiness']['status']=='READY' and business(cur)==before
  command(cur,'REOPEN',intent(read(cur,day),'REOPEN',initial['control']['closed_through']));assert read(cur,day)['control']['closed_through']==initial['control']['closed_through'] and filings(cur)==first
  second=command(cur,'CLOSE',intent(read(cur,day)));assert second['filing_id']!=r['filing_id'] and len(filings(cur))==len(old)+2 and business(cur)==before
  return dict(status='PASS',native_close_reopen_reclose=True,two_distinct_immutable_archives=True,reopen_keeps_filed_history=True,GL_and_all_stock_unchanged=True)
 def replay():
  f,day,initial=ready(cur,today);p=intent(initial);key=str(uuid.uuid4());closed=command(cur,'CLOSE',p,key);after=filings(cur)
  assert command(cur,'CLOSE',p,key)==closed and filings(cur)==after
  command(cur,'REOPEN',intent(read(cur,day),'REOPEN',initial['control']['closed_through']));before=b.boundary.snapshot(cur)
  assert command(cur,'CLOSE',p,key)==closed and b.boundary.snapshot(cur)==before and read(cur,day)['control']['closed_through']==initial['control']['closed_through']
  bad=dict(p,reason='Changed replay intent');auth.refused(cur,lambda:command(cur,'CLOSE',bad,key),'CP7_PERIOD_REQUEST_CHANGED');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',same_UUID_one_filing=True,old_commit_replay_after_reopen_is_metadata_not_reclose=True,changed_payload_refused=True)
 def stale():
  f,day,initial=ready(cur,today);old_intent=intent(initial);late(cur,f,True);changed=read(cur,day)
  assert changed['preflight']['status']=='READY' and changed['review_token']!=initial['review_token']
  before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'CLOSE',old_intent),'CP7_PERIOD_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
  initial=changed;p=intent(initial);command(cur,'CLOSE',p);command(cur,'REOPEN',intent(read(cur,day),'REOPEN',initial['control']['closed_through']))
  current=read(cur,day);assert current['control']['closed_through']==initial['control']['closed_through'] and current['review_token']!=initial['review_token']
  before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'CLOSE',p),'CP7_PERIOD_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
  r=command(cur,'CLOSE',intent(current));before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'CLOSE',intent(read(cur,day))),'CLOSE_ALREADY_CLOSED');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',READY_financial_change_retires_old_review=True,same_cutoff_after_control_change_retires_old_review=True,already_closed_cannot_file_twice=True,fresh_review_continues=True)
 def blocked():
  f,day,initial=ready(cur,today);late(cur,f);current=read(cur,day);assert current['preflight']['status']!='READY',current
  before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'CLOSE',intent(current)),'CLOSE_BLOCKED');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',native_pending_cost_or_policy_blocker_refuses_close_atomically=True,no_new_filing_or_control_change=True)
 def input_guards():
  f,day,state=ready(cur,today);before=b.boundary.snapshot(cur);p=intent(state)
  for bad in (dict(p,reason=''),dict(p,review_token='bad'),dict(p,extra='x'),dict(p,through=None)):
   auth.refused(cur,lambda:command(cur,'CLOSE',bad),'CP7_PERIOD_')
  auth.refused(cur,lambda:command(cur,'CLOSE',dict(p,through=str(day+timedelta(days=1)))),'CP7_PERIOD_CLOSE_REVIEW_DATE')
  auth.refused(cur,lambda:read(cur,today+timedelta(days=1)),'CP7_PERIOD_REVIEW_DATE')
  assert b.boundary.snapshot(cur)==before
  today_state=read(cur,today);auth.refused(cur,lambda:command(cur,'CLOSE',intent(today_state)),'sebelum hari ini');assert b.boundary.snapshot(cur)==before
  command(cur,'CLOSE',p);before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,'REOPEN',intent(read(cur,day),'REOPEN',str(day))),'Tanggal reopen harus lebih awal');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',closed_exact_payload_dates_reasons_and_backward_reopen_required=True,invalid_commands_have_no_partial_effects=True)
 def access():
  f,day,state=ready(cur,today)
  custom,_=receipt.custom(cur,('finance.reports.view','finance.period_close.manage'));before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:read(cur,day,custom),'CP7_PERIOD_OWNER_ADMIN_REQUIRED')
  auth.refused(cur,lambda:command(cur,'CLOSE',intent(state),subject=custom),'CP7_PERIOD_OWNER_ADMIN_REQUIRED');assert b.boundary.snapshot(cur)==before
  ops,_=receipt.custom(cur,('finance.reports.view',));auth.refused(cur,lambda:read(cur,day,ops),'CP7_PERIOD_ACCESS_DENIED')
  def service_claim():
   auth.actor(cur,role='service_role');cur.execute('select public.erp_cp7_get_period_control_v1(%s)',(day,))
  auth.refused(cur,service_claim,'CP7_PERIOD_ACCESS_DENIED')
  return dict(status='PASS',live_both_permissions_and_native_owner_admin_required=True,no_custom_role_or_service_bypass=True)
 def private():
  for principal in ('anon','authenticated','service_role','cp7_capture','cp7_finance_read'):
   for sig in ('cp7_period.lock_current()','cp7_period.command(text,jsonb,uuid)'):
    assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(principal,sig)).fetchone()[0]
  for principal in ('cp7_period_read','cp7_period_write'):
   assert not cur.execute("select exists(select 1 from pg_tables where schemaname='erp' and(has_table_privilege(%s,quote_ident(schemaname)||'.'||quote_ident(tablename),'INSERT,UPDATE,DELETE,TRUNCATE')))",(principal,)).fetchone()[0]
  for sig in ('erp.close_accounting_through(date,text)','erp.reopen_accounting_through(date,text)'):
   assert not cur.execute("select has_function_privilege('cp7_period_read',%s,'EXECUTE')",(sig,)).fetchone()[0]
  return dict(status='PASS',private_lock_and_command_unreachable=True,no_facade_ERP_DML=True,financial_report_and_period_read_roles_cannot_close=True)
 def late_archive():
  f,day,state=ready(cur,today);result=command(cur,'CLOSE',intent(state));original=finance.read(cur,day,filing_id=result['filing_id'])['filing'];late(cur,f,True)
  current=finance.read(cur,day,filing_id=result['filing_id']);assert current['filing']==original and current['snapshot']['data_confidence']['status']=='READY' and current['snapshot']['data_confidence']['changed_since_filing']
  before=filings(cur);command(cur,'REOPEN',intent(read(cur,day),'REOPEN',state['control']['closed_through']));assert filings(cur)==before
  return dict(status='PASS',actual_CP7_filing_stays_immutable_after_native_late_recost=True,corrected_READY_retains_change_marker=True,reopen_preserves_original_archive=True)
 return [('P13_PERIOD_CLOSE_REOPEN',lifecycle),('P13_PERIOD_REPLAY',replay),('P13_PERIOD_STALE',stale),('P13_PERIOD_BLOCKED',blocked),('P13_PERIOD_INVALID',input_guards),('P13_PERIOD_ACCESS',access),('P13_PERIOD_PRIVATE',private),('P13_PERIOD_LATE_ARCHIVE',late_archive)]

def races(tools,today):
 def double_close():
  with tools.connect()as conn,conn.cursor()as cur:f,day,state=ready(cur,today);before=len(filings(cur));conn.commit()
  gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:
    gate.wait()
    try:r=command(cur,'CLOSE',intent(state));conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
  with ThreadPoolExecutor(max_workers=2)as pool:jobs=[pool.submit(send)for _ in range(2)];results=[j.result(30)for j in jobs]
  assert sum(isinstance(r,dict)for r in results)==1 and any('CP7_PERIOD_REVIEW_CHANGED'in r for r in results if isinstance(r,str)),results
  with tools.connect()as conn,conn.cursor()as cur:assert len(filings(cur))==before+1
  return dict(status='PASS',two_real_close_transactions_one_filing=True,loser_must_review_changed_period=True)
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:
   f,day,state=ready(cur,today);before=len(filings(cur));subject,_=receipt.custom(cur,('finance.reports.view','finance.period_close.manage'));role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
   # Native ADMIN admits the lifecycle but does not receive close management
   # in the seed. Grant this disposable fixture explicitly before revoking it.
   for permission in ('finance.reports.view','finance.period_close.manage'):
    cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s) on conflict do nothing',(role,permission))
   cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));state=read(cur,day,subject);conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute('select singleton_id from erp.accounting_period_control where singleton_id=1 for update')
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=command(cur,'CLOSE',intent(state),subject=subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
   with ThreadPoolExecutor(max_workers=1)as pool:
    future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
    while time.monotonic()<deadline:
     with tools.connect()as watcher,watcher.cursor()as c:
      blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and query like 'select public.erp_cp7_save_period_control_v1%')").fetchone()[0]
     if blocked:break
     time.sleep(.05)
    try:
     assert blocked,'Native period lock wait not observed'
     with tools.connect()as other,other.cursor()as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.period_close.manage'",(role,));other.commit()
    finally:holder.rollback()
    result=future.result(30)
  assert 'CP7_PERIOD_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:assert len(filings(cur))==before
  return dict(status='PASS',revocation_during_observed_control_lock_wait_refused=True,no_filing=True)
 return [('P13_PERIOD_RACE_CLOSE',double_close),('P13_PERIOD_RACE_REVOKE',revoke)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p13-period-owner')
  with http.connect()as conn,conn.cursor()as cur:f,day,state=ready(cur,today);initial=len(filings(cur));conn.commit()
  q=dict(p_through=str(day));r=owner.rpc('erp_cp7_get_period_control_v1',q);assert r['status']==200,r
  p=intent(r['body']);args=dict(p_action='CLOSE',p_payload=p,p_request=str(uuid.uuid4()))
  assert http.anon_rpc('erp_cp7_save_period_control_v1',args)['status']in(401,403,404)
  closed=owner.rpc('erp_cp7_save_period_control_v1',args);assert closed['status']==200,closed
  assert owner.rpc('erp_cp7_save_period_control_v1',args)['body']==closed['body']
  with http.connect()as conn,conn.cursor()as cur:assert len(filings(cur))==initial+1;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_save_period_control_v1',args)['status']==403
  assert owner.rpc('erp_cp7_get_period_control_v1',q)['status']==403
  return dict(status='PASS',real_auth_review_close_exact_replay_one_archive=True,anonymous_and_deactivated_identity_refused_before_cached_outcome=True)
 return [('P13_PERIOD_HTTP',flow)]
