"""Actual Native prospective cohort; no injected clocks or posted facts."""
import copy,json,uuid,time
from concurrent.futures import ThreadPoolExecutor
import psycopg
import cp7_cutting_observation_cases as observations
import cp7_cutting_model_bundle as bundle
inputs,e01,b,auth=observations.inputs,observations.e01,observations.b,observations.auth
D=inputs.D
def workspace(cur,f,subject=None):
 auth.actor(cur,subject);out=cur.execute('select public.erp_cp7_get_cutting_model_workspace_v1(%s,%s)',(f['group'],f['roll'])).fetchone()[0];b.api.admin(cur);return out
def send(cur,p,key=None,lookup=False,subject=None):
 auth.actor(cur,subject);fn='erp_cp7_get_cutting_model_request_v1'if lookup else'erp_cp7_capture_cutting_model_v1'
 out=cur.execute('select public.'+fn+'(%s,%s)',(json.dumps(p),key or uuid.uuid4())).fetchone()[0];b.api.admin(cur);return out
def policy_payload(cur,f,subject=None):
 w=workspace(cur,f,subject)
 return dict(action='POLICY',group_id=f['group'],roll_id=f['roll'],expected_group_version=w['input']['group']['version'],expected_input_version=w['input']['record']['version'],expected_policy_id=w['policy']['id']if w['policy']else None,coverage='0.75',train_batches='3',calibration_batches='4',holdout_batches='3',explicit_review=True)
def check_payload(cur,f,subject=None,policy_id=None):
 w=workspace(cur,f,subject)
 return dict(action='CHECK',group_id=f['group'],roll_id=f['roll'],expected_group_version=w['input']['group']['version'],expected_input_version=w['input']['record']['version'],policy_id=policy_id or w['policy']['id'])
def draft(cur,today,width=None,pcs=60,subject=None):
 f=e01.production(cur,today,cutting_draft_only=True);f['cut_payload']=copy.deepcopy(f['cut_payload']);f['cut_payload']['rolls'][0]['yields'][0]['qty_pcs']=pcs
 # Correct quantities only while DRAFT, through its Native optimistic writer.
 inputs.change_native_draft(cur,f)
 p=inputs.payload(cur,f,subject);p['roll_inputs'][0]['width_cm']=None if width is None else str(width);inputs.send(cur,p,subject=subject);return f
def post_and_observe(cur,f,subject=None):
 inputs.change_native_draft(cur,f,post=True,prospective=True)
 out=observations.send(cur,observations.payload(cur,f,subject),subject=subject)['result']['observation'];r=out['records'][0]
 assert r['native_valid']and D(r['actual_pcs'])==D(f['cut_payload']['rolls'][0]['yields'][0]['qty_pcs']),r
 return out
def cohort(cur,today,subject=None):
 first=draft(cur,today,160,48,subject);policy=send(cur,policy_payload(cur,first,subject),subject=subject)['result']['policy'];post_and_observe(cur,first,subject);groups=[first]
 for width in[170,180,160,170,180,170,160,180,170]:
  f=draft(cur,today,width,int(D(width)*D('0.3')),subject);post_and_observe(cur,f,subject);groups.append(f)
 current=draft(cur,today,170,51,subject);return current,policy,groups
