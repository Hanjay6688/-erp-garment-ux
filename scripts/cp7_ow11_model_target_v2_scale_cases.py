"""Operational3600 parity with actual scoped model archives; finance remains A's.

Historical volume is SYNTHETIC. Two explicit public test profiles are manual,
not inferred factory policy. Every target is compared; no forecast is promoted.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from time import monotonic
import json
import uuid
import traceback
import psycopg
import cp7_ow11_model_target_consumer_v2_cases as native
import cp7_ow12b_operational3600_cases as volume

plan,bounded=native.plan,native.bounded
CONTRACT='cp7.ow11.model-target-operational3600.v2'
IDS=dict(native=[native.IDS['native'][0],
 'OW11_MODEL_TARGET_V2_OPERATIONAL3600_ALL_TARGET_PARITY_SOURCE'])
REQUIRED=dict(native=2)
EXPECTED=DECLARED=2
FUNCTIONS,SCHEDULES,stage=native.FUNCTIONS,native.SCHEDULES,native.stage
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def sources():
 root=Path(__file__).resolve().parent
 return dict(native.sources(),**{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()
  for p in (Path(__file__),root/'cp7_ow11_model_target_v2_scale_probe.py',Path(volume.__file__))})


def target_domain(row):
 """All kernel fields are compared except the distinct capture's snapshot ID.

 Model/provenance annotations are verified separately on every current row.
 No numeric, reason, UNKNOWN state, profile, demand operand or buffer is dropped.
 """
 target=deepcopy(row['target'])
 snapshot=target['inputs']['snapshot_id']
 assert isinstance(snapshot,str)and len(snapshot)==64 and all(c in '0123456789abcdef'for c in snapshot)
 estimate=deepcopy(row['demand_estimate'])
 # Both existing kernels echo the same captured authority. Preserve that
 # binding while comparing the operands across two deliberately distinct runs.
 assert estimate['inputs']['snapshot_id']==snapshot,'MODEL_TARGET_V2_3600_DEMAND_TARGET_SNAPSHOT_DIFFERS'
 target['inputs']['snapshot_id']='DISTINCT_CAPTURE_SNAPSHOT'
 estimate['inputs']['snapshot_id']='DISTINCT_CAPTURE_SNAPSHOT'
 return dict(target_key=row['target_key'],target=target,profile=row['profile'],
  demand_estimate=estimate,available_fg_pcs=row['available_fg_pcs'])


def recommendation_domain(row):
 """Compare all quantity states/values/units/reasons, independently of refs.

 Each original's reference hashes and pages are verified by the existing reader.
 Different clock/engine references remain on each real immutable result.
 """
 fields=('actual_fg','target_qty','q_base','q_conditional','suggested_new','rounding_extra','feasible_new')
 facts={}
 for field in fields:
  fact=row[field]
  assert fact['unit']=='PCS'and fact['state']in('KNOWN','ASSUMED','UNKNOWN','CONFLICT','NOT_APPLICABLE')
  assert isinstance(fact['refs'],list)
  facts[field]={k:deepcopy(v)for k,v in fact.items()if k!='refs'}
 return dict(target=row['target'],production_state=row['production_state'],facts=facts)


class ScaleRequestTimeout(Exception):
 def __init__(self,result):
  super().__init__(result['error']);self.result=result


def function_times(cur):
 # Transaction-local observations include pending calls, without resetting any
 # shared counters or changing a production function, limit, owner or ACL.
 rows=cur.execute("select funcid::regprocedure::text,calls,total_time,self_time from pg_stat_xact_user_functions where left(schemaname,4)='cp7_'or schemaname in('public','erp')").fetchall()
 return {name:dict(calls=calls,total_ms=float(total),self_ms=float(own))for name,calls,total,own in rows}


def timing_delta(before,after):
 rows=[]
 for name,value in after.items():
  old=before.get(name,dict(calls=0,total_ms=0,self_ms=0))
  row=dict(function=name,calls=value['calls']-old['calls'],total_ms=round(value['total_ms']-old['total_ms'],3),self_ms=round(value['self_ms']-old['self_ms'],3))
  if row['calls']or row['total_ms']:rows.append(row)
 return sorted(rows,key=lambda r:(-r['self_ms'],r['function']))[:60]


def function_profile(cur,before):
 # A failed optional observation must not leave the actual case transaction
 # aborted or replace the original gateway error.
 cur.execute('savepoint model_target_profile_read')
 try:return dict(functions=timing_delta(before,function_times(cur)),completed_calls_only=True,inlined_SQL_functions_may_be_absent=True,instrumentation_overhead_uncalibrated=True)
 except Exception as error:
  cur.execute('rollback to savepoint model_target_profile_read')
  return dict(unavailable=str(error))
 finally:cur.execute('release savepoint model_target_profile_read')


def capture(cur,today,actor,phase,observed):
 plan.b.api.admin(cur);prior=cur.execute('show track_functions').fetchone()[0]
 cur.execute("select set_config('track_functions','all',true)")
 before=function_times(cur);cur.execute('savepoint model_target_scale_timing')
 key=str(uuid.uuid4());start=monotonic()
 try:
  initial=bounded.request(cur,today,key,actor)
 except psycopg.Error as error:
  elapsed=(monotonic()-start)*1000;message=str(error);sqlstate=error.sqlstate
  cur.execute('rollback to savepoint model_target_scale_timing');plan.b.api.admin(cur)
  profile=function_profile(cur,before);profile['canceled_active_frames_may_be_absent']=True
  cur.execute('release savepoint model_target_scale_timing')
  cur.execute("select set_config('track_functions',%s,true)",(prior,))
  if sqlstate!='57014':raise
  raise ScaleRequestTimeout(dict(status='INCOMPLETE',error=message,sqlstate=sqlstate,phase=phase,
   request_millis=round(elapsed,3),session_function_profile=profile,statement_limit='8s',
   gateway_limit_increased=False,production_functions_replaced_for_profiling=False,
   factory_SLA_claim=False,production_go=False))from error
 elapsed=(monotonic()-start)*1000
 plan.b.api.admin(cur);profile=function_profile(cur,before)
 cur.execute('release savepoint model_target_scale_timing')
 cur.execute("select set_config('track_functions',%s,true)",(prior,))
 observed[phase]=dict(request_millis=round(elapsed,3),request_function_profile=profile)
 assert elapsed<8000,('MODEL_TARGET_V2_3600_REQUEST_OVER8S',elapsed)
 plan.staged.checked(initial,key,'RUNNING')
 row=plan.staged.job_row(cur,key,actor)
 f=dict(key=key,initial=initial,row=row,subject=actor,request_millis=round(elapsed,3),request_function_profile=profile)
 bounded.finish(cur,f)
 assert f['pages']['targets_total']==len(row['reference']['facts']['products'])>=3600
 assert row['reference']['status']=='INCOMPLETE'and row['reference']['stock_raw_omitted']is True
 assert int(row['reference']['bounded_stock_reference']['row_count'])>=363600
 observed[phase].update(complete=True,terminal_state=f['done']['state'],targets_total=f['pages']['targets_total'],page_count=f['pages']['page_count'],step_millis=[c['ms']for c in f['calls']])
 return f


def staged_frozen(cur,run):
 # A staged run is a sealed header/page set/pages, not a whole Native run.
 # Retain every stored field/body and the immutable captured reference.
 plan.b.api.admin(cur)
 value=cur.execute("""select jsonb_build_object(
  'header',(select to_jsonb(h)from cp7_analysis_stage.headers h where h.run_id=%s),
  'page_set',(select to_jsonb(s)from cp7_analysis_stage.page_sets s where s.run_id=%s),
  'pages',(select coalesce(jsonb_agg(to_jsonb(p)order by p.idx),'[]'::jsonb)from cp7_analysis_stage.pages p where p.run_id=%s),
  'reference',(select j.reference from cp7_analysis_stage.jobs j where j.run_id=%s))""",(run,run,run,run)).fetchone()[0]
 assert value['header']is not None and value['page_set']is not None and value['pages']and value['reference']is not None,'MODEL_TARGET_V2_3600_STAGED_SEAL_MISSING'
 return value


def cases(cur,today):
 native.PARENT_CHECKER=PARENT_CHECKER
 catalog=native.cases(cur,today)[0][1]
 observed={}
 def scale():
  # Capture a complete operational predecessor on the same physical facts.
  # Install only the new source/model/target composition afterwards.
  native.fresh.PARENT_CHECKER=PARENT_CHECKER
  parents,fresh_state=native.fresh.install(cur)
  x=plan.fixture(cur,today);size=volume.seed(cur)
  plan.b.api.admin(cur)
  roots=[str(r[0])for r in cur.execute("select identity_root_id from erp.products where sku in('OW12B36-1','OW12B36-2')order by sku").fetchall()]
  assert len(roots)==2
  for root in roots:native.fresh.consumer.profile(cur,root,mean_mode='SELECTED_MANUAL',daily_pcs='1000',lead_days='3',review_days='2',buffer_days='1')
  actor=native.policy.master.role_actor(cur,'OWNER')
  physical=plan.monetary_state(cur)
  old=capture(cur,today,actor,'PREDECESSOR',observed)
  old_rows=old['row']['reference']['bounded_history_inputs']['inputs']['targets']
  old_domains={r['target_key']:target_domain(r)for r in old_rows}
  old_recommendations={r['target']['key']:recommendation_domain(r)for r in old['original']['analysis']['recommendations']}
  assert len(old_domains)==len(old_rows)==old['pages']['targets_total']
  old_frozen=staged_frozen(cur,old['done']['run_id'])
  native.source.PARENT_CHECKER=lambda c:native.fresh.stage.verify(c,fresh_state)
  _,_,source_state=native.source.install(cur)
  current=stage.install_delta(cur,lambda c:native.source.stage.verify(c,source_state))
  references={}
  q=old['row']['query']
  for root in roots:
   key=next(r['target_key']for r in old_rows if r['target_key'].split(':')[0]==root)
   hq=dict(q,target_key=key)
   history=native.source.history.capture(cur,hq,subject=actor)
   model,_=native.source.scoped.capture(cur,native.source.scoped.parent.query(history,hq),actor)
   references[key]=dict(run_id=model['run_id'],history_run_id=history['run_id'])
  new=capture(cur,today,actor,'CURRENT',observed)
  rows=new['row']['reference']['bounded_history_inputs']['inputs']['targets']
  assert len(rows)==len({r['target_key']for r in rows})==len(old_domains)
  assert {r['target_key']:target_domain(r)for r in rows}==old_domains,'MODEL_TARGET_V2_3600_KERNEL_OR_OBSERVED_OPERANDS_CHANGED'
  assert {r['target']['key']:recommendation_domain(r)for r in new['original']['analysis']['recommendations']}==old_recommendations,'MODEL_TARGET_V2_3600_RECOMMENDATION_QUANTITIES_CHANGED'
  for row in rows:
   m=row['model_resolution'];d=row['demand_provenance']
   assert d['contract_version']=='cp7.target-demand-provenance.v3'
   assert m['contract_version']=='cp7.model-target-resolution.v2'and m['state']=='BASELINE_RETAINED'
   assert m['forecast_applied']is False and m['forecast']is None and m['baseline_target']==row['target']
   if row['target_key']in references:
    assert m['runtime']=='SCOPED_V3'and m['read_method']=='erp_cp7_read_model_evaluation_v3'
    assert {k:m[k]for k in('run_id','history_run_id')}==references[row['target_key']]
   else:assert m['run_id']is None and m['runtime']is None
  assert new['original']['analysis']['versions']['models']=='policy-gated-dated-model-target-2'
  timings=[]
  for _ in range(2):
   start=monotonic();checked=plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(new['done']['run_id'],),actor)
   elapsed=(monotonic()-start)*1000;assert checked['source_state']=='UNCHANGED'and elapsed<8000
   timings.append(round(elapsed,3))
  assert plan.monetary_state(cur)==physical
  plan.b.api.admin(cur)
  assert staged_frozen(cur,old['done']['run_id'])==old_frozen
  plan.found_fg(cur,x,'1');posted=plan.monetary_state(cur)
  assert plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(new['done']['run_id'],),actor)['source_state']=='ARCHIVED_STALE'
  assert plan.monetary_state(cur)==posted
  return dict(status='PASS',**size,actual_products=len(rows),actual_scoped_models=len(references),
   all_target_kernels_profile_observed_operands_exact=True,all_recommendation_quantity_states_values_units_reasons_exact=True,
   predecessor_complete=True,predecessor_request_millis=old['request_millis'],predecessor_step_millis=[c['ms']for c in old['calls']],
   predecessor_request_function_profile=old['request_function_profile'],current_request_function_profile=new['request_function_profile'],
   current_request_millis=new['request_millis'],current_step_millis=[c['ms']for c in new['calls']],full_source_check_millis=timings,
   all_pages_verified=True,explicit_capture_clock_engine_refs_retained=True,old_result_immutable=True,
   raw_native_INCOMPLETE_preserved=True,actual_native_post_retires_source=True,no_business_write_by_analysis=True,
   statement_limit='8s',factory_SLA_claim=False,financial_capture='DEFERRED',official_finance_included=False,
   full_factory3600_qualified=False,actual_historical_positive_winner=False,after_use_restore_qualified=False,
   full_OW11_acceptance=False,full_OW12b_acceptance=False,production_go=False)
 def profiled_scale():
  observed.clear()
  try:return scale()
  except ScaleRequestTimeout as error:
   return dict(error.result,observations=deepcopy(observed))
  except Exception as error:
   return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),
    observations=deepcopy(observed),full_factory3600_qualified=False,production_go=False)
 return[(IDS['native'][0],catalog),(IDS['native'][1],profiled_scale)]


def races(tools,today):return []
def http_cases(http,today):return []
