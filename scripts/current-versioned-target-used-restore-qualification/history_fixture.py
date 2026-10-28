"""Retain both clocks and complete immutable rows for two actual Native roots."""
from copy import deepcopy
import uuid
import cp7_ow11_model_history_runtime_cases as native


def stored(cur,run):
    native.plan.b.api.admin(cur)
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("select set_config('TimeZone','UTC',true)")
    try:return native.stored(cur,run)
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def prepare(cur,today,analog_target,return_product,report):
    return_target=native.source.target(cur,return_product)
    assert analog_target!=return_target
    before=native.plan.monetary_state(cur);held={}
    for label,target in [('ANALOG_TARGET',analog_target),('NATIVE_RETURN_TARGET',return_target)]:
        query=dict(native.history.query(today,days=3),target_key=target);key=str(uuid.uuid4())
        result=native.capture(cur,query,key)
        assert result['current_guard']['source_state']=='UNCHANGED'
        assert result['history']['scope']=='SINGLE_CURRENT_PHYSICAL_ROOT'
        assert result['history']['training_known_at']==result['captured_at']
        native.same_archive(result,native.read(cur,result['run_id']))
        native.same_archive(result,native.capture(cur,query,key))
        held[label]=dict(query=deepcopy(query),key=key,result=result,stored=stored(cur,result['run_id']))
    assert native.plan.monetary_state(cur)==before
    report['scoped_history_before_full_used_backup']=dict(actual_Native_roots=2,
        immutable_all_columns_UTC=True,actual_capture_knowledge_times=True,
        original_physical_and_visible_clocks_retained=True,exact_UUID_replay=True,
        no_stock_money_HPP_write=True,forecast_applied=False)
    return held


def assert_restored(cur,held,report,label,*,native_return_changed=False):
    before=native.plan.monetary_state(cur)
    for kind,row in held.items():
        current=native.read(cur,row['result']['run_id'])
        replay=native.capture(cur,row['query'],row['key'])
        native.same_archive(row['result'],current);native.same_archive(row['result'],replay)
        changed=native_return_changed and kind=='NATIVE_RETURN_TARGET'
        expected='ARCHIVED_STALE'if changed else'UNCHANGED'
        assert current['current_guard']['source_state']==replay['current_guard']['source_state']==expected
        if changed:assert current['current_guard']['reason']=='CURRENT_SCOPED_SOURCE_CHANGED'
        assert stored(cur,row['result']['run_id'])==row['stored']
        native.plan.b.api.admin(cur)
        assert cur.execute('select count(*)from cp7_model_history_runtime.runs where actor=%s and request_id=%s',
            (row['stored']['actor'],row['key'])).fetchone()[0]==1
        report.setdefault('scoped_history_full_restore_checks',[]).append(dict(label=label,scope=kind,
            exact_immutable_source_result_payload_and_both_clocks=True,all_stored_columns_UTC_equal=True,
            current_guard_kept_separate=True,current_source_state=expected,same_UUID_one_row=True,
            no_stock_money_HPP_write=True,forecast_applied=False))
    assert native.plan.monetary_state(cur)==before
