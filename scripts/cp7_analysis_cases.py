"""Declared Native analysis.v2 oracles; never promote fixtures to factory facts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import json,sys,threading,time,uuid
import cp7_analysis_finance_cases as financial_cases
import cp7_analysis_archive_cases as archive_cases
import cp7_analysis_publication_cases as publication_cases
import psycopg
from jsonschema import Draft7Validator,FormatChecker
import cp7_planning_netting_cases as previous
import cp7_fg_adjustment_cases as adjustments
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'docs/cp7/framework-v2/verification'))
from semantic_contract import validate_semantics
SCHEMA=json.loads((Path(__file__).resolve().parents[1]/'docs/cp7/framework-v2/contracts/analysis.schema.json').read_text())
VALIDATOR=Draft7Validator(SCHEMA,format_checker=FormatChecker())
schedule=previous.schedule;auth=previous.auth;b=previous.b

def capture(cur,today,key=None,subject=None,q=None):
 return schedule.rpc(cur,'erp_cp7_capture_analysis_v1',(json.dumps(q or previous.baseline.history.query(today)),key or uuid.uuid4()),subject)
def read(cur,run,subject=None):return schedule.rpc(cur,'erp_cp7_read_analysis_v1',(run,),subject)
def checked(envelope):
 assert envelope['contract_version']=='cp7.native-analysis-run.v1'and not envelope['apply_enabled']and not envelope['production_go']
 x=envelope['analysis'];VALIDATOR.validate(x);assert not validate_semantics(x),validate_semantics(x)
 assert x['run_id']==envelope['run_id']and'fixture_kind'not in x and x['snapshot']['capture_complete']
 financial=envelope.get('financial_source')
 if financial is None:
  assert x['financial_readiness']=='BLOCKED'and x['quality']['financial']=='UNKNOWN'
  assert not any(m['value']['unit']=='IDR'for m in x['metrics'])
 else:
  f=financial['report']['snapshot'];status=f['data_confidence']['status']
  assert financial['contract_version']=='cp7.native-analysis-finance.v1'
  assert x['financial_readiness']==dict(READY='READY',RECALC_PENDING='LIMITED',BLOCKED='BLOCKED')[status]
  assert x['quality']['financial']==('COMPLETE'if status=='READY'else'PARTIAL')
  for section in('performance','financial_position'):
   for key,value in f[section].items():
    if not isinstance(value,str)or key in('gross_margin_pct','net_margin_pct'):continue
    metric=next(m for m in x['metrics']if m['metric_id']=='NATIVE_FINANCE:'+section+':'+key)
    assert metric['operands'][0]['value']==value and metric['operands'][0]['unit']=='IDR'
    recorded=section=='performance'and key not in('gross_profit','net_profit')or section=='financial_position'and key in('cash','customer_ar','supplier_final_ap','grni_estimated_liability')
    if status=='READY'or recorded:assert metric['value']['state']=='KNOWN'and metric['value']['value']==value
    else:assert metric['value']['state']=='UNKNOWN'and'value'not in metric['value']
 def visit(v):
  if isinstance(v,list):
   for a in v:visit(a)
  elif isinstance(v,dict):
   if v.get('state')in('KNOWN','ASSUMED')and'value'in v:assert v.get('refs'),v
   for a in v.values():visit(a)
 visit(x);return x
def recommendation(x,root):return next(r for r in x['recommendations']if r['target']['product_id']==root)
def setup(cur,today,review=True):
 f,root,s,p=previous.setup(cur,today,True)
 p['expected_revision']=str(cur.execute('select coalesce(max(revision),0)from cp7_schedule_native.plans').fetchone()[0])
 if review:schedule.save(cur,p)
 return f,root,s,p

def cases(cur,today):
 def frozen():
  f,root,s,p=setup(cur,today);before=b.boundary.snapshot(cur);e=capture(cur,today);x=checked(e);r=recommendation(x,root)
  assert r['actual_fg']['value']=='0'and r['target_qty']['value']=='100'and r['q_base']['value']==r['q_conditional']['value']=='93'
  assert x['allocation_edges'][0]['input_qty']['value']=='8'and x['allocation_edges'][0]['projected_output_qty']['value']=='7'
  assert x['sources'][0]['physical_remaining']['value']=='8'and x['status']=='PARTIAL'
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',unchanged_frozen_schema_and_semantic_validator=True,native8_projected7_target100_gap93_no_business_DML=True)
 def unreviewed():
  f,root,s,p=setup(cur,today,False);x=checked(capture(cur,today));r=recommendation(x,root)
  assert r['q_base']['state']=='UNKNOWN'and not x['allocation_edges']
  assert x['sources'][0]['physical_remaining']['state']=='KNOWN'and x['sources'][0]['eligible_input']['state']=='UNKNOWN'
  return dict(status='PASS',physical8_known_unreviewed_work_yield_eta_and_gap_unknown_not_zero=True)
 def policy_missing():
  f,root,s,p=previous.setup(cur,today);x=checked(capture(cur,today))
  assert not any(r['target']['product_id']==root for r in x['recommendations'])
  assert 'PRODUCTION_POLICY_UNREVIEWED:'+root+':'+cur.execute('select size_id::text from erp.products where id=%s',(root,)).fetchone()[0]in x['generation_warnings']
  assert any(a['primary_reason']=='PRODUCTION_POLICY_UNREVIEWED'for a in x['actions'])
  return dict(status='PASS',missing_native_policy_not_relabelled_active_or_dropped_from_review=True)
 def replay():
  setup(cur,today);key=uuid.uuid4();e=capture(cur,today,key);stored=cur.execute('select facts,result from cp7_analysis_native.runs where id=%s',(e['run_id'],)).fetchone()
  again=capture(cur,today,key);assert again['run_id']==e['run_id']and again['analysis']==e['analysis']
  assert cur.execute('select count(*)from cp7_analysis_native.runs where request_id=%s',(key,)).fetchone()[0]==1
  assert cur.execute('select facts,result from cp7_analysis_native.runs where id=%s',(e['run_id'],)).fetchone()==stored
  return dict(status='PASS',lost_reply_same_UUID_one_original_body_and_source_clock=True)
 def changed():
  setup(cur,today);key=uuid.uuid4();capture(cur,today,key);q=previous.baseline.history.query(today);q['group_mode']='RESTATED'
  auth.refused(cur,lambda:capture(cur,today,key,q=q),'CP7_ANALYSIS_REQUEST_CHANGED')
  return dict(status='PASS',same_UUID_changed_query_refused=True)
 def source_change():
  f,root,s,p=setup(cur,today);e=capture(cur,today);original=e['analysis'];previous.production.b.bbp.complete(cur,f,f['cutover']+timedelta(days=2),3)
  old=read(cur,e['run_id']);assert old['source_state']=='ARCHIVED_STALE'and old['analysis']==original
  fresh=capture(cur,today);assert fresh['analysis']['snapshot']['source_hash']!=original['snapshot']['source_hash']
  return dict(status='PASS',actual_native_output3_stales_archive_original_body_unchanged=True)
 def actor_scope():
  setup(cur,today);subject,role=auth.custom_actor(cur);e=capture(cur,today,subject=subject);x=checked(e)
  assert x['scope']['actor_scope_id']==subject
  auth.refused(cur,lambda:read(cur,e['run_id']),'CP7_ANALYSIS_RUN_UNAVAILABLE')
  assert not any(word in json.dumps(x)for word in ('unit_hpp','unit_price','debit','credit','cost_amount','refund_amount'))
  return dict(status='PASS',four_native_operational_permissions_actor_bound_no_financial_operands=True)
 def revoke():
  setup(cur,today);subject,role=auth.custom_actor(cur);key=uuid.uuid4();e=capture(cur,today,key,subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
  auth.refused(cur,lambda:capture(cur,today,key,subject),'CP7_ACCESS_DENIED');auth.refused(cur,lambda:read(cur,e['run_id'],subject),'CP7_ACCESS_DENIED')
  return dict(status='PASS',current_permission_before_cached_UUID_and_archived_read=True)
 def immutable():
  setup(cur,today);e=capture(cur,today)
  auth.refused(cur,lambda:cur.execute('delete from cp7_analysis_native.runs'),'CP7_RUN_IMMUTABLE')
  auth.refused(cur,lambda:cur.execute("update cp7_analysis_native.runs set result='{}'"),'CP7_RUN_IMMUTABLE')
  assert read(cur,e['run_id'])['analysis']==e['analysis']
  return dict(status='PASS',immutable_captured_facts_and_analysis_body=True)
 def late():
  f,root,s,p=setup(cur,today,False);at=cur.execute('select clock_timestamp()').fetchone()[0]
  p['config']['windows'][0]['starts_at']=schedule.stamp(at+timedelta(days=11));p['config']['windows'][0]['ends_at']=schedule.stamp(at+timedelta(days=11,hours=2));p['config']['through_at']=schedule.stamp(at+timedelta(days=12));schedule.save(cur,p)
  x=checked(capture(cur,today));assert recommendation(x,root)['q_base']['value']=='100'and not x['allocation_edges']
  assert any(r['target_key'].split(':')[0]==root and r['first_gap_at']for r in x['timeline'])
  return dict(status='PASS',late7_not_deducted_from_earlier_gap100=True)
 def available_signed():
  # Current Native writers also forbid a count correction that would overdraw
  # reserved stock. Exercise that actual guard and its atomicity; do not claim
  # a legacy 10-minus24 example was constructible through this Native lifecycle.
  h=previous.baseline.history;f=h.fixture(cur,today,qty=24,stock=100)
  d=adjustments.command(cur,'SAVE',adjustments.payload(cur,f,'-90'));before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:adjustments.action(cur,'POST',d),'Finished goods stock cannot become negative')
  assert b.boundary.snapshot(cur)==before
  previous.select_profiles(cur,f['product'],True);x=checked(capture(cur,today));r=recommendation(x,f['product'])
  assert r['actual_fg']['value']=='100'
  metric=next(m for m in x['metrics']if m['scope_key']==r['target']['key']);assert metric['value']['value']=='76'
  assert [o['value']for o in metric['operands']]==['100','24']
  return dict(status='PASS',native_overreservation_count_correction_refused_atomically=True,native_physical100_reserved24_available76_once=True,negative_available_lifecycle_not_native_constructible=True)
 def paused():
  f,root,s,p=setup(cur,today);source=cur.execute('select cp7_baseline_native.source()').fetchone()[0];product=next(r for r in source['facts']['products']if r['root_id']==root);sku=product['commercial'][0]['sku_id'];w=previous.policies.get(cur,[sku]);previous.policies.apply(cur,[previous.policies.proposal(w['rows'][0],'PAUSED')])
  # Policy is a real source dependency. Review the unchanged remaining-work
  # assumptions against the new Native policy source instead of reusing a
  # schedule whose source hash was invalidated by the pause command.
  current=previous.supply.capture(cur,today);revision=str(cur.execute('select max(revision)from cp7_schedule_native.plans').fetchone()[0]);review=schedule.payload(cur,current,revision);review['config']=p['config'];schedule.save(cur,review)
  x=checked(capture(cur,today));r=recommendation(x,root);assert r['production_state']=='PAUSED'and r['suggested_new']['value']==r['feasible_new']['value']=='0'
  assert r['q_base']['value']=='93'and r['unresolved_qty']['value']=='93'
  return dict(status='PASS',paused_keeps_shortage93_and_starts_zero=True)
 def engine_change():
  setup(cur,today);e=capture(cur,today);definition=cur.execute("select pg_get_functiondef('cp7_analysis_native.fact(text,text,jsonb,jsonb)'::regprocedure)").fetchone()[0]
  assert 'SOURCE_INPUT_NOT_PROVEN'in definition;cur.execute(definition.replace('SOURCE_INPUT_NOT_PROVEN','SOURCE_INPUT_NOT_PROVEN_REVISED'),prepare=False)
  old=read(cur,e['run_id']);assert old['source_state']=='ARCHIVED_STALE'and old['analysis']==e['analysis']
  return dict(status='PASS',actual_compiler_definition_change_stales_original_result=True)
 def capacity_unknown():
  f,root,s,p=setup(cur,today,False);p['config']['windows'][0]['other_load_minutes']=None;schedule.save(cur,p);x=checked(capture(cur,today))
  assert x['capacity_checks'][0]['available']['state']=='UNKNOWN'and x['capacity_checks'][0]['feasible_new']['state']=='UNKNOWN'
  assert recommendation(x,root)['feasible_new']['state']=='UNKNOWN'
  return dict(status='PASS',unreviewed_other_load_not_free_time_material_not_zero_feasible=True)
 declared=[('FROZEN_NATIVE',frozen),('UNKNOWN_WORK',unreviewed),('MISSING_POLICY',policy_missing),('REPLAY',replay),('CHANGED_QUERY',changed),('SOURCE_CHANGE',source_change),('ACTOR_SCOPE',actor_scope),('CURRENT_REVOKE',revoke),('IMMUTABLE',immutable),('LATE_SUPPLY',late),('SIGNED_AVAILABLE',available_signed),('PAUSED',paused),('ENGINE_CHANGE',engine_change),('UNKNOWN_CAPACITY',capacity_unknown)]
 return previous.cases(cur,today)+[('P14_NATIVE_ANALYSIS_'+n,f)for n,f in declared]+financial_cases.cases(cur,today,sys.modules[__name__])+archive_cases.cases(cur,today,sys.modules[__name__])+publication_cases.cases(cur,today,sys.modules[__name__])

def races(tools,today):
 def same_uuid():
  with tools.connect()as conn,conn.cursor()as cur:setup(cur,today);conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(timeout=5);r=capture(cur,today,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:rs=[j.result(30)for j in[pool.submit(send),pool.submit(send)]]
  assert rs[0]['run_id']==rs[1]['run_id']and rs[0]['analysis']==rs[1]['analysis']
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_analysis_native.runs where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',two_real_transactions_one_immutable_analysis_UUID=True)
 def changed_query():
  with tools.connect()as conn,conn.cursor()as cur:setup(cur,today);conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send(mode):
   with tools.connect()as conn,conn.cursor()as cur:
    q=previous.baseline.history.query(today);q['group_mode']=mode;gate.wait(timeout=5)
    try:r=capture(cur,today,key,q=q);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e)
  with ThreadPoolExecutor(max_workers=2)as pool:rs=[j.result(30)for j in[pool.submit(send,'AS_SOLD'),pool.submit(send,'RESTATED')]]
  assert sum(isinstance(r,dict)for r in rs)==1 and any(isinstance(r,str)and'CP7_ANALYSIS_REQUEST_CHANGED'in r for r in rs),rs
  return dict(status='PASS',same_UUID_two_queries_exactly_one_capture_other_refused=True)
 def revoke_waiting():
  with tools.connect()as conn,conn.cursor()as cur:setup(cur,today);subject,role=auth.custom_actor(cur);key=uuid.uuid4();e=capture(cur,today,key,subject);conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=capture(cur,today,key,subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_capture_analysis_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P14_REAL_CAPTURE_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(30)
  assert isinstance(result,str)and'CP7_ACCESS_DENIED'in result,result
  return dict(status='PASS',current_permission_revoked_during_observed_cached_capture_lock_refused=True)
 return previous.races(tools,today)+[('P14_ANALYSIS_RACE_UUID',same_uuid),('P14_ANALYSIS_RACE_QUERY',changed_query),('P14_ANALYSIS_RACE_CURRENT_AUTH',revoke_waiting)]+financial_cases.races(tools,today,sys.modules[__name__])+publication_cases.races(tools,today,sys.modules[__name__])

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p14-analysis-owner');other=http.login('OWNER','p14-analysis-other')
  with http.connect()as conn,conn.cursor()as cur:setup(cur,today);conn.commit()
  args=dict(p_query=previous.baseline.history.query(today),p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_capture_analysis_v1',args);assert r['status']==200,r;checked(r['body'])
  assert owner.rpc('erp_cp7_capture_analysis_v1',args)['body']['analysis']==r['body']['analysis']
  a=dict(p_run=r['body']['run_id']);assert other.rpc('erp_cp7_read_analysis_v1',a)['status']==403 and http.anon_rpc('erp_cp7_read_analysis_v1',a)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_capture_analysis_v1',args)['status']==403 and owner.rpc('erp_cp7_read_analysis_v1',a)['status']==403
  return dict(status='PASS',real_Auth_PostgREST_frozen_analysis_UUID_current403_and_actor_scope=True)
 return previous.http_cases(http,today)+[('P14_ANALYSIS_HTTP_AUTH',flow)]+financial_cases.http_cases(http,today,sys.modules[__name__])+archive_cases.http_cases(http,today,sys.modules[__name__])+publication_cases.http_cases(http,today,sys.modules[__name__])
