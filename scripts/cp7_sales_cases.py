"""P11 invoice reader proof. Writes below are native fixture controls, not UI claims."""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp7_fg_cases as fg
import cp7_snapshot_cases as auth
import cp6_bc_probe as bc
b=fg.b

def fixture(cur,today,qty=4,price='20',discount='0',stock=10,tag=None):
 f=fg.fixture(cur,today,stock);f['tag']=tag or 'P11-'+uuid.uuid4().hex[:12];f['customer']=str(fg.base.create_customer(cur,f['tag']))
 f['sale_at']=(fg.ax.r1.now(cur)-timedelta(minutes=10)).isoformat()
 d=b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number=f['tag'],customer_id=f['customer'],source_location_id=f['location'],sale_date=f['sale_at'],reason='P11 native source document',items=[dict(product_id=f['product'],qty_pcs=qty,unit_price_snapshot=price,discount_amount=discount)]),uuid.uuid4(),None)
 f['sale']=d['sale_id'];f['draft']=d
 b.api.admin(cur)
 return f

def read(cur,f=None,subject=None,**query):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_sales_v1(%s::jsonb)',(json.dumps(dict({'q':f['tag'] if f else '', 'sale_id':f['sale'] if f else None},**query)),)).fetchone()[0];b.api.admin(cur);return r

def native(cur,sql,args):
 b.chain.production.owner(cur);r=cur.execute(sql,args).fetchone()[0];b.api.admin(cur);return r

def payment(cur,f,today,amount):
 bank=bc.bank_account(cur,'P11'+uuid.uuid4().hex[:10]);p=str(cur.execute("insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,status) values(%s,%s,%s,%s,%s,'BANK_TRANSFER','DRAFT') returning id",(f['sale'],'PAY-'+f['tag'],fg.ax.r1.now(cur),amount,bank)).fetchone()[0]);native(cur,'select erp.post_sales_payment(%s)',(p,));return p

def returned(cur,f,amount='20'):
 alloc=str(cur.execute('select a.id from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s',(f['sale'],)).fetchone()[0])
 r=str(cur.execute("insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,status) values(%s,%s,%s,%s,'DRAFT') returning id",('RET-'+f['tag'],f['sale'],f['customer'],fg.ax.r1.now(cur))).fetchone()[0])
 cur.execute("insert into erp.sales_return_items(return_id,product_id,lot_id,location_id,qty_pcs,unit_hpp_snapshot,refund_amount,quality_grade,sale_stock_allocation_id) values(%s,%s,%s,%s,1,10,%s,'GRADE_A',%s)",(r,f['product'],f['lot'],f['location'],amount,alloc));native(cur,'select erp.post_sales_return(%s)',(r,));return r

def gl(cur):return cur.execute('select account_id,sum(debit-credit) from erp.journal_lines group by account_id having sum(debit-credit)<>0 order by account_id').fetchall()
def numbers(d):return {k:D(d['financial'][k]) if d['financial'][k] is not None else None for k in ('gross_total','return_total','net_total','paid_total','open_balance')}

