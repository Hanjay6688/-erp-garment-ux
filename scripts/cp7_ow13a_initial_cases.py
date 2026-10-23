"""Native initial-analysis controls, retaining every113 fabric/WA case.

Products/stock/drafts/profile are made by the accepted writers. Administrative
identity revocation and deliberate metadata-refusal controls are labelled.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
import json
import time
import uuid
import psycopg
import cp7_ow14b_rule_cases as retained
import cp7_planning_baseline_cases as profile
import cp7_initial_analysis_stage as initial_stage
import cp7_target_policy_stage as target_stage
from cp7_ow04_restore_bundle import _catalog_rows

b,auth,master=retained.b,retained.auth,retained.master
CONTRACT='cp7.ow13a.initial-statistical.v1'
FUNCTIONS=retained.FUNCTIONS+('erp_cp7_request_staged_analysis_v1','erp_cp7_get_staged_analysis_v1',
 'erp_cp7_step_staged_analysis_v1','erp_cp7_get_planning_profiles_v1','erp_cp7_save_planning_profile_v1',
 'erp_cp7_capture_baseline_v1')
SCHEDULES=retained.SCHEDULES
ADDED_IDS=dict(native=[
 'OW13A_NATIVE_MINIMUM_CONFIG_NO_JOB','OW13A_NATIVE_READY_ONCE_NO_BUSINESS_WRITE',
 'OW13A_NATIVE_TICK_WITHOUT_WA_RESTORES_CLAIMS','OW13A_NATIVE_REUSES_EXISTING_MANUAL_JOB',
 'OW13A_NATIVE_CURRENT_ACCESS_AND_CLOSED_MODE','OW13A_NATIVE_AFTER_USE_ROLLBACK_REFUSED',
 'OW10_NATIVE_EXPLICIT_STATISTICAL_UNKNOWN_NOT_ZERO'],
 races=['OW13A_RACE_TWO_ENSURES_ONE_SERVER_UUID','OW13A_RACE_SOURCE_WAIT_CURRENT_OWNER_REVOKED'],
 http=['OW13A_REAL_AUTH_INITIAL_PROFILE_AND_UUID','OW13A_REAL_AUTH_CURRENT_REVOKE_AND_PRIVATE_DENIAL'],
 browser=['OW13A_BROWSER_DESKTOP_MINIMUM_TO_AUTO','OW13A_BROWSER_MOBILE_LOST_REPLY_SAME_JOB'])
IDS={k:list(v)+ADDED_IDS[k]for k,v in retained.IDS.items()}
REQUIRED={k:len(v)for k,v in IDS.items()};EXPECTED=DECLARED=sum(REQUIRED.values())
assert REQUIRED==dict(native=68,races=36,http=9,browser=13)and EXPECTED==126
INSTALL_STATES={}


def call(cur,subject,ensure=False):
 return retained.retained.rpc(cur,'erp_cp7_request_staged_analysis_v1',
  (json.dumps(dict(initial_auto='ENSURE'if ensure else'STATUS')),None),subject)


def prepare(cur,today,subject=None,configured=True,statistical=False):
 f=profile.history.fixture(cur,today)
 subject=subject or master.role_actor(cur,'OWNER')
 p=profile.payload(cur,f)
 if statistical:
  p['config'].update(mean_mode='OWN_AVAILABLE_HISTORY',daily_pcs=None,minimum_available_days='14',
                     buffer_days=None,buffer_mode='STATISTICAL',service_level='0.95')
 if configured:profile.save(cur,p,subject=subject)
 return f,subject,p


def own_count(cur,subject):
 b.api.admin(cur)
 return cur.execute('select(select count(*)from cp7_initial_analysis.intents where actor=%s),'
  '(select count(*)from cp7_analysis_stage.jobs where actor=%s)',(subject,subject)).fetchone()


def cases(cur,today):
 def missing():
  f,subject,p=prepare(cur,today,configured=False)
  before=retained.formula.business(cur);r=call(cur,subject,True)
  assert r['state']=='NOT_READY'and'PLANNING_PROFILE_INCOMPLETE'in r['readiness']['reasons'],r
  assert own_count(cur,subject)==(0,0)and retained.formula.business(cur)==before
  empty=cur.execute("select cp7_initial_analysis.readiness('{\"status\":\"COMPLETE\",\"facts\":{\"products\":[]},\"profiles\":[]}'::jsonb)").fetchone()[0]
  assert empty['reasons']==['NO_ACTIVE_PRODUCTS']and empty['ready']is False,empty
  return dict(status='PASS',actual_Native_product_requires_reviewed_profile=True,missing_no_job=True,pure_empty_source_control=True)

 def once():
  f,subject,p=prepare(cur,today);before=retained.formula.business(cur)
  ready=call(cur,subject);assert ready['state']=='READY'and own_count(cur,subject)==(0,0),ready
  first=call(cur,subject,True);assert first['state']=='RUNNING'and first['job']['request_id'],first
  for _ in range(3):assert call(cur,subject,True)['job']['request_id']==first['job']['request_id']
  assert own_count(cur,subject)==(1,1)and retained.formula.business(cur)==before
  stored=cur.execute('select j.reference,j.query,j.request_id from cp7_analysis_stage.jobs j '
   'join cp7_initial_analysis.intents i on i.job_id=j.id where i.actor=%s',(subject,)).fetchone()
  assert stored[0]['financial_capture']=='DEFERRED'and stored[0]['financial_source']is None and stored[1]==first['query']
  return dict(status='PASS',server_UUID=str(stored[2]),four_ensures_one_job=True,Native_business_unchanged=True,finance_deferred=True)

 def tick():
  f,subject,p=prepare(cur,today)
  assert cur.execute('select count(*)from cp7_alert_native.settings').fetchone()[0]==0
  out=retained.retained.tick(cur,'analysis_tick')
  assert out['outcome']=='NOT_CONFIGURED'and out['initial_analysis']['state']=='RUNNING'and out['initial_analysis']['actor']==subject,out
  saved=out['initial_analysis']['job']['request_id'];again=retained.retained.tick(cur,'analysis_tick')
  assert again['initial_analysis']['outcome']=='INITIAL_ALREADY_REQUESTED'and again['initial_analysis']['request_id']==saved,again
  assert own_count(cur,subject)==(1,1)
  claims=cur.execute("select current_setting('request.jwt.claims',true),current_setting('request.jwt.claim.sub',true)").fetchone()
  assert subject not in (claims[0]or'')and subject not in(claims[1]or''),claims
  cur.execute("set local statement_timeout='8s';set local role cp7_capture")
  worker=cur.execute('select cp7_analysis_stage.run_next()').fetchone()[0];cur.execute('reset role');b.api.admin(cur)
  progressed=call(cur,subject)['job'];assert progressed['request_id']==saved and progressed['units_done']>0,(worker,progressed)
  return dict(status='PASS',actual_postgres_tick_without_WA_settings=True,initial_UUID=saved,claims_not_left_as_planning_actor=True,actual_existing_K4_worker_progressed_same_job=True)

 def reuse():
  f,subject,p=prepare(cur,today);q=call(cur,subject)['query'];key=str(uuid.uuid4())
  old=retained.retained.rpc(cur,'erp_cp7_request_staged_analysis_v1',(json.dumps(q),key),subject)
  new=call(cur,subject,True)
  assert new['job']['request_id']==old['request_id']==key and own_count(cur,subject)==(1,1),(old,new)
  return dict(status='PASS',existing_manual_staged_UUID=key,no_duplicate_job_or_capture=True)

 def access():
  f,subject,p=prepare(cur,today);first=call(cur,subject,True)
  other=master.role_actor(cur,'STAFF')
  code,message=retained.retained.refusal(cur,lambda:call(cur,other))
  assert code=='42501'and message in('CP7_INITIAL_OWNER_OR_ADMIN_REQUIRED','CP7_ACCESS_DENIED'),(code,message)
  for payload,key in[(dict(initial_auto='STATUS',finance_mode='STAGED'),None),(dict(initial_auto='ENSURE'),str(uuid.uuid4()))]:
   auth.refused(cur,lambda:retained.retained.rpc(cur,'erp_cp7_request_staged_analysis_v1',(json.dumps(payload),key),subject),'CP7_INITIAL_MODE')
  b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
  auth.refused(cur,lambda:call(cur,subject),'CP7_ACCESS_DENIED')
  assert own_count(cur,subject)==(1,1)
  return dict(status='PASS',current_deactivation_hides_existing_job=True,STAFF_automatic_mode_refused=True,mixed_mode_and_UUID_refused=True)

 def rollback():
  f,subject,p=prepare(cur,today);call(cur,subject,True)
  before=_catalog_rows(cur)
  try:initial_stage.rollback_preuse(cur,INSTALL_STATES['initial'])
  except ValueError as error:assert str(error)=='OW13A_AFTER_USE_REQUIRES_BACKUP_RESTORE'
  else:raise AssertionError('OW13A_AFTER_USE_ROLLBACK_DID_NOT_REFUSE')
  assert _catalog_rows(cur)==before
  return dict(status='PASS',actual_post_use_guard_before_any_catalog_change=True,catalog_groups=22)

 def statistical():
  f,subject,p=prepare(cur,today,statistical=True);q=call(cur,subject)['query']
  result=retained.retained.rpc(cur,'erp_cp7_capture_baseline_v1',(json.dumps(q),str(uuid.uuid4())),subject)
  row=profile.row(result,f);t=row['target']
  assert result['contract_version']=='cp7.native-baseline.v2'and t['inputs']['mode']=='STATISTICAL'and t['inputs']['service_level']=='0.95',t
  assert t['inputs']['buffer_days']is None and t['status']=='UNKNOWN'and t['target_pcs']is None,t
  b.api.admin(cur);facts=cur.execute('select facts from cp7_baseline_native.runs where id=%s',(result['run_id'],)).fetchone()[0]
  h=result['history_run_result'];staged=cur.execute('select cp7_analysis_stage.baseline_rows(%s::jsonb,%s::jsonb,%s::jsonb,%s)',
   (json.dumps(facts),json.dumps(h['history']['rows']),json.dumps(h['current_stock']),result['source_hash'])).fetchone()[0]
  same=next(x for x in staged if x['target_key']==row['target_key'])['target'];assert same==t,(same,t)
  before=_catalog_rows(cur)
  try:target_stage.rollback_preuse(cur,INSTALL_STATES['target'])
  except ValueError as error:assert str(error)=='OW10_TARGET_POLICY_AFTER_USE_REQUIRES_BACKUP_RESTORE'
  else:raise AssertionError('OW10_AFTER_USE_ROLLBACK_DID_NOT_REFUSE')
  assert _catalog_rows(cur)==before
  return dict(status='PASS',explicit_Native_statistical_profile_accepted=True,real_insufficient_history_UNKNOWN_not_zero=True,
   direct_staged_target_equal=True,no_second_days_buffer=True,after_use_rollback_refused=True)

 return retained.cases(cur,today)+list(zip(ADDED_IDS['native'],[missing,once,tick,reuse,access,rollback,statistical]))


def races(tools,today):
 def fixture():
  with tools.connect()as conn,conn.cursor()as cur:
   f,subject,p=prepare(cur,today);conn.commit();return subject
 def ensure(subject):
  with tools.connect()as conn,conn.cursor()as cur:
   try:r=call(cur,subject,True);conn.commit();return r
   except psycopg.Error as error:conn.rollback();return dict(error=error.sqlstate,message=error.diag.message_primary)
 def two():
  subject=fixture()
  with ThreadPoolExecutor(max_workers=2)as pool:answers=list(pool.map(lambda _:ensure(subject),range(2)))
  assert all(r.get('state')in('RUNNING','BUSY')for r in answers),answers
  final=ensure(subject);key=final['job']['request_id']
  assert all(r.get('job')is None or r['job']['request_id']==key for r in answers),answers
  with tools.connect()as conn,conn.cursor()as cur:assert own_count(cur,subject)==(1,1)
  return dict(status='PASS',two_actual_sessions_one_initial_intent_and_job=True,server_UUID=key)
 def revoke():
  subject=fixture();started=Event();pid=[]
  def waiting():
   with tools.connect()as conn,conn.cursor()as cur:
    pid.append(cur.execute('select pg_backend_pid()').fetchone()[0]);started.set()
    try:r=call(cur,subject,True);conn.commit();return r
    except psycopg.Error as error:conn.rollback();return dict(code=error.sqlstate,message=error.diag.message_primary)
  with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=1)as pool:
   h.execute('lock table erp.products in access exclusive mode');future=pool.submit(waiting);assert started.wait(5)
   deadline=time.monotonic()+5;observed=False
   while time.monotonic()<deadline:
    row=h.execute("select wait_event_type from pg_stat_activity where pid=%s",(pid[0],)).fetchone()
    if row and row[0]=='Lock':observed=True;break
    time.sleep(.05)
   assert observed,'OW13A_SOURCE_READER_DID_NOT_WAIT'
   with tools.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,));conn.commit()
   holder.rollback();out=future.result(timeout=15)
  assert out.get('code')=='42501'and out.get('message')in('CP7_ACCESS_DENIED','CP7_INITIAL_ACCESS_CHANGED'),out
  with tools.connect()as conn,conn.cursor()as cur:assert own_count(cur,subject)==(0,0)
  return dict(status='PASS',actual_source_lock_wait_observed=True,current_deactivation_after_wait_refused=True,no_orphan_job=True)
 return retained.races(tools,today)+list(zip(ADDED_IDS['races'],[two,revoke]))


def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','ow13a-initial-owner')
  with http.connect()as conn,conn.cursor()as cur:f,subject,p=prepare(cur,today,subject=owner.auth_user_id,configured=False);conn.commit()
  args=dict(p_query=dict(initial_auto='STATUS'),p_request=None);before=owner.rpc('erp_cp7_request_staged_analysis_v1',args)
  assert before['status']==200 and before['body']['state']=='NOT_READY',before
  saved=owner.rpc('erp_cp7_save_planning_profile_v1',dict(p_payload=p,p_request=str(uuid.uuid4())));assert saved['status']==200,saved
  ensured=owner.rpc('erp_cp7_request_staged_analysis_v1',dict(p_query=dict(initial_auto='ENSURE'),p_request=None))
  assert ensured['status']==200 and ensured['body']['state']=='RUNNING',ensured
  key=ensured['body']['job']['request_id'];again=owner.rpc('erp_cp7_request_staged_analysis_v1',args)
  assert again['status']==200 and again['body']['job']['request_id']==key,again
  with http.connect()as conn,conn.cursor()as cur:assert own_count(cur,owner.auth_user_id)==(1,1)
  return dict(status='PASS',real_Auth_PostgREST_profile_then_initial_UUID=True,UUID=key,request_nullable_mode_accepted=True)
 def denied():
  owner=http.login('ADMIN','ow13a-current-admin')
  with http.connect()as conn,conn.cursor()as cur:f,subject,p=prepare(cur,today,subject=owner.auth_user_id);conn.commit()
  args=dict(p_query=dict(initial_auto='ENSURE'),p_request=None);r=owner.rpc('erp_cp7_request_staged_analysis_v1',args);assert r['status']==200,r
  assert http.anon_rpc('erp_cp7_request_staged_analysis_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  denied=owner.rpc('erp_cp7_request_staged_analysis_v1',dict(p_query=dict(initial_auto='STATUS'),p_request=None));assert denied['status']==403,denied
  with http.connect()as conn,conn.cursor()as cur:
   for role in('anon','authenticated','service_role'):
    assert not cur.execute("select has_schema_privilege(%s,'cp7_initial_analysis','USAGE')or has_function_privilege(%s,'cp7_initial_analysis.tick()','EXECUTE')",(role,role)).fetchone()[0]
  return dict(status='PASS',real_Auth_current_admin_revocation_hides_job=True,no_anonymous_or_private_tick_access=True)
 return retained.http_cases(http,today)+list(zip(ADDED_IDS['http'],[flow,denied]))
