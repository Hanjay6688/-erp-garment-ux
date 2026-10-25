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
 target['inputs']['snapshot_id']='DISTINCT_CAPTURE_SNAPSHOT'
 return dict(target_key=row['target_key'],target=target,profile=row['profile'],
  demand_estimate=row['demand_estimate'],available_fg_pcs=row['available_fg_pcs'])


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


def capture(cur,today,actor):
 key=str(uuid.uuid4());start=monotonic();initial=bounded.request(cur,today,key,actor)
 elapsed=(monotonic()-start)*1000
 assert elapsed<8000,('MODEL_TARGET_V2_3600_REQUEST_OVER8S',elapsed)
 plan.staged.checked(initial,key,'RUNNING')
 row=plan.staged.job_row(cur,key,actor)
 f=dict(key=key,initial=initial,row=row,subject=actor,request_millis=round(elapsed,3))
 bounded.finish(cur,f)
 assert f['pages']['targets_total']==len(row['reference']['facts']['products'])>=3600
 assert row['reference']['status']=='INCOMPLETE'and row['reference']['stock_raw_omitted']is True
 assert int(row['reference']['bounded_stock_reference']['row_count'])>=363600
 return f


def cases(cur,today):
 native.PARENT_CHECKER=PARENT_CHECKER
 catalog=native.cases(cur,today)[0][1]
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
  old=capture(cur,today,actor)
  old_rows=old['row']['reference']['bounded_history_inputs']['inputs']['targets']
  old_domains={r['target_key']:target_domain(r)for r in old_rows}
  old_recommendations={r['target']['key']:recommendation_domain(r)for r in old['original']['analysis']['recommendations']}
  assert len(old_domains)==len(old_rows)==old['pages']['targets_total']
  old_frozen=cur.execute('select to_jsonb(r)from cp7_analysis_native.runs r where id=%s',(old['done']['run_id'],)).fetchone()[0]
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
  new=capture(cur,today,actor)
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
  assert cur.execute('select to_jsonb(r)from cp7_analysis_native.runs r where id=%s',(old['done']['run_id'],)).fetchone()[0]==old_frozen
  plan.found_fg(cur,x,'1');posted=plan.monetary_state(cur)
  assert plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(new['done']['run_id'],),actor)['source_state']=='ARCHIVED_STALE'
  assert plan.monetary_state(cur)==posted
  return dict(status='PASS',**size,actual_products=len(rows),actual_scoped_models=len(references),
   all_target_kernels_profile_observed_operands_exact=True,all_recommendation_quantity_states_values_units_reasons_exact=True,
   predecessor_complete=True,predecessor_request_millis=old['request_millis'],predecessor_step_millis=[c['ms']for c in old['calls']],
   current_request_millis=new['request_millis'],current_step_millis=[c['ms']for c in new['calls']],full_source_check_millis=timings,
   all_pages_verified=True,explicit_capture_clock_engine_refs_retained=True,old_result_immutable=True,
   raw_native_INCOMPLETE_preserved=True,actual_native_post_retires_source=True,no_business_write_by_analysis=True,
   statement_limit='8s',factory_SLA_claim=False,financial_capture='DEFERRED',official_finance_included=False,
   full_factory3600_qualified=False,actual_historical_positive_winner=False,after_use_restore_qualified=False,
   full_OW11_acceptance=False,full_OW12b_acceptance=False,production_go=False)
 return[(IDS['native'][0],catalog),(IDS['native'][1],scale)]


def races(tools,today):return []
def http_cases(http,today):return []
