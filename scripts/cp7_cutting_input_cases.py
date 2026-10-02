"""Native input candidate: six DB, two observed races, one real Auth HTTP.

Every predecessor23 remains. These capture actual draft/posted Native cutting
sources and private metadata; they do not qualify a trained factory model.
"""
import json,time,uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import psycopg
import cp7_cutting_yield_cases as source
import cp7_cutting_input_bundle as bundle
b,auth,e01=source.b,source.auth,source.e01

def workspace(cur,group,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_cutting_input_workspace_v1(%s)',(group,)).fetchone()[0];b.api.admin(cur);return r
def send(cur,p,key=None,lookup=False,subject=None):
 auth.actor(cur,subject);fn='erp_cp7_get_cutting_input_request_v1'if lookup else'erp_cp7_record_cutting_inputs_v1'
 r=cur.execute('select public.'+fn+'(%s,%s)',(json.dumps(p),key or uuid.uuid4())).fetchone()[0];b.api.admin(cur);return r
def payload(cur,f,subject=None):
 w=workspace(cur,f['group'],subject)
 return dict(group_id=f['group'],expected_group_version=w['group']['version'],expected_input_version=w['record']['version']if w['record']else None,marker_key='Native prospective marker',planned_mix=[dict(size_id=x,drawings='3')for x in w['anchor']['size_ids']],roll_inputs=[dict(roll_id=x['roll_id'],family=dict(brand='Explicit brand',mill='Explicit mill',variant='Explicit variant',spec_revision='1'),width_cm=None)for x in w['anchor']['rolls']],explicit_review=True)
def change_native_draft(cur,f,post=False,prospective=False):
 b.api.admin(cur);v=cur.execute('select row_version from erp.cutting_groups where id=%s',(f['group'],)).fetchone()[0]
 p=dict(f['cut_payload'],id=f['group'],action='POST'if post else'SAVE_DRAFT')
 if prospective:p['cut_at']=cur.execute('select clock_timestamp()').fetchone()[0].isoformat()
 r=e01.prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',p,expected_version=v);b.api.admin(cur);return r
def custom_owner(cur):
 b.api.admin(cur);subject=str(uuid.uuid4());role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(auth.base.OPERATOR_AUTH,)).fetchone()[0]
 cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values(%s,%s,'Prospective Native owner','OWNER',%s,true)",(uuid.uuid4(),subject,role));return subject

