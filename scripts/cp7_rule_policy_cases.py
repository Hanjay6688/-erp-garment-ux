"""Versioned policy metadata. Twelve DB, three real races, three Auth/HTTP.

No clock oracle is an ERP event, no policy review is a business resolution,
and no rule setting changes money, stock, HPP or delivery.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json,threading,time,uuid
import psycopg
import cp7_obligation_history_cases as previous
parent,auth,b,attention=previous.parent,previous.auth,previous.b,previous.attention

def config(enabled=None,value=None,unit='PCS',cooldown=None,quiet=None):
 return dict(enabled=enabled,threshold_value=value,threshold_unit=unit,cooldown_minutes=cooldown,
  quiet=quiet or dict(enabled=None,starts_at=None,ends_at=None,timezone='Asia/Jakarta'))
def ready(value='0',unit='PCS',cooldown='0'):
 return config(True,value,unit,cooldown,dict(enabled=False,starts_at=None,ends_at=None,timezone='Asia/Jakarta'))
def get(cur,run,subject=None):return attention.rpc(cur,'erp_cp7_get_reminder_policy_v1',(run,),subject)
def command(cur,p,key=None,subject=None):return attention.rpc(cur,'erp_cp7_save_reminder_policy_v1',(json.dumps(p),key or uuid.uuid4()),subject)
def resolve(cur,p,key,subject=None):return attention.rpc(cur,'erp_cp7_get_reminder_policy_request_v1',(json.dumps(p),key),subject)
def intent(original,r='PRODUCTION_GAP',revision='0',c=None,target=None):
 return dict(run_id=original['run_id'],rule_id=r,scope_kind='TARGET'if target else'GLOBAL',scope_key=target or'*',expected_revision=revision,config=c or config(unit='DAY'if r in('AR_DUE','AP_DUE')else'PCS'),reason='Explicit Native policy fixture decision, not an operating default')
def fixture(cur,today,subject=None):parent.setup(cur,today);return parent.capture(cur,today,subject=subject)
def admin(cur):
 from cp7_analysis_finance_cases import admin_actor
 subject,role=admin_actor(cur,parent)
 cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'master.product.manage')on conflict do nothing",(role,))
 return subject,role
def stored(cur):return cur.execute('select rule_id,scope_kind,scope_key,revision,id,previous_id,config,reason,created_by,created_at from cp7_reminder_native.rule_policies order by rule_id,scope_kind,scope_key,revision').fetchall()
def receipt(cur,key):return cur.execute('select result from cp7_reminder_native.requests where request_id=%s',(key,)).fetchone()
def rows(result):return result['rows']
def timing(cur,c,at,last=None):return cur.execute('select cp7_reminder_native.policy_timing(%s::jsonb,%s,%s)',(json.dumps(c)if c is not None else None,at,last)).fetchone()[0]

def cases(cur,today):
 def empty():
  original=fixture(cur,today);before=b.boundary.snapshot(cur);e=get(cur,original['run_id'])
  assert e['contract_version']=='cp7.native-rule-policy-workspace.v1'and e['rows']==[]and e['total']=='0'and e['page_complete']
  assert set(e['allowed_rules'])=={'PRODUCTION_GAP','ACCESSORY_NEED','AR_DUE','AP_DUE'}and e['manage_allowed']and not e['external_delivery_enabled']
  assert e['analysis']['analysis']==original['analysis']and e['analysis']['financial_source']==original['financial_source']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_empty_complete_workspace_no_implicit_zero_or_disable=True,Original_and_entire_ERP_boundary_unchanged=True)
 def nullable():
  original=fixture(cur,today);before=b.boundary.snapshot(cur);first=command(cur,intent(original));one=deepcopy(rows(first)[0]);p=intent(original,revision='1',c=ready());second=command(cur,p);two=deepcopy(rows(second)[0]);third=command(cur,intent(original,revision='2',c=dict(ready(),enabled=False)));three=rows(third)[0]
  assert one['config']['enabled']is None and one['config']['threshold_value']is None and one['config']['cooldown_minutes']is None
  assert two['config']['enabled']is True and two['config']['threshold_value']==two['config']['cooldown_minutes']=='0'
  assert three['config']['enabled']is False and three['config']['threshold_value']=='0'and three['previous_id']==two['policy_id']and two['previous_id']==one['policy_id']
  saved=stored(cur);auth.refused(cur,lambda:cur.execute("update cp7_reminder_native.rule_policies set reason='changed'where id=%s",(one['policy_id'],)),'CP7_REMINDER_REQUEST_IMMUTABLE');auth.refused(cur,lambda:cur.execute('delete from cp7_reminder_native.rule_policies where id=%s',(one['policy_id'],)),'CP7_REMINDER_REQUEST_IMMUTABLE')
  assert stored(cur)==saved and len(saved)==3 and b.boundary.snapshot(cur)==before and third['analysis']['analysis']==original['analysis']
  return dict(status='PASS',three_immutable_versions_preserve_NULL_zero_disabled_and_reasons=True,linked_history_and_entire_ERP_boundary_preserved=True)
 def units():
  original=fixture(cur,today);before=b.boundary.snapshot(cur)
  for r in('PRODUCTION_GAP','ACCESSORY_NEED','AR_DUE','AP_DUE'):
   unit='DAY'if r in('AR_DUE','AP_DUE')else'PCS';e=command(cur,intent(original,r,c=ready(unit=unit)));assert next(p for p in rows(e)if p['rule_id']==r)['config']['threshold_unit']==unit
  assert len(stored(cur))==4 and b.boundary.snapshot(cur)==before
  return dict(status='PASS',all_four_current_authorized_units_stored_without_conversion_or_money_calculation=True)
 def hierarchy():
  original=fixture(cur,today);target=original['analysis']['recommendations'][0]['target']['key'];global_row=rows(command(cur,intent(original,c=ready())))[0]
  missing=cur.execute("select cp7_reminder_native.policy_resolve(%s::jsonb,'ACCESSORY_NEED',%s)",(json.dumps([global_row]),target)).fetchone()[0];assert missing['basis']=='MISSING'and missing['policy']is None
  global_result=cur.execute("select cp7_reminder_native.policy_resolve(%s::jsonb,'PRODUCTION_GAP',%s)",(json.dumps([global_row]),target)).fetchone()[0];assert global_result['basis']=='GLOBAL'
  e=command(cur,intent(original,target=target));chosen=cur.execute("select cp7_reminder_native.policy_resolve(%s::jsonb,'PRODUCTION_GAP',%s)",(json.dumps(rows(e)),target)).fetchone()[0]
  assert chosen['basis']=='EXACT_TARGET'and chosen['policy']['config']['enabled']is None and chosen['policy']['config']['threshold_value']is None
  e=command(cur,intent(original,revision='1',target=target,c=dict(ready(),enabled=False)));chosen=cur.execute("select cp7_reminder_native.policy_resolve(%s::jsonb,'PRODUCTION_GAP',%s)",(json.dumps(rows(e)),target)).fetchone()[0];assert chosen['policy']['config']['enabled']is False
  return dict(status='PASS',actual_saved_target_whole_version_overrides_global=True,target_NULL_not_partial_inheritance_disabled_not_global_activation=True)
 def quiet():
  c=ready();c['quiet']=dict(enabled=True,starts_at='22:00',ends_at='06:00',timezone='Asia/Jakarta')
  for zone in('UTC','America/Los_Angeles','Pacific/Kiritimati'):
   cur.execute("select set_config('TimeZone',%s,true)",(zone,))
   assert timing(cur,c,datetime.fromisoformat('2026-10-01T21:59:59+07:00'))['status']=='READY'
   start=timing(cur,c,datetime.fromisoformat('2026-10-01T22:00:00+07:00'));assert start['status']=='QUIET'and datetime.fromisoformat(start['next_at'])==datetime.fromisoformat('2026-10-02T06:00:00+07:00')
   assert timing(cur,c,datetime.fromisoformat('2026-10-02T05:59:59+07:00'))['status']=='QUIET'and timing(cur,c,datetime.fromisoformat('2026-10-02T06:00:00+07:00'))['status']=='READY'
  return dict(status='PASS',fixture_kind='POLICY_CLOCK_CONTRACT_ORACLE',WIB_overnight_start_inclusive_end_exclusive_identical_under_three_caller_timezones=True,no_Native_event_or_delivery_claim=True)
 def cooldown():
  at=datetime.fromisoformat('2026-10-01T10:00:00+07:00');c=ready(cooldown='30')
  assert timing(cur,c,at,at-timedelta(minutes=30))['status']=='READY'and timing(cur,c,at,at-timedelta(minutes=29))['status']=='COOLDOWN'
  assert timing(cur,dict(c,cooldown_minutes='0'),at,at)['status']=='READY'and timing(cur,c,at,at+timedelta(seconds=1))['status']=='CLOCK_CONFLICT'
  assert timing(cur,dict(c,cooldown_minutes=None),at)['status']=='UNCONFIGURED'and timing(cur,None,at)['status']=='UNCONFIGURED'and timing(cur,dict(c,enabled=False),at)['status']=='DISABLED'
  later=ready(cooldown='1440');later['quiet']=dict(enabled=True,starts_at='22:00',ends_at='06:00',timezone='Asia/Jakarta');night=datetime.fromisoformat('2026-10-01T23:00:00+07:00');assert datetime.fromisoformat(timing(cur,later,night,night)['next_at'])==datetime.fromisoformat('2026-10-03T06:00:00+07:00')
  return dict(status='PASS',fixture_kind='POLICY_CLOCK_CONTRACT_ORACLE',cooldown_exact_boundary_NULL_zero_future_clock_and_disabled_distinct=True,no_Native_elapsed_history_fabricated=True)
 def replay():
  original=fixture(cur,today);p=intent(original,c=ready());key=uuid.uuid4();first=command(cur,p,key);second=command(cur,intent(original,revision='1',c=dict(ready(),enabled=False)));again=command(cur,p,key)
  assert again['request_result']==first['request_result']and rows(again)[0]['revision']=='2'and rows(again)[0]['policy_id']==rows(second)[0]['policy_id']and len(stored(cur))==2
  return dict(status='PASS',same_UUID_old_receipt_replays_exactly_with_current_successor_workspace=True,no_duplicate_policy_version=True)
 def conflict():
  original=fixture(cur,today);p=intent(original,c=ready());key=uuid.uuid4();command(cur,p,key);saved=stored(cur)
  auth.refused(cur,lambda:command(cur,dict(p,reason='Changed same UUID'),key),'CP7_REMINDER_REQUEST_CHANGED');auth.refused(cur,lambda:command(cur,p),'CP7_RULE_POLICY_STALE_REVISION');assert stored(cur)==saved
  return dict(status='PASS',changed_UUID_payload_and_stale_shared_revision_refused_without_write=True)
 def absent():
  original=fixture(cur,today);p=intent(original,c=ready());key=uuid.uuid4();sealed=resolve(cur,p,key);late=command(cur,p,key)
  assert sealed['request_result']['status']=='NOT_COMMITTED'and sealed['request_result']==late['request_result']and stored(cur)==[]
  auth.refused(cur,lambda:cur.execute("update cp7_reminder_native.requests set result='{}'where request_id=%s",(key,)),'CP7_REMINDER_REQUEST_IMMUTABLE')
  return dict(status='PASS',absent_request_sealed_at_actual_request_lock_and_late_write_cannot_create_version=True)
 def current():
  original=fixture(cur,today);subject,role=admin(cur);own=parent.capture(cur,today,subject=subject);p=intent(own,c=ready());key=uuid.uuid4();command(cur,p,key,subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,))
  assert not get(cur,own['run_id'],subject)['manage_allowed']
  for fn in(lambda:command(cur,p,key,subject),lambda:resolve(cur,p,key,subject)):auth.refused(cur,fn,'CP7_RULE_POLICY_MANAGE_DENIED')
  auth.refused(cur,lambda:get(cur,own['run_id']),'CP7_ANALYSIS_RUN_UNAVAILABLE')
  cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,));auth.refused(cur,lambda:get(cur,own['run_id'],subject),'CP7_REMINDER_ACCESS_DENIED')
  return dict(status='PASS',current_manage_revocation_refuses_cached_write_and_lookup_read_remains_truthful=True,foreign_Original_and_inactive_actor_denied=True)
 def stale_source():
  original=fixture(cur,today);definition=cur.execute("select pg_get_functiondef('cp7_analysis_native.fact(text,text,jsonb,jsonb)'::regprocedure)").fetchone()[0];assert 'SOURCE_INPUT_NOT_PROVEN'in definition
  cur.execute(definition.replace('SOURCE_INPUT_NOT_PROVEN','SOURCE_INPUT_NOT_PROVEN_POLICY_REVISED'),prepare=False);before=stored(cur);e=get(cur,original['run_id']);assert e['analysis']['source_state']=='ARCHIVED_STALE'and e['analysis']['analysis']==original['analysis']
  auth.refused(cur,lambda:command(cur,intent(original,c=ready())),'CP7_RULE_POLICY_SOURCE_CHANGED');assert stored(cur)==before
  return dict(status='PASS',actual_source_definition_change_archives_Original_refuses_new_policy_write=True,no_Original_relabel_or_metadata_commit=True)
 def private_and_bad():
  original=fixture(cur,today);p=intent(original);before=stored(cur)
  for c in(dict(ready(),threshold_unit='KG'),dict(ready(),threshold_unit=None),dict(ready(),threshold_value='-1'),dict(ready(),cooldown_minutes='525601')):auth.refused(cur,lambda c=c:command(cur,dict(p,config=c)),'CP7_RULE_POLICY_CONFIG')
  auth.refused(cur,lambda:command(cur,intent(original,'AR_DUE',c=ready(value='1.5',unit='DAY'))),'CP7_RULE_POLICY_CONFIG')
  auth.refused(cur,lambda:command(cur,intent(original,target=str(uuid.uuid4())+':'+str(uuid.uuid4()))),'CP7_RULE_POLICY_TARGET_UNAVAILABLE')
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_reminder_native','USAGE')or has_table_privilege(%s,'cp7_reminder_native.rule_policies','SELECT,INSERT,UPDATE,DELETE')",(who,who)).fetchone()[0]
  assert stored(cur)==before
  return dict(status='PASS',current_target_units_signed_threshold_fractional_due_cap_and_private_RLS_fail_closed=True)
 extra=[('EMPTY_CURRENT',empty),('NULL_ZERO_DISABLED_HISTORY',nullable),('FOUR_RULE_UNITS',units),('SCOPE_WHOLE_VERSION',hierarchy),('WIB_OVERNIGHT',quiet),('COOLDOWN_CLOCK',cooldown),('OLD_UUID_CURRENT_SUCCESSOR',replay),('UUID_CAS_CONFLICT',conflict),('SEALED_ABSENT',absent),('CURRENT_AUTH',current),('SOURCE_CHANGED',stale_source),('PRIVATE_INVALID_INPUT',private_and_bad)]
 return previous.cases(cur,today)+[('P16_POLICY_'+name,fn)for name,fn in extra]

def races(tools,today):
 def duplicate():
  with tools.connect()as conn,conn.cursor()as cur:original=fixture(cur,today);p=intent(original,c=ready());conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(5);e=command(cur,p,key);conn.commit();return e
  with ThreadPoolExecutor(max_workers=2)as pool:results=[f.result(60)for f in[pool.submit(send),pool.submit(send)]]
  assert results[0]['request_result']==results[1]['request_result']
  with tools.connect()as conn,conn.cursor()as cur:assert len(stored(cur))==1
  return dict(status='PASS',two_real_connections_same_UUID_one_version_one_exact_receipt=True)
 def cross_actor():
  with tools.connect()as conn,conn.cursor()as cur:original=fixture(cur,today);subject,_=admin(cur);own=parent.capture(cur,today,subject=subject);conn.commit()
  gate=threading.Barrier(2)
  def send(e,subject):
   with tools.connect()as conn,conn.cursor()as cur:
    gate.wait(5)
    try:r=command(cur,intent(e,c=ready()),subject=subject);conn.commit();return r
    except psycopg.Error as ex:conn.rollback();return str(ex)
  with ThreadPoolExecutor(max_workers=2)as pool:results=[f.result(60)for f in[pool.submit(send,original,None),pool.submit(send,own,subject)]]
  assert sum(isinstance(x,dict)for x in results)==1 and any(isinstance(x,str)and'CP7_RULE_POLICY_STALE_REVISION'in x for x in results),results
  with tools.connect()as conn,conn.cursor()as cur:assert len(stored(cur))==1
  return dict(status='PASS',shared_rule_scope_CAS_serializes_two_authorized_actors_at_real_lock=True)
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);subject,role=admin(cur);original=parent.capture(cur,today,subject=subject);p=intent(original,c=ready());key=uuid.uuid4();before=stored(cur);conn.commit()
  with tools.connect()as holder,holder.cursor()as held:
   held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||%s||':'||%s,0))",(str(subject),str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=command(cur,p,key,subject);conn.commit();return r
     except psycopg.Error as ex:conn.rollback();return str(ex)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+12
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as cur:
      while time.monotonic()<deadline:
       waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_save_reminder_policy_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P16_POLICY_REAL_REQUEST_WAIT_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(60)
  assert isinstance(result,str)and'CP7_REMINDER_ACCESS_CHANGED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:assert stored(cur)==before and receipt(cur,key)is None
  return dict(status='PASS',current_manage_revoked_during_observed_request_wait_refuses_no_policy_or_receipt_commit=True)
 return previous.races(tools,today)+[('P16_POLICY_RACE_DUPLICATE_UUID',duplicate),('P16_POLICY_RACE_CROSS_ACTOR_CAS',cross_actor),('P16_POLICY_RACE_CURRENT_MANAGE',revoke)]

def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p16-policy-http')
  with http.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);conn.commit()
  original=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert original['status']==200
  e=owner.rpc('erp_cp7_get_reminder_policy_v1',dict(p_run=original['body']['run_id']));assert e['status']==200 and e['body']['rows']==[]
  p=intent(original['body'],c=ready());args=dict(p_payload=p,p_request=str(uuid.uuid4()));saved=owner.rpc('erp_cp7_save_reminder_policy_v1',args);again=owner.rpc('erp_cp7_get_reminder_policy_request_v1',args)
  assert saved['status']==again['status']==200 and saved['body']['request_result']==again['body']['request_result']and saved['body']['analysis']['analysis']==original['body']['analysis']
  return dict(status='PASS',actual_Auth_PostgREST_explicit_policy_write_and_current_exact_receipt=True)
 def authority():
  owner=http.login('OWNER','p16-policy-revoke');foreign=http.login('OWNER','p16-policy-foreign')
  with http.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);conn.commit()
  got=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert got['status']==200;original=got['body']
  current=owner.rpc('erp_cp7_get_reminder_policy_v1',dict(p_run=original['run_id']));assert current['status']==200,current
  revision=next((r['revision']for r in current['body']['rows']if r['rule_id']=='PRODUCTION_GAP'and r['scope_kind']=='GLOBAL'),'0')
  p=intent(original,revision=revision,c=ready());args=dict(p_payload=p,p_request=str(uuid.uuid4()))
  saved=owner.rpc('erp_cp7_save_reminder_policy_v1',args);assert saved['status']==200,saved
  assert foreign.rpc('erp_cp7_get_reminder_policy_v1',dict(p_run=original['run_id']))['status']==403
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  for name,payload in[('erp_cp7_get_reminder_policy_v1',dict(p_run=original['run_id'])),('erp_cp7_save_reminder_policy_v1',args),('erp_cp7_get_reminder_policy_request_v1',args)]:assert owner.rpc(name,payload)['status']==403
  return dict(status='PASS',actual_current_deactivation_before_read_cached_write_and_lookup_and_foreign_Original_denial=True)
 def absent():
  owner=http.login('OWNER','p16-policy-absence')
  with http.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);conn.commit()
  original=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert original['status']==200
  current=owner.rpc('erp_cp7_get_reminder_policy_v1',dict(p_run=original['body']['run_id']));assert current['status']==200,current
  revision=next((r['revision']for r in current['body']['rows']if r['rule_id']=='PRODUCTION_GAP'and r['scope_kind']=='GLOBAL'),'0')
  p=intent(original['body'],revision=revision);args=dict(p_payload=p,p_request=str(uuid.uuid4()));sealed=owner.rpc('erp_cp7_get_reminder_policy_request_v1',args);late=owner.rpc('erp_cp7_save_reminder_policy_v1',args)
  assert sealed['status']==late['status']==200 and sealed['body']['request_result']==late['body']['request_result']and sealed['body']['request_result']['status']=='NOT_COMMITTED'and late['body']['rows']==current['body']['rows']
  assert http.anon_rpc('erp_cp7_get_reminder_policy_v1',dict(p_run=original['body']['run_id']))['status']in(401,403)
  return dict(status='PASS',actual_Auth_sealed_absent_intent_late_write_does_not_save_and_anon_denied=True)
 return previous.http_cases(http,today)+[('P16_POLICY_HTTP_LIFECYCLE',actual),('P16_POLICY_HTTP_CURRENT_AUTH',authority),('P16_POLICY_HTTP_SEALED_ABSENT',absent)]
