"""New supplier cash/bank payment through the owning CP7 command; Native posts it.

Receipt 100 x 10 FINAL gives supplier AP 1000. Payments 400 then 600 settle it exactly. Every refusal leaves
Native payments, journals, request records and stock/HPP unchanged. No GL row is seeded and no Native
definition changes: erp.post_supplier_payment remains the AP-capacity and journal authority.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import json,threading,time,uuid
import psycopg
import cp7_supplier_payment_cases as supplier
import cp7_invoice_cases as invoice
import cp7_misc_cases as misc
import cp6_bc_probe as bc
auth,b=invoice.auth,invoice.b
READ='erp_cp7_get_supplier_payment_create_v1'
WRITE='erp_cp7_create_supplier_payment_v1'
NOTE='Transfer bank pelunasan supplier'
EXPECTED=10
REQUIRED=dict(native=4,races=3,http=1,browser=2)

def read(cur,f,subject=None,**q):
 auth.actor(cur,subject)
 r=cur.execute('select public.erp_cp7_get_supplier_payment_create_v1(%s)',(json.dumps(dict(purchase_id=f['receipt']['purchase_id'],**q)),)).fetchone()[0]
 b.api.admin(cur);return r

def command(cur,p,key=None,subject=None):
 auth.actor(cur,subject)
 r=cur.execute('select public.erp_cp7_create_supplier_payment_v1(%s::jsonb,%s)',(json.dumps(p),key or uuid.uuid4())).fetchone()[0]
 b.api.admin(cur);return r

def fixture(cur,today):
 bank=bc.fixture(cur,today,zones=False,purchase=False)
 f=invoice.fixture(cur,today,'100','10',True);f['cash']=bank['cash']
 f['coa']=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(f['cash'],)).fetchone()[0])
 f['cash_before']=misc.cash_balance(cur,f['cash']);f['physical']=supplier.physical_state(cur)
 f['received']=cur.execute('select physical_at from erp.material_purchase_headers where id=%s',(f['receipt']['purchase_id'],)).fetchone()[0]
 return f

def at(cur,minutes=1):
 return (cur.execute('select statement_timestamp()').fetchone()[0]-timedelta(minutes=minutes)).isoformat()

def payload(cur,f,amount,subject=None,**extra):
 w=read(cur,f,subject)
 return dict(dict(purchase_id=f['receipt']['purchase_id'],review_token=w['review_token'],amount=amount,cash_account_id=f['cash'],payment_date=at(cur),note=NOTE),**extra)

def state(cur,f):
 """Native payments, their journals and request records of this receipt, compared whole."""
 pid=f['receipt']['purchase_id']
 return dict(payments=cur.execute("select coalesce(jsonb_agg(to_jsonb(p)-'updated_at' order by p.id),'[]') from erp.supplier_payments p where p.purchase_id=%s",(pid,)).fetchone()[0],
  journals=cur.execute("select coalesce(jsonb_agg(jsonb_build_object('id',j.id,'status',j.status,'lines',(select jsonb_agg(jsonb_build_array(l.account_id,l.debit,l.credit)order by l.id)from erp.journal_lines l where l.journal_entry_id=j.id))order by j.id),'[]') from erp.journal_entries j join erp.supplier_payments p on p.id=j.source_id where p.purchase_id=%s",(pid,)).fetchone()[0],
  requests=cur.execute("select count(*) from cp7_supplier_payment_create.requests where payload->>'purchase_id'=%s",(pid,)).fetchone()[0],
  header=cur.execute('select payment_status from erp.material_purchase_headers where id=%s',(pid,)).fetchone()[0])

def observe(cur,f,paid):
 w=read(cur,f);ap=w['Native_AP'];cash=misc.cash_balance(cur,f['cash'])-f['cash_before']
 assert D(ap['final_ap'])==1000 and D(ap['paid'])==D(paid) and D(ap['remaining'])==1000-D(paid),('SUPPLIER_PAYMENT_CREATE_AP',ap)
 assert cash==-D(paid),('SUPPLIER_PAYMENT_CREATE_CASH',cash)
 assert supplier.physical_state(cur)==f['physical'],'SUPPLIER_PAYMENT_CREATE_CHANGED_STOCK_HPP'
 assert w['eligible']==(D(paid)<1000)
 return w

def admin(cur,pay=True):
 subject,role=invoice.admin_actor(cur)
 for permission in supplier.PERMISSIONS if pay else supplier.PERMISSIONS[:2]:
  cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
 if not pay:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,))
 return subject,role

def legacy_direct_path(cur,f,subject):
 """Observation, not a control of the new command. The hosted-faithful clone keeps authenticated USAGE on erp
 (G-01). First run 4042235f showed a direct DRAFT insert by role authenticated does not raise. Record whether that
 role, without finance.ap.pay, could also post it through Native; always rolled back. PostgREST exposes only public."""
 out={}
 b.api.admin(cur);cur.execute('savepoint legacy_direct')
 try:
  auth.actor(cur,subject)
  ident=cur.execute("insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id)values(%s,%s,now(),1,%s)returning id",(f['receipt']['purchase_id'],'LEGACY-'+uuid.uuid4().hex[:8],f['cash'])).fetchone()[0]
  out['authenticated_direct_draft_insert']='ALLOWED'
  try:cur.execute('select erp.post_supplier_payment(%s)',(ident,));out['native_post_without_finance_ap_pay']='POSTED'
  except psycopg.Error as e:out['native_post_without_finance_ap_pay']='REFUSED: '+str(e).splitlines()[0]
 except psycopg.Error as e:out['authenticated_direct_draft_insert']='REFUSED: '+str(e).splitlines()[0]
 finally:cur.execute('rollback to savepoint legacy_direct');cur.execute('release savepoint legacy_direct');b.api.admin(cur)
 out['rolled_back']=True;out['app_http_surface']='PostgREST exposes public only; erp tables are not an application route'
 return out

def cases(cur,today):
 refused=auth.refused
 def exact():
  f=fixture(cur,today);w=read(cur,f)
  assert w['contract_version']=='cp7.supplier-payment-create-workspace.v1'and w['eligible']and w['can_create']and w['Native_AP']['remaining']=='1000.00'
  assert w['purchase']['id']==f['receipt']['purchase_id']and any(x['id']==f['cash']for x in w['cash_accounts']['rows'])or int(w['cash_accounts']['total'])>25
  p=payload(cur,f,'400.00');key=uuid.uuid4();r=command(cur,p,key)
  assert r['contract_version']=='cp7.supplier-payment-create.v1'and r['action']=='CREATE'and r['status']=='POSTED'and r['amount']=='400.00'and r['remaining_after']=='600.00'and r['request_payload']==p
  row=cur.execute('select status,amount,cash_account_id::text,notes,payment_number from erp.supplier_payments where id=%s',(r['payment_id'],)).fetchone()
  assert row==('POSTED',D('400.00'),f['cash'],NOTE,'B-'+str(key).replace('-','')),row
  lines=cur.execute("select a.account_type,l.debit,l.credit,l.account_id::text from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id join erp.chart_accounts a on a.id=l.account_id where j.source_type='SUPPLIER_PAYMENT'and j.source_id=%s and j.status='POSTED' order by l.debit desc",(r['payment_id'],)).fetchall()
  assert [(x[1],x[2])for x in lines]==[(D(400),D(0)),(D(0),D(400))]and lines[0][3]==cur.execute("select erp.account_id('AP_SUPPLIER')::text").fetchone()[0]and lines[1][3]==f['coa'],lines
  observe(cur,f,400);before=state(cur,f)
  assert command(cur,p,key)==r and state(cur,f)==before,'SUPPLIER_PAYMENT_CREATE_REPLAY_SECOND_EFFECT'
  changed=refused(cur,lambda:command(cur,dict(p,amount='401.00'),key),'CP7_SUPPLIER_PAYMENT_REQUEST_CHANGED')
  stale=refused(cur,lambda:command(cur,dict(p,amount='10.00')),'CP7_SUPPLIER_PAYMENT_STALE_REVIEW')
  assert state(cur,f)==before
  rest=command(cur,payload(cur,f,'600.00'));assert rest['remaining_after']=='0.00'
  w=observe(cur,f,1000);assert w['eligible']is False and state(cur,f)['header']=='PAID'
  done=refused(cur,lambda:command(cur,payload(cur,f,'0.01')),'CP7_SUPPLIER_PAYMENT_NOTHING_PAYABLE')
  return dict(status='PASS',workspace_AP_token_banks=True,Native_post_AP_SUPPLIER_debit_cash_credit=True,same_UUID_replay_no_second_effect=True,
   changed_payload_refused=changed,stale_review_refused=stale,settled_exactly_paid_status=True,nothing_payable_refused=done,stock_HPP_unchanged=True)
 def refusals():
  f=fixture(cur,today);before=state(cur,f);cash=misc.cash_balance(cur,f['cash'])
  inactive=bc.bank_account(cur,'P18X'+uuid.uuid4().hex[:8]);cur.execute('update erp.cash_accounts set is_active=false where id=%s',(inactive,))
  received=f['received']-timedelta(minutes=1)
  out=dict(
   over=refused(cur,lambda:command(cur,payload(cur,f,'1000.01')),'CP7_SUPPLIER_PAYMENT_EXCEEDS_REMAINING'),
   future=refused(cur,lambda:command(cur,dict(payload(cur,f,'1.00'),payment_date=(cur.execute('select statement_timestamp()').fetchone()[0]+timedelta(minutes=5)).isoformat())),'CP7_SUPPLIER_PAYMENT_DATE_FUTURE'),
   before_receipt=refused(cur,lambda:command(cur,dict(payload(cur,f,'1.00'),payment_date=received.isoformat())),'CP7_SUPPLIER_PAYMENT_BEFORE_RECEIPT'),
   inactive_bank=refused(cur,lambda:command(cur,dict(payload(cur,f,'1.00'),cash_account_id=str(inactive))),'CP7_SUPPLIER_PAYMENT_CASH_ACCOUNT_INACTIVE'),
   no_cents=refused(cur,lambda:command(cur,payload(cur,f,'1')),'CP7_SUPPLIER_PAYMENT_CREATE_FIELDS'),
   zero=refused(cur,lambda:command(cur,payload(cur,f,'0.00')),'CP7_SUPPLIER_PAYMENT_CREATE_FIELDS'),
   short_note=refused(cur,lambda:command(cur,dict(payload(cur,f,'1.00'),note='abc')),'CP7_SUPPLIER_PAYMENT_CREATE_FIELDS'),
   extra_field=refused(cur,lambda:command(cur,dict(payload(cur,f,'1.00'),reference='X')),'CP7_SUPPLIER_PAYMENT_CREATE_FIELDS'),
   unknown_receipt=refused(cur,lambda:command(cur,dict(payload(cur,f,'1.00'),purchase_id=str(uuid.uuid4()))),'CP7_SUPPLIER_PAYMENT_RECEIPT_NOT_FOUND'))
  assert state(cur,f)==before and misc.cash_balance(cur,f['cash'])==cash and supplier.physical_state(cur)==f['physical'],'SUPPLIER_PAYMENT_CREATE_REFUSAL_HAD_EFFECT'
  return dict(status='PASS',refusals=out,Native_payments_journals_requests_cash_stock_unchanged=True)
 def access():
  f=fixture(cur,today);before=state(cur,f);p=payload(cur,f,'5.00')
  viewer,role=admin(cur,pay=False);w=read(cur,f,viewer)
  assert w['can_create']is False and w['Native_AP']['remaining']=='1000.00'
  denied=refused(cur,lambda:command(cur,p,subject=viewer),'CP7_SUPPLIER_PAYMENT_CREATE_DENIED')
  def as_service():
   b.api.admin(cur);cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=str(uuid.uuid4()),role='service_role')),))
   cur.execute('set local session authorization authenticated')
   cur.execute('select public.erp_cp7_create_supplier_payment_v1(%s::jsonb,%s)',(json.dumps(p),uuid.uuid4()))
  service=refused(cur,as_service,'CP7_INVOICE_ACCESS_DENIED')
  private=refused(cur,lambda:(auth.actor(cur),cur.execute('select cp7_supplier_payment_create.apply(%s::jsonb,%s)',(json.dumps(p),uuid.uuid4()))),'permission denied')
  legacy=legacy_direct_path(cur,f,viewer)
  assert state(cur,f)==before
  allowed,_=admin(cur);r=command(cur,payload(cur,f,'5.00',allowed),subject=allowed);assert r['status']=='POSTED';observe(cur,f,5)
  return dict(status='PASS',ADMIN_without_pay_reads_but_cannot_pay=denied,service_role_refused=service,private_apply_not_executable=private,legacy_hosted_direct_path_observation=legacy,ADMIN_with_pay_records=True)
 def boundary():
  f=fixture(cur,today);r=command(cur,payload(cur,f,'25.00'))
  assert not cur.execute('select exists(select 1 from cp7_supplier_payment_create.context)').fetchone()[0],'SUPPLIER_PAYMENT_CREATE_CONTEXT_LEFT'
  for who in('anon','authenticated','service_role','cp7_capture'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_supplier_payment_create','USAGE')",(who,)).fetchone()[0],who
   for table in('requests','context'):
    assert not cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE')",(who,'cp7_supplier_payment_create.'+table)).fetchone()[0],(who,table)
  for who in('cp7_invoice_read','cp7_invoice_write'):
   assert not cur.execute("select has_table_privilege(%s,'erp.supplier_payments','INSERT,UPDATE,DELETE')",(who,)).fetchone()[0],who
  observe(cur,f,25)
  return dict(status='PASS',private_context_cleared=True,no_App_private_schema_or_ERP_DML=True,payment_id=r['payment_id'])
 return [('CP7_SUPPLIER_PAYMENT_CREATE_EXACT_REPLAY_SETTLE',exact),('CP7_SUPPLIER_PAYMENT_CREATE_REFUSALS_ZERO_EFFECT',refusals),
  ('CP7_SUPPLIER_PAYMENT_CREATE_CURRENT_ACCESS',access),('CP7_SUPPLIER_PAYMENT_CREATE_PRIVATE_BOUNDARY',boundary)]

def races(tools,today):
 def same_request():
  with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p=payload(cur,f,'300.00');conn.commit()
  barrier=threading.Barrier(2);key=uuid.uuid4()
  def send():
   with tools.connect()as conn,conn.cursor()as cur:barrier.wait(5);r=command(cur,p,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:a=pool.submit(send);z=pool.submit(send);assert a.result(30)==z.result(30)
  with tools.connect()as conn,conn.cursor()as cur:observe(cur,f,300);assert state(cur,f)['requests']==1
  return dict(status='PASS',two_sessions_same_UUID_one_payment_one_journal=True)
 def double_pay():
  with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p=payload(cur,f,'600.00');conn.commit()
  barrier=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:
    barrier.wait(5)
    try:r=command(cur,p);conn.commit();return('PASS',r['payment_id'])
    except psycopg.Error as e:conn.rollback();return('REFUSED',str(e).splitlines()[0])
  with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(30)for x in(pool.submit(send),pool.submit(send))]
  assert sorted(x[0]for x in results)==['PASS','REFUSED']and 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW'in next(x[1]for x in results if x[0]=='REFUSED'),results
  with tools.connect()as conn,conn.cursor()as cur:observe(cur,f,600);assert state(cur,f)['requests']==1
  return dict(status='PASS',same_review_two_new_requests_one_payment_other_stale=results)
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:
   f=fixture(cur,today);subject,role=admin(cur);first=command(cur,payload(cur,f,'10.00',subject),subject=subject);p=payload(cur,f,'20.00',subject);conn.commit()
  holder=tools.connect();holder.cursor().execute('select 1 from erp.supplier_payments where id=%s for update',(first['payment_id'],))
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
      assert blocked,'SUPPLIER_PAYMENT_CREATE_LOCK_WAIT_NOT_OBSERVED'
      cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,));conn.commit()
    finally:holder.rollback()
    result=future.result(30);assert 'CP7_SUPPLIER_PAYMENT_ACCESS_CHANGED'in result or 'CP7_SUPPLIER_PAYMENT_CREATE_DENIED'in result,result
  finally:holder.rollback();holder.close()
  with tools.connect()as conn,conn.cursor()as cur:observe(cur,f,10);assert state(cur,f)['requests']==1
  return dict(status='PASS',actual_lock_wait_then_current_ADMIN_revoke_refuses_before_any_effect=True)
 return [('CP7_SUPPLIER_PAYMENT_CREATE_RACE_SAME_REQUEST',same_request),('CP7_SUPPLIER_PAYMENT_CREATE_RACE_DOUBLE_PAY',double_pay),('CP7_SUPPLIER_PAYMENT_CREATE_RACE_CURRENT_REVOKE',revoke)]

def http_cases(http,today):
 def flow():
  owner=http.login('ADMIN','cp7-supplier-payment-create')
  with http.connect()as conn,conn.cursor()as cur:
   f=fixture(cur,today);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(owner.auth_user_id,)).fetchone()[0]
   for key in supplier.PERMISSIONS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
   when=at(cur);conn.commit()
  q=dict(p_query=dict(purchase_id=f['receipt']['purchase_id']))
  assert http.anon_rpc(READ,q)['status']in(401,403,404)
  w=owner.rpc(READ,q);assert w['status']==200 and w['body']['eligible']is True and w['body']['can_create']is True,w
  p=dict(purchase_id=f['receipt']['purchase_id'],review_token=w['body']['review_token'],amount='250.00',cash_account_id=f['cash'],payment_date=when,note=NOTE)
  args=dict(p_payload=p,p_request=str(uuid.uuid4()))
  assert http.anon_rpc(WRITE,args)['status']in(401,403,404)
  one=owner.rpc(WRITE,args);assert one['status']==200 and one['body']['remaining_after']=='750.00',one
  assert owner.rpc(WRITE,args)['body']==one['body']
  with http.connect()as conn,conn.cursor()as cur:
   observe(cur,f,250);assert state(cur,f)['requests']==1
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.pay'",(role,));conn.commit()
  assert owner.rpc(WRITE,args)['status']==403
  after=owner.rpc(READ,q);assert after['status']==200 and after['body']['can_create']is False
  return dict(status='PASS',real_Auth_HTTP_create_exact_replay_current_pay_revocation=True,anonymous_refused=True)
 return [('CP7_SUPPLIER_PAYMENT_CREATE_HTTP_CURRENT_REPLAY',flow)]
