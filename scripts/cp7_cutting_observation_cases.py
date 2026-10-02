"""Native observations from actual cutting/input writers, no fabricated positive output."""
from concurrent.futures import ThreadPoolExecutor
import copy,json,time,uuid
import psycopg
import cp7_cutting_input_cases as inputs
import cp7_cutting_observation_bundle as bundle
e01,b,auth=inputs.e01,inputs.b,inputs.auth

def payload(cur,f,subject=None):
 w=inputs.workspace(cur,f['group'],subject)
 return dict(group_id=f['group'],expected_group_version=w['group']['version']if w['group']else None,expected_input_version=w['record']['version']if w['record']else None)
def send(cur,p,key=None,lookup=False,subject=None):
 auth.actor(cur,subject);fn='erp_cp7_get_cutting_observation_request_v1'if lookup else'erp_cp7_capture_cutting_observation_v1'
 out=cur.execute('select public.'+fn+'(%s,%s)',(json.dumps(p),key or uuid.uuid4())).fetchone()[0];b.api.admin(cur);return out
def ready(cur,today,subject=None):
 f=e01.production(cur,today,cutting_draft_only=True);inputs.send(cur,inputs.payload(cur,f,subject),subject=subject)
 inputs.change_native_draft(cur,f,post=True,prospective=True);return f
def cases(cur,today):
 def posted():
  f=ready(cur,today);before=b.boundary.snapshot(cur);out=send(cur,payload(cur,f));r=out['result']['observation']['records'][0]
  assert r['native_valid'],r
  assert inputs.D(r['actual_pcs'])==inputs.D(60)and inputs.D(r['consumed'])==inputs.D(60)and r['width_cm']is None,r
  unit=cur.execute('select m.unit_code from erp.material_rolls x join erp.materials m on m.id=x.material_id where x.id=%s',(f['roll'],)).fetchone()[0];assert r['context']['unit']==unit
  assert out['original_matches_current_native']and out['original_matches_current_inputs']and b.boundary.snapshot(cur)==before
  assert cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot)from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()==(inputs.D(40),inputs.D(400))
  return dict(status='PASS',actual_Native_POST60_with_real_input_preknown_clock=True,exact_Native_unit_output_consumption=True,unknown_width_not_inferred=True,raw40_value400_and_every_Native_row_unchanged_by_capture=True,no_trained_model_claim=True)
 def unposted():
  f=e01.production(cur,today,cutting_draft_only=True);inputs.send(cur,inputs.payload(cur,f));before=b.boundary.snapshot(cur);r=send(cur,payload(cur,f))['result']['observation']
  assert not r['records'][0]['native_valid']and r['exclusions'][0]['reason']=='NATIVE_UNPOSTED_OR_CANCELLED'and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_unposted_Native_draft_never_training_output=True,observed_source_preserved_no_Native_write=True)
 def late():
  f=e01.production(cur,today,cutting_draft_only=True);inputs.change_native_draft(cur,f,post=True);inputs.send(cur,inputs.payload(cur,f));before=b.boundary.snapshot(cur);r=send(cur,payload(cur,f))['result']['observation']
  assert not r['records'][0]['native_valid']and r['exclusions'][0]['reason']=='INPUT_RECORDED_AFTER_PHYSICAL_EVENT'and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_old_Native_post_new_input_not_backdated_into_training=True)
 def revised_input():
  f=ready(cur,today);p=payload(cur,f);old=send(cur,p);change=inputs.payload(cur,f);change['roll_inputs'][0]['width_cm']='175.250';inputs.send(cur,change);latest=send(cur,payload(cur,f))
  assert not latest['result']['observation']['records'][0]['native_valid']and latest['result']['observation']['records'][0]['width_cm']=='175.250'
  recovered=send(cur,p,uuid.UUID(old['result']['request_id']),True);assert recovered['result']==old['result']and not recovered['original_matches_current_inputs']
  records=old['result']['observation']['records']+latest['result']['observation']['records'];context=old['result']['observation']['records'][0]['context']
  dataset=cur.execute("select cp7_cutting_learning.dataset(%s,%s,null,clock_timestamp(),'not-this-Native-batch')",(json.dumps(records),json.dumps(context))).fetchone()[0]
  assert f['group']not in json.dumps(dataset)
  return dict(status='PASS',late_corrected_input_is_latest_invalid_revision_before_filter=True,no_old_valid_resurrection=True,Original_recovery_not_relabelled_as_current_input=True)
 def replay():
  f=ready(cur,today);p=payload(cur,f);key=uuid.uuid4();first=send(cur,p,key);assert send(cur,p,key)['result']==first['result']and send(cur,p,key,True)['result']==first['result']
  auth.refused(cur,lambda:send(cur,dict(p,expected_input_version='99'),key),'CP7_CUTTING_OBSERVATION_REQUEST_CHANGED')
  key=uuid.uuid4();absent=send(cur,p,key,True);assert absent['result']['status']=='NOT_COMMITTED'and send(cur,p,key)['result']==absent['result']
  assert cur.execute('select count(*)from cp7_cutting_observations.runs').fetchone()[0]==1
  return dict(status='PASS',exact_UUID_one_immutable_observation=True,changed_payload_refused=True,absent_lookup_permanently_sealed=True)
 def closed():
  f=ready(cur,today);p=payload(cur,f);before=b.boundary.snapshot(cur)
  for extra in(dict(source_complete=True),dict(known_at='2025-01-01T00:00:00Z'),dict(actual_pcs='0'),dict(unit='M')):
   auth.refused(cur,lambda:send(cur,p|extra),'CP7_WIP_FIELDS')
  auth.refused(cur,lambda:send(cur,dict(p,expected_group_version='999')),'CP7_CUTTING_OBSERVATION_SOURCE_CHANGED')
  assert cur.execute('select count(*)from cp7_cutting_observations.runs').fetchone()[0]==0 and b.boundary.snapshot(cur)==before
  return dict(status='PASS',caller_clock_actual_context_unit_and_completeness_refused=True,current_Native_CAS_and_zero_partial_capture=True)
 def private():
  bundle.verify(cur);f=ready(cur,today);first=send(cur,payload(cur,f));auth.refused(cur,lambda:cur.execute("update cp7_cutting_observations.runs set records='[]'"),'CP7_RUN_IMMUTABLE');auth.refused(cur,lambda:cur.execute('delete from cp7_cutting_observations.requests'),'CP7_RUN_IMMUTABLE')
  foreign=inputs.custom_owner(cur);p=payload(cur,f,foreign);before=b.boundary.snapshot(cur);r=send(cur,p,subject=foreign)['result']['observation'];assert not r['records'][0]['native_valid']and r['input_record_id']is None and b.boundary.snapshot(cur)==before
  assert r['actor_scope_id']==foreign and r['id']!=first['result']['observation']['id']
  return dict(status='PASS',all_schema_role_function_table_trigger_ACL_and_no_Native_DML_verified=True,foreign_actor_does_not_inherit_own_input_or_Original=True,immutable_originals=True)
 return [('CUT_OBS_NATIVE_POSTED',posted),('CUT_OBS_NATIVE_UNPOSTED',unposted),('CUT_OBS_NATIVE_LATE',late),('CUT_OBS_NATIVE_INPUT_REVISION',revised_input),('CUT_OBS_NATIVE_UUID_RECOVERY',replay),('CUT_OBS_NATIVE_CLOSED_CAS',closed),('CUT_OBS_NATIVE_PRIVATE_ACTOR',private)]

