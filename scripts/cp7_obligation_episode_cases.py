"""Native business-source identity/recovery metadata, never an AP/AR ledger."""
import json,uuid,threading,time
from concurrent.futures import ThreadPoolExecutor
import psycopg
import cp7_payable_condition_cases as previous
ar,attention,parent,auth,b=previous.ar,previous.ar.attention,previous.parent,previous.auth,previous.b
def evaluate(cur,original,domain='AR',key=None,subject=None,lookup=False):
 return attention.rpc(cur,'erp_cp7_get_obligation_episode_request_v1'if lookup else'erp_cp7_evaluate_obligation_episodes_v1',
  (json.dumps(dict(run_id=original['run_id'],domain=domain)),key or uuid.uuid4()),subject)
def row(e,source):return next(x for x in e['result']['rows']if x['source_id']==source)
def checked(e,original):
 assert e['contract_version']=='cp7.native-obligation-observation.v1'and e['read_kind']=='SAVED_OBSERVATION'
 assert e['analysis']['analysis']==original['analysis']and e['analysis']['financial_source']==original['financial_source']
 assert len({x['source_id']for x in e['result']['rows']})==len(e['result']['rows'])
 assert not any(k in x for x in e['result']['rows']for k in('remaining','paid','gross_total','final_ap','open_balance'))
 return e
def ar_fixture(cur,today):
 parent.setup(cur,today);f=ar.sales.fixture(cur,today,qty=20,price='25',stock=30);ar.sales.fg.post_sale(cur,f['draft']);ar.sales.payment(cur,f,today,'200');return f,parent.capture(cur,today)
def cases(cur,today):
 def recurrence():
  f,original=ar_fixture(cur,today);before=b.boundary.snapshot(cur);key=uuid.uuid4();one=checked(evaluate(cur,original,key=key),original);first=row(one,f['sale'])['episode'];assert first['state']=='ACTIVE'and first['number']=='1'
  replay=evaluate(cur,original,key=key);assert replay['result']==one['result'];two=evaluate(cur,original);assert row(two,f['sale'])['episode']['id']==first['id']and row(two,f['sale'])['episode']['first_observed_at']==first['first_observed_at'];assert b.boundary.snapshot(cur)==before
  saved=attention.get(cur,original['run_id']);attention.command(cur,attention.intent(saved,'DONE'));assert row(evaluate(cur,original),f['sale'])['episode']['id']==first['id']and row(evaluate(cur,original),f['sale'])['episode']['state']=='ACTIVE'
  paid=ar.sales.payment(cur,dict(f,tag=f['tag']+'-episode-final'),today,'300');settled=checked(evaluate(cur,original),original);closed=row(settled,f['sale'])['episode'];assert closed['id']==first['id']and closed['state']=='RESOLVED'
  ar.sales.native(cur,'select erp.reverse_sales_payment(%s,%s)',(paid,'Native episode recurrence inverse'));reopened=checked(evaluate(cur,original),original);r=row(reopened,f['sale']);assert r['transition']=='REOPENED_NEW_EPISODE'and r['episode']['id']!=first['id']and r['episode']['previous_episode_id']==first['id']and r['episode']['number']=='2'
  assert cur.execute('select state from cp7_reminder_native.obligation_episodes where id=%s',(first['id'],)).fetchone()[0]=='RESOLVED'
  auth.refused(cur,lambda:cur.execute('update cp7_reminder_native.obligation_episodes set state=\'ACTIVE\',closed_at=null where id=%s',(first['id'],)),'CP7_OBLIGATION_EPISODE_HISTORY_IMMUTABLE')
  return dict(status='PASS',actual_Native_AR500_paid200_remaining300_one_business_episode=True,review_DONE_does_not_close_episode=True,Native_final300_settlement_resolves_and_inverse_new_linked_episode=True,Original_and_closed_episode_history_immutable=True,no_ERP_business_write_from_evaluation=True)
 def material():
  f,original=previous.prepared(cur,today);ident=f['receipt']['purchase_id'];before=b.boundary.snapshot(cur);r=row(checked(evaluate(cur,original,'MATERIAL_AP'),original),ident);first=r['episode'];assert r['condition_state']=='INVOICE_PENDING'and first['state']=='ACTIVE'and not r['business_resolved'];assert b.boundary.snapshot(cur)==before
  previous.finalize(cur,f,today);previous.payment(cur,f,today,'200');r=row(evaluate(cur,original,'MATERIAL_AP'),ident);assert r['episode']['id']==first['id']and r['condition_state']=='OVERDUE'
  paid=previous.payment(cur,f,today,'300');r=row(evaluate(cur,original,'MATERIAL_AP'),ident);assert r['episode']['state']=='RESOLVED'and r['business_resolved'];previous.inverse(cur,paid);r=row(checked(evaluate(cur,original,'MATERIAL_AP'),original),ident);assert r['episode']['previous_episode_id']==first['id']and r['episode']['state']=='ACTIVE'
  return dict(status='PASS',actual_Native_GRNI500_final0_episode_stays_open=True,final_invoice500_payment200_same_episode=True,actual_final300_and_inverse_linked_recurrence=True,no_opening_payroll_other_obligation_claim=True)
 def partial_and_fence():
  f,original=ar_fixture(cur,today);one=evaluate(cur,original);first=row(one,f['sale'])['episode'];before=b.boundary.snapshot(cur)
  definition=cur.execute("select pg_get_functiondef('cp7_reminder_native.receivable_source()'::regprocedure)").fetchone()[0]
  try:
   # Explicit private-source fault control, never a fabricated Native balance.
   cur.execute("create or replace function cp7_reminder_native.receivable_source()returns jsonb language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$begin raise exception 'CP7_REMINDER_AR_SOURCE_INCOMPLETE';end$$")
   e=checked(evaluate(cur,original),original);r=row(e,f['sale']);assert e['result']['source_status']=='INCOMPLETE'and r['freshness']=='UNKNOWN'and not r['business_resolved']and r['episode']['state']=='ACTIVE'and r['episode']['first_observed_at']==first['first_observed_at']and r['episode']['last_known_observed_at']==first['last_known_observed_at']
  finally:cur.execute(definition)
  assert b.boundary.snapshot(cur)==before
  key=uuid.uuid4();count=cur.execute('select count(*)from cp7_reminder_native.obligation_observations').fetchone()[0];sealed=evaluate(cur,original,key=key,lookup=True);assert sealed['result']['status']=='NOT_COMMITTED';late=evaluate(cur,original,key=key);assert late['result']==sealed['result']and cur.execute('select count(*)from cp7_reminder_native.obligation_observations').fetchone()[0]==count
  return dict(status='PASS',controlled_private_source_failure_NOT_financial_fixture=True,unknown_preserves_active_age_last_known_no_false_resolution=True,absent_UUID_resolution_fences_late_evaluator_without_observation=True)
 def shared_authority():
  f,original=ar_fixture(cur,today);one=evaluate(cur,original);first=row(one,f['sale'])['episode'];subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='STAFF'").fetchone()[0];cur.execute('update erp.app_roles set is_active=true where id=%s',(role,));cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
  for perm in(*auth.PERMS,'finance.ar.view'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,perm))
  own=parent.capture(cur,today,subject=subject);key=uuid.uuid4();two=evaluate(cur,own,key=key,subject=subject);assert row(two,f['sale'])['episode']['id']==first['id']
  auth.refused(cur,lambda:evaluate(cur,original,subject=subject),'CP7_ANALYSIS_RUN_UNAVAILABLE');cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,))
  for lookup in(False,True):auth.refused(cur,lambda:evaluate(cur,own,key=key,subject=subject,lookup=lookup),'CP7_OBLIGATION_ACCESS_DENIED')
  assert parent.read(cur,own['run_id'],subject)['analysis']==own['analysis']
  return dict(status='PASS',two_authorized_actors_one_shared_business_episode_own_Originals=True,current_AR_only_loss_denies_saved_replay_and_resolution=True,foreign_Original_denied_Ops_original_still_permitted=True)
 return previous.cases(cur,today)+[('P16_EPISODE_NATIVE_AR_RECURRENCE',recurrence),('P16_EPISODE_NATIVE_AP_RECURRENCE',material),('P16_EPISODE_NATIVE_PARTIAL_ABSENT_FENCE',partial_and_fence),('P16_EPISODE_NATIVE_SHARED_CURRENT_AUTH',shared_authority)]
