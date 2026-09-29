"""Source-to-draft P11 oracles. Creation/edit use public commands, not table writes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import copy,json,threading,uuid
import psycopg
import cp7_sales_command_cases as cmd
source,b,auth=cmd.source,cmd.b,cmd.auth

def fixture(cur,today,stock=10):
 f=source.fg.fixture(cur,today,stock);b.api.admin(cur);f['tag']='P11-DRAFT-'+uuid.uuid4().hex[:10];f['customer']=str(source.fg.base.create_customer(cur,f['tag']));f['sale_at']=(source.fg.ax.r1.now(cur)-timedelta(minutes=7,seconds=3,microseconds=321)).isoformat();return f

def payload(f,qty='4',price='20',discount='0'):
 return dict(sale_number=f['tag'],customer_id=f['customer'],source_location_id=f['location'],sale_date=f['sale_at'],due_date=None,payment_terms='Bayar setelah invoice disahkan',notes='All source lines retained',change_reason='Reviewed exact customer stock and price',items=[dict(product_id=f['product'],qty_pcs=qty,unit_price_snapshot=price,discount_amount=discount,notes='Exact source line')])

def create(cur,f,p=None,key=None,subject=None):
 r=cmd.command(cur,'CREATE',p or payload(f),None,key,subject);f['sale']=r['sale_id'];return r

def edit_payload(cur,f,p):
 d=source.read(cur,f)['detail'];return dict(copy.deepcopy(p),sale_id=f['sale'],review_token=d['review_token']),d['row_version']

def options(cur,kind,at,subject=None,**q):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_sales_form_v1(%s)',(json.dumps(dict(kind=kind,physical_at=at,**q)),)).fetchone()[0];b.api.admin(cur);return r

def cases(cur,today):
 def multi():
  f=fixture(cur,today);g=fixture(cur,today);p=payload(f);p['items']+=payload(g,'3','10.01','0.02')['items'];before=cmd.accounts(cur)
  d=create(cur,f,p);detail=source.read(cur,f)['detail'];assert detail['line_count']=='2' and detail['financial']['gross_total']=='110.01' and cmd.available(cur,f)==6 and cmd.available(cur,g)==7 and cmd.accounts(cur)==before
  edit,v=edit_payload(cur,f,p);edit['items'][0]['qty_pcs']='5';edit['items'][1]['qty_pcs']='1';edited=cmd.command(cur,'EDIT',edit,v);detail=source.read(cur,f)['detail']
  assert edited['sale_id']==d['sale_id'] and edited['row_version']!=v and detail['financial']['gross_total']=='109.99' and cmd.available(cur,f)==5 and cmd.available(cur,g)==9 and detail['payment_terms']==p['payment_terms'] and detail['notes']==p['notes']
  assert cur.execute('select sale_date::text from erp.sales_headers where id=%s',(f['sale'],)).fetchone()[0]==cur.execute('select %s::timestamptz::text',(p['sale_date'],)).fetchone()[0]
  a,v=cmd.review(cur,f);cmd.command(cur,'POST',a,v);assert cmd.available(cur,f)==5 and cmd.available(cur,g)==9
  assert cmd.delta(before,cmd.accounts(cur))=={cmd.mapping(cur,'AR_CUSTOMER'):source.D('109.99'),cmd.mapping(cur,'SALES_REVENUE'):source.D('-109.99'),cmd.mapping(cur,'FG_INVENTORY'):-60,cmd.mapping(cur,'COGS'):60}
  source.native(cur,'select erp.reverse_sale(%s,%s)',(f['sale'],'Native inverse after public create edit post'));assert cmd.available(cur,f)==cmd.available(cur,g)==10 and cmd.accounts(cur)==before
  return dict(status='PASS',complete_two_product_create_edit=True,initial_total='110.01',edited_total='109.99',edited_available=[5,9],post_no_second_stock_effect=True,native_inverse_stock=[10,10],all_gl_neutral=True,full_timestamp_notes_terms_retained=True)
 def replay():
  f=fixture(cur,today);p=payload(f);key=uuid.uuid4();d=create(cur,f,p,key);assert create(cur,f,p,key)==d
  e,v=edit_payload(cur,f,p);e['items'][0]['qty_pcs']='3';edited=cmd.command(cur,'EDIT',e,v);assert edited['sale_id']==d['sale_id'] and cmd.available(cur,f)==7 and create(cur,f,p,key)==d
  bad=dict(p,sale_number=p['sale_number']+'-other');auth.refused(cur,lambda:create(cur,f,bad,key),'CP7_SALES_REQUEST_CHANGED')
  a,v=cmd.review(cur,f);cmd.command(cur,'CANCEL',a,v);assert cmd.available(cur,f)==10 and create(cur,f,p,key)==d
  assert cur.execute('select count(*) from erp.sales_headers where sale_number=%s',(p['sale_number'],)).fetchone()[0]==1
  return dict(status='PASS',one_draft_same_uuid=True,original_create_outcome_after_edit_and_cancel=True,changed_payload_refused=True)
 def unavailable_edit():
  f=fixture(cur,today);p=payload(f);create(cur,f,p);e,v=edit_payload(cur,f,p);e['items'][0]['qty_pcs']='11';before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:cmd.command(cur,'EDIT',e,v),'Insufficient FG stock');assert b.boundary.snapshot(cur)==before and cmd.available(cur,f)==6 and source.read(cur,f)['detail']['reserved_qty']=='4'
  e['items'][0]['qty_pcs']='5';auth.refused(cur,lambda:cmd.command(cur,'EDIT',e,str(int(v)+1)),'CP7_SALES_REVIEW_CHANGED')
  return dict(status='PASS',insufficient_edit_rolls_back_release_and_replacement=True,original4_reservation_retained=True,stale_edit_atomic=True)
 def exact_fields():
  f=fixture(cur,today,30);p=payload(f,'13','10.01','0.02');before=b.boundary.snapshot(cur)
  for field,value in [('qty_pcs',13),('qty_pcs','1.5'),('unit_price_snapshot',None),('unit_price_snapshot','10.001'),('discount_amount','999'),('unit_hpp_snapshot','0')]:
   bad=copy.deepcopy(p);bad['items'][0][field]=value;auth.refused(cur,lambda:create(cur,f,bad),'CP7_SALES_DISCOUNT' if field=='discount_amount' else 'CP7_SALES_DRAFT_LINE')
  assert b.boundary.snapshot(cur)==before;create(cur,f,p);assert source.read(cur,f)['detail']['financial']['gross_total']=='130.11' and cmd.available(cur,f)==17
  return dict(status='PASS',manual13_preserved=True,exact_total='130.11',no_silent_round_or_missing_price_zero=True,client_hpp_rejected=True)
 def selectors():
  f=fixture(cur,today);tag='P11-PAGE-'+uuid.uuid4().hex[:8]
  for suffix in ('a','b','c'):source.fg.base.create_customer(cur,tag+suffix)
  ids=[]
  for off in range(3):
   o=options(cur,'CUSTOMER',f['sale_at'],q=tag,offset=off,limit=1);assert o['total']=='3' and len(o['rows'])==1 and o['next_offset']==(off+1 if off<2 else None);ids.append(o['rows'][0]['id'])
  assert len(set(ids))==3
  o=options(cur,'STOCK',f['sale_at'],q=f['sku']);assert o['total']=='1' and o['rows'][0]['product_id']==f['product'] and o['rows'][0]['available_qty']=='10'
  create(cur,f);assert options(cur,'STOCK',f['sale_at'],q=f['sku'])['rows'][0]['available_qty']=='6'
  assert options(cur,'STOCK',f['sale_at'],q=uuid.uuid4().hex)['total']=='0'
  auth.refused(cur,lambda:options(cur,'STOCK',f['sale_at'],q=f['sku'],limit=101),'CP7_SALES_FORM_QUERY')
  return dict(status='PASS',complete_customer_pages=3,current_available10_to6=True,dated_sku_selector_not_historical_stock_claim=True,empty_and_invalid_query_explicit=True)
 def master_refusal():
  f=fixture(cur,today);p=payload(f);cur.execute('update erp.products set is_active=false where id=%s',(f['product'],));before=b.boundary.snapshot(cur)
  assert options(cur,'STOCK',f['sale_at'],q=f['sku'])['rows']==[]
  auth.refused(cur,lambda:create(cur,f,p),'CP7_SALES_PRODUCT_UNAVAILABLE');assert b.boundary.snapshot(cur)==before
  cur.execute('update erp.products set is_active=true where id=%s',(f['product'],));future=dict(p,sale_date=(source.fg.ax.r1.now(cur)+timedelta(days=1)).isoformat());auth.refused(cur,lambda:create(cur,f,future),'CP7_SALES_FUTURE_DATE')
  cur.execute('update erp.customers set is_active=false where id=%s',(f['customer'],));auth.refused(cur,lambda:create(cur,f,p),'Active customer')
  return dict(status='PASS',inactive_product_or_customer_and_future_refused=True,selectors_not_an_authorization_bypass=True)
 def permissions():
  f=fixture(cur,today);subject,role=auth.custom_actor(cur);cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.ar.view'),(%s,'sales.invoice.create')",(role,role))
  p=payload(f);d=create(cur,f,p,subject=subject);e,v=edit_payload(cur,f,p)
  auth.refused(cur,lambda:cmd.command(cur,'EDIT',e,v,subject=subject),'CP7_SALES_WRITE_DENIED')
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.invoice.edit_draft')",(role,));e['items'][0]['qty_pcs']='3';cmd.command(cur,'EDIT',e,v,subject=subject);assert cmd.available(cur,f)==7
  p2,v2=cmd.review(cur,f);auth.refused(cur,lambda:cmd.command(cur,'POST',p2,v2,subject=subject),'CP7_SALES_WRITE_DENIED')
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.invoice.post')",(role,));cmd.command(cur,'POST',p2,v2,subject=subject);assert source.read(cur,f)['detail']['status']=='POSTED' and cmd.available(cur,f)==7
  g=fixture(cur,today);create(cur,g,subject=subject);p2,v2=cmd.review(cur,g);cmd.command(cur,'CANCEL',p2,v2,subject=subject);assert cmd.available(cur,g)==10
  assert cur.execute('select count(*) from cp7_sales.command_context').fetchone()[0]==0
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,));auth.refused(cur,lambda:options(cur,'STOCK',f['sale_at'],subject,q=f['sku']),'CP7_SALES_FORM_DENIED')
  return dict(status='PASS',custom_role_create_edit_post_cancel=True,create_edit_post_authority_distinct=True,current_financial_authority_required_for_form=True,private_context_removed=True)
 return [('P11_DRAFT_'+n,fn) for n,fn in [('MULTI_CREATE_EDIT_POST',multi),('REPLAY',replay),('INSUFFICIENT_EDIT',unavailable_edit),('EXACT_FIELDS',exact_fields),('SELECTORS',selectors),('MASTER_REFUSAL',master_refusal),('PERMISSIONS',permissions)]]

def races(tools,today):
 def stock():
  with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);p=payload(f,'7');conn.commit()
  barrier=threading.Barrier(2)
  def send(n):
   with tools.connect() as conn,conn.cursor() as cur:
    barrier.wait()
    try:r=cmd.command(cur,'CREATE',dict(p,sale_number=p['sale_number']+'-'+str(n)),None);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
  with ThreadPoolExecutor(max_workers=2) as pool:jobs=[pool.submit(send,n) for n in (1,2)];results=[j.result(30) for j in jobs]
  assert sum(isinstance(x,dict) for x in results)==1 and any('Insufficient FG stock' in str(x) for x in results),results
  with tools.connect() as conn,conn.cursor() as cur:assert cmd.available(cur,f)==3
  return dict(status='PASS',concurrent7_plus7_against10_one_draft=True,remaining_available=3,loser_atomic=True)
 return [('P11_DRAFT_RACE_AVAILABLE',stock)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p11-draft-owner')
  with http.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);p=payload(f,'3','10.01','0.02');conn.commit()
  o=owner.rpc('erp_cp7_get_sales_form_v1',dict(p_query=dict(kind='STOCK',physical_at=f['sale_at'],q=f['sku'])));assert o['status']==200 and o['body']['rows'][0]['available_qty']=='10',o
  args=dict(p_action='CREATE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=None);r=owner.rpc('erp_cp7_save_sale_v1',args);assert r['status']==200,r;assert owner.rpc('erp_cp7_save_sale_v1',args)['body']==r['body'];f['sale']=r['body']['sale_id']
  with http.connect() as conn,conn.cursor() as cur:assert cmd.available(cur,f)==7;assert source.read(cur,f)['detail']['financial']['gross_total']=='30.01'
  assert http.anon_rpc('erp_cp7_save_sale_v1',args)['status'] in(401,403)
  return dict(status='PASS',real_auth_options_create_and_exact_replay=True,exact_invoice='30.01',stock_available=7)
 return [('P11_DRAFT_HTTP',flow)]