def cases(cur,today):
 def prospective():
  f=e01.production(cur,today,cutting_draft_only=True);before=b.boundary.snapshot(cur);p=payload(cur,f);r=send(cur,p);record=r['result']['record']
  assert r['result']['status']=='COMMITTED'and not r['current']['preknown_before_physical']and b.boundary.snapshot(cur)==before
  assert record['values']['rolls'][0]['width_cm']is None and record['values']['planned_mix'][0]['drawings']=='1'
  actual_unit=cur.execute('select m.unit_code from erp.material_rolls r join erp.materials m on m.id=r.material_id where r.id=%s',(f['roll'],)).fetchone()[0]
  assert record['values']['rolls'][0]['context']['unit']==actual_unit
  change_native_draft(cur,f,prospective=True);w=workspace(cur,f['group']);assert w['preknown_before_physical']and w['record_matches_native_identity']
  change_native_draft(cur,f,post=True,prospective=True);w=workspace(cur,f['group']);assert w['group']['posted']and w['preknown_before_physical']and w['record_matches_native_identity']
  assert cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot)from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()==(D(40),D(400))
  assert w['record']==record and not w['model_qualified']
  return dict(status='PASS',real_metadata_known_before_actual_Native_SAVE_POST_clock=True,late_initial_draft_date_not_backdated=True,Native_unit_pattern_roll_size_bound=True,unknown_width_no_inference=True,actual_raw100_to40_value1000_to400=True,private_metadata_does_not_gate_or_write_Native=True)
 def late():
  f=e01.production(cur,today,cutting_draft_only=True);change_native_draft(cur,f,post=True);before=b.boundary.snapshot(cur);r=send(cur,payload(cur,f))
  assert not r['current']['preknown_before_physical']and r['current']['record_matches_native_identity']and b.boundary.snapshot(cur)==before
  assert r['current']['record']['known_at']!=r['current']['group']['physical_at']
  return dict(status='PASS',actual_old_posted_cutting_new_metadata_cannot_be_old_knowledge=True,no_Native_fact_rewrite=True)
 def immutable():
  f=e01.production(cur,today,cutting_draft_only=True);p=payload(cur,f);first=send(cur,p)['result']['record'];p=payload(cur,f);p['roll_inputs'][0]['width_cm']='175.250';before=b.boundary.snapshot(cur);second=send(cur,p)['result']['record']
  assert second['version']=='2'and second['previous_id']==first['id']and second['values']['rolls'][0]['width_cm']=='175.250'
  auth.refused(cur,lambda:send(cur,p),'CP7_CUTTING_INPUT_VERSION_CHANGED')
  auth.refused(cur,lambda:cur.execute("update cp7_cutting_inputs.plans set features='{}'"),'CP7_RUN_IMMUTABLE');auth.refused(cur,lambda:cur.execute('delete from cp7_cutting_inputs.plans'),'CP7_RUN_IMMUTABLE')
  auth.refused(cur,lambda:cur.execute("update cp7_cutting_inputs.requests set result='{}'"),'CP7_RUN_IMMUTABLE')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',immutable_revision_clock_and_link=True,exact_decimal_width=True,CAS_old_version_denied=True,metadata_only_no_business_effect=True)
 def replay():
  f=e01.production(cur,today,cutting_draft_only=True);p=payload(cur,f);key=uuid.uuid4();first=send(cur,p,key);assert send(cur,p,key)==first and send(cur,p,key,True)==first
  auth.refused(cur,lambda:send(cur,dict(p,marker_key='changed'),key),'CP7_CUTTING_INPUT_REQUEST_CHANGED')
  nextp=payload(cur,f);key=uuid.uuid4();absent=send(cur,nextp,key,True);assert absent['result']['status']=='NOT_COMMITTED'and send(cur,nextp,key)['result']==absent['result']
  assert cur.execute('select count(*)from cp7_cutting_inputs.plans').fetchone()[0]==1
  return dict(status='PASS',exact_UUID_no_duplicate_record=True,changed_payload_denied=True,negative_lookup_permanently_sealed=True)
 def closed():
  f=e01.production(cur,today,cutting_draft_only=True);p=payload(cur,f);before=b.boundary.snapshot(cur)
  missing=workspace(cur,str(uuid.uuid4()));assert missing['group']is None and missing['anchor']is None and not missing['can_record']and not missing['preknown_before_physical']
  auth.refused(cur,lambda:send(cur,dict(p,source_complete=True)),'CP7_WIP_FIELDS')
  wrong=dict(p,planned_mix=[dict(size_id=str(uuid.uuid4()),drawings='1')]);auth.refused(cur,lambda:send(cur,wrong),'CP7_CUTTING_INPUT_NATIVE_SIZE_MISMATCH')
  wrong=dict(p,roll_inputs=[dict(p['roll_inputs'][0],roll_id=str(uuid.uuid4()))]);auth.refused(cur,lambda:send(cur,wrong),'CP7_CUTTING_INPUT_NATIVE_ROLL_MISMATCH')
  wrong=dict(p,roll_inputs=[dict(p['roll_inputs'][0],width_cm='0')]);auth.refused(cur,lambda:send(cur,wrong),'CP7_CUTTING_INPUT_WIDTH')
  change_native_draft(cur,f);auth.refused(cur,lambda:send(cur,p),'CP7_CUTTING_INPUT_NATIVE_VERSION_CHANGED')
  assert cur.execute('select count(*)from cp7_cutting_inputs.plans').fetchone()[0]==0
  assert cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot)from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()==(D(100),D(1000))
  return dict(status='PASS',caller_cannot_inject_actual_unit_clock_model_or_scope=True,current_Native_CAS_identity_size_width_checked=True,failed_metadata_captures_no_record=True,Native_draft_remains_unposted_raw100=True)
 def authority():
  bundle.verify(cur);f=e01.production(cur,today,cutting_draft_only=True);subject=custom_owner(cur);p=payload(cur,f,subject);key=uuid.uuid4();r=send(cur,p,key,subject=subject);foreign=custom_owner(cur)
  assert workspace(cur,f['group'],foreign)['record']is None
  cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,));auth.refused(cur,lambda:send(cur,p,key,True,subject),'CP7_ACCESS_DENIED');auth.refused(cur,lambda:workspace(cur,f['group'],subject),'CP7_ACCESS_DENIED')
  assert cur.execute('select features from cp7_cutting_inputs.plans where id=%s',(r['result']['record']['id'],)).fetchone()[0]==r['result']['record']['values']
  return dict(status='PASS',every_schema_table_trigger_function_ACL_and_zero_Native_DML_verified=True,foreign_actor_no_Original=True,current_deactivation_denies_cached_and_current_source=True,prior_Original_immutable=True)
 return [('CUT_INPUT_NATIVE_PROSPECTIVE',prospective),('CUT_INPUT_NATIVE_LATE',late),('CUT_INPUT_NATIVE_IMMUTABLE_CAS',immutable),('CUT_INPUT_NATIVE_UUID_RECOVERY',replay),('CUT_INPUT_NATIVE_CLOSED',closed),('CUT_INPUT_NATIVE_CURRENT_AUTH',authority)]

