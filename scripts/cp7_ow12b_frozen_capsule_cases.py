"""Closed Native4: actual frozen capture and unchanged compiler, no ERP route."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from time import monotonic
import json
import traceback
import cp7_frozen_analysis_v2 as capsule
import cp7_history_reference_binary_v2 as binary
import cp7_ow11_model_target_consumer_v2_cases as native
import cp7_ow11_model_target_v2_factory_cases as geometry
from cp7_ow04_restore_bundle import _catalog_rows

CONTRACT='cp7.ow12b.frozen-capsule-native4.v2'
IDS=dict(native=['OW12B_FROZEN_V2_CATALOG22_EXACT_PREUSE',
 'OW12B_FROZEN_V2_ACTUAL_CAPTURE_COMPILER_PARITY_AND_BINDINGS',
 'OW12B_FROZEN_V2_SYNTHETIC1200X3_CAPTURE_PREPARE_ALL_TARGET_PARITY',
 'OW12B_FROZEN_V2_ACTUAL_POST_FROZEN_INPUTS_UNCHANGED'])
REQUIRED=dict(native=4)
EXPECTED=DECLARED=4
FUNCTIONS,SCHEDULES,stage=native.FUNCTIONS,native.SCHEDULES,native.stage
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def sources():
 root=Path(__file__).resolve().parent
 paths=[Path(__file__),Path(geometry.__file__),Path(geometry.fixture.__file__),
  root/'cp7_ow12b_frozen_capsule_probe.py',root/'cp7_ow12b_frozen_capsule_preflight.py',
  root/'cp7_ow12b_frozen_capsule_local.mjs',root/'cp7_f05_analysis_probe.py']
 return {**native.sources(),**{'cp7_history_reference_binary_v2/'+k:v for k,v in binary.sources().items()},
  **{'cp7_frozen_analysis_v2/'+k:v for k,v in capsule.sources().items()},
  **{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()for p in paths}}


def install(cur):
 native.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(native,name,globals()[name])
 parents=native.install(cur)
 before=_catalog_rows(cur);bs=binary.install_delta(cur);binary.admit_catalog(before,_catalog_rows(cur),bs)
 before=_catalog_rows(cur);cs=capsule.install_delta(cur);capsule.admit_catalog(before,_catalog_rows(cur),cs)
 return dict(parents=parents,binary=bs,capsule=cs)


def call(cur,name,args=(),observed=None,phase=None):
 native.plan.b.api.admin(cur)
 prior=cur.execute('show statement_timeout').fetchone()[0]
 cur.execute('savepoint frozen_capsule_private_call');start=monotonic()
 try:
  cur.execute("set local statement_timeout='8s'");cur.execute('set local role cp7_capture')
  value=cur.execute('select '+name+'('+','.join(['%s']*len(args))+')',args).fetchone()[0]
 except Exception as error:
  elapsed=round((monotonic()-start)*1000,3)
  if observed is not None:observed['failed_call']=dict(phase=phase,name=name,millis=elapsed,sqlstate=getattr(error,'sqlstate',None),error=str(error))
  cur.execute('rollback to savepoint frozen_capsule_private_call');native.plan.b.api.admin(cur)
  cur.execute('release savepoint frozen_capsule_private_call');raise
 native.plan.b.api.admin(cur);cur.execute("select set_config('statement_timeout',%s,true)",(prior,))
 cur.execute('release savepoint frozen_capsule_private_call')
 elapsed=round((monotonic()-start)*1000,3)
 if observed is not None:observed.setdefault('ordered_calls',[]).append(dict(phase=phase,name=name,millis=elapsed))
 assert elapsed<8000,('FROZEN_CAPSULE_PRIVATE_CALL_OVER8S',name,elapsed)
 return value


def source(cur,q,observed=None,phase='CAPTURE_FROZEN',frozen=True):
 return call(cur,'cp7_frozen_analysis_v2.source',(json.dumps(q),frozen),observed,phase)


def prepare(cur,c,q,observed=None,phase='PREPARE_SEALED'):
 return call(cur,'cp7_frozen_analysis_v2.prepare',(json.dumps(c),json.dumps(q),5000),observed,phase)


def original_compile(cur,c,q,observed=None):
 raw=call(cur,'cp7_frozen_analysis_v2.base',(json.dumps(c),))
 summary=c['bounded_frozen_stock_summary']
 return call(cur,'cp7_history_bounded.compile',
  (json.dumps(raw),json.dumps(q),None if summary is None else json.dumps(summary),5000),observed,'UNCHANGED_COMPILER_SAME_ARGUMENTS')


def inputs_shape(c,result):
 assert c['bounded_request_contract']=='cp7.bounded-analysis-request.v2'
 assert c['bounded_reference_contract']=='cp7.bounded-analysis-reference.v2'
 assert c['bounded_capture_state']=='FROZEN'and c['bounded_input_coverage']=='PENDING'
 assert c['bounded_history_inputs']is None
 assert result['coverage']=='COMPLETE'and result['raw_native_capture_status']==c['status']
 assert result['raw_native_status_overridden']is False
 inputs=result['inputs'];products=c['facts']['products'];keys={p['root_id']+':'+p['size_id']for p in products}
 assert len(keys)==len(products)
 for name in('history','current_stock','targets'):
  assert len(inputs[name])==len(products)and {r['target_key']for r in inputs[name]}==keys
 assert inputs['products']==products and inputs['query']==c['bounded_query']and inputs['captured_at']==c['captured_at']


def cases(cur,today):
 observed={}
 def catalog():
  before=_catalog_rows(cur);s=install(cur);assert len(before)==22
  assert capsule.verify(cur,s['capsule'])['private_functions']==11
  capsule.rollback_preuse(cur,s['capsule']);binary.rollback_preuse(cur,s['binary']);native.unwind(cur,s['parents'])
  assert _catalog_rows(cur)==before
  return dict(status='PASS',private11_no_table_RPC_replacement=True,exact22_composed_inverse=True,
   unchanged_current_compiler_and_old_request=True,producer_dependencies_exact=True)
 def parity():
  install(cur);native.plan.fixture(cur,today);q=native.plan.staged.query(today)
  physical=native.plan.monetary_state(cur);c=source(cur,q,observed)
  assert c['status']=='COMPLETE'
  assert c['financial_source']is None and c['financial_capture']=='DEFERRED'
  expected=original_compile(cur,c,q,observed);actual=prepare(cur,c,q,observed)
  assert actual==expected;inputs_shape(c,actual)
  immutable=deepcopy(c)
  for change in('clock','fact','query','stock','producer','capsule','reference','coverage','compiled'):
   changed=deepcopy(c)
   if change=='clock':changed['captured_at']='2000-01-01T00:00:00.000000Z'
   elif change=='fact':changed['facts']['products'][0]['product_name']='changed'
   elif change=='query':changed['bounded_query']['group_mode']='RESTATED'if q['group_mode']=='AS_SOLD'else'AS_SOLD'
   elif change=='stock':changed['bounded_stock_reference']['rows_sha256']='e'*64
   elif change=='producer':changed['bounded_producer_hash']='e'*64
   elif change=='capsule':changed['bounded_capsule_hash']='e'*64
   elif change=='reference':changed['bounded_reference_contract']='cp7.bounded-analysis-reference.v1'
   elif change=='coverage':changed['bounded_input_coverage']='COMPLETE'
   else:changed['bounded_history_inputs']=actual
   state,message,_detail=native.plan.refusal(cur,lambda:prepare(cur,changed,q))
   assert state in('P0001','22023')and message.startswith(('CP7_FROZEN_','CP7_BOUNDED_')),(change,state,message)
  assert c==immutable and prepare(cur,c,q)==actual
  first=call(cur,'cp7_frozen_analysis_v2.work_fingerprint',(json.dumps(c),))
  fresh=source(cur,q,observed,'REFERENCE_ONLY',False)
  assert fresh['bounded_capture_state']=='REFERENCE_ONLY'and fresh['bounded_input_coverage']=='NOT_CAPTURED'
  assert call(cur,'cp7_frozen_analysis_v2.work_fingerprint',(json.dumps(fresh),))==first
  assert native.plan.monetary_state(cur)==physical
  return dict(status='PASS',actual_Native_capture=True,entire_current_compiler_JSON_identical=True,
   all_target_sets_exact=True,capsule_tampering_refused=9,raw_capture_and_PENDING_honest=True,
   immutable_source_and_old_v1_unchanged=True,reference_only_same_work_identity=True,
   reader_no_ERP_write=True,ordered_calls=deepcopy(observed['ordered_calls']),actual_Auth_HTTP_credit=False)
 def volume():
  install(cur);native.plan.fixture(cur,today);native.plan.b.api.admin(cur)
  base=native.bounded.work.base.retained.formula.sales.fg.base
  actor=native.policy.master.role_actor(cur,'OWNER');size=geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
  q=native.plan.staged.query(today);physical=native.plan.monetary_state(cur)
  c=source(cur,q,observed)
  assert c['status']=='INCOMPLETE'and c['stock_raw_omitted']is True
  signature=geometry.dimensional_signature(c['facts']['products']);assert len(signature)==3600
  assert int(c['bounded_stock_reference']['row_count'])>=363600
  assert c['bounded_frozen_stock_summary']['raw_rows_read']==int(c['bounded_stock_reference']['row_count'])
  expected=original_compile(cur,c,q,observed);actual=prepare(cur,c,q,observed)
  assert actual==expected;inputs_shape(c,actual)
  assert len(actual['inputs']['targets'])==len(c['facts']['products'])>=3600
  assert native.plan.monetary_state(cur)==physical
  return dict(size,status='PASS',actual_Native_qualification=True,
   actual_products=len(c['facts']['products']),actual_rows=int(c['bounded_stock_reference']['row_count']),
   actual_1200_commercial_SKUs_three_distinct_physical_sizes=True,all3600_physical_targets_once=True,
   every_compiled_JSON_field_quantity_operand_reason_reference_identical=True,
   raw_INCOMPLETE_and_frozen_PENDING_preserved=True,full_summary_count_matches_full_raw_reference=True,
   ordered_calls=deepcopy(observed['ordered_calls']),statement_limit='8s',request_or_unit_integrated=False,
   caller_latency_or_factory_SLA_qualified=False,official_finance_included=False,full_factory3600_qualified=False,production_go=False)
 def late():
  install(cur);x=native.plan.fixture(cur,today);q=native.plan.staged.query(today)
  c=source(cur,q,observed);old=prepare(cur,c,q,observed);immutable=deepcopy(c)
  native.plan.found_fg(cur,x,'1');physical=native.plan.monetary_state(cur)
  assert prepare(cur,c,q,observed,'PREPARE_AFTER_ACTUAL_POST')==old and c==immutable
  fresh=source(cur,q,observed,'CAPTURE_AFTER_ACTUAL_POST')
  assert fresh['bounded_stock_reference']['rows_sha256']!=c['bounded_stock_reference']['rows_sha256']
  old_fp=call(cur,'cp7_frozen_analysis_v2.work_fingerprint',(json.dumps(c),))
  fresh_fp=call(cur,'cp7_frozen_analysis_v2.work_fingerprint',(json.dumps(fresh),))
  assert old_fp!=fresh_fp and native.plan.monetary_state(cur)==physical
  return dict(status='PASS',actual_Native_post=True,prepare_after_post_uses_only_frozen_operands=True,
   entire_prepared_result_identical_after_post=True,old_capsule_immutable=True,new_full_stock_reference_changes=True,
   work_identity_changes=True,no_posted_row_or_date_rewrite=True,reader_no_ERP_write=True,
   ordered_calls=deepcopy(observed['ordered_calls']))
 def checked(fn):
  def run():
   observed.clear()
   try:return fn()
   except Exception as error:return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run
 return list(zip(IDS['native'],map(checked,(catalog,parity,volume,late))))


def races(tools,today):return []
def http_cases(http,today):return []