def cases(cur,today):
 def positive():
  f,policy,groups=cohort(cur,today);before=b.boundary.snapshot(cur);p=check_payload(cur,f);key=uuid.uuid4();out=send(cur,p,key);e=out['result']['model']['evaluation']
  assert e['status']=='PREDICTION_ONLY'and e['basis']=='WITH_RECORDED_WIDTH',e
  assert D(e['interval']['center_pcs'])==51 and D(e['width_score']['interval_score'])<D(e['baseline_score']['interval_score']),e
  assert[len(e[k])for k in('train_rows','calibration_rows','holdout_rows')]==[3,4,3]
  assert len({r['batch_key']for k in('train_rows','calibration_rows','holdout_rows')for r in e[k]})==10
  assert all(r['batch_key']!=f['group']for k in('train_rows','calibration_rows','holdout_rows')for r in e[k])
  assert out['original_matches_current_inputs']and out['original_matches_current_history']and out['original_matches_current_policy']
  assert b.boundary.snapshot(cur)==before and send(cur,p,key,True)['result']==out['result']
  change=inputs.payload(cur,f);change['roll_inputs'][0]['width_cm']=None;inputs.send(cur,change);baseline=send(cur,check_payload(cur,f))['result']['model']['evaluation']
  assert baseline['basis']=='WITHOUT_WIDTH'and D(baseline['interval']['lower_pcs'])==48 and D(baseline['interval']['upper_pcs'])==54,baseline
  recovered=send(cur,p,key,True);assert recovered['result']==out['result']and not recovered['original_matches_current_inputs']and not recovered['original_matches_current_history']
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_ten_independent_Native_POST_batches=True,real_policy_before_training_and_inputs_before_physical=True,separate_3train_4calibration_3holdout=True,Native_width_challenger_strictly_improves_and_unknown_width_baseline48_54=True,current_batch_not_training=True,exact_UUID_Original_and_no_Native_money_stock_HPP_change=True,factory_guarantee=False)
 def early():
  f=draft(cur,today);policy=send(cur,policy_payload(cur,f));before=b.boundary.snapshot(cur);out=send(cur,check_payload(cur,f))['result']['model']['evaluation']
  assert out['status']=='UNAVAILABLE'and out['interval']is None and out['reason']=='PROSPECTIVE_SEPARATE_BATCHES_REQUIRED',out
  assert policy['result']['policy']['known_at']!=workspace(cur,f)['input']['group']['physical_at']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',new_real_policy_does_not_relabel_past_Native_history_or_manufacture_interval=True)
 def missing():
  old=draft(cur,today);policy=send(cur,policy_payload(cur,old))['result']['policy'];f=draft(cur,today);before=b.boundary.snapshot(cur)
  out=send(cur,check_payload(cur,f,policy_id=policy['id']))['result']['model']['evaluation'];assert out['reason']=='CURRENT_HISTORY_RECAPTURE_REQUIRED'and out['interval']is None,out
  assert old['group']in json.dumps(out['unavailable'])and b.boundary.snapshot(cur)==before
  return dict(status='PASS',missing_complete_current_Native_observation_withholds_instead_of_partial_training=True)
 def replay():
  f=draft(cur,today);p=policy_payload(cur,f);key=uuid.uuid4();before=b.boundary.snapshot(cur);first=send(cur,p,key)
  assert send(cur,p,key,True)['result']==first['result'];auth.refused(cur,lambda:send(cur,dict(p,coverage='0.7'),key),'CP7_CUTTING_MODEL_REQUEST_CHANGED')
  key=uuid.uuid4();absent=send(cur,p,key,True);assert absent['result']['status']=='NOT_COMMITTED'and send(cur,p,key)['result']==absent['result']
  assert cur.execute('select count(*)from cp7_cutting_model.policies').fetchone()[0]==1 and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_UUID_and_permanent_negative_receipt_one_immutable_policy=True)
 def closed():
  f=draft(cur,today);p=policy_payload(cur,f);before=b.boundary.snapshot(cur)
  for extra in(dict(known_at='2025-01-01T00:00:00Z'),dict(source_complete=True),dict(actual_pcs='60'),dict(train_through='2025-01-01T00:00:00Z')):auth.refused(cur,lambda:send(cur,p|extra),'CP7_WIP_FIELDS')
  auth.refused(cur,lambda:send(cur,dict(p,holdout_batches='2')),'CP7_CUTTING_MODEL_FOLD_COUNTS');auth.refused(cur,lambda:send(cur,dict(p,coverage='0.95')),'CP7_CUTTING_MODEL_CALIBRATION_SUPPORT');auth.refused(cur,lambda:send(cur,dict(p,expected_group_version='999')),'CP7_CUTTING_MODEL_SOURCE_CHANGED')
  assert cur.execute('select count(*)from cp7_cutting_model.requests').fetchone()[0]==0 and b.boundary.snapshot(cur)==before
  return dict(status='PASS',caller_facts_clock_cutoffs_completeness_not_admitted=True,real_Native_and_input_CAS_no_partial_metadata=True)
 def private():
  bundle.verify(cur);f=draft(cur,today);first=send(cur,policy_payload(cur,f));auth.refused(cur,lambda:cur.execute('delete from cp7_cutting_model.policies'),'CP7_RUN_IMMUTABLE');auth.refused(cur,lambda:cur.execute("update cp7_cutting_model.requests set result='{}'"),'CP7_RUN_IMMUTABLE')
  foreign=inputs.custom_owner(cur);w=workspace(cur,f,foreign);assert w['policy']is None and w['feature']is None and w['actor_scope_id']!=first['actor_scope_id']
  return dict(status='PASS',all_role_ACL_schema_table_trigger_guards_and_zero_Native_DML=True,foreign_actor_not_given_Original_or_private_features=True)
 return [('CUT_MODEL_NATIVE_WIDTH_BASELINE',positive),('CUT_MODEL_NATIVE_EARLY_POLICY',early),('CUT_MODEL_NATIVE_MISSING_SCOPE',missing),('CUT_MODEL_NATIVE_UUID',replay),('CUT_MODEL_NATIVE_CLOSED_CAS',closed),('CUT_MODEL_NATIVE_PRIVATE_ACTOR',private)]
