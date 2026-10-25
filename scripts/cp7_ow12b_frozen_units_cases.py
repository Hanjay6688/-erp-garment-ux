"""Closed private-request Native4. No public facade or default adoption."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import traceback
import uuid
import cp7_frozen_analysis_units_v2 as stage
import cp7_ow12b_frozen_capsule_cases as frozen
from cp7_ow04_restore_bundle import _catalog_rows

native,geometry=frozen.native,frozen.geometry
plan,bounded=native.plan,native.bounded
CONTRACT='cp7.ow12b.frozen-units-private-native4.v2'
IDS=dict(native=['OW12B_FROZEN_UNITS_V2_CATALOG22_EXACT_PREUSE',
 'OW12B_FROZEN_UNITS_V2_ACTUAL_REQUEST_UNITS_PAGES_REPLAY',
 'OW12B_FROZEN_UNITS_V2_FACTORY1200X3_ALL_TARGETS_PAGES',
 'OW12B_FROZEN_UNITS_V2_POST_STALE_IMMUTABLE_USED_INVERSE'])
REQUIRED=dict(native=4);EXPECTED=DECLARED=4
FUNCTIONS,SCHEDULES=native.FUNCTIONS,native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def sources():
 root=Path(__file__).resolve().parent
 return {**frozen.sources(),**{'cp7_frozen_analysis_units_v2/'+k:v for k,v in stage.sources().items()},
  **{p.name:sha256(p.read_bytes()).hexdigest()for p in(Path(__file__),root/'cp7_ow12b_frozen_units_local.mjs',root/'cp7_ow12b_frozen_units_preflight.py',root/'cp7_ow12b_frozen_units_probe.py')}}


def install(cur):
 frozen.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(frozen,name,globals()[name])
 parents=frozen.install(cur)
 def checked(c):
  native.stage.verify(c,parents['parents']['current'])
  frozen.binary.verify(c,parents['binary']);frozen.capsule.verify(c,parents['capsule'])
 current=stage.install_delta(cur,checked)
 return dict(parents=parents,current=current)


def unwind(cur,s):
 stage.rollback_preuse(cur,s['current'])
 frozen.capsule.rollback_preuse(cur,s['parents']['capsule'])
 frozen.binary.rollback_preuse(cur,s['parents']['binary'])
 native.unwind(cur,s['parents']['parents'])


def request(cur,q,key,subject,observed=None):
 # Explicit private invocation as cp7_capture with the actual actor claims.
 # This is not a public facade or an Auth HTTP qualification.
 plan.auth.actor(cur,subject)
 return frozen.call(cur,'cp7_frozen_analysis_units_v2.request',(json.dumps(q),key),observed,'PRIVATE_REQUEST')


def coverage(cur,job):return frozen.call(cur,'cp7_frozen_analysis_units_v2.coverage',(job,))


def prepared_cache(cur,job):
 plan.b.api.admin(cur)
 p=cur.execute("select payload from cp7_analysis_stage.target_rows where job_id=%s and kind='FROZEN_INPUTS_V2'and ord=1",(job,)).fetchone()
 assert p is not None,'FROZEN_UNITS_CACHE_ABSENT'
 return p[0]


def capture(cur,today,subject,observed):
 q=plan.staged.query(today);key=str(uuid.uuid4());physical=plan.monetary_state(cur)
 initial=request(cur,q,key,subject,observed);plan.staged.checked(initial,key,'RUNNING')
 row=plan.staged.job_row(cur,key,subject);c=row['reference'];saved=deepcopy(c)
 assert c['bounded_capture_state']=='FROZEN'and c['bounded_input_coverage']=='PENDING'and c['bounded_history_inputs']is None
 assert initial['units_done']==0 and coverage(cur,row['id'])=='PENDING'
 plan.b.api.admin(cur)
 assert cur.execute("select count(*)from cp7_analysis_stage.target_rows where job_id=%s and kind='FROZEN_INPUTS_V2'",(row['id'],)).fetchone()[0]==0
 f=dict(key=key,initial=initial,row=row,subject=subject)
 bounded.finish(cur,f)
 observed['completed']=dict(state=f['done']['state'],targets=f['pages']['targets_total'],pages=f['pages']['page_count'],step_millis=[x['ms']for x in f['calls']])
 cached=prepared_cache(cur,row['id']);expected=frozen.original_compile(cur,c,q,observed)
 assert cached['inputs']==expected;frozen.inputs_shape(c,expected)
 assert plan.staged.job_row(cur,key,subject)['reference']==saved and coverage(cur,row['id'])=='COMPLETE'
 assert plan.monetary_state(cur)==physical
 f['cache']=cached;f['expected']=expected
 return f


def cases(cur,today):
 observed={}
 def catalog():
  before=_catalog_rows(cur);s=install(cur);verified=stage.verify(cur,s['current'])
  assert(verified['new_private_functions'],verified['existing_replacements'],verified['new_public_rpcs'],verified['new_tables'])==(8,8,0,0)
  cur.execute('create view public.ow12b_frozen_units_inverse_guard as select cp7_frozen_analysis_units_v2.coverage(null::uuid)value')
  held=_catalog_rows(cur)
  try:stage.rollback_preuse(cur,s['current'])
  except Exception as error:assert getattr(error,'sqlstate',None)=='2BP01',str(error)
  else:raise AssertionError('FROZEN_UNITS_DEPENDENCY_VIEW_DROPPED')
  assert _catalog_rows(cur)==held;cur.execute('drop view public.ow12b_frozen_units_inverse_guard')
  unwind(cur,s);assert _catalog_rows(cur)==before
  return dict(status='PASS',private8_replacements8_no_new_RPC_table=True,exact22_composed_inverse=True,
   dependent_view_partial_inverse_atomic=True)
 def flow():
  install(cur);plan.fixture(cur,today);actor=native.policy.master.role_actor(cur,'OWNER')
  f=capture(cur,today,actor,observed);q=f['row']['query'];key=f['key']
  assert request(cur,q,key,actor)==f['done']
  plan.refused(cur,lambda:request(cur,{**q,'group_mode':'RESTATED'if q['group_mode']=='AS_SOLD'else'AS_SOLD'},key,actor),'CP7_ANALYSIS_REQUEST_CHANGED')
  plan.refused(cur,lambda:bounded.request(cur,today,key,actor),'CP7_ANALYSIS_REQUEST_CHANGED')
  # The old request remains callable for its own UUID and keeps v1 inputs.
  old_key=str(uuid.uuid4());old=bounded.request(cur,today,old_key,actor)
  plan.staged.checked(old,old_key,'RUNNING')
  old_row=plan.staged.job_row(cur,old_key,actor)
  assert old_row['reference']['bounded_request_contract']=='cp7.bounded-analysis-request.v1'
  plan.refused(cur,lambda:request(cur,q,old_key,actor),'CP7_ANALYSIS_REQUEST_CHANGED')
  bounded.finish(cur,dict(key=old_key,initial=old,row=old_row,subject=actor))
  w=bounded.work.get(cur,key,actor)
  assert w['contract_version']=='cp7.planning-schedule-staged-bounded.v2'and w['history_input_coverage']=='COMPLETE'and w['source_state']=='UNCHANGED'
  return dict(status='PASS',private_request_actual_Native_units_and_pages=True,unchanged_compiler_entire_JSON_exact=True,
   reference_immutable_pending=True,exact_replay_and_cross_method_refusals=True,old_v1_request_and_pages_complete=True,
   workspace_v2_complete_only_after_HIST_PREP=True,observations=deepcopy(observed),actual_Auth_HTTP_credit=False)
 def volume():
  install(cur);plan.fixture(cur,today);plan.b.api.admin(cur)
  base=native.bounded.work.base.retained.formula.sales.fg.base
  actor=native.policy.master.role_actor(cur,'OWNER');size=geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
  f=capture(cur,today,actor,observed);c=f['row']['reference']
  assert c['status']=='INCOMPLETE'and c['stock_raw_omitted']is True
  signature=geometry.dimensional_signature(c['facts']['products']);assert len(signature)==3600
  assert f['pages']['targets_total']==len(c['facts']['products'])==3602
  assert c['bounded_frozen_stock_summary']['raw_rows_read']==int(c['bounded_stock_reference']['row_count'])>=363600
  w=bounded.work.get(cur,f['key'],actor)
  assert w['source_state']=='UNCHANGED'and w['history_input_coverage']=='COMPLETE'
  return dict(size,status='PASS',actual_private_request_complete=True,all3602_targets_entire_compiler_JSON_exact=True,
   exact1200_SKUs_three_physical_sizes=True,all_actual_pages_verified=True,raw_INCOMPLETE_preserved=True,
   observations=deepcopy(observed),factory_SLA_claim=False,public_request_adopted=False,production_go=False)
 def stale():
  s=install(cur);x=plan.fixture(cur,today);actor=native.policy.master.role_actor(cur,'OWNER')
  f=capture(cur,today,actor,observed);old=deepcopy(f['original']);reference=deepcopy(f['row']['reference'])
  plan.b.api.admin(cur)
  try:stage.rollback_preuse(cur,s['current'])
  except ValueError as error:assert str(error)=='FROZEN_UNITS_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
  else:raise AssertionError('FROZEN_UNITS_USED_INVERSE_ACCEPTED')
  # Use the already qualified Native poster; never rewrite a posted clock.
  plan.found_fg(cur,x,'1')
  physical=plan.monetary_state(cur)
  after,pages,meta=plan.staged.fetch(cur,f['done']['run_id'],actor)
  assert after==old and plan.staged.job_row(cur,f['key'],actor)['reference']==reference
  w=bounded.work.get(cur,f['key'],actor);assert w['source_state']=='ARCHIVED_STALE'
  assert prepared_cache(cur,f['row']['id'])==f['cache']
  plan.b.api.admin(cur)
  removed=cur.execute('select cp7_analysis_stage.purge_intermediates(%s)',(f['row']['id'],)).fetchone()[0]
  assert removed['removed']['target_rows']>0 and coverage(cur,f['row']['id'])=='COMPLETE'
  assert plan.staged.fetch(cur,f['done']['run_id'],actor)[0]==old
  assert plan.monetary_state(cur)==physical
  return dict(status='PASS',actual_post_marks_source_stale=True,archived_pages_and_reference_exact=True,
   used_inverse_refused=True,existing_K3_cache_purge_keeps_pages_and_coverage=True,reader_no_ERP_write=True,
   observations=deepcopy(observed),production_go=False)
 def checked(fn):
  def run():
   observed.clear()
   try:return fn()
   except Exception as error:return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run
 return list(zip(IDS['native'],map(checked,(catalog,flow,volume,stale))))


def races(tools,today):return []
def http_cases(http,today):return []
