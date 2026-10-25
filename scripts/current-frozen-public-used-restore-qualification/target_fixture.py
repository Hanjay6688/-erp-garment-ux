"""Actual baseline target history, with current source state kept separate."""
from copy import deepcopy
import uuid
import cp7_ow11_model_target_consumer_v2_cases as native


def stored(cur,run):
    native.plan.b.api.admin(cur)
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("select set_config('TimeZone','UTC',true)")
    try:return native.fresh.stored(cur,run)
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def prepare(cur,query,target,report):
    before=native.plan.monetary_state(cur);key=str(uuid.uuid4())
    result=native.capture(cur,query,key)
    assert result['contract_version']=='cp7.native-baseline.v4'and result['source_state']=='UNCHANGED'
    row=next(x for x in result['rows']if x['target_key']==target)
    assert row['target']['target_pcs']=='1'
    assert row['demand_provenance']['contract_version']=='cp7.target-demand-provenance.v3'
    assert row['model_resolution']['state']=='BASELINE_RETAINED'
    assert row['model_resolution']['forecast']is None
    assert native.read(cur,result['run_id'])==result and native.capture(cur,query,key)==result
    frozen=stored(cur,result['run_id'])
    assert native.plan.monetary_state(cur)==before
    report['dated_target_before_full_used_backup']=dict(actual_Native_baseline_v4=True,
        actual_provenance_v3=True,baseline_retained_target='1',forecast_applied=False,
        exact_UUID_replay=True,no_stock_money_HPP_write=True)
    return dict(key=key,query=deepcopy(query),result=result,stored=frozen)


def assert_restored(cur,held,report,label,*,source_changed):
    before=native.plan.monetary_state(cur)
    current=native.read(cur,held['result']['run_id'])
    replay=native.capture(cur,held['query'],held['key'])
    assert replay==current
    assert {k:v for k,v in current.items()if k!='source_state'}=={k:v for k,v in held['result'].items()if k!='source_state'}
    assert current['source_state']==('ARCHIVED_STALE'if source_changed else'UNCHANGED')
    assert stored(cur,held['result']['run_id'])==held['stored']
    native.plan.b.api.admin(cur)
    assert cur.execute('select count(*)from cp7_baseline_native.runs where request_id=%s',(held['key'],)).fetchone()[0]==1
    assert native.plan.monetary_state(cur)==before
    report.setdefault('dated_target_full_restore_checks',[]).append(dict(label=label,
        exact_all_stored_columns_UTC=True,exact_old_target_provenance_and_model_input=True,
        only_current_source_state_separate=True,current_source_state=current['source_state'],
        same_UUID_one_baseline_run=True,no_stock_money_HPP_write=True,forecast_applied=False))
