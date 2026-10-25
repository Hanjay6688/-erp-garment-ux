"""Committed model metadata over existing Native history, without new ERP rows.

The explicit baseline-only policy is a labelled disposable test fixture, never
an owner production policy. Actual clocks are retained; no backdated history,
positive forecast winner, custom forecast or recalculated money is introduced.
"""
from copy import deepcopy
import uuid
import cp7_ow11_model_policy_cases as policy
import cp7_ow11_model_evaluation_v2_cases as evaluation
import cp7_model_native_cases as legacy

history=legacy.previous


def prepare(cur,today,query,target,report):
    before=policy.plan.monetary_state(cur)
    workspace=policy.get(cur,None)
    assert workspace['revision']=='0'and workspace['current']is None
    payload=policy.payload(cur,None)
    payload['config']['allowed_methods']=[]
    payload['reason']='Explicit SYNTHETIC used-restore baseline-only policy; not an owner factory setting'
    policy_key=str(uuid.uuid4());saved=policy.save(cur,payload,None,policy_key)
    assert saved['policy']['config']['allowed_methods']==[]and saved['policy']['state']=='ACTIVE'
    original=history.capture(cur,today,q=query)
    model_query=dict(history_run_id=original['run_id'],target_key=target,horizon_days='1')
    key=str(uuid.uuid4());v1=legacy.capture(cur,model_query,key);v1_row=legacy.stored(cur,v1['run_id'])
    v2=evaluation.capture(cur,model_query,key=key);v2_row=evaluation.stored(cur,v2['run_id'])
    assessment=v2['assessment']
    assert assessment['policy_source']['policy']==saved['policy']
    assert assessment['evaluation']is None and assessment['evaluation_state']=='NOT_REQUESTED_NO_ALLOWED_CHALLENGER'
    assert assessment['source']['history_run_id']==original['run_id']and assessment['source']['target_key']==target
    assert assessment['activation']['state']=='BASELINE_REQUIRED'and assessment['forecast_applied']is False
    assert assessment['automatic_activation']is False and assessment['apply_allowed']is False
    assert cur.execute('select %s::timestamptz<=%s::timestamptz',
        (saved['policy']['recorded_at'],assessment['source']['known_as_of'])).fetchone()[0]
    evaluation.unchanged(v2,evaluation.capture(cur,model_query,key=key))
    assert evaluation.stored(cur,v2['run_id'])==v2_row
    assert legacy.capture(cur,model_query,key)==v1 and legacy.stored(cur,v1['run_id'])==v1_row
    assert policy.save(cur,payload,None,policy_key)==saved
    assert policy.plan.monetary_state(cur)==before
    tables=policy.state(cur)
    report['model_before_full_used_backup']=dict(actual_Native_history=True,history_not_backdated=True,
        explicit_synthetic_baseline_only_policy=True,source_header_preserved_without_fake_backtest=True,
        same_UUID_v1_and_v2_separate=True,immutable_v1_and_v2=True,forecast_applied=False,
        no_physical_stock_money_HPP_write=True)
    return dict(query=model_query,key=key,v1=v1,v1_row=v1_row,v2=v2,v2_row=v2_row,
        policy_key=policy_key,policy_payload=payload,policy_saved=saved,policy_tables=tables)


def assert_restored(cur,held,report,label,*,source_changed=False,policy_changed=False):
    before=policy.plan.monetary_state(cur)
    v2=evaluation.read(cur,held['v2']['run_id']);evaluation.unchanged(held['v2'],v2)
    replay=evaluation.capture(cur,held['query'],key=held['key']);evaluation.unchanged(held['v2'],replay)
    assert evaluation.stored(cur,held['v2']['run_id'])==held['v2_row']
    assert legacy.stored(cur,held['v1']['run_id'])==held['v1_row']
    assert policy.save(cur,held['policy_payload'],None,held['policy_key'])==held['policy_saved']
    assert v2['current_guard']['engine_unchanged']is True
    if source_changed:
        assert v2['current_guard']['history_unchanged']is False
        assert v2['current_guard']['reason']=='NATIVE_HISTORY_SOURCE_CHANGED'
        assert policy.plan.refusal(cur,lambda:evaluation.capture(cur,held['query']))[1]=='CP7_MODEL_V2_HISTORY_STALE'
    if policy_changed:assert v2['current_guard']['policy_unchanged']is False
    for table in('cp7_model_native.runs','cp7_model_registry_adapter.runs'):
        assert cur.execute('select count(*)from '+table+' where request_id=%s',(held['key'],)).fetchone()[0]==1
    if not policy_changed:assert policy.state(cur)==held['policy_tables']
    assert policy.plan.monetary_state(cur)==before
    report.setdefault('model_full_restore_checks',[]).append(dict(label=label,
        exact_immutable_v1_v2_input_assessment_payload=True,old_UUID_no_duplicate=True,
        old_policy_receipt_exact=True,current_guard=deepcopy(v2['current_guard']),
        no_physical_stock_money_HPP_write=True,forecast_applied=False))


def suspend(cur,held,report):
    before=policy.plan.monetary_state(cur)
    payload=policy.payload(cur,None)
    payload.update(action='SUSPEND',config=None,template_hash=None,
        reason='Explicit SYNTHETIC post-restore policy withdrawal')
    saved=policy.save(cur,payload,None)
    assert saved['policy']['state']=='SUSPENDED'and saved['policy']['revision']=='2'
    current=evaluation.read(cur,held['v2']['run_id']);evaluation.unchanged(held['v2'],current)
    assert current['current_guard']['policy_unchanged']is False
    assert evaluation.stored(cur,held['v2']['run_id'])==held['v2_row']
    assert policy.plan.monetary_state(cur)==before
    report['model_policy_withdrawal_after_restore']=dict(append_only_revision='2',
        old_assessment_immutable=True,current_guard_refuses_policy=True,forecast_applied=False,
        no_physical_stock_money_HPP_write=True)
    return saved
