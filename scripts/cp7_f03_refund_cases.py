"""F03 ALL-S03: lawful source-owned old-sale credit/refund on the full stack.

These are actual Native/public-command executions of declared disposable
fixtures. They never turn current paid-sale refusal into a refund policy.
"""
import uuid,threading,time
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
import psycopg
import cp6_bb_probe as bb

def prepare(cur,today):
 f=bb.financial_fixture(cur,today,legacy=[('CUSTOMER_RECEIVABLE','LEGACY-E03-PAID','100.00')],
  rights=[('E03-RETURN','LEGACY-E03-PAID','3','10.00','6.00')],extra=bb.product_masters())
 w=bb.ws(cur,f['batch']);f.update(today=str(today),right_id=w['sale_return_rights'][0]['id'],
  location_id=str(cur.execute('select id from erp.locations where location_code=%s',(f['code']+'G',)).fetchone()[0]),
  before_accounts=bb.gl(cur),before_bank=str(bb.bank(cur,f)))
 return f

def payload(cur,f,**values):
 return dict(batch_id=f['batch'],expected_revision=bb.revision(cur,f['batch']),**values)

def receive_payload(cur,f):
 return payload(cur,f,operation='RECEIVE',right_id=f['right_id'],qty='3',location_id=f['location_id'],
  effective_date=f['today'],reason='Actual physical return of the three lawful old-sale pieces')

def receive(cur,f):return bb.api.call(cur,'OPENING_RETURN',receive_payload(cur,f))

def observe(cur,f):
 bb.api.admin(cur);w=bb.ws(cur,f['batch']);credits=w['customer_credits'];receipts=cur.execute(
  'select r.id::text,r.lot_id::text,r.status,r.credit_id::text from erp.bb_opening_sale_return_receipts_v1 r where r.right_id=%s order by r.id',(f['right_id'],)).fetchall()
 lots=[r[1]for r in receipts];qty=cur.execute('select coalesce(sum(qty_signed),0)from erp.fg_stock_movements where lot_id=any(%s::uuid[])',(lots,)).fetchone()[0]
 return dict(credits=credits,bank=str(bb.bank(cur,f)),accounts=bb.gl(cur),company_returned_pcs=int(qty),
  receipts=[dict(id=i,lot_id=l,status=s,credit_id=c)for i,l,s,c in receipts],
  refund_events=cur.execute('select count(*)from erp.bb_customer_credit_events_v1 where credit_id in(select id from erp.bb_customer_credits_v1 where batch_id=%s)',(f['batch'],)).fetchone()[0])

def refund_payload(cur,f,credit,amount='10.00'):
 return payload(cur,f,operation='REFUND',credit_id=credit,amount=amount,effective_date=f['today'],
  cash_account_id=f['cash'],reason='Explicit refund of this source-owned customer credit')

def assert_refund(cur,f,amount):
 now=observe(cur,f);assert len(now['credits'])==1 and now['company_returned_pcs']==3,now
 assert D(now['credits'][0]['remaining_amount'])==D(30)-D(amount)and D(now['bank'])==D(f['before_bank'])-D(amount),now
 assert now['credits'][0]['origin']=='RETURN',now
 return now

def cases(cur,today):
 def legacy():
  result=bb.return_right(cur,today,'LEGACY');assert result['status']=='PASS',result
  return dict(result,journey='F03_E03_LAWFUL_FULLY_PAID_OLD_SALE_RETURN_CREDIT_REFUND_AND_INVERSE',
   Native_public_commands=True,current_paid_sale_policy_unchanged=True)
 def imported():
  result=bb.imported_credit(cur,today);assert result['status']=='PASS',result
  return dict(result,journey='F03_E03_IMPORTED_REFUND15_OF_LAWFUL_REMAINING25_AND_INVERSE',
   Native_public_commands=True,no_new_revenue_or_stock_for_previously_received_return=True)
 return [('F03_E03_NATIVE_LEGACY_REFUND',legacy),('F03_E03_NATIVE_IMPORTED_REFUND',imported)]

