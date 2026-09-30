"""Declared P06 native profile/target cases, retaining the qualified P05 cases.

Every stock/sales fixture uses unchanged ERP writers. No WIP, capacity, or model
promotion is fabricated; those missing source adapters remain explicit UNKNOWN.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from copy import deepcopy
import json,threading,time,uuid
import psycopg
import cp7_planning_history_cases as history
import cp7_identity_cases as policies
import cp7_snapshot_cases as auth
import cp6_bf_probe as bf
b=history.b

def get(cur,roots,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_planning_profiles_v1(%s::uuid[])',(roots,)).fetchone()[0];b.api.admin(cur);return r

def save(cur,payload,key=None,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_save_planning_profile_v1(%s,%s)',(json.dumps(payload),key or uuid.uuid4())).fetchone()[0];b.api.admin(cur);return r

def capture(cur,today,key=None,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_capture_baseline_v1(%s,%s)',(json.dumps(history.query(today)),key or uuid.uuid4())).fetchone()[0];b.api.admin(cur);return r

def read(cur,run,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_read_baseline_v1(%s)',(run,)).fetchone()[0];b.api.admin(cur);return r

def payload(cur,f,revision='0',**changes):
 p=get(cur,[f['product']])['rows'][0]
 return dict(root_id=p['root_id'],product_version_id=p['product_version_id'],expected_revision=revision,
  reason='P06 explicit selected calendar-day assumptions, no production authorisation',
  config={**dict(mean_mode='SELECTED_MANUAL',daily_pcs='10',minimum_available_days='20',lead_days='3',review_days='7',buffer_days='0'),**changes})

def row(result,f):return next(r for r in result['rows']if r['target_key'].split(':')[0]==f['product'])

def custom_writer(cur):
 subject,role=auth.custom_actor(cur);cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'master.product.manage')",(role,));return subject,role

def assert_unknown_execution(r):
 assert r['final_gap_pcs']is None and all(r[k]=='UNKNOWN'for k in('supply_state','capacity_state','timeline_state')),r

def cases(cur,today):
 def metadata():
  f=history.fixture(cur,today);before=b.boundary.snapshot(cur);p=payload(cur,f);s=save(cur,p);w=get(cur,[f['product']]);a=w['rows'][0]
  assert a['revision']=='1'and a['quality']=='SELECTED_ASSUMPTION'and a['config']==p['config']and a['profile_id']==s['profile_id'],w
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',native_source_identity_reviewed=True,one_immutable_metadata_revision_no_native_business_write=True)
 def replay():
  f=history.fixture(cur,today);p=payload(cur,f);key=uuid.uuid4();r=save(cur,p,key);assert save(cur,p,key)==r
  changed=deepcopy(p);changed['config']['daily_pcs']='11';auth.refused(cur,lambda:save(cur,changed,key),'CP7_PROFILE_REQUEST_CHANGED')
  assert cur.execute('select count(*)from cp7_profile.profiles where root_id=%s',(f['product'],)).fetchone()[0]==1
  return dict(status='PASS',same_UUID_same_outcome_one_revision=True,changed_payload_refused=True)
 def stale():
  f=history.fixture(cur,today);p=payload(cur,f);save(cur,p);before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:save(cur,p),'CP7_PROFILE_REVISION_CHANGED')
  assert cur.execute('select count(*)from cp7_profile.profiles where root_id=%s',(f['product'],)).fetchone()[0]==1 and b.boundary.snapshot(cur)==before
  return dict(status='PASS',stale_expected_revision_atomic=True)
 def wrong_version():
  f=history.fixture(cur,today);p=payload(cur,f);p['product_version_id']=str(uuid.uuid4());auth.refused(cur,lambda:save(cur,p),'CP7_PROFILE_SOURCE_CHANGED')
  p['root_id']=str(uuid.uuid4());auth.refused(cur,lambda:save(cur,p),'CP7_PROFILE_SOURCE_CHANGED')
  assert cur.execute('select count(*)from cp7_profile.profiles').fetchone()[0]==0
  return dict(status='PASS',wrong_native_version_and_unknown_root_refused=True)
 def malformed():
  f=history.fixture(cur,today);p=payload(cur,f);before=b.boundary.snapshot(cur)
  invalid=[('mean_mode','DEFAULT'),('daily_pcs',10),('daily_pcs',None),('daily_pcs','-1'),('minimum_available_days','0'),('minimum_available_days','1.2'),('minimum_available_days','20.0'),('lead_days',True),('review_days','3661')]
  for field,value in invalid:
   bad=deepcopy(p);bad['config'][field]=value;auth.refused(cur,lambda bad=bad:save(cur,bad),'CP7_')
  bad=deepcopy(p);bad['config']['lead_days']='0';bad['config']['review_days']='0';auth.refused(cur,lambda:save(cur,bad),'CP7_PROFILE_HORIZON')
  bad=deepcopy(p);bad['config']['capacity_pcs']='1000';auth.refused(cur,lambda:save(cur,bad),'CP7_WIP_FIELDS')
  bad=dict(p,reason=123);auth.refused(cur,lambda:save(cur,bad),'CP7_PROFILE_CONFIG')
  bad=dict(p,complete_scope=True);auth.refused(cur,lambda:save(cur,bad),'CP7_WIP_FIELDS')
  assert cur.execute('select count(*)from cp7_profile.profiles').fetchone()[0]==0 and b.boundary.snapshot(cur)==before
  return dict(status='PASS',strict_decimal_closed_config_and_scope=True,all_invalid_inputs_atomic=True)
 def absent():
  f=history.fixture(cur,today);r=capture(cur,today);a=row(r,f)
  assert a['profile']['quality']=='UNREVIEWED'and a['demand_estimate']['status']=='UNKNOWN'and a['target']['status']=='UNKNOWN'and a['start_new_pcs']is None,a
  assert a['available_fg_pcs']=='76'and r['apply_enabled']is False and r['production_go']is False;assert_unknown_execution(a)
  return dict(status='PASS',no_profile_no_default_mean_or_lead=True,native_FG76_known_missing_supply_unknown=True)
 def manual():
  f=history.fixture(cur,today);s=save(cur,payload(cur,f));before=b.boundary.snapshot(cur);r=capture(cur,today);a=row(r,f)
  assert a['demand_estimate']['basis']=='SELECTED_MANUAL_ASSUMPTION'and a['demand_estimate']['daily_pcs']=='10'and a['target']['target_pcs']=='100',a
  assert a['available_fg_pcs']=='76'and r['apply_enabled']is False and a['start_new_pcs']is None;assert_unknown_execution(a)
  assert any(x['kind']=='PLANNING_PROFILE'and x['id']==s['profile_id']and x['revision']=='1'for x in a['refs'])and b.boundary.snapshot(cur)==before
  return dict(status='PASS',selected_mean10_lead3_review7_buffer0_target100=True,native_FG76_not_fake_final_gap24=True,private_single_target_kernel=True)
 def own_unknown():
  f=history.fixture(cur,today);p=payload(cur,f);p['config'].update(mean_mode='OWN_AVAILABLE_HISTORY',daily_pcs=None);save(cur,p);a=row(capture(cur,today),f)
  assert a['demand_estimate']['status']=='UNKNOWN'and a['demand_estimate']['daily_pcs']is None and a['target']['status']=='UNKNOWN';assert_unknown_execution(a)
  return dict(status='PASS',insufficient_actual_historical_availability_unknown_not_zero=True)
 def horizon_unknown():
  f=history.fixture(cur,today);p=payload(cur,f);p['config']['lead_days']=None;save(cur,p);a=row(capture(cur,today),f)
  assert a['demand_estimate']['daily_pcs']=='10'and a['target']['status']=='UNKNOWN'and a['target']['reason']=='HORIZON_UNKNOWN';assert_unknown_execution(a)
  return dict(status='PASS',missing_lead_never_defaulted_or_imputed=True)
 def archive():
  f=history.fixture(cur,today);p=payload(cur,f);save(cur,p);key=uuid.uuid4();r=capture(cur,today,key);assert capture(cur,today,key)==r
  original=cur.execute('select facts,result from cp7_baseline_native.runs where id=%s',(r['run_id'],)).fetchone()
  p['expected_revision']='1';p['config']['daily_pcs']='20';save(cur,p);old=read(cur,r['run_id']);new=capture(cur,today)
  assert old['source_state']=='ARCHIVED_STALE'and row(old,f)['target']['target_pcs']=='100'and row(new,f)['target']['target_pcs']=='200'
  assert cur.execute('select facts,result from cp7_baseline_native.runs where id=%s',(r['run_id'],)).fetchone()==original
  assert cur.execute('select count(*)from cp7_baseline_native.runs where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',profile_revision_stales_immutable_prior_target=True,new_capture200_prior_target100=True,exact_baseline_UUID_one_run=True)
 def revoke():
  f=history.fixture(cur,today);subject,role=custom_writer(cur);p=payload(cur,f);key=uuid.uuid4();save(cur,p,key,subject);run=capture(cur,today,subject=subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,))
  auth.refused(cur,lambda:save(cur,p,key,subject),'CP7_POLICY_ACCESS_DENIED')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
  auth.refused(cur,lambda:capture(cur,today,uuid.UUID(run['request_id']),subject),'CP7_ACCESS_DENIED');auth.refused(cur,lambda:read(cur,run['run_id'],subject),'CP7_ACCESS_DENIED')
  return dict(status='PASS',current_native_authority_before_cached_profile_and_baseline_and_archive=True)
 def private():
  f=history.fixture(cur,today);s=save(cur,payload(cur,f));r=capture(cur,today)
  for table,key in [('cp7_profile.profiles',s['profile_id']),('cp7_baseline_native.runs',r['run_id'])]:
   code='CP7_POLICY_HISTORY_IMMUTABLE'if table.startswith('cp7_profile')else'CP7_RUN_IMMUTABLE'
   auth.refused(cur,lambda table=table,key=key:cur.execute('delete from '+table+' where id=%s',(key,)),code)
  auth.refused(cur,lambda:cur.execute("update cp7_profile.profiles set reason='overwrite'where id=%s",(s['profile_id'],)),'CP7_POLICY_HISTORY_IMMUTABLE')
  for who in('anon','authenticated','service_role'):
   for table in('cp7_profile.profiles','cp7_profile.commands','cp7_baseline_native.runs'):
    assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE\')',(who,table)).fetchone()[0]
  for who in('cp7_policy','cp7_capture'):
   assert not cur.execute("select exists(select 1 from pg_class t join pg_namespace n on n.oid=t.relnamespace where n.nspname='erp'and t.relkind in('r','p','v')and has_table_privilege(%s,t.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))",(who,)).fetchone()[0]
   for fn in('erp.save_sale_draft_v2(jsonb,uuid,bigint)','erp.post_sale_v2(uuid,uuid,bigint)'):
    assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(who,fn)).fetchone()[0]
  return dict(status='PASS',immutable_metadata_and_read_principals_no_native_DML_or_writer_EXEC=True)
 def zones():
  f=history.fixture(cur,today);p=payload(cur,f);pk=uuid.uuid4();save(cur,p,pk);key=uuid.uuid4();r=capture(cur,today,key);w=get(cur,[f['product']])
  for zone in('UTC','Asia/Jakarta','America/Los_Angeles'):
   cur.execute("select set_config('TimeZone',%s,true)",(zone,));assert capture(cur,today,key)==r and get(cur,[f['product']])==w
  return dict(status='PASS',three_caller_zones_same_native_capture_profile_and_hash=True)
 def stopped_stock():
  f=history.fixture(cur,today);at=cur.execute('select clock_timestamp()').fetchone()[0];g=bf.group(cur,[f['product']],at,settings=dict(price=None,bom=None,work_rates=[],laundry_rates=[]));bf.save(cur,[g],at)
  w=policies.get(cur,[g['id']]);policies.apply(cur,[policies.proposal(w['rows'][0],'STOPPED')]);save(cur,payload(cur,f));r=capture(cur,today);a=row(r,f)
  assert a['production_policy']['policy']['state']=='STOPPED'and a['start_new_pcs']=='0'and a['available_fg_pcs']=='76'and a['target']['target_pcs']=='100',a
  assert_unknown_execution(a);history.sales.fg.post_sale(cur,f['draft']);fresh=row(capture(cur,today),f)
  assert fresh['available_fg_pcs']=='76'and fresh['start_new_pcs']=='0'and read(cur,r['run_id'])['source_state']=='ARCHIVED_STALE'
  return dict(status='PASS',known_STOP_new_production0_existing_native_stock_still_sellable=True,native_post_allowed_stop_not_sales_cancellation=True)
 declared=[('PROFILE_METADATA',metadata),('PROFILE_UUID',replay),('STALE_REVISION',stale),('NATIVE_VERSION',wrong_version),('STRICT_CONFIG',malformed),('UNREVIEWED_UNKNOWN',absent),('SELECTED_TARGET100',manual),('OWN_HISTORY_UNKNOWN',own_unknown),('LEAD_UNKNOWN',horizon_unknown),('IMMUTABLE_ARCHIVE200',archive),('CURRENT_AUTHORITY',revoke),('PRIVATE_CAPS',private),('TIMEZONES',zones),('STOP_NATIVE_STOCK',stopped_stock)]
 return history.cases(cur,today)+[('P06_NATIVE_'+name,fn)for name,fn in declared]

def races(tools,today):
 def prepare():
  with tools.connect()as conn,conn.cursor()as cur:f=history.fixture(cur,today);p=payload(cur,f);conn.commit();return f,p
 def same_uuid():
  f,p=prepare();key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(timeout=5);r=save(cur,p,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:rs=[j.result(30)for j in[pool.submit(send),pool.submit(send)]]
  assert rs[0]==rs[1],rs
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_profile.profiles where root_id=%s',(f['product'],)).fetchone()[0]==1
  return dict(status='PASS',two_real_transactions_one_UUID_one_profile_revision=True)
 def competing():
  f,p=prepare();gate=threading.Barrier(2)
  def send(daily):
   q=deepcopy(p);q['config']['daily_pcs']=daily
   with tools.connect()as conn,conn.cursor()as cur:
    gate.wait(timeout=5)
    try:r=save(cur,q);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e)
  with ThreadPoolExecutor(max_workers=2)as pool:rs=[j.result(30)for j in[pool.submit(send,'10'),pool.submit(send,'20')]]
  assert sum(isinstance(r,dict)for r in rs)==1 and sum(isinstance(r,str)and'CP7_PROFILE_REVISION_CHANGED'in r for r in rs)==1,rs
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_profile.profiles where root_id=%s',(f['product'],)).fetchone()[0]==1
  return dict(status='PASS',two_distinct_commands_same_revision_exactly_one_append=True)
 def revoke_waiting():
  with tools.connect()as conn,conn.cursor()as cur:f=history.fixture(cur,today);p=payload(cur,f);subject,role=custom_writer(cur);key=uuid.uuid4();save(cur,p,key,subject);conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:PROFILE:REQUEST:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=save(cur,p,key,subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_save_planning_profile_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P06_REAL_PROFILE_REQUEST_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(30)
  assert isinstance(result,str)and'CP7_POLICY_ACCESS_DENIED'in result,result
  return dict(status='PASS',current_native_authority_revoked_during_observed_cached_profile_UUID_lock=True)
 return history.races(tools,today)+[('P06_RACE_SAME_PROFILE_UUID',same_uuid),('P06_RACE_COMPETING_REVISION',competing),('P06_RACE_CURRENT_PROFILE_REVOKE',revoke_waiting)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p06-native-owner')
  with http.connect()as conn,conn.cursor()as cur:f=history.fixture(cur,today);p=payload(cur,f);conn.commit()
  w=owner.rpc('erp_cp7_get_planning_profiles_v1',dict(p_roots=[f['product']]));assert w['status']==200 and w['body']['rows'][0]['quality']=='UNREVIEWED',w
  args=dict(p_payload=p,p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_save_planning_profile_v1',args);assert r['status']==200,r;assert owner.rpc('erp_cp7_save_planning_profile_v1',args)['body']==r['body']
  q=dict(p_query=history.query(today),p_request=str(uuid.uuid4()));n=owner.rpc('erp_cp7_capture_baseline_v1',q);assert n['status']==200,n;assert row(n['body'],f)['target']['target_pcs']=='100'and row(n['body'],f)['available_fg_pcs']=='76'and n['body']['apply_enabled']is False
  assert http.anon_rpc('erp_cp7_save_planning_profile_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  for fn,payload_ in [('erp_cp7_save_planning_profile_v1',args),('erp_cp7_capture_baseline_v1',q),('erp_cp7_read_baseline_v1',dict(p_run=n['body']['run_id']))]:assert owner.rpc(fn,payload_)['status']==403
  return dict(status='PASS',actual_Auth_HTTP_profile_and_target100_nativeFG76=True,current_deactivation_before_cached_commands_and_archive=True)
 return history.http_cases(http,today)+[('P06_ACTUAL_AUTH_HTTP',flow)]
