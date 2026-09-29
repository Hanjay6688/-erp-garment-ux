"""Selected-allocation physical return, current cash constraint and full inverse."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import copy,json,threading,time,uuid
import psycopg
import cp7_sales_payment_cases as payments
cmd,source,b,auth=payments.cmd,payments.source,payments.b,payments.auth

def location(cur,label='P11 return destination'):
 ident=uuid.uuid4();cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,'FG_WAREHOUSE',true)",(ident,'P11RET-'+ident.hex[:8],label));return str(ident)

def read(cur,f,kind='ALLOCATIONS',subject=None,**q):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_sales_returns_v1(%s)',(json.dumps(dict(sale_id=f['sale'],kind=kind,**q)),)).fetchone()[0];b.api.admin(cur);return r

def fixture(cur,today,two=False):
 f=source.fixture(cur,today)
 if two:
  p=dict(sale_id=f['sale'],sale_number=f['tag'],customer_id=f['customer'],source_location_id=f['location'],sale_date=f['sale_at'],reason='Two independent allocations for one product',items=[dict(product_id=f['product'],qty_pcs=2,unit_price_snapshot='20',discount_amount='0') for _ in range(2)])
  f['draft']=b.chain.production.rpc(cur,'erp.save_sale_draft_v2',p,uuid.uuid4(),int(f['draft']['row_version']));b.api.admin(cur)
 f['before_sale']=cmd.accounts(cur);source.fg.post_sale(cur,f['draft']);f['destination']=location(cur);f['bank']=str(source.bc.bank_account(cur,'P11RET'+uuid.uuid4().hex[:8]));f['allocations']=read(cur,f)['page']['rows'];return f

def payload(cur,f,qty='1',refund='20',grade='GRADE_A',allocation=None,destination=None):
 p,v=cmd.review(cur,f);p.update(return_number='RET-'+uuid.uuid4().hex[:12],physical_at=source.fg.ax.r1.now(cur).isoformat(),notes='Physical return notes',items=[dict(allocation_id=allocation or f['allocations'][0]['allocation_id'],location_id=destination or f['destination'],qty_pcs=qty,quality_grade=grade,refund_amount=refund,notes='Return original allocation only')]);return p,v

def returned(cur,f,**options):
 p,v=payload(cur,f,**options);return cmd.command(cur,'RETURN',p,v)

def inverse(cur,f,ident):
 p,v=cmd.review(cur,f);p['return_id']=ident;return cmd.command(cur,'RETURN_REVERSE',p,v)

def reverse_sale(cur,f):
 p,v=cmd.review(cur,f);return cmd.command(cur,'SALE_REVERSE',p,v)

def positions(cur,f):
 return {(str(l),g):int(n) for l,g,n in cur.execute('select location_id,quality_grade,sum(qty_signed) from erp.fg_stock_movements where lot_id=%s group by location_id,quality_grade having sum(qty_signed)<>0',(f['lot'],))}

def cases(cur,today):
 def lifecycle():
  f=fixture(cur,today);before=cmd.accounts(cur);r=returned(cur,f,qty='2',refund='40');assert positions(cur,f)=={(f['location'],'GRADE_A'):6,(f['destination'],'GRADE_A'):2}
  assert cmd.delta(before,cmd.accounts(cur))=={cmd.mapping(cur,'AR_CUSTOMER'):-40,cmd.mapping(cur,'SALES_REVENUE'):40,cmd.mapping(cur,'FG_INVENTORY'):20,cmd.mapping(cur,'COGS'):-20}
  pay=payments.pay(cur,f,'30');assert source.read(cur,f)['detail']['financial']['open_balance']=='10.00'
  p,v=cmd.review(cur,f);auth.refused(cur,lambda:cmd.command(cur,'SALE_REVERSE',p,v),'Reverse pembayaran aktif terlebih dahulu')
  payments.inverse(cur,f,pay['payment_id']);p,v=cmd.review(cur,f);auth.refused(cur,lambda:cmd.command(cur,'SALE_REVERSE',p,v),'Reverse retur aktif terlebih dahulu')
  inverse(cur,f,r['return_id']);assert cmd.accounts(cur)==before and positions(cur,f)=={(f['location'],'GRADE_A'):6}
  z=reverse_sale(cur,f);assert z['status']=='REVERSED' and cmd.accounts(cur)==f['before_sale'] and positions(cur,f)=={(f['location'],'GRADE_A'):10}
  return dict(status='PASS',sale80_return40_cash30_balance10=True,return_A_to_other_warehouse2=True,return_AR_minus40_revenue_plus40_FG_plus20_COGS_minus20=True,inverse_payment_return_sale_order=True,all_GL_neutral=True,final_stock10=True)
 def grades():
  f=fixture(cur,today,True);before=cmd.accounts(cur);p,v=payload(cur,f,refund='20',destination=f['location']);p['items'].append(dict(p['items'][0],allocation_id=f['allocations'][1]['allocation_id'],quality_grade='GRADE_B',location_id=f['destination']))
  r=cmd.command(cur,'RETURN',p,v);hold=returned(cur,f,grade='HOLD')
  assert positions(cur,f)=={(f['location'],'GRADE_A'):7,(f['destination'],'GRADE_B'):1,(f['destination'],'HOLD'):1}
  assert source.read(cur,f)['detail']['financial']['open_balance']=='20.00' and read(cur,f)['page']['rows'][0]['remaining_qty']=='1'
  history=read(cur,f,'RETURNS')['page']['rows'];assert sorted(h['line_count'] for h in history)==['1','2'] and {i['quality_grade'] for h in history for i in h['items']}=={'GRADE_A','GRADE_B','HOLD'}
  assert 'unit_hpp' not in json.dumps(history);inverse(cur,f,hold['return_id']);inverse(cur,f,r['return_id']);assert cmd.accounts(cur)==before and positions(cur,f)=={(f['location'],'GRADE_A'):6}
  return dict(status='PASS',two_allocations_split_A_B_in_one_document=True,same_allocation_HOLD_in_separate_document=True,native_unique_allocation_constraint_preserved=True,current_remaining1=True,native_HPP_conserved_and_inverse_neutral=True,no_HPP_in_AR_projection=True)
 def capacity():
  f=fixture(cur,today,True);assert len(f['allocations'])==2 and all(a['allocated_qty']=='2' for a in f['allocations']);p,v=payload(cur,f,qty='2',refund='40');p['items']*=2;before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v),'CP7_SALES_RETURN_DUPLICATE_ALLOCATION');assert b.boundary.snapshot(cur)==before
  p,v=payload(cur,f,qty='3',refund='60');auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v),'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION');assert b.boundary.snapshot(cur)==before
  a=returned(cur,f,qty='2',refund='40');p,v=payload(cur,f,qty='1',refund='20');before=b.boundary.snapshot(cur);auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v),'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION');assert b.boundary.snapshot(cur)==before
  assert read(cur,f)['page']['rows'][0]['allocation_id']==f['allocations'][1]['allocation_id'];returned(cur,f,qty='2',refund='40',allocation=f['allocations'][1]['allocation_id']);assert read(cur,f)['page']['total']=='0' and source.read(cur,f)['detail']['status']=='PAID'
  return dict(status='PASS',same_product_lot_has_two_independent_allocations=True,duplicate_same_document_line_refused_before_effect=True,prior_documents_share_selected_cap=True,other_allocation_remains_eligible=True,full_return_net_zero=True)
 def fields():
  f=fixture(cur,today);g=fixture(cur,today);p,v=payload(cur,f);before=b.boundary.snapshot(cur)
  for key,value in [('qty_pcs','0'),('qty_pcs','1.5'),('qty_pcs',1),('refund_amount',None),('refund_amount','20.001'),('unit_hpp_snapshot','0'),('product_id',f['product']),('lot_id',g['lot']),('quality_grade','UNKNOWN')]:
   bad=copy.deepcopy(p);bad['items'][0][key]=value;auth.refused(cur,lambda:cmd.command(cur,'RETURN',bad,v),'CP7_SALES_RETURN_LINES')
  bad=copy.deepcopy(p);bad['items'][0]['allocation_id']=g['allocations'][0]['allocation_id'];auth.refused(cur,lambda:cmd.command(cur,'RETURN',bad,v),'CP7_SALES_RETURN_ALLOCATION_CHANGED')
  bad=copy.deepcopy(p);bad['items'][0]['refund_amount']='20.02';auth.refused(cur,lambda:cmd.command(cur,'RETURN',bad,v),'exceeds original net sales value')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',closed_exact_fields_no_client_cost_product_or_lot=True,foreign_sale_and_excess_refund_refused_atomically=True)
 def paid_return():
  f=fixture(cur,today);cash=payments.pay(cur,f,'80');p,v=payload(cur,f);before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v),'membuat pembayaran customer melebihi nilai penjualan tersisa');assert b.boundary.snapshot(cur)==before and cmd.available(cur,f)==6
  payments.inverse(cur,f,cash['payment_id']);returned(cur,f);assert source.read(cur,f)['detail']['financial']['open_balance']=='60.00'
  return dict(status='PASS',paid80_then_return20_refused_without_automatic_refund=True,explicit_payment_inverse_then_return_allowed=True,no_cash_credit_policy_invented=True)
 def dates_locations():
  f=fixture(cur,today);p,v=payload(cur,f);before=b.boundary.snapshot(cur)
  bad=dict(p,physical_at=(source.fg.ax.r1.now(cur)+timedelta(days=1)).isoformat());auth.refused(cur,lambda:cmd.command(cur,'RETURN',bad,v),'CP7_SALES_RETURN_FUTURE_DATE')
  bad=dict(p,physical_at=(source.fg.ax.r1.now(cur)-timedelta(days=1)).isoformat());auth.refused(cur,lambda:cmd.command(cur,'RETURN',bad,v),'lebih awal dari tanggal penjualan sumber');assert b.boundary.snapshot(cur)==before
  cur.execute('update erp.locations set is_active=false where id=%s',(f['destination'],));before=b.boundary.snapshot(cur);auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v),'active FG warehouse');assert b.boundary.snapshot(cur)==before
  assert all(x['id']!=f['destination'] for x in read(cur,f,'LOCATIONS')['page']['rows'])
  return dict(status='PASS',physical_before_sale_or_future_refused=True,inactive_destination_hidden_and_refused=True)
 def replay():
  f=fixture(cur,today);p,v=payload(cur,f);key=uuid.uuid4();r=cmd.command(cur,'RETURN',p,v,key);assert cmd.command(cur,'RETURN',p,v,key)==r;inverse(cur,f,r['return_id']);assert cmd.command(cur,'RETURN',p,v,key)==r
  changed=copy.deepcopy(p);changed['items'][0]['quality_grade']='GRADE_B';auth.refused(cur,lambda:cmd.command(cur,'RETURN',changed,v,key),'CP7_SALES_REQUEST_CHANGED')
  g=fixture(cur,today);rev,version=cmd.review(cur,g);rev['return_id']=r['return_id'];auth.refused(cur,lambda:cmd.command(cur,'RETURN_REVERSE',rev,version),'CP7_SALES_RETURN_SOURCE_CHANGED')
  assert read(cur,f,'RETURNS')['page']['total']=='1' and read(cur,f,'RETURNS')['page']['rows'][0]['status']=='REVERSED'
  return dict(status='PASS',same_UUID_one_return_original_outcome_after_inverse=True,changed_grade_and_foreign_return_refused=True)
 def source_change():
  f=fixture(cur,today);p,v=payload(cur,f)
  cur.execute("insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at) values(%s,%s,%s,%s)",('DRAFT-'+f['tag'],f['sale'],f['customer'],p['physical_at']))
  assert source.read(cur,f)['detail']['row_version']==v and read(cur,f)['review_token']!=p['review_token'];before=b.boundary.snapshot(cur);auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v),'CP7_SALES_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
  reverse_sale(cur,f);p,v=payload(cur,f);auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v),'CP7_SALES_ACTIVE_ONLY')
  return dict(status='PASS',draft_return_activity_invalidates_review_without_header_revision=True,reversed_sale_cannot_receive_return=True)
 def permissions():
  f=fixture(cur,today);subject,role=auth.custom_actor(cur)
  for permission in ('finance.ar.view','sales.return.view','sales.return.create'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,permission))
  p,v=payload(cur,f);key=uuid.uuid4();auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v,key,subject),'CP7_SALES_WRITE_DENIED')
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.return.post'),(%s,'sales.return.reverse')",(role,role));r=cmd.command(cur,'RETURN',p,v,key,subject);assert r['return_status']=='POSTED'
  rev,version=cmd.review(cur,f);rev['return_id']=r['return_id'];auth.refused(cur,lambda:cmd.command(cur,'RETURN_REVERSE',rev,version,subject=subject),'CP7_SALES_OWNER_ADMIN_REQUIRED')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.return.view'",(role,));auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v,key,subject),'CP7_SALES_WRITE_DENIED');auth.refused(cur,lambda:read(cur,f,subject=subject),'CP7_SALES_RETURN_DENIED')
  for principal in ('anon','authenticated','service_role','cp7_capture'):assert not cur.execute("select has_function_privilege(%s,'cp7_sales.return_workspace(jsonb)','EXECUTE') or has_schema_privilege(%s,'cp7_sales','USAGE')",(principal,principal)).fetchone()[0]
  return dict(status='PASS',distinct_current_create_post_view_AR_required=True,legacy_OWNER_ADMIN_inverse_preserved=True,private_source_not_accessible=True)
 def pages():
  f=fixture(cur,today,True);ids=[]
  for off in range(2):
   w=read(cur,f,offset=off,limit=1);assert w['page']['total']=='2' and w['page']['next_offset']==(1 if off==0 else None);ids.append(w['page']['rows'][0]['allocation_id'])
  assert len(set(ids))==2
  for alloc in [f['allocations'][0]['allocation_id'],f['allocations'][0]['allocation_id'],f['allocations'][1]['allocation_id']]:returned(cur,f,allocation=alloc)
  ids=[]
  for off in range(3):
   w=read(cur,f,'RETURNS',offset=off,limit=1);assert w['page']['total']=='3' and w['page']['next_offset']==(off+1 if off<2 else None);ids.append(w['page']['rows'][0]['id'])
  assert len(set(ids))==3;tag='P11 Locations '+uuid.uuid4().hex[:8]
  for suffix in ('A','B','C'):location(cur,tag+suffix)
  for off in range(3):assert read(cur,f,'LOCATIONS',q=tag,offset=off,limit=1)['page']['total']=='3'
  assert read(cur,f,q=uuid.uuid4().hex)['page']['total']=='0';auth.refused(cur,lambda:read(cur,f,limit=101),'CP7_SALES_RETURN_QUERY')
  return dict(status='PASS',complete_allocation_pages2_return_pages3_location_pages3=True,explicit_empty_and_invalid_page=True)
 def consumed():
  f=fixture(cur,today);r=returned(cur,f);sale=b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number='DOWN-'+f['tag'],customer_id=f['customer'],source_location_id=f['destination'],sale_date=source.fg.ax.r1.now(cur).isoformat(),reason='Consume exactly the returned stock',items=[dict(product_id=f['product'],qty_pcs=1,unit_price_snapshot='20',discount_amount=0)]),uuid.uuid4(),None);source.fg.post_sale(cur,sale)
  before=b.boundary.snapshot(cur);auth.refused(cur,lambda:inverse(cur,f,r['return_id']),'Finished goods stock cannot become negative');assert b.boundary.snapshot(cur)==before
  source.native(cur,'select erp.reverse_sale(%s,%s)',(sale['sale_id'],'Undo downstream sale before original return'));inverse(cur,f,r['return_id']);assert positions(cur,f)=={(f['location'],'GRADE_A'):6}
  return dict(status='PASS',consumed_other_warehouse_return_inverse_refused=True,downstream_inverse_then_return_inverse_allowed=True)
 return [('P11_RETURN_'+n,fn) for n,fn in [('LIFECYCLE',lifecycle),('SPLIT_GRADES',grades),('ALLOCATION_CAP',capacity),('FIELDS',fields),('PAID_REFUSAL',paid_return),('DATE_LOCATION',dates_locations),('REPLAY',replay),('SOURCE_CHANGE',source_change),('PERMISSIONS',permissions),('PAGES',pages),('CONSUMED',consumed)]]

def races(tools,today):
 def compete(with_cash=False):
  with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);p,v=payload(cur,f,qty='3' if not with_cash else '2',refund='60' if not with_cash else '40');cash,cv=payments.payment_payload(cur,f,'60');conn.commit()
  barrier=threading.Barrier(2)
  def send(n):
   with tools.connect() as conn,conn.cursor() as cur:
    barrier.wait()
    try:r=cmd.command(cur,'PAYMENT' if with_cash and n==1 else 'RETURN',cash if with_cash and n==1 else dict(p,return_number=p['return_number']+'-'+str(n)),cv if with_cash and n==1 else v);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
  with ThreadPoolExecutor(max_workers=2) as pool:jobs=[pool.submit(send,n) for n in (0,1)];results=[j.result(30) for j in jobs]
  winners=[r for r in results if isinstance(r,dict)];assert len(winners)==1 and any('CP7_SALES_REVIEW_CHANGED' in str(r) for r in results),results
  with tools.connect() as conn,conn.cursor() as cur:
   d=source.read(cur,f)['detail'];assert source.D(d['financial']['paid_total'])<=source.D(d['financial']['net_total'])
   assert cmd.available(cur,f)==(6 if winners[0]['action']=='PAYMENT' else 8 if with_cash else 9)
  return dict(status='PASS',competing_cash_and_return=with_cash,one_exact_review_winner=True,no_overpayment_or_overreturned_stock=True,winner=winners[0]['action'])
 def revoke():
  with tools.connect() as conn,conn.cursor() as cur:
   f=fixture(cur,today);p,v=payload(cur,f);subject,role=auth.custom_actor(cur)
   for permission in ('finance.ar.view','sales.return.view','sales.return.create','sales.return.post'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,permission))
   conn.commit()
  with tools.connect() as holder,holder.cursor() as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
   def send():
    with tools.connect() as conn,conn.cursor() as cur:
     try:cmd.command(cur,'RETURN',p,v,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
     except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
   with ThreadPoolExecutor(max_workers=1) as pool:
    future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
      while time.monotonic()<deadline:
       c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
       if blocked:break
       time.sleep(.03)
      assert blocked,'EXPECTED_REAL_RETURN_WAIT';c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.return.post'",(role,))
    finally:holder.rollback()
    result=future.result(30)
  assert 'CP7_SALES_WRITE_DENIED' in result,result
  with tools.connect() as conn,conn.cursor() as cur:assert read(cur,f,'RETURNS')['page']['total']=='0' and cmd.available(cur,f)==6
  return dict(status='PASS',actual_wait_and_current_revocation_refused_before_effect=True)
 return [('P11_RETURN_RACE_CAPACITY',compete),('P11_RETURN_RACE_CASH',lambda:compete(True)),('P11_RETURN_RACE_REVOKE',revoke)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p11-return-owner')
  with http.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);p,v=payload(cur,f,grade='GRADE_B');conn.commit()
  q=owner.rpc('erp_cp7_get_sales_returns_v1',dict(p_query=dict(sale_id=f['sale'],kind='ALLOCATIONS')));assert q['status']==200 and q['body']['page']['rows'][0]['remaining_qty']=='4',q
  args=dict(p_action='RETURN',p_payload=p,p_request=str(uuid.uuid4()),p_expected=v);assert http.anon_rpc('erp_cp7_save_sale_v1',args)['status'] in(401,403);r=owner.rpc('erp_cp7_save_sale_v1',args);assert r['status']==200 and r['body']['return_status']=='POSTED',r;assert owner.rpc('erp_cp7_save_sale_v1',args)['body']==r['body']
  with http.connect() as conn,conn.cursor() as cur:
   assert positions(cur,f)=={(f['location'],'GRADE_A'):6,(f['destination'],'GRADE_B'):1};p,v=cmd.review(cur,f);p['return_id']=r['body']['return_id']
  r=owner.rpc('erp_cp7_save_sale_v1',dict(p_action='RETURN_REVERSE',p_payload=p,p_request=str(uuid.uuid4()),p_expected=v));assert r['status']==200 and r['body']['return_status']=='REVERSED',r
  return dict(status='PASS',real_auth_selected_allocation_to_other_warehouse_GradeB=True,exact_replay_and_inverse=True)
 return [('P11_RETURN_HTTP',flow)]