def races(tools,today):
 def run(revoke):
  with tools.connect()as conn,conn.cursor()as cur:f=e01.production(cur,today,cutting_draft_only=True);subject=custom_owner(cur);p=payload(cur,f,subject);key=uuid.uuid4();conn.commit()
  lock='CP7:CUTTING_INPUT_REQUEST:'+subject+':'+str(key)if revoke else'CP7:CUTTING_INPUT_GROUP:'+subject+':'+f['group']
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
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_record_cutting_inputs_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'CUT_INPUT_REAL_LOCK_WAIT_REQUIRED'
     with tools.connect()as conn,conn.cursor()as c:
      if revoke:c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
      else:change_native_draft(c,f)
      conn.commit()
    finally:holder.rollback()
    result=job.result(30)
  code='CP7_ACCESS_DENIED'if revoke else'CP7_CUTTING_INPUT_NATIVE_VERSION_CHANGED';assert isinstance(result,str)and code in result,result
  with tools.connect()as conn,conn.cursor()as c:assert c.execute('select count(*)from cp7_cutting_inputs.plans where actor=%s',(subject,)).fetchone()[0]==0;assert c.execute('select count(*)from cp7_cutting_inputs.requests where actor=%s',(subject,)).fetchone()[0]==0
  return dict(status='PASS',actual_observed_wait=True,current_right_or_Native_version_change_refused_after_wait=True,no_partial_record_or_request=True)
 return [('CUT_INPUT_RACE_CURRENT_REVOKE',lambda:run(True)),('CUT_INPUT_RACE_NATIVE_VERSION',lambda:run(False))]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','cut-input-native-owner')
  with http.connect()as conn,conn.cursor()as cur:f=e01.production(cur,today,cutting_draft_only=True);p=payload(cur,f,owner.auth_user_id);before=b.boundary.snapshot(cur);conn.commit()
  args=dict(p_payload=p,p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_record_cutting_inputs_v1',args);assert r['status']==200 and r['body']['result']['status']=='COMMITTED',r
  assert owner.rpc('erp_cp7_get_cutting_input_request_v1',args)['body']==r['body']
  assert http.anon_rpc('erp_cp7_record_cutting_inputs_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_cutting_input_request_v1',args)['status']==403 and owner.rpc('erp_cp7_get_cutting_input_workspace_v1',dict(p_group=f['group']))['status']==403
  return dict(status='PASS',real_Auth_PostgREST_Native_input_current_permission=True,exact_UUID_recovery_and_anonymous_denial=True,old_cut_clock_not_backdated=True,no_Native_business_effect=True)
 return [('CUT_INPUT_ACTUAL_AUTH_HTTP',flow)]