def races(tools,today):
 def duplicate():
  with tools.connect()as conn,conn.cursor()as cur:f,original=ar_fixture(cur,today);conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(timeout=5);result=evaluate(cur,original,key=key);conn.commit();return result
  with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(send),pool.submit(send)]]
  assert results[0]['result']==results[1]['result'];assert row(results[0],f['sale'])['episode']['id']==row(results[1],f['sale'])['episode']['id']
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_reminder_native.obligation_episodes where domain=\'AR\'and source_id=%s',(f['sale'],)).fetchone()[0]==1
  return dict(status='PASS',two_actual_transactions_same_UUID_one_batch_one_business_episode=True)
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:
   original,e,subject=attention.prepared(cur,today,True);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(subject,)).fetchone()[0];cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.ar.view')on conflict do nothing",(role,));conn.commit()
  key=uuid.uuid4()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OBLIGATION_DOMAIN:AR',0))")
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=evaluate(cur,original,key=key,subject=subject);conn.commit();return r
     except psycopg.Error as ex:conn.rollback();return str(ex)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+10
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as cur:
      while time.monotonic()<deadline:
       waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_evaluate_obligation_episodes_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P16_REAL_EPISODE_DOMAIN_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(60)
  assert isinstance(result,str)and'CP7_OBLIGATION_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_reminder_native.requests where actor=%s and request_id=%s',(subject,key)).fetchone()[0]==0
  return dict(status='PASS',current_AR_revoked_during_observed_domain_lock_wait_refuses_no_metadata_commit=True)
 return attention.races(tools,today)+[('P16_EPISODE_RACE_UUID',duplicate),('P16_EPISODE_RACE_CURRENT_AR',revoke)]
def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p16-episode-http');other=http.login('OWNER','p16-episode-other')
  with http.connect()as conn,conn.cursor()as cur:f,_=ar_fixture(cur,today);conn.commit()
  original=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert original['status']==200,original
  args=dict(p_payload=dict(run_id=original['body']['run_id'],domain='AR'),p_request=str(uuid.uuid4()));one=owner.rpc('erp_cp7_evaluate_obligation_episodes_v1',args);assert one['status']==200,one;checked(one['body'],original['body']);assert row(one['body'],f['sale'])['episode']['state']=='ACTIVE'
  replay=owner.rpc('erp_cp7_get_obligation_episode_request_v1',args);assert replay['status']==200 and replay['body']['result']==one['body']['result'];assert other.rpc('erp_cp7_evaluate_obligation_episodes_v1',args)['status']==403
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_evaluate_obligation_episodes_v1',args)['status']==403 and owner.rpc('erp_cp7_get_obligation_episode_request_v1',args)['status']==403
  return dict(status='PASS',actual_Auth_PostgREST_Native_AR_metadata_episode_exact_replay=True,foreign_and_current_deactivated_actor_denied_before_saved_result=True)
 return previous.http_cases(http,today)+[('P16_EPISODE_HTTP_CURRENT_AUTH',actual)]
