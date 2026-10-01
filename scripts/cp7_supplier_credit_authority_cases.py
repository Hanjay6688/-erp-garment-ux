"""Actual Native authority retirement during observed credit lock waits.

All fixtures and outcomes live only on the disposable full F03 stack. A denial
before the call is deliberately insufficient: the actor enters while permitted,
the exact worker is observed blocked, then another committed session revokes it.
"""
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import time,uuid
import psycopg
import cp6_bf_supplier_probe as credit

def wait_revoke(tools,today,wait_kind,revoke_user=False):
 with tools.connect()as conn,conn.cursor()as cur:
  f=credit.fixture(cur,today)
  role=credit.one(cur,"select id from erp.app_roles where role_code='ADMIN' and is_active")
  subject=str(uuid.uuid4());actor=str(uuid.uuid4())
  cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values(%s,%s,'Disposable F03 authority actor','ADMIN',%s,true)",(actor,subject,role))
  assert credit.one(cur,"select count(*) from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",role)==1
  if wait_kind=='journal_row':credit.call(cur,credit.payload(cur,f,[(f['purchases'][1],'12.00')]))
  p=credit.payload(cur,f,[(f['purchases'][2]if wait_kind=='journal_row'else f['purchases'][1],'20.00')]);key=str(uuid.uuid4());saved=None
  if wait_kind=='cached_request':saved=credit.call(cur,p,key,subject)
  before=credit.state(cur,f);moves=credit.one(cur,'select count(*) from erp.bf_supplier_credit_moves_v1 where return_id=%s',f['ret'])
  conn.commit()
 queue=Queue()
 with tools.connect()as holder,holder.cursor()as cur:
  holder_pid=holder.info.backend_pid
  if wait_kind in('cached_request','fresh_request'):
   cur.execute("select pg_advisory_xact_lock(hashtextextended('BF:REQUEST:'||%s,0))",(key,))
  elif wait_kind=='source_row':cur.execute('select id from erp.material_supplier_returns where id=%s for update',(f['ret'],))
  elif wait_kind=='target_row':cur.execute('select id from erp.material_purchase_headers where id=%s for update',(f['purchases'][1],))
  elif wait_kind=='journal_row':
   cur.execute("select account_id from erp.account_daily_balances where account_id=erp.account_id('AP_SUPPLIER')and balance_date=%s for update",(today,));assert cur.rowcount==1
  else:raise ValueError('Unknown exact wait kind')
  def send():
   with tools.connect()as worker,worker.cursor()as cursor:
    cursor.execute("set statement_timeout='20s'")
    queue.put(worker.info.backend_pid)
    try:
     result=credit.call(cursor,p,key,subject);worker.commit()
     return dict(committed=True,response=result)
    except psycopg.Error as error:
     worker.rollback()
     return dict(committed=False,sqlstate=error.sqlstate,message=error.diag.message_primary)
  with ThreadPoolExecutor(max_workers=1)as pool:
   job=pool.submit(send);worker_pid=queue.get(timeout=5);blocked=None;deadline=time.monotonic()+8
   try:
    while time.monotonic()<deadline:
     with tools.connect()as observer,observer.cursor()as cursor:
      row=cursor.execute('select wait_event_type,wait_event,pg_blocking_pids(pid) from pg_stat_activity where pid=%s',(worker_pid,)).fetchone()
     if row and row[0]=='Lock'and holder_pid in row[2]:
      blocked=dict(wait_event_type=row[0],wait_event=row[1],holder_blocks_exact_worker=True);break
     time.sleep(.05)
    assert blocked,'Exact credit worker was not observed blocked by holder'
    with tools.connect()as revoker,revoker.cursor()as cursor:
     if revoke_user:cursor.execute('update erp.app_users set is_active=false where id=%s',(actor,))
     else:cursor.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,))
     assert cursor.rowcount==1;revoker.commit()
   finally:holder.rollback()
   outcome=job.result(25)
 with tools.connect()as observer,observer.cursor()as cur:
  after=credit.state(cur,f);after_moves=credit.one(cur,'select count(*) from erp.bf_supplier_credit_moves_v1 where return_id=%s',f['ret'])
  cached=cur.execute('select response from erp.bf_requests_v1 where request_id=%s',(key,)).fetchone()
  observer.rollback()
 expected=(outcome.get('sqlstate')=='P0001'and outcome.get('message')=='OWNER or ADMIN access required')if revoke_user else(outcome.get('sqlstate')=='42501'and outcome.get('message')=='PERMISSION_DENIED: finance.ap.pay')
 checks=dict(actual_wait_observed=bool(blocked),revocation_committed_before_release=True,current_authority_refused=not outcome['committed']and expected,
  native_money_stock_cost_unchanged=after==before,allocation_events_unchanged=after_moves==moves,
  existing_response_preserved=cached is not None and cached[0]==saved if saved is not None else cached is None)
 return dict(status='PASS'if all(checks.values())else'FAIL',checks=checks,wait_kind=wait_kind,revoked='APP_USER_ACTIVE'if revoke_user else'finance.ap.pay',
  observed_wait=blocked,outcome=outcome,before=before,after=after,move_count_before=moves,move_count_after=after_moves,
  actual_Native_call=True,test_claims_not_real_Auth_HTTP=True,full_family_acceptance=False)

def races(tools,today):
 rows=[('F03_CREDIT_AUTHORITY_'+kind.upper(),lambda kind=kind:wait_revoke(tools,today,kind))for kind in('cached_request','fresh_request','source_row','target_row','journal_row')]
 rows.append(('F03_CREDIT_ACTOR_REVOKED_DURING_CACHED_REQUEST',lambda:wait_revoke(tools,today,'cached_request',True)))
 return rows
