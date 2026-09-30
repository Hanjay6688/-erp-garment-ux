"""Declared P05 native-source cases. No fabricated business rows or source flags."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import json,threading,time,uuid
import psycopg
import cp7_sales_cases as sales
import cp7_finance_analysis_cases as analysis
import cp7_procurement_cases as receipt
import cp7_snapshot_cases as auth

b=sales.b

def query(today,days=1):
 return dict(from_date=str(today-timedelta(days=days)),through_date=str(today-timedelta(days=1)),group_mode='AS_SOLD')

def capture(cur,today,key=None,subject=None,q=None):
 auth.actor(cur,subject)
 r=cur.execute('select public.erp_cp7_capture_demand_history_v1(%s,%s)',(json.dumps(q or query(today)),key or uuid.uuid4())).fetchone()[0]
 b.api.admin(cur);return r

def read(cur,run,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_read_demand_history_v1(%s)',(run,)).fetchone()[0]
 b.api.admin(cur);return r

def fixture(cur,today,qty=24,stock=100):
 day=today-timedelta(days=1)
 product,_=sales.fg.ax.owner_only_model_product(cur,effective_from=day-timedelta(days=10))
 found=sales.fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=sales.fg.base.LOCATION,
  qty_pcs=stock,physical_at=receipt.aa.at(day,8).isoformat(),reason='P05 native stock source',owner_unit_value='10',owner_value_reason='P05 explicit source value'))
 b.api.admin(cur);tag='P05-'+uuid.uuid4().hex[:12];customer=str(sales.fg.base.create_customer(cur,tag))
 draft=b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number=tag,customer_id=customer,
  source_location_id=sales.fg.base.LOCATION,sale_date=receipt.aa.at(day,10).isoformat(),reason='P05 native demand source',
  items=[dict(product_id=product,qty_pcs=qty,unit_price_snapshot='20',discount_amount='0')]),uuid.uuid4(),None)
 b.api.admin(cur);lot=str(cur.execute('select lot_id from erp.fg_unsourced_receipts_v1 where id=%s',(found['receipt_id'],)).fetchone()[0])
 return dict(product=str(product),lot=lot,location=sales.fg.base.LOCATION,tag=tag,customer=customer,sale=draft['sale_id'],draft=draft,day=day)

def row(r,f):
 return next(x for x in r['current_stock']if x['root_id']==f['product'])

def history(r,f):
 return next(x for x in r['history']['rows']if x['target_key'].split(':')[0]==f['product'])

def stock_assert(cur,r,f,physical,reserved,available):
 native=sales.fg.workspace(cur,dict(sku=cur.execute('select sku from erp.products where id=%s',(f['product'],)).fetchone()[0]))
 assert sales.fg.qty(native)==[physical,reserved,available],native
 a=row(r,f)['availability']
 assert [D(a[k])for k in('physical_fg_pcs','reserved_pcs','available_fg_pcs')]==list(map(D,[physical,reserved,available])),a
 assert D(row(r,f)['native_available_pcs'])==available

def cases(cur,today):
 def draft_once():
  f=fixture(cur,today);before=b.boundary.snapshot(cur);r=capture(cur,today)
  stock_assert(cur,r,f,100,24,76);h=history(r,f)
  assert h['gross_observed_pcs']=='0' and h['draft_reserved_pcs']=='24',h
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',native_draft=[100,24,76],gross=0,no_native_business_write=True)
 def posted_once():
  f=fixture(cur,today);sales.fg.post_sale(cur,f['draft']);r=capture(cur,today);stock_assert(cur,r,f,76,0,76)
  assert history(r,f)['gross_observed_pcs']=='24',history(r,f)
  return dict(status='PASS',native_posted=[76,0,76],gross=24,no_second_stock_subtraction=True)
 def returned_separate():
  f=fixture(cur,today);sales.fg.post_sale(cur,f['draft']);sales.returned(cur,f);r=capture(cur,today)
  stock_assert(cur,r,f,77,0,77);h=history(r,f);assert h['gross_observed_pcs']=='24' and h['days'][0]['returned_pcs']=='1',h
  return dict(status='PASS',gross=24,returns_separate=1,native_fg=77)
 def inverses():
  f=fixture(cur,today);sales.fg.post_sale(cur,f['draft']);ret=sales.returned(cur,f)
  sales.native(cur,'select erp.reverse_sales_return(%s,%s)',(ret,'P05 native return inverse'))
  sales.native(cur,'select erp.reverse_sale(%s,%s)',(f['sale'],'P05 native whole invoice inverse'))
  r=capture(cur,today);stock_assert(cur,r,f,100,0,100);assert history(r,f)['gross_observed_pcs']=='0',history(r,f)
  return dict(status='PASS',native_inverse_fg=100,cancelled_gross=0,WIB_inverse_date=True)
 def replay_stale():
  f=fixture(cur,today);key=uuid.uuid4();r=capture(cur,today,key);assert capture(cur,today,key)==r
  original=cur.execute('select result,facts from cp7_planning.history_runs where id=%s',(r['run_id'],)).fetchone()
  sales.fg.post_sale(cur,f['draft']);stale=read(cur,r['run_id']);assert stale['source_state']=='ARCHIVED_STALE'and row(stale,f)==row(r,f),stale
  assert cur.execute('select result,facts from cp7_planning.history_runs where id=%s',(r['run_id'],)).fetchone()==original
  changed=query(today);changed['group_mode']='RESTATED'
  auth.refused(cur,lambda:capture(cur,today,key,q=changed),'CP7_PLANNING_REQUEST_CHANGED')
  assert cur.execute('select count(*)from cp7_planning.history_runs where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',exact_UUID_one_immutable_run=True,native_post_makes_archive_stale=True,changed_payload_refused=True)
 def access_redacted():
  f=fixture(cur,today);subject,_=auth.custom_actor(cur);r=capture(cur,today,subject=subject);stock_assert(cur,r,f,100,24,76)
  forbidden=('unit_price','unit_hpp','debit','credit','gross_total','net_total','cost_amount','refund_amount')
  assert all(k not in json.dumps(r)for k in forbidden),r
  return dict(status='PASS',four_operational_permissions_suffice=True,no_financial_operands=True)
 def current_revocation():
  fixture(cur,today);subject,role=auth.custom_actor(cur);key=uuid.uuid4();r=capture(cur,today,key,subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
  auth.refused(cur,lambda:capture(cur,today,key,subject),'CP7_ACCESS_DENIED');auth.refused(cur,lambda:read(cur,r['run_id'],subject),'CP7_ACCESS_DENIED')
  return dict(status='PASS',current_revocation_precedes_cached_UUID_and_archive=True)
 def closed_query():
  fixture(cur,today)
  for extra in({'scope':'SELECTED'},{'history_complete':True},{'q':'P05'},{'complete_scope':True}):
   auth.refused(cur,lambda extra=extra:capture(cur,today,q=dict(query(today),**extra)),'CP7_WIP_FIELDS')
  q=query(today);q['through_date']=str(today);auth.refused(cur,lambda:capture(cur,today,q=q),'CP7_PLANNING_HISTORY_QUERY')
  q=query(today);q['from_date']='2026-02-30';auth.refused(cur,lambda:capture(cur,today,q=q),'date/time field value out of range')
  return dict(status='PASS',client_scope_completeness_filters_refused=True,current_incomplete_day_refused=True,invalid_day_refused=True)
 def immutable_private():
  fixture(cur,today);r=capture(cur,today)
  auth.refused(cur,lambda:cur.execute('update cp7_planning.history_runs set facts=\'{}\'where id=%s',(r['run_id'],)),'CP7_RUN_IMMUTABLE')
  auth.refused(cur,lambda:cur.execute('delete from cp7_planning.history_runs where id=%s',(r['run_id'],)),'CP7_RUN_IMMUTABLE')
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_planning','USAGE')or has_table_privilege(%s,'cp7_planning.history_runs','SELECT,INSERT,UPDATE,DELETE')",(who,who)).fetchone()[0]
  assert not cur.execute("select exists(select 1 from pg_class t join pg_namespace n on n.oid=t.relnamespace where n.nspname='erp'and t.relkind in('r','p','v')and has_table_privilege('cp7_capture',t.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
  for fn in('erp.save_sale_draft_v2(jsonb,uuid,bigint)','erp.post_sale_v2(uuid,uuid,bigint)','erp.post_sales_return(uuid)'):
   assert not cur.execute("select has_function_privilege('cp7_capture',%s,'EXECUTE')",(fn,)).fetchone()[0]
  return dict(status='PASS',private_metadata_immutable=True,native_read_principal_no_business_DML_or_writer_EXEC=True)
 def timezone():
  f=fixture(cur,today);sales.fg.post_sale(cur,f['draft']);key=uuid.uuid4();r=capture(cur,today,key)
  for zone in('UTC','Asia/Jakarta','America/Los_Angeles'):
   cur.execute("select set_config('TimeZone',%s,true)",(zone,));assert capture(cur,today,key)==r
  assert history(r,f)['days'][0]['date']==str(f['day'])
  return dict(status='PASS',three_caller_timezones_same_immutable_result_and_source_hash=True,WIB_sale_day=True)
 def unknown_history():
  f=fixture(cur,today);sales.fg.cancel(cur,f['draft']);r=capture(cur,today);h=history(r,f)
  assert h['days'][0]['state']=='UNKNOWN'and h['days'][0]['training_pcs']is None and h['available_sales_mean']is None,h
  assert r['model_eligibility']=='HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED'
  return dict(status='PASS',backdated_stock_not_fake_historical_training=True,unknown_not_zero_or_forecast=True)
 def complete_scope():
  fs=[fixture(cur,today,qty=1,stock=1)for _ in range(30)];r=capture(cur,today);roots={x['root_id']for x in r['current_stock']}
  assert all(f['product']in roots for f in fs) and len(roots)>=30 and r['capture_complete']is True
  return dict(status='PASS',actual_native_roots=30,global_scope_has_all30_not_first25=True)
 return [('P05_NATIVE_'+name,fn)for name,fn in [('DRAFT_ONCE',draft_once),('POSTED_ONCE',posted_once),('RETURN_SEPARATE',returned_separate),('NATIVE_INVERSES',inverses),('IMMUTABLE_REPLAY_STALE',replay_stale),('OPERATIONAL_REDACTION',access_redacted),('CURRENT_REVOKE',current_revocation),('CLOSED_QUERY',closed_query),('PRIVATE_CAPS',immutable_private),('TIMEZONES',timezone),('UNKNOWN_HISTORY',unknown_history),('GLOBAL_30_ROOTS',complete_scope)]]

def races(tools,today):
 def same_uuid():
  with tools.connect()as conn,conn.cursor()as cur:fixture(cur,today);conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:
    gate.wait(timeout=5);r=capture(cur,today,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:
   jobs=[pool.submit(send)for _ in range(2)];rs=[j.result(30)for j in jobs]
  assert rs[0]==rs[1],rs
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_planning.history_runs where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',two_real_transactions_one_UUID_one_immutable_run=True)
 def revoke_waiting():
  with tools.connect()as conn,conn.cursor()as cur:
   fixture(cur,today);subject,role=auth.custom_actor(cur);key=uuid.uuid4();r=capture(cur,today,key,subject);conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:HISTORY:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:out=capture(cur,today,key,subject);conn.commit();return out
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_capture_demand_history_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P05_REAL_REQUEST_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(30)
  assert isinstance(result,str)and'CP7_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select result from cp7_planning.history_runs where id=%s',(r['run_id'],)).fetchone()[0]['source_hash']==r['source_hash']
  return dict(status='PASS',current_revocation_during_observed_cached_UUID_lock_refuses=True,immutable_prior_run_preserved=True)
 return [('P05_RACE_SAME_UUID',same_uuid),('P05_RACE_CURRENT_REVOKE',revoke_waiting)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p05-native-owner')
  with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);conn.commit()
  args=dict(p_query=query(today),p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_capture_demand_history_v1',args);assert r['status']==200,r
  assert row(r['body'],f)['native_available_pcs']=='76';assert owner.rpc('erp_cp7_capture_demand_history_v1',args)['body']==r['body']
  assert http.anon_rpc('erp_cp7_capture_demand_history_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_capture_demand_history_v1',args)['status']==403
  assert owner.rpc('erp_cp7_read_demand_history_v1',dict(p_run=r['body']['run_id']))['status']==403
  return dict(status='PASS',real_Auth_PostgREST_native76=True,current_deactivation_before_cached_response=True,anonymous_refused=True)
 return [('P05_ACTUAL_AUTH_HTTP',flow)]
