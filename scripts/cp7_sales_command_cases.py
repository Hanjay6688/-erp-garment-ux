"""Reviewed P11 draft transitions, stock/GL conservation, actual wait and replay."""
from concurrent.futures import ThreadPoolExecutor
import copy,json,threading,time,uuid
import psycopg
import cp7_sales_cases as source
b,auth=source.b,source.auth

def command(cur,action,payload,version,key=None,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_save_sale_v1(%s,%s,%s,%s)',(action,json.dumps(payload),key or uuid.uuid4(),version)).fetchone()[0];b.api.admin(cur);return r

def review(cur,f):
 d=source.read(cur,f)['detail'];return dict(sale_id=d['id'],review_token=d['review_token'],change_reason='Invoice quantities and amount reviewed'),d['row_version']

def available(cur,f):return int(cur.execute('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(f['lot'],)).fetchone()[0])

def accounts(cur):return {str(k):v for k,v in source.gl(cur)}
def mapping(cur,key):return str(cur.execute('select account_id from erp.accounting_account_mappings where mapping_key=%s',(key,)).fetchone()[0])
def delta(before,after):return {k:after.get(k,0)-before.get(k,0) for k in before.keys()|after.keys() if after.get(k,0)!=before.get(k,0)}

def cases(cur,today):
 def post():
  f=source.fixture(cur,today);p,v=review(cur,f);key=uuid.uuid4();before=accounts(cur);assert available(cur,f)==6
  r=command(cur,'POST',p,v,key);assert r['status']=='POSTED' and r['row_version']!=v and available(cur,f)==6
  assert delta(before,accounts(cur))=={mapping(cur,'AR_CUSTOMER'):80,mapping(cur,'SALES_REVENUE'):-80,mapping(cur,'FG_INVENTORY'):-40,mapping(cur,'COGS'):40}
  assert command(cur,'POST',p,v,key)==r
  source.native(cur,'select erp.reverse_sale(%s,%s)',(f['sale'],'native inverse control'))
  assert available(cur,f)==10 and accounts(cur)==before and command(cur,'POST',p,v,key)==r
  return dict(status='PASS',reserved_available=6,post_available=6,AR=80,COGS=40,one_native_post=True,replay_after_native_inverse_is_original_outcome=True,inverse_stock=10,inverse_gl_neutral=True)
 def cancel():
  f=source.fixture(cur,today);p,v=review(cur,f);key=uuid.uuid4();before=accounts(cur);r=command(cur,'CANCEL',p,v,key)
  assert r['status']=='CANCELLED' and available(cur,f)==10 and source.read(cur,f)['detail']['reserved_qty']=='0' and accounts(cur)==before
  assert command(cur,'CANCEL',p,v,key)==r
  return dict(status='PASS',draft_cancel_releases_exact4=True,no_invoice_or_cash_posting=True,exact_replay=True)
 def child():
  f=source.fixture(cur,today);p,v=review(cur,f)
  cur.execute('update erp.sales_items set unit_price_snapshot=21 where sale_id=%s',(f['sale'],));before=b.boundary.snapshot(cur)
  assert source.read(cur,f)['detail']['row_version']==v,'TEST_REQUIRES_UNCHANGED_HEADER_VERSION'
  auth.refused(cur,lambda:command(cur,'POST',p,v),'CP7_SALES_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
  p,v=review(cur,f);r=command(cur,'POST',p,v);assert r['status']=='POSTED' and source.read(cur,f)['detail']['financial']['net_total']=='84.00'
  return dict(status='PASS',child_price_change_rejected_without_header_bump=True,fresh_review_posts_native84=True)
 def version():
  f=source.fixture(cur,today);p,v=review(cur,f);before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:command(cur,'CANCEL',p,str(int(v)+1)),'CP7_SALES_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
  fg=copy.deepcopy(p);fg['review_token']='0'*32;auth.refused(cur,lambda:command(cur,'POST',fg,v),'CP7_SALES_REVIEW_CHANGED')
  source.fg.cancel(cur,f['draft']);p,v=review(cur,f);auth.refused(cur,lambda:command(cur,'POST',p,v),'CP7_SALES_DRAFT_ONLY')
  return dict(status='PASS',stale_version_token_and_non_draft_refused_atomically=True)
 def replay_access():
  f=source.fixture(cur,today);p,v=review(cur,f);key=uuid.uuid4();r=command(cur,'CANCEL',p,v,key)
  bad=dict(p,change_reason='Different intent must not replay');auth.refused(cur,lambda:command(cur,'CANCEL',bad,v,key),'CP7_SALES_REQUEST_CHANGED')
  subject,role=auth.custom_actor(cur);cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.ar.view'),(%s,'sales.invoice.edit_draft')",(role,role))
  auth.refused(cur,lambda:command(cur,'CANCEL',p,v,key,subject),'CP7_SALES_REVIEW_CHANGED')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,));auth.refused(cur,lambda:command(cur,'CANCEL',p,v,key,subject),'CP7_SALES_WRITE_DENIED')
  assert command(cur,'CANCEL',p,v,key)==r
  return dict(status='PASS',changed_intent_refused=True,another_actor_cannot_replay_cached_result=True,current_financial_authority_required=True)
 def private():
  f=source.fixture(cur,today);p,v=review(cur,f);before=b.boundary.snapshot(cur)
  for bad in (dict(p,unit_hpp='0'),dict(p,review_token=None),dict(p,change_reason='')):auth.refused(cur,lambda:command(cur,'POST',bad,v),'CP7_SALES_COMMAND_FIELDS')
  assert b.boundary.snapshot(cur)==before
  assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_sales_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
  for who in ('anon','authenticated','service_role','cp7_capture'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_sales','USAGE') or has_function_privilege(%s,'cp7_sales.apply_command(text,jsonb,uuid,text)','EXECUTE')",(who,who)).fetchone()[0]
  assert not cur.execute("select has_function_privilege('cp7_sales_write','erp.post_sale_v2(uuid,uuid,bigint)','EXECUTE')").fetchone()[0]
  for who in ('anon','authenticated','service_role','cp7_capture','cp7_sales_write'):
   assert not cur.execute("select has_function_privilege(%s,'cp7_sales.command_allowed(text)','EXECUTE')",(who,)).fetchone()[0]
  import cp7_p19_sales_admission_equivalence as admission
  equivalence=admission.compare(cur,auth,b.api,b.boundary)
  import cp7_p19_sales_dispatch_equivalence as dispatch
  precedence=dispatch.compare(cur,auth,b.api,b.boundary)
  return dict(status='PASS',closed_payload=True,client_hpp_rejected=True,no_business_dml_or_native_writer_grant=True,private_context_unreachable=True,private_admission_equivalence=equivalence,private_dispatch_equivalence=precedence)
 return [('P11_COMMAND_'+n,fn) for n,fn in [('POST_ONCE',post),('CANCEL',cancel),('CHILD_REVIEW',child),('VERSION_STATUS',version),('REPLAY_AUTH',replay_access),('PRIVATE_FIELDS',private)]]

def races(tools,today):
 def compete():
  with tools.connect() as conn,conn.cursor() as cur:f=source.fixture(cur,today);p,v=review(cur,f);conn.commit()
  barrier=threading.Barrier(2)
  def send(action):
   with tools.connect() as conn,conn.cursor() as cur:
    barrier.wait()
    try:r=command(cur,action,p,v);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
  with ThreadPoolExecutor(max_workers=2) as pool:jobs=[pool.submit(send,a) for a in ('POST','CANCEL')];results=[j.result(30) for j in jobs]
  good=[x for x in results if isinstance(x,dict)];assert len(good)==1,results
  with tools.connect() as conn,conn.cursor() as cur:assert available(cur,f)==(6 if good[0]['status']=='POSTED' else 10)
  assert any('CP7_SALES_REVIEW_CHANGED' in str(x) for x in results),results
  return dict(status='PASS',real_competing_post_cancel_one_transition=True,loser_atomic=True,winner=good[0]['status'])
 def revoke():
  with tools.connect() as conn,conn.cursor() as cur:
   f=source.fixture(cur,today);p,v=review(cur,f);subject,role=auth.custom_actor(cur)
   cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.ar.view'),(%s,'sales.invoice.post')",(role,role));conn.commit()
  with tools.connect() as holder,holder.cursor() as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
   def send():
    with tools.connect() as conn,conn.cursor() as cur:
     try:command(cur,'POST',p,v,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
     except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
   with ThreadPoolExecutor(max_workers=1) as pool:
    future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
      while time.monotonic()<deadline:
       c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
       if blocked:break
       time.sleep(.03)
      assert blocked,'EXPECTED_REAL_SALES_WAIT';c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
    finally:holder.rollback()
    result=future.result(30)
  assert 'CP7_SALES_ACCESS_DENIED' in result,result
  with tools.connect() as conn,conn.cursor() as cur:assert available(cur,f)==6 and source.read(cur,f)['detail']['status']=='DRAFT'
  return dict(status='PASS',actual_lock_wait_observed=True,revocation_before_native_effect=True,draft_and_reservation_retained=True)
 return [('P11_COMMAND_RACE_POST_CANCEL',compete),('P11_COMMAND_RACE_REVOKE',revoke)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p11-command-owner')
  with http.connect() as conn,conn.cursor() as cur:f=source.fixture(cur,today);p,v=review(cur,f);conn.commit()
  args=dict(p_action='POST',p_payload=p,p_request=str(uuid.uuid4()),p_expected=v)
  assert http.anon_rpc('erp_cp7_save_sale_v1',args)['status'] in(401,403)
  r=owner.rpc('erp_cp7_save_sale_v1',args);assert r['status']==200 and r['body']['status']=='POSTED',r
  assert owner.rpc('erp_cp7_save_sale_v1',args)['body']==r['body']
  with http.connect() as conn,conn.cursor() as cur:assert available(cur,f)==6;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_save_sale_v1',args)['status']==403
  return dict(status='PASS',real_auth_command_and_exact_replay=True,no_direct_tables=True,current_deactivation_before_cached_outcome=True)
 return [('P11_COMMAND_HTTP_AUTH',flow)]
