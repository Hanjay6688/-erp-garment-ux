"""Preserve two actual scoped model archives through full database recovery."""
from copy import deepcopy
import cp7_ow11_model_scoped_evaluation_cases as native


def stored(cur,run):
    native.plan.b.api.admin(cur)
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("set local TimeZone='UTC'")
    try:
        return native.stored(cur,run)
    finally:
        cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def prepare(cur,histories,report):
    before=native.plan.monetary_state(cur);held={}
    for kind,h in histories.items():
        actor=h['stored']['actor'];query=native.parent.query(h['result'],h['query'])
        result,_=native.capture(cur,query,actor,h['key'])
        row=stored(cur,result['run_id'])
        assert result['contract_version']=='cp7.scoped-model-run.v3'
        assert result['assessment']['activation']['state']=='BASELINE_REQUIRED'
        assert result['forecast_applied']is False
        assert row['input']['known_as_of']==h['result']['captured_at']
        assert result['assessment']['policy_source']['policy']['config']['allowed_methods']==[]
        native.history.same_archive(result,native.read(cur,result['run_id'],actor))
        native.history.same_archive(result,native.capture(cur,query,actor,h['key'])[0])
        assert stored(cur,result['run_id'])==row
        held[kind]=dict(actor=actor,query=deepcopy(query),key=h['key'],result=result,stored=row)
    assert native.plan.monetary_state(cur)==before
    report['scoped_model_before_full_used_backup']=dict(actual_Native_models=2,
        complete_immutable_input_result_payload=True,all_columns_UTC=True,
        actual_history_knowledge_clock=True,same_UUID_separate_history_model_namespace=True,
        explicit_synthetic_baseline_only_policy=True,no_stock_money_HPP_write=True,forecast_applied=False)
    return held


def assert_restored(cur,held,report,label,*,native_return_changed=False,policy_changed=False):
    before=native.plan.monetary_state(cur)
    for kind,row in held.items():
        current=native.read(cur,row['result']['run_id'],row['actor'])
        replay=native.capture(cur,row['query'],row['actor'],row['key'])[0]
        native.history.same_archive(row['result'],current)
        native.history.same_archive(row['result'],replay)
        changed=native_return_changed and kind=='NATIVE_RETURN_TARGET'
        for result in (current,replay):
            guard=result['current_guard']
            assert guard['engine_unchanged']is True
            assert guard['history_unchanged']is (not changed)
            assert guard['policy_unchanged']is (not policy_changed)
            assert result['forecast_applied']is False
            if changed:
                assert guard['reason']=='NATIVE_HISTORY_SOURCE_CHANGED'
            elif policy_changed:
                assert guard['reason']=='ACTIVATION_POLICY_CHANGED'
        assert stored(cur,row['result']['run_id'])==row['stored']
        if changed:
            assert native.plan.refusal(cur,lambda:native.capture(cur,row['query'],row['actor']))[0:2]==('P0001','CP7_SCOPED_EVALUATION_HISTORY_STALE')
        native.plan.b.api.admin(cur)
        assert cur.execute('select count(*)from cp7_model_scoped_evaluation.runs where actor=%s and request_id=%s',
            (row['actor'],row['key'])).fetchone()[0]==1
        report.setdefault('scoped_model_full_restore_checks',[]).append(dict(label=label,scope=kind,
            exact_immutable_input_assessment_payload=True,all_stored_columns_UTC_equal=True,
            actual_history_knowledge_clock_preserved=True,current_guard_kept_separate=True,
            history_unchanged=not changed,policy_unchanged=not policy_changed,
            same_UUID_one_row=True,no_stock_money_HPP_write=True,forecast_applied=False))
    assert native.plan.monetary_state(cur)==before
