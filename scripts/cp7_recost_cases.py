"""Queue command proof; native costing rules stay unchanged and authoritative."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import json,uuid,threading,time
import psycopg
import cp7_finance_cases as finance
import cp7_period_cases as period
import cp7_procurement_cases as receipt
b,auth,aw=finance.b,finance.auth,finance.aw
def read(cur,offset=0,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_recost_queue_v1(%s)',(offset,)).fetchone()[0];b.api.admin(cur);return r
def command(cur,key=None,subject=None,payload=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_process_recost_v1(%s,%s)',(json.dumps(payload or dict(limit=20,reason='P13 review late source cost')),key or uuid.uuid4())).fetchone()[0];b.api.admin(cur);return r
def stock(cur):
 return {table:cur.execute('select coalesce(jsonb_agg(jsonb_build_array(id,qty_signed) order by id),\'[]\') from erp.'+table).fetchone()[0]for table in ('material_stock_movements','fg_stock_movements')}
def values(cur,f):
 return cur.execute('select jsonb_build_object(\'hpp\',hpp_total_cost,\'fg\',fg_value,\'cogs\',cogs_value) from erp.po_hpp_gl_state where po_id=%s',(f['po'],)).fetchone()[0]
def fixture(cur,today):
 f,day,filing=finance.archive_fixture(cur,today);original=finance.read(cur,day,filing_id=filing);period.late(cur,f)
 assert cur.execute("select count(*) from erp.cost_recalc_queue where entity_id=%s and status='PENDING'",(f['po'],)).fetchone()[0]>0
 return dict(f=f,day=day,filing=filing,original=original)
def fault(cur,status='PENDING',attempts=0,future=False):
 # Explicit administrative fault injection. No ordinary business API creates
 # an unsupported queue entity. It tests the unchanged native catch/retry path.
 b.api.admin(cur)
 return str(cur.execute("insert into erp.cost_recalc_queue(entity_type,entity_id,reason,status,attempt_count,next_attempt_at) values('P13_UNSUPPORTED',%s,'Disposable queue failure control',%s,%s,case when %s then statement_timestamp()+interval '1 hour' end) returning id",(uuid.uuid4(),status,attempts,future)).fetchone()[0])
def cases(cur,today):
 def lifecycle():
  f=fixture(cur,today);old=values(cur,f['f']);physical=stock(cur);r=command(cur);new=values(cur,f['f'])
  assert {k:D(v)for k,v in old.items()}==dict(hpp=D(85),fg=D(51),cogs=D(34)),old
  assert {k:D(v)for k,v in new.items()}==dict(hpp=D(90),fg=D(54),cogs=D(36)),new
  assert r['completed']>=1 and r['queue_after']['counts']['eligible']=='0' and stock(cur)==physical
  now=finance.read(cur,f['day'],filing_id=f['filing']);assert now['filing']==f['original']['filing'] and now['snapshot']['financial_position']==f['original']['snapshot']['financial_position']
  assert now['snapshot']['data_confidence']['status']=='READY' and now['snapshot']['data_confidence']['changed_since_filing']
  return dict(status='PASS',native_PO_cost85_to90_FG51_to54_COGS34_to36=True,no_new_physical_movement=True,closed_day_GL_and_original_filing_immutable=True,READY_still_keeps_later_change_marker=True)
 def replay():
  f=fixture(cur,today);key=uuid.uuid4();first=command(cur,key);fault(cur);before=b.boundary.snapshot(cur);assert command(cur,key)==first and b.boundary.snapshot(cur)==before
  auth.refused(cur,lambda:command(cur,key,payload=dict(limit=20,reason='Different intent')),'CP7_RECOST_REQUEST_CHANGED');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',same_request_never_consumes_newly_queued_work=True,changed_intent_refused_atomically=True)
 def empty():
  assert read(cur)['page']['total']=='0';before=finance.cmd.accounts(cur);r=command(cur);assert r['completed']==0 and r['queue_after']['counts']['eligible']=='0' and finance.cmd.accounts(cur)==before
  return dict(status='PASS',zero_completed_is_explicit_no_cash_or_HPP_finality_claim=True)
 def bounded_failure():
  ids=[fault(cur)for _ in range(26)];before=finance.cmd.accounts(cur);r=command(cur);state=read(cur)
  assert r['completed']==0 and state['counts']['failed']=='20' and state['counts']['pending']=='6' and state['counts']['eligible']=='6'
  rows=state['page']['rows']+read(cur,25)['page']['rows'];assert len(rows)==26 and {x['id']for x in rows}==set(ids)
  assert all('Unsupported cost recalc entity_type' in x['error_message']for x in rows if x['status']=='FAILED') and finance.cmd.accounts(cur)==before
  return dict(status='PASS',administrative_fault_injection=True,native_max20_of26_attempted_failed_not_reported_done=True,complete_pages_and_unmodified_GL=True)
 def retry():
  future=fault(cur,'FAILED',1,True);exhausted=fault(cur,'FAILED',3);running=fault(cur,'RUNNING',1);due=fault(cur,'FAILED',1)
  r=command(cur);rows={x['id']:x for x in read(cur)['page']['rows']};assert r['completed']==0 and r['queue_after']['counts']['exhausted']=='1' and r['queue_after']['counts']['eligible']=='0'
  assert rows[future]['attempt_count']==1 and rows[exhausted]['attempt_count']==3 and rows[running]['status']=='RUNNING' and rows[due]['attempt_count']==2
  return dict(status='PASS',administrative_fault_injection=True,native_retry_schedule_max_attempts_and_running_exclusion_preserved=True)
 def invalid():
  before=b.boundary.snapshot(cur)
  for payload in (dict(limit=21,reason='x'),dict(limit='20',reason='x'),dict(limit=20,reason=''),dict(limit=20,reason='x',force=True)):
   auth.refused(cur,lambda:command(cur,payload=payload),'CP7_RECOST_COMMAND')
  auth.refused(cur,lambda:read(cur,-1),'CP7_RECOST_QUERY');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',closed_intent_no_limit_override_force_or_queue_id_selection=True,atomic_refusals=True)
 def access():
  subject,role=receipt.custom(cur,('finance.hpp.view',));assert read(cur,subject=subject)['contract_version']=='cp7.recost-queue.v1'
  auth.refused(cur,lambda:command(cur,subject=subject),'CP7_RECOST_ACCESS_DENIED');cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.hpp.manage')",(role,));auth.refused(cur,lambda:command(cur,subject=subject),'CP7_RECOST_NATIVE_ROLE_REQUIRED')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,));auth.refused(cur,lambda:read(cur,subject=subject),'CP7_RECOST_ACCESS_DENIED')
  return dict(status='PASS',current_read_and_manage_permissions_separate=True,native_internal_role_boundary_preserved=True)
 def private():
  for role in ('anon','authenticated','service_role','cp7_capture','cp7_finance_read'):
   assert not cur.execute("select has_function_privilege(%s,'cp7_recost.command(jsonb,uuid)','EXECUTE')",(role,)).fetchone()[0]
  for role in ('cp7_recost_read','cp7_recost_write'):
   assert not cur.execute("select exists(select 1 from pg_tables where schemaname='erp' and has_table_privilege(%s,quote_ident(schemaname)||'.'||quote_ident(tablename),'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))",(role,)).fetchone()[0]
  assert not cur.execute("select has_function_privilege('cp7_recost_read','erp.process_cost_recalc_queue(integer)','EXECUTE')").fetchone()[0]
  return dict(status='PASS',no_facade_business_DML_or_reader_process_authority=True,no_public_private_command_access=True)
 return [('P13_RECOST_'+name,fn)for name,fn in [('LATE_COST',lifecycle),('REPLAY',replay),('EMPTY',empty),('BOUNDED_FAILURE',bounded_failure),('RETRY',retry),('INVALID',invalid),('ACCESS',access),('PRIVATE',private)]]
def races(tools,today):
 def duplicate():
  with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);conn.commit()
  gate=threading.Barrier(2);key=uuid.uuid4()
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait();r=command(cur,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:jobs=[pool.submit(send)for _ in range(2)];rows=[j.result(30)for j in jobs]
  assert rows[0]==rows[1] and rows[0]['completed']>=1
  with tools.connect()as conn,conn.cursor()as cur:
   assert cur.execute('select count(*) from cp7_recost.requests where request_id=%s',(key,)).fetchone()[0]==1
   assert cur.execute('select max(attempt_count) from erp.cost_recalc_queue where entity_id=%s',(f['f']['po'],)).fetchone()[0]==1
  return dict(status='PASS',two_real_transactions_same_uuid_one_native_attempt=True)
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:
   f=fixture(cur,today);subject,_=receipt.custom(cur,());role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
   for permission in ('finance.hpp.view','finance.hpp.manage'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s) on conflict do nothing',(role,permission))
   cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));conn.commit()
  key=uuid.uuid4()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',('cp7.recost.request:'+subject+':'+str(key),))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=command(cur,key,subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    future=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    while time.monotonic()<deadline:
     with tools.connect()as conn,conn.cursor()as cur:waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and query like 'select public.erp_cp7_process_recost_v1%')").fetchone()[0]
     if waiting:break
     time.sleep(.05)
    try:
     assert waiting,'Request lock wait not observed'
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.manage'",(role,));conn.commit()
    finally:holder.rollback()
    result=future.result(30)
  assert isinstance(result,str) and 'CP7_RECOST_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*) from cp7_recost.requests where request_id=%s',(key,)).fetchone()[0]==0
  return dict(status='PASS',revocation_during_observed_request_lock_refused_before_cost_processing=True)
 return [('P13_RECOST_RACE_REPLAY',duplicate),('P13_RECOST_RACE_REVOKE',revoke)]
def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p13-recost-owner')
  with http.connect()as conn,conn.cursor()as cur:
   # Native source preparation needs only a temporary schema USAGE, restored
   # before the real public HTTP calls; no EXECUTE grants are widened.
   had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
   if not had:cur.execute('grant usage on schema erp to authenticated')
   f=fixture(cur,today);b.api.admin(cur)
   if not had:cur.execute('revoke usage on schema erp from authenticated')
   conn.commit()
  args=dict(p_payload=dict(limit=20,reason='HTTP actual late costs'),p_request=str(uuid.uuid4()));assert http.anon_rpc('erp_cp7_process_recost_v1',args)['status']in(401,403)
  r=owner.rpc('erp_cp7_process_recost_v1',args);assert r['status']==200 and r['body']['completed']>=1,r
  assert owner.rpc('erp_cp7_process_recost_v1',args)['body']==r['body']
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_process_recost_v1',args)['status']==403 and owner.rpc('erp_cp7_get_recost_queue_v1',dict(p_offset=0))['status']==403
  return dict(status='PASS',real_Auth_native_recost_and_exact_replay=True,deactivation_blocks_cached_outcome_and_queue=True)
 return [('P13_RECOST_HTTP',flow)]