def races(tools,today):
 def run(revoke):
  with tools.connect()as conn,conn.cursor()as cur:
   subject=inputs.custom_owner(cur);f=draft(cur,today,subject=subject);p=policy_payload(cur,f,subject);key=uuid.uuid4();conn.commit()
  lock='CP7:CUTTING_MODEL_REQUEST:'+subject+':'+str(key)if revoke else'CP7:CUTTING_INPUT_GROUP:'+subject+':'+f['group']
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
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_capture_cutting_model_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'CUT_MODEL_REAL_LOCK_WAIT_REQUIRED'
     with tools.connect()as conn,conn.cursor()as c:
      if revoke:c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
      else:inputs.change_native_draft(c,f)
      conn.commit()
    finally:holder.rollback()
    result=job.result(30)
  code='CP7_ACCESS_DENIED'if revoke else'CP7_CUTTING_MODEL_SOURCE_CHANGED';assert isinstance(result,str)and code in result,result
  with tools.connect()as conn,conn.cursor()as c:
   assert c.execute('select count(*)from cp7_cutting_model.policies where actor=%s',(subject,)).fetchone()[0]==0 and c.execute('select count(*)from cp7_cutting_model.requests where actor=%s',(subject,)).fetchone()[0]==0
  return dict(status='PASS',actual_observed_wait_current_right_or_Native_version_rechecked=True,no_partial_metadata_or_request=True)
 return [('CUT_MODEL_RACE_CURRENT_REVOKE',lambda:run(True)),('CUT_MODEL_RACE_NATIVE_VERSION',lambda:run(False))]
def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','cut-model-native-owner')
  with http.connect()as conn,conn.cursor()as cur:f,policy,groups=cohort(cur,today,owner.auth_user_id);p=check_payload(cur,f,owner.auth_user_id);before=b.boundary.snapshot(cur);conn.commit()
  args=dict(p_payload=p,p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_capture_cutting_model_v1',args);assert r['status']==200 and r['body']['result']['model']['evaluation']['basis']=='WITH_RECORDED_WIDTH',r
  assert owner.rpc('erp_cp7_get_cutting_model_request_v1',args)['body']['result']==r['body']['result']and http.anon_rpc('erp_cp7_capture_cutting_model_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_cutting_model_request_v1',args)['status']==403
  return dict(status='PASS',real_Auth_HTTP_ten_Native_POST_model_width_and_exact_Original_recovery=True,current403_and_anonymous_denial=True,no_Native_money_stock_HPP_effect=True,factory_guarantee=False)
 return [('CUT_MODEL_ACTUAL_AUTH_HTTP',flow)]