def races(tools,today):
 def run(revoke):
  with tools.connect()as conn,conn.cursor()as cur:
   f=e01.production(cur,today,cutting_draft_only=True);subject=inputs.custom_owner(cur);p=payload(cur,f,subject);key=uuid.uuid4();conn.commit()
  lock='CP7:CUTTING_OBSERVATION_REQUEST:'+subject+':'+str(key)if revoke else'CP7:CUTTING_INPUT_GROUP:'+subject+':'+f['group']
  with tools.connect()as holder,holder.cursor()as h:
   h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(lock,))
   def call():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=send(cur,p,key,subject=subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(call);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_capture_cutting_observation_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'CUT_OBS_REAL_LOCK_WAIT_REQUIRED'
     with tools.connect()as conn,conn.cursor()as c:
      if revoke:c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
      else:inputs.change_native_draft(c,f)
      conn.commit()
    finally:holder.rollback()
    result=job.result(30)
  code='CP7_ACCESS_DENIED'if revoke else'CP7_CUTTING_OBSERVATION_SOURCE_CHANGED';assert isinstance(result,str)and code in result,result
  with tools.connect()as conn,conn.cursor()as c:
   assert c.execute('select count(*)from cp7_cutting_observations.runs where actor=%s',(subject,)).fetchone()[0]==0
   assert c.execute('select count(*)from cp7_cutting_observations.requests where actor=%s',(subject,)).fetchone()[0]==0
  return dict(status='PASS',actual_observed_wait=True,current_authority_or_Native_version_rechecked_after_wait=True,no_partial_record_or_request=True)
 return [('CUT_OBS_RACE_CURRENT_REVOKE',lambda:run(True)),('CUT_OBS_RACE_NATIVE_VERSION',lambda:run(False))]
def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','cut-observation-native-owner')
  with http.connect()as conn,conn.cursor()as cur:f=ready(cur,today,owner.auth_user_id);p=payload(cur,f,owner.auth_user_id);before=b.boundary.snapshot(cur);conn.commit()
  args=dict(p_payload=p,p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_capture_cutting_observation_v1',args);assert r['status']==200 and r['body']['result']['observation']['records'][0]['native_valid'],r
  assert owner.rpc('erp_cp7_get_cutting_observation_request_v1',args)['body']['result']==r['body']['result']
  assert http.anon_rpc('erp_cp7_capture_cutting_observation_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_cutting_observation_request_v1',args)['status']==403
  return dict(status='PASS',real_Auth_HTTP_actual_Native_POST_source_observation=True,identical_UUID_Original_recovery_and_current403=True,no_Native_business_effect=True)
 return [('CUT_OBS_ACTUAL_AUTH_HTTP',flow)]