def cases(cur,today):
 def draft_cancel():
  f=fixture(cur,today);before=b.boundary.snapshot(cur);w=read(cur,f);d=w['detail']
  assert d['status']=='DRAFT' and d['qty_pcs']=='4' and d['reserved_qty']=='4' and d['returned_qty']=='0' and d['line_count']=='1'
  assert numbers(d)==dict(gross_total=D(80),return_total=D(0),net_total=D(80),paid_total=D(0),open_balance=None)
  assert d['financial']['state']=='DRAFT_PREVIEW' and len(d['items'])==1 and b.boundary.snapshot(cur)==before
  fg.cancel(cur,f['draft']);d=read(cur,f)['detail'];assert d['status']=='CANCELLED' and d['reserved_qty']=='0' and d['financial']['open_balance'] is None
  return dict(status='PASS',draft_reserves4_without_receivable=True,cancel_releases4=True,read_has_no_business_effect=True)
 def lifecycle():
  f=fixture(cur,today);before=gl(cur);fg.post_sale(cur,f['draft']);d=read(cur,f)['detail'];assert d['reserved_qty']=='0' and d['financial']['open_balance']=='80.00'
  p=payment(cur,f,today,'30');d=read(cur,f)['detail'];assert d['status']=='PARTIAL_PAID' and d['financial']['paid_total']=='30.00' and d['financial']['open_balance']=='50.00'
  r=returned(cur,f);d=read(cur,f)['detail'];assert d['returned_qty']=='1' and numbers(d)==dict(gross_total=D(80),return_total=D(20),net_total=D(60),paid_total=D(30),open_balance=D(30))
  native(cur,'select erp.reverse_sales_payment(%s,%s)',(p,'P11 payment inverse control'));native(cur,'select erp.reverse_sales_return(%s,%s)',(r,'P11 return inverse control'));native(cur,'select erp.reverse_sale(%s,%s)',(f['sale'],'P11 sale inverse control'))
  d=read(cur,f)['detail'];assert d['status']=='REVERSED' and d['reserved_qty']==d['returned_qty']=='0' and d['financial']['open_balance'] is None and d['financial']['paid_total']=='0.00' and gl(cur)==before
  return dict(status='PASS',native_draft_post_partial_payment_return_inverse=True,invoice='80',payment='30',return_value='20',remaining='30',final_gl_neutral=True,not_connected_writer_proof=True)
 def exact():
  f=fixture(cur,today,qty=3,price='10.01',discount='0.02');fg.post_sale(cur,f['draft']);payment(cur,f,today,'30.01');d=read(cur,f)['detail'];i=d['items'][0]
  assert d['status']=='PAID' and numbers(d)['net_total']==D('30.01') and d['financial']['open_balance']=='0.00' and i['financial']==dict(unit_price='10.01',discount='0.02',line_total='30.01')
  return dict(status='PASS',exact_native_invoice='30.01',full_payment_zero_receivable=True)
 def redaction():
  f=fixture(cur,today);subject,role=auth.custom_actor(cur);cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.invoice.view')",(role,))
  w=read(cur,f,subject);assert not w['financial_captured'] and 'financial' not in json.dumps(w).replace('financial_captured','') and 'unit_price' not in json.dumps(w)
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.ar.view')",(role,));assert read(cur,f,subject)['financial_captured']
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,));auth.refused(cur,lambda:read(cur,f,subject),'CP7_SALES_ACCESS_DENIED')
  return dict(status='PASS',invoice_view_does_not_expose_money=True,ar_authority_required=True,current_permission_revocation=True)
 def private():
  assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_sales_read',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
  for who in ('anon','authenticated','service_role','cp7_capture'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_sales','USAGE') or has_function_privilege(%s,'cp7_sales.workspace(jsonb)','EXECUTE')",(who,who)).fetchone()[0]
  for signature in ('erp.save_sale_draft_v2(jsonb,uuid,bigint)','erp.post_sale(uuid)','erp.post_sales_payment(uuid)','erp.post_sales_return(uuid)'):
   assert not cur.execute("select has_function_privilege('cp7_sales_read',%s,'EXECUTE')",(signature,)).fetchone()[0]
  return dict(status='PASS',reader_no_business_dml_or_native_writer_execution=True,private_helper_unreachable=True)
 def pages():
  tag='P11-PAGES-'+uuid.uuid4().hex[:6];f=fixture(cur,today,tag=tag+'-0');fixture(cur,today,tag=tag+'-1');fixture(cur,today,tag=tag+'-2')
  ids=[]
  for off in range(3):
   w=read(cur,offset=off,limit=1,q=tag);assert w['page']['total']=='3' and len(w['page']['rows'])==1 and w['page']['next_offset']==(off+1 if off<2 else None);ids.append(w['page']['rows'][0]['id'])
  assert len(set(ids))==3
  return dict(status='PASS',complete_pages=3,total_not_page_subtotal=True)
 def malformed():
  f=fixture(cur,today)
  for q in ({'limit':101},{'offset':-1},{'status':'UNKNOWN'},{'as_of':'2020-01-01'},{'limit':'25'}):
   auth.refused(cur,lambda:read(cur,f,**q),'CP7_SALES_QUERY')
  return dict(status='PASS',invalid_bounds_and_unimplemented_historical_query_refused=True)
 def missing():
  empty=read(cur,q=uuid.uuid4().hex);assert empty['page']['total']=='0' and not empty['page']['rows'] and empty['detail'] is None
  auth.refused(cur,lambda:read(cur,dict(tag='missing',sale=str(uuid.uuid4()))),'CP7_SALES_NOT_FOUND')
  return dict(status='PASS',empty_is_explicit=True,missing_selected_document_not_silent=True)
 return [('P11_READ_'+n,f) for n,f in [('DRAFT_CANCEL',draft_cancel),('NATIVE_LIFECYCLE',lifecycle),('EXACT_CENTS',exact),('FINANCIAL_REDACTION',redaction),('PRIVATE_READ_ONLY',private),('COMPLETE_PAGES',pages),('QUERY_REFUSAL',malformed),('EMPTY_MISSING',missing)]]

def http_cases(http,today):
 def current_auth():
  owner=http.login('OWNER','p11-read-owner')
  with http.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);conn.commit()
  args=dict(p_query=dict(q=f['tag'],sale_id=f['sale']));r=owner.rpc('erp_cp7_get_sales_v1',args)
  assert r['status']==200 and r['body']['detail']['financial']['gross_total']=='80.00',r
  with http.connect() as conn,conn.cursor() as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_sales_v1',args)['status']==403 and http.anon_rpc('erp_cp7_get_sales_v1',args)['status'] in(401,403)
  return dict(status='PASS',real_auth_postgrest=True,live_deactivation_refused=True)
 return [('P11_READ_HTTP_CURRENT_AUTH',current_auth)]
