"""Owning supplier payments: actual Native drafts/posts/inverses, no seeded GL.

Declared additional controls only. The preceding source41 remains required.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import copy,json,threading,time,uuid
import psycopg
import cp7_invoice_cases as invoice
import cp7_misc_cases as misc
import cp6_bc_probe as bc
auth,b=invoice.auth,invoice.b
READ='erp_cp7_get_supplier_payments_v1'
WRITE='erp_cp7_reverse_supplier_payment_v1'
PERMISSIONS=('warehouse.procurement.view','finance.ap.view','finance.ap.pay')

def read(cur,f,offset=0,payment=None,q='',subject=None):
 auth.actor(cur,subject)
 r=cur.execute('select public.erp_cp7_get_supplier_payments_v1(%s,%s,%s,%s)',(f['receipt']['purchase_id'],q,offset,payment)).fetchone()[0]
 b.api.admin(cur);return r

def command(cur,p,key=None,subject=None):
 auth.actor(cur,subject)
 r=cur.execute('select public.erp_cp7_reverse_supplier_payment_v1(%s::jsonb,%s)',(json.dumps(p),key or uuid.uuid4())).fetchone()[0]
 b.api.admin(cur);return r

def original_payment(cur,ident):
 zone=cur.execute('show timezone').fetchone()[0];invoice.aa.zone(cur,'UTC')
 try:return cur.execute('select to_jsonb(p)from erp.supplier_payments p where id=%s',(ident,)).fetchone()[0]
 finally:invoice.aa.zone(cur,zone)

def fixture(cur,today,count=26):
 bank=bc.fixture(cur,today,zones=False,purchase=False)
 f=invoice.fixture(cur,today,'100','10',True);f['cash']=bank['cash'];f['cash_before']=str(misc.cash_balance(cur,f['cash']))
 f['physical']=misc.stock_cost(cur)
 for _ in range(count):
  ident=bc.supplier_payment(cur,f['receipt']['purchase_id'],'10.00',f['cash'],f['day']+timedelta(days=2))
  auth.actor(cur);cur.execute('select erp.post_supplier_payment(%s)',(ident,));b.api.admin(cur)
 ids=[str(r[0])for r in cur.execute('select id from erp.supplier_payments where purchase_id=%s order by payment_date,created_at,id',(f['receipt']['purchase_id'],)).fetchall()]
 f['payments']=ids;f['target']=ids[-1];f['original']=original_payment(cur,f['target'])
 f['journal']=str(cur.execute("select id from erp.journal_entries where source_type='SUPPLIER_PAYMENT'and source_id=%s and status='POSTED'",(f['target'],)).fetchone()[0])
 return f

def intent(cur,f,subject=None):
 w=read(cur,f,payment=f['target'],subject=subject);p=next(p for p in w['page']['rows']if p['id']==f['target'])
 return dict(purchase_id=f['receipt']['purchase_id'],payment_id=f['target'],review_token=p['review_token'],reason='Actual supplier payment was recorded incorrectly')

def observe(cur,f):
 w=read(cur,f,payment=f['target']);p=next(p for p in w['page']['rows']if p['id']==f['target'])
 assert misc.stock_cost(cur)==f['physical'],'SUPPLIER_PAYMENT_CHANGED_STOCK_HPP'
 ap=w['Native_AP'];paid=D(ap['paid']);cash=misc.cash_balance(cur,f['cash'])-D(f['cash_before'])
 assert D(ap['final_ap'])==D('1000.00') and D(ap['remaining'])==D('1000.00')-paid
 assert cash==-paid,'SUPPLIER_PAYMENT_NATIVE_CASH_AP_MISMATCH'
 original=original_payment(cur,f['target'])
 assert {k:v for k,v in original.items()if k not in('status','updated_at','row_version')}=={k:v for k,v in f['original'].items()if k not in('status','updated_at','row_version')}
 return dict(workspace=w,payment=p,cash_delta=str(cash),stock_HPP_unchanged=True,
  requests=cur.execute("select count(*)from cp7_invoice.payment_requests where payload->>'purchase_id'=%s",(f['receipt']['purchase_id'],)).fetchone()[0])

def admin_actor(cur):
 subject,role=invoice.admin_actor(cur)
 for permission in PERMISSIONS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
 return subject,role

def cases(cur,today):
 def reader():
  f=fixture(cur,today);before=b.boundary.snapshot(cur);w=read(cur,f,payment=f['target']);assert w['selected_payment_id']==f['target']and w['page']['offset']==25 and len(w['page']['rows'])==1
  assert w['page']['total']=='26' and w['Native_AP']['paid']=='260.00'and w['Native_AP']['remaining']=='740.00'
  auth.actor(cur);native=cur.execute('select public.erp_get_supplier_credit_v1(%s::jsonb)',(json.dumps(dict(supplier_id=w['purchase']['supplier_id'],page=1)),)).fetchone()[0];b.api.admin(cur)
  assert w['Native_AP']==next(p for p in native['purchases']if p['id']==w['purchase']['id'])
  first=read(cur,f);assert len(first['page']['rows'])==25 and f['target']not in[p['id']for p in first['page']['rows']]
  assert b.boundary.snapshot(cur)==before
  # Native review hashes preserve the full rows and are independent of session
  # formatting. The helper must restore the caller zone before Native writes.
  invoice.aa.zone(cur,'America/Los_Angeles');a=read(cur,f,payment=f['target']);assert cur.execute('show timezone').fetchone()[0]=='America/Los_Angeles'
  invoice.aa.zone(cur,'Asia/Jakarta');z=read(cur,f,payment=f['target']);assert a['page']['rows'][0]['review_token']==z['page']['rows'][0]['review_token']
  return dict(status='PASS',actual26_Native_payments_exact_child25_same_Native_AP=True,full_read_no_DML=True,full_snapshot_timezone_stable_caller_zone_restored=True)
 def inverse():
  f=fixture(cur,today);p=intent(cur,f);key=str(uuid.uuid4());one=command(cur,p,key);assert command(cur,p,key)==one
  s=observe(cur,f);assert s['workspace']['Native_AP']['paid']=='250.00'and s['workspace']['Native_AP']['remaining']=='750.00'
  assert s['payment']['status']=='REVERSED'and s['payment']['journal']['id']==f['journal']and s['payment']['inverse']['id']==one['inverse_journal_id']
  assert s['payment']['inverse']['accounting_date']==str(today)and s['requests']==1
  original=cur.execute('select count(*)from erp.journal_entries where reversal_of_id=%s',(f['journal'],)).fetchone()[0];assert original==1
  changed=copy.deepcopy(p);changed['reason']='Different intent';auth.refused(cur,lambda:command(cur,changed,key),'CP7_SUPPLIER_PAYMENT_REQUEST_CHANGED')
  auth.refused(cur,lambda:command(cur,p),'CP7_SUPPLIER_PAYMENT_POSTED_REQUIRED')
  return dict(status='PASS',Native_inverse10_once_paid260_to250_remaining740_to750=True,original_payment_date_cash_and_journal_preserved=True,one_cached_request_exact_payload=True)
 def authority():
  f=fixture(cur,today,2);subject,role=admin_actor(cur);p=intent(cur,f,subject);key=str(uuid.uuid4());command(cur,p,key,subject)
  before=b.boundary.snapshot(cur);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,));revoked=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:command(cur,p,key,subject),'CP7_SUPPLIER_PAYMENT_REVERSE_DENIED');assert b.boundary.snapshot(cur)==revoked
  cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,'finance.ap.pay'))
  assert command(cur,p,key,subject)['payment_id']==f['target'];assert b.boundary.snapshot(cur)==before
  other,custom_role=invoice.receipt.custom(cur,PERMISSIONS);readonly=read(cur,f,subject=other);assert readonly['capabilities']['reverse']is False
  auth.refused(cur,lambda:command(cur,p,key,other),'CP7_SUPPLIER_PAYMENT_REVERSE_DENIED')
  for who in('anon','authenticated','service_role','cp7_capture','cp7_invoice_read'):
   assert not cur.execute("select has_function_privilege(%s,'cp7_invoice.reverse_payment_locked(jsonb)','EXECUTE')",(who,)).fetchone()[0]
  for who in('cp7_invoice_read','cp7_invoice_write'):
   for table in('erp.supplier_payments','erp.journal_entries','erp.journal_lines','erp.material_purchase_headers'):
    assert not cur.execute("select has_table_privilege(%s,%s,'INSERT,UPDATE,DELETE')",(who,table)).fetchone()[0]
  return dict(status='PASS',current_database_pay_before_replay=True,custom_role_readonly_no_inverse=True,private_helper_and_all_ERP_DML_denied=True)
 def atomic():
  f=fixture(cur,today,2);p=intent(cur,f);other=fixture(cur,today,1);f['physical']=misc.stock_cost(cur);bad={**p,'purchase_id':other['receipt']['purchase_id']}
  before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,bad),'CP7_SUPPLIER_PAYMENT_NOT_FOUND');assert b.boundary.snapshot(cur)==before
  peer=next(x for x in f['payments']if x!=f['target']);readpeer=read(cur,f,payment=peer);pp={**p,'payment_id':peer,'review_token':readpeer['page']['rows'][0]['review_token']};command(cur,pp)
  before=b.boundary.snapshot(cur);auth.refused(cur,lambda:command(cur,p),'CP7_SUPPLIER_PAYMENT_STALE_REVIEW');assert b.boundary.snapshot(cur)==before
  p=intent(cur,f)
  cur.execute("create function public.cp7_supplier_outcome_fail()returns trigger language plpgsql as $$begin raise exception 'CP7_TEST_SUPPLIER_OUTCOME_FAILURE';end$$;create trigger cp7_supplier_outcome_fail before update on cp7_invoice.payment_requests for each row execute function public.cp7_supplier_outcome_fail()",prepare=False)
  before=b.boundary.snapshot(cur);count=cur.execute('select count(*)from cp7_invoice.payment_requests').fetchone()[0]
  auth.refused(cur,lambda:command(cur,p),'CP7_TEST_SUPPLIER_OUTCOME_FAILURE')
  assert b.boundary.snapshot(cur)==before and cur.execute('select count(*)from cp7_invoice.payment_requests').fetchone()[0]==count
  assert observe(cur,f)['payment']['status']=='POSTED'
  return dict(status='PASS',foreign_owner_stale_peer_change_rejected_no_partial_effect=True,forced_final_response_failure_restores_all_Native_rows_and_cache=True)
 return [('CP7_SOURCE_SUPPLIER_PAYMENT_READER',reader),('CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE',inverse),('CP7_SOURCE_SUPPLIER_PAYMENT_AUTHORITY',authority),('CP7_SOURCE_SUPPLIER_PAYMENT_ATOMIC',atomic)]

def races(tools,today):
 def same_request():
  with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today,2);p=intent(cur,f);conn.commit()
  barrier=threading.Barrier(2);key=str(uuid.uuid4())
  def send():
   with tools.connect()as conn,conn.cursor()as cur:barrier.wait(5);r=command(cur,p,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:a=pool.submit(send);z=pool.submit(send);assert a.result(30)==z.result(30)
  with tools.connect()as conn,conn.cursor()as cur:
   s=observe(cur,f);assert s['requests']==1 and s['workspace']['Native_AP']['paid']=='10.00'
  return dict(status='PASS',two_actual_sessions_same_UUID_one_Native_inverse_cache_and_cash_effect=True)
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today,2);subject,role=admin_actor(cur);p=intent(cur,f,subject);conn.commit()
  holder=tools.connect();holder.cursor().execute('select 1 from erp.supplier_payments where id=%s for update',(f['target'],))
  pid=threading.Event();waiting=[]
  def send():
   with tools.connect()as conn,conn.cursor()as cur:
    waiting.append(cur.execute('select pg_backend_pid()').fetchone()[0]);pid.set()
    try:command(cur,p,subject=subject);conn.commit();return 'UNEXPECTED_COMMIT'
    except psycopg.Error as e:conn.rollback();return str(e)
  try:
   with ThreadPoolExecutor(max_workers=1)as pool:
    future=pool.submit(send)
    try:
     assert pid.wait(5);deadline=time.monotonic()+8;blocked=False
     with tools.connect()as conn,conn.cursor()as cur:
      while time.monotonic()<deadline:
       blocked=bool(cur.execute('select pg_blocking_pids(%s)',(waiting[0],)).fetchone()[0]);conn.rollback()
       if blocked:break
       time.sleep(.02)
      assert blocked,'SUPPLIER_PAYMENT_ACTUAL_LOCK_WAIT_NOT_OBSERVED'
      cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,));conn.commit()
    finally:holder.rollback()
    result=future.result(30);assert 'CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED'in result or 'CP7_SUPPLIER_PAYMENT_REVERSE_DENIED'in result,result
  finally:holder.rollback();holder.close()
  with tools.connect()as conn,conn.cursor()as cur:
   s=observe(cur,f);assert s['payment']['status']=='POSTED'and s['requests']==0 and s['workspace']['Native_AP']['paid']=='20.00'
  return dict(status='PASS',actual_Native_payment_lock_wait_current_ADMIN_revoke_before_effect=True,no_partial_GL_AP_cash_or_request=True)
 return [('CP7_SOURCE_SUPPLIER_PAYMENT_RACE_SAME_REQUEST',same_request),('CP7_SOURCE_SUPPLIER_PAYMENT_RACE_CURRENT_REVOKE',revoke)]

def http_cases(http,today):
 def flow():
  admin=http.login('ADMIN','cp7-supplier-payment-current')
  with http.connect()as conn,conn.cursor()as cur:
   f=fixture(cur,today,2);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,)).fetchone()[0]
   for key in PERMISSIONS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
   conn.commit()
  args=dict(p_purchase=f['receipt']['purchase_id'],p_q='',p_offset=0,p_payment=f['target'])
  assert http.anon_rpc(READ,args)['status']in(401,403,404)
  before=admin.rpc(READ,args);assert before['status']==200,before;row=next(x for x in before['body']['page']['rows']if x['id']==f['target'])
  p=dict(purchase_id=f['receipt']['purchase_id'],payment_id=f['target'],review_token=row['review_token'],reason='Actual Auth supplier inverse')
  intentargs=dict(p_payload=p,p_request=str(uuid.uuid4()));one=admin.rpc(WRITE,intentargs);assert one['status']==200,one
  assert admin.rpc(WRITE,intentargs)['body']==one['body']
  with http.connect()as conn,conn.cursor()as cur:
   s=observe(cur,f);assert s['payment']['status']=='REVERSED'and s['requests']==1
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,));conn.commit()
  assert admin.rpc(WRITE,intentargs)['status']==403
  readonly=admin.rpc(READ,args);assert readonly['status']==200 and readonly['body']['capabilities']['reverse']is False
  return dict(status='PASS',real_Auth_HTTP_Native_invoice_AP_inverse_exact_replay_current_pay_revocation=True)
 return [('CP7_SOURCE_SUPPLIER_PAYMENT_HTTP_CURRENT_REPLAY',flow)]