def races(tools,today):
 def capacity():
  with tools.connect()as conn,conn.cursor()as cur:
   f=prepare(cur,today);r=receive(cur,f);p=refund_payload(cur,f,r['credit_id'],'20.00');conn.commit()
  barrier=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:
    barrier.wait(timeout=5)
    try:out=bb.api.call(cur,'CUSTOMER_CREDIT',p,uuid.uuid4());conn.commit();return out
    except psycopg.Error as e:conn.rollback();return str(e)
  with tools.connect()as holder,holder.cursor()as h:
   h.execute('select id from erp.bb_customer_credits_v1 where id=%s for update',(r['credit_id'],))
   with ThreadPoolExecutor(max_workers=2)as pool:
    jobs=[pool.submit(send)for _ in range(2)];blocked=False;deadline=time.monotonic()+10
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       blocked=c.execute("select count(*)>=2 from pg_stat_activity where datname=current_database()and cardinality(pg_blocking_pids(pid))>0 and query like '%%erp_save_initial_import_action_v1%%'").fetchone()[0]
       if blocked:break
       time.sleep(.05)
      assert blocked,'The actual source-credit lock did not block both public refund requests'
    finally:holder.commit()
    out=[j.result(45)for j in jobs]
  assert sum(isinstance(x,dict)for x in out)==1,out
  # The second exact reviewed batch can legitimately fail on its revision
  # after the first commit, or on the remaining credit after its source lock.
  assert any('BB_RETURN_CREDIT_EXCEEDS_REMAINING'in str(x)or 'STALE_REVISION'in str(x)or 'STALE_VERSION'in str(x)for x in out),out
  with tools.connect()as conn,conn.cursor()as cur:
   state=assert_refund(cur,f,'20.00');assert state['refund_events']==1
  return dict(status='PASS',two_real_connections=True,observed_actual_source_credit_wait_for_both_requests=True,lawful_credit30_two_competing_refunds20_one_effect=True,
   remaining_credit10_bank80_company_FG3_unchanged=True)
 return [('F03_E03_REAL_REFUND_CAPACITY_RACE',capacity)]

def http_cases(http,today):
 def source_refund():
  owner=http.login('OWNER','f03-e03-refund');viewer=http.login('VIEWER','f03-e03-refund-viewer')
  with http.connect()as conn,conn.cursor()as cur:
   f=prepare(cur,today);p=receive_payload(cur,f);conn.commit()
  args=dict(p_action='OPENING_RETURN',p_payload=p,p_client_request_id=str(uuid.uuid4()))
  first=owner.rpc('erp_save_initial_import_action_v1',args);assert first['status']==200,first
  assert owner.rpc('erp_save_initial_import_action_v1',args)['body']==first['body']
  with http.connect()as conn,conn.cursor()as cur:p=refund_payload(cur,f,first['body']['credit_id']);conn.commit()
  args=dict(p_action='CUSTOMER_CREDIT',p_payload=p,p_client_request_id=str(uuid.uuid4()))
  assert http.anon_rpc('erp_save_initial_import_action_v1',args)['status']in(401,403)
  assert viewer.rpc('erp_save_initial_import_action_v1',args)['status']==403
  one=owner.rpc('erp_save_initial_import_action_v1',args);assert one['status']==200,one
  assert owner.rpc('erp_save_initial_import_action_v1',args)['body']==one['body']
  with http.connect()as conn,conn.cursor()as cur:
   state=assert_refund(cur,f,'10.00');assert state['refund_events']==1
   cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_save_initial_import_action_v1',args)['status']==403
  assert owner.rpc('erp_get_initial_import_workspace_v1',dict(p_batch_id=f['batch']))['status']==403
  return dict(status='PASS',actual_Auth_HTTP=True,lawful_source_return3_credit30_refund10_remaining20_bank90=True,
   exact_UUID_replay_once=True,anonymous_viewer_current_deactivation_denied=True,current_authority_before_cached_refund=True)
 return [('F03_E03_REAL_HTTP_SOURCE_REFUND',source_refund)]
