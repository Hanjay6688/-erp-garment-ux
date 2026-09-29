"""Exact cash receipt/inverse qualification through P11 public boundaries."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import copy,json,threading,time,uuid
import psycopg
import cp7_sales_command_cases as cmd
source,b,auth=cmd.source,cmd.b,cmd.auth

def fixture(cur,today,**kw):
 f=source.fixture(cur,today,**kw);source.fg.post_sale(cur,f['draft']);b.api.admin(cur);f['bank']=str(source.bc.bank_account(cur,'P11PAY'+uuid.uuid4().hex[:8]));return f

def cash(cur,f,subject=None,**query):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_sales_cash_v1(%s)',(json.dumps(dict(sale_id=f['sale'],**query)),)).fetchone()[0];b.api.admin(cur);return r

def payment_payload(cur,f,amount='30'):
 p,v=cmd.review(cur,f);p.update(payment_number='PAY-'+uuid.uuid4().hex[:12],payment_date=source.fg.ax.r1.now(cur).isoformat(),amount=amount,cash_account_id=f['bank'],payment_method='BANK_TRANSFER',reference_number='reference retained',notes='cash receipt notes retained');return p,v

def pay(cur,f,amount='30',subject=None,key=None):
 p,v=payment_payload(cur,f,amount);return cmd.command(cur,'PAYMENT',p,v,key,subject)

def inverse(cur,f,payment_id,subject=None,key=None):
 p,v=cmd.review(cur,f);p['payment_id']=payment_id;return cmd.command(cur,'PAYMENT_REVERSE',p,v,key,subject)

def bank_account(cur,f):return str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(f['bank'],)).fetchone()[0])

def cases(cur,today):
 def exact_lifecycle():
  f=fixture(cur,today,qty=3,price='10.01',discount='0.02');before=cmd.accounts(cur);a=pay(cur,f,'10.01');d=source.read(cur,f)['detail'];assert d['financial']['open_balance']=='20.00' and d['status']=='PARTIAL_PAID' and cmd.available(cur,f)==7
  assert cmd.delta(before,cmd.accounts(cur))=={bank_account(cur,f):source.D('10.01'),cmd.mapping(cur,'AR_CUSTOMER'):source.D('-10.01')}
  z=pay(cur,f,'20');d=source.read(cur,f)['detail'];assert d['status']=='PAID' and d['financial']['open_balance']=='0.00'
  inverse(cur,f,a['payment_id']);assert source.read(cur,f)['detail']['financial']['open_balance']=='10.01';inverse(cur,f,z['payment_id']);assert cmd.accounts(cur)==before and cmd.available(cur,f)==7
  assert cur.execute('select count(*) from erp.sales_payment_posting_facts where payment_id in(%s,%s)',(a['payment_id'],z['payment_id'])).fetchone()[0]==2
  assert cur.execute('select count(*) from erp.sales_payment_reversal_facts where payment_id in(%s,%s)',(a['payment_id'],z['payment_id'])).fetchone()[0]==2
  return dict(status='PASS',invoice='30.01',partial='10.01',remaining='20.00',full_cash='30.01',inverse_each_original_payment=True,cash_AR_gl_neutral_after_both_inverse=True,stock_stays7=True,immutable_posting_and_reversal_facts=2)
 def replay():
  f=fixture(cur,today);p,v=payment_payload(cur,f);key=uuid.uuid4();r=cmd.command(cur,'PAYMENT',p,v,key);assert cmd.command(cur,'PAYMENT',p,v,key)==r
  inverse_p,inverse_v=cmd.review(cur,f);inverse_p['payment_id']=r['payment_id'];inverse_key=uuid.uuid4()
  inv=cmd.command(cur,'PAYMENT_REVERSE',inverse_p,inverse_v,inverse_key);assert inv['payment_status']=='REVERSED' and cmd.command(cur,'PAYMENT',p,v,key)==r
  bad=dict(p,amount='31');auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',bad,v,key),'CP7_SALES_REQUEST_CHANGED')
  assert cur.execute('select count(*) from erp.sales_payments where sale_id=%s',(f['sale'],)).fetchone()[0]==1
  subject,role=auth.custom_actor(cur)
  for permission in ('finance.ar.view','sales.payment.view','sales.payment.reverse'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,permission))
  cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,auth.base.OPERATOR_AUTH))
  auth.refused(cur,lambda:cmd.command(cur,'PAYMENT_REVERSE',inverse_p,inverse_v,inverse_key),'CP7_SALES_OWNER_ADMIN_REQUIRED')
  return dict(status='PASS',one_payment_after_same_UUID=True,original_committed_outcome_after_inverse=True,changed_amount_refused=True,current_native_role_required_before_cached_inverse=True)
 def fields():
  f=fixture(cur,today);p,v=payment_payload(cur,f);before=b.boundary.snapshot(cur)
  for change in (dict(amount='1.001'),dict(amount=30),dict(amount='0'),dict(cash_account_id=None),dict(payment_method='OPENING_ADVANCE'),dict(unit_hpp='0'),dict(notes=3)):
   auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',dict(p,**change),v),'CP7_SALES_PAYMENT_FIELDS')
  auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',dict(p,amount='80.01'),v),'exceeds exact remaining receivable')
  auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',dict(p,payment_date=(source.fg.ax.r1.now(cur)+timedelta(days=1)).isoformat()),v),'business date cannot be in the future')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',no_fraction_rounding_or_zero_cash=True,overpayment_and_future_refused_atomically=True,no_injected_HPP_or_opening_advance=True)
 def changed_source():
  f=fixture(cur,today);p,v=payment_payload(cur,f);other=source.payment(cur,f,today,'10');auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',p,v),'CP7_SALES_REVIEW_CHANGED')
  p,v=payment_payload(cur,f);old_token=p['review_token']
  # A draft payment is source activity even before native header revision changes.
  cur.execute("insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method) values(%s,%s,%s,1,%s,'CASH')",(f['sale'],'PENDING-'+f['tag'],source.fg.ax.r1.now(cur),f['bank']))
  assert source.read(cur,f)['detail']['row_version']==v and cash(cur,f)['review_token']!=old_token
  before=b.boundary.snapshot(cur);auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',p,v),'CP7_SALES_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
  g=fixture(cur,today);p,v=cmd.review(cur,g);p['payment_id']=other;auth.refused(cur,lambda:cmd.command(cur,'PAYMENT_REVERSE',p,v),'CP7_SALES_PAYMENT_SOURCE_CHANGED')
  return dict(status='PASS',posted_payment_invalidates_old_review=True,draft_child_changes_token_without_header_revision=True,foreign_invoice_payment_refused=True)
 def selectors():
  f=fixture(cur,today);tag='P11BANK'+uuid.uuid4().hex[:8]
  for suffix in ('A','B','C'):source.bc.bank_account(cur,tag+suffix)
  ids=[]
  for off in range(3):
   w=cash(cur,f,bank_q=tag,bank_offset=off,bank_limit=1);assert w['cash_accounts']['total']=='3' and len(w['cash_accounts']['rows'])==1 and w['cash_accounts']['next_offset']==(off+1 if off<2 else None);ids.append(w['cash_accounts']['rows'][0]['id'])
  assert len(set(ids))==3
  for value in ('1','2','3'):pay(cur,f,value)
  ids=[]
  for off in range(3):
   w=cash(cur,f,payment_offset=off,payment_limit=1);assert w['payments']['total']=='3' and len(w['payments']['rows'])==1 and w['payments']['next_offset']==(off+1 if off<2 else None);ids.append(w['payments']['rows'][0]['id'])
  assert len(set(ids))==3;inverse(cur,f,ids[0]);assert cash(cur,f)['payments']['total']=='3' and sum(x['status']=='REVERSED' for x in cash(cur,f)['payments']['rows'])==1
  auth.refused(cur,lambda:cash(cur,f,payment_limit=101),'CP7_SALES_CASH_QUERY');auth.refused(cur,lambda:cash(cur,f,bank_limit='1'),'CP7_SALES_CASH_QUERY')
  return dict(status='PASS',complete_active_bank_and_payment_pages=3,reversed_payment_kept_in_history=True,invalid_pages_refused=True)
 def inactive():
  f=fixture(cur,today);p,v=payment_payload(cur,f);cur.execute('update erp.cash_accounts set is_active=false where id=%s',(f['bank'],));before=b.boundary.snapshot(cur)
  assert all(x['id']!=f['bank'] for x in cash(cur,f)['cash_accounts']['rows']);auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',p,v),'CP7_SALES_CASH_UNAVAILABLE');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',inactive_bank_hidden_and_direct_ID_refused=True,no_payment_or_GL_side_effect=True)
 def permissions():
  f=fixture(cur,today);subject,role=auth.custom_actor(cur)
  for permission in ('finance.ar.view','sales.payment.view','sales.payment.create'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,permission))
  assert cash(cur,f,subject)['cash_accounts']['total']=='0';p,v=payment_payload(cur,f);key=uuid.uuid4();auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',p,v,key,subject),'CP7_SALES_WRITE_DENIED')
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.payment.post')",(role,));r=cmd.command(cur,'PAYMENT',p,v,key,subject);assert r['status']=='PARTIAL_PAID'
  assert cmd.command(cur,'PAYMENT',p,v,key,subject)==r
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.payment.reverse')",(role,));auth.refused(cur,lambda:inverse(cur,f,r['payment_id'],subject),'CP7_SALES_OWNER_ADMIN_REQUIRED')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.payment.view'",(role,));auth.refused(cur,lambda:cmd.command(cur,'PAYMENT',p,v,key,subject),'CP7_SALES_WRITE_DENIED');auth.refused(cur,lambda:cash(cur,f,subject),'CP7_SALES_CASH_DENIED')
  assert cur.execute('select count(*) from cp7_sales.command_context').fetchone()[0]==0
  return dict(status='PASS',custom_role_can_record_only_with_all_current_permissions=True,current_view_required_before_cached_outcome=True,native_OWNER_ADMIN_inverse_restriction_preserved=True)
 def private():
  f=fixture(cur,today);subject,role=auth.custom_actor(cur);before=b.boundary.snapshot(cur);auth.refused(cur,lambda:cash(cur,f,subject),'CP7_SALES_CASH_DENIED')
  assert b.boundary.snapshot(cur)==before
  for principal in ('anon','authenticated','service_role','cp7_capture'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_sales','USAGE') or has_function_privilege(%s,'cp7_sales.cash_workspace(jsonb)','EXECUTE')",(principal,principal)).fetchone()[0]
  assert not cur.execute("select has_function_privilege('cp7_sales_write','erp.post_sales_payment(uuid)','EXECUTE') or has_table_privilege('cp7_sales_write','erp.sales_payments','INSERT,UPDATE,DELETE')").fetchone()[0]
  return dict(status='PASS',cash_data_requires_AR_and_payment_view=True,no_browser_private_or_writer_business_DML=True)
 return [('P11_PAYMENT_'+name,fn) for name,fn in [('EXACT_LIFECYCLE',exact_lifecycle),('REPLAY',replay),('FIELDS',fields),('SOURCE_CHANGE',changed_source),('PAGES',selectors),('INACTIVE_BANK',inactive),('PERMISSIONS',permissions),('PRIVATE',private)]]

def races(tools,today):
 def compete(same=False):
  with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);p,v=payment_payload(cur,f,'60');bank=bank_account(cur,f);before=cmd.accounts(cur);conn.commit()
  barrier=threading.Barrier(2);key=uuid.uuid4()
  def send(n):
   with tools.connect() as conn,conn.cursor() as cur:
    barrier.wait()
    try:r=cmd.command(cur,'PAYMENT',p if same else dict(p,payment_number=p['payment_number']+'-'+str(n)),v,key if same else uuid.uuid4());conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
  with ThreadPoolExecutor(max_workers=2) as pool:jobs=[pool.submit(send,n) for n in (1,2)];results=[j.result(30) for j in jobs]
  if same:assert results[0]==results[1] and isinstance(results[0],dict),results
  else:assert sum(isinstance(x,dict) for x in results)==1 and any('CP7_SALES_REVIEW_CHANGED' in str(x) for x in results),results
  with tools.connect() as conn,conn.cursor() as cur:
   assert source.read(cur,f)['detail']['financial']['open_balance']=='20.00' and cmd.available(cur,f)==6
   assert cur.execute('select count(*) from erp.sales_payments where sale_id=%s',(f['sale'],)).fetchone()[0]==1
   assert cmd.delta(before,cmd.accounts(cur))=={bank:60,cmd.mapping(cur,'AR_CUSTOMER'):-60}
  return dict(status='PASS',same_UUID=same,one_native_cash60=True,open_balance20=True,stock6_unchanged=True)
 def revoke():
  with tools.connect() as conn,conn.cursor() as cur:
   f=fixture(cur,today);p,v=payment_payload(cur,f);subject,role=auth.custom_actor(cur)
   for permission in ('finance.ar.view','sales.payment.view','sales.payment.create','sales.payment.post'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,permission))
   conn.commit()
  with tools.connect() as holder,holder.cursor() as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
   def send():
    with tools.connect() as conn,conn.cursor() as cur:
     try:cmd.command(cur,'PAYMENT',p,v,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
     except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
   with ThreadPoolExecutor(max_workers=1) as pool:
    future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
      while time.monotonic()<deadline:
       c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
       if blocked:break
       time.sleep(.03)
      assert blocked,'EXPECTED_REAL_PAYMENT_WAIT';c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.payment.post'",(role,))
    finally:holder.rollback()
    result=future.result(30)
  assert 'CP7_SALES_WRITE_DENIED' in result,result
  with tools.connect() as conn,conn.cursor() as cur:assert cash(cur,f)['payments']['total']=='0' and source.read(cur,f)['detail']['financial']['open_balance']=='80.00'
  return dict(status='PASS',actual_FG_wait_observed=True,permission_revoked_before_effect=True,no_payment=True)
 return [('P11_PAYMENT_RACE_SAME_UUID',lambda:compete(True)),('P11_PAYMENT_RACE_COMPETING',compete),('P11_PAYMENT_RACE_REVOKE',revoke)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p11-payment-owner')
  with http.connect() as conn,conn.cursor() as cur:f=fixture(cur,today,qty=3,price='10.01',discount='0.02');p,v=payment_payload(cur,f,'30.01');conn.commit()
  args=dict(p_action='PAYMENT',p_payload=p,p_request=str(uuid.uuid4()),p_expected=v);assert http.anon_rpc('erp_cp7_save_sale_v1',args)['status'] in(401,403)
  r=owner.rpc('erp_cp7_save_sale_v1',args);assert r['status']==200 and r['body']['status']=='PAID',r
  assert owner.rpc('erp_cp7_save_sale_v1',args)['body']==r['body'];q=owner.rpc('erp_cp7_get_sales_cash_v1',dict(p_query=dict(sale_id=f['sale'])));assert q['status']==200 and q['body']['payments']['rows'][0]['amount']=='30.01'
  with http.connect() as conn,conn.cursor() as cur:p,v=cmd.review(cur,f);p['payment_id']=r['body']['payment_id']
  inverse=owner.rpc('erp_cp7_save_sale_v1',dict(p_action='PAYMENT_REVERSE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=v));assert inverse['status']==200 and inverse['body']['payment_status']=='REVERSED',inverse
  with http.connect() as conn,conn.cursor() as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_sales_cash_v1',dict(p_query=dict(sale_id=f['sale'])))['status']==403
  return dict(status='PASS',real_auth_exact_cash_and_inverse=True,amount='30.01',replay=True,current_revocation=True)
 return [('P11_PAYMENT_HTTP',flow)]
