"""Committed bounded work receipt, real DONE snapshot and checked draft.

Only public Native fixture/business commands create these rows. Expiration
uses the retained labelled K2 finish-time fixture inside a rolled-back control.
"""
from datetime import timedelta
import uuid
import cp7_ow13c_bounded_stage_cases as bounded
import cp7_ow13c_checked_cases as checked
import cp7_k2_retention_cases as retention
from cp7_ow04_restore_bundle import _data,_catalog_rows

plan=bounded.plan


def create(cur,today):
    f=bounded.prepare(cur,today)
    workspace,payload=bounded.work_payload(cur,f)
    work_key=str(uuid.uuid4());work_result=bounded.work.save(cur,payload,work_key)
    assert work_result['bounded_request_contract']==bounded.stage.source.REQUEST
    # The changed calendar requires a new real snapshot, never reusing the old.
    key=str(uuid.uuid4());initial=bounded.request(cur,today,key)
    current=dict(f,key=key,initial=initial,row=plan.staged.job_row(cur,key))
    bounded.finish(cur,current)
    options,query,draft_payload=plan.draft_payload(cur,f['x'],current['done']['run_id'])
    checked_payload=checked.payload(dict(payload=draft_payload))
    physical=plan.monetary_state(cur);draft_key=str(uuid.uuid4())
    draft=checked.save(cur,checked_payload,draft_key)
    assert draft['state']=='SAVED'and draft['cutting_save_guard']['feasible']is True
    assert plan.monetary_state(cur)==physical
    plan.b.api.admin(cur)
    return dict(work_key=work_key,work_payload=payload,work_result=work_result,
        request=key,job=plan.staged.job_row(cur,key),run=current['done']['run_id'],
        original=current['original'],pages=current['pages'],page_meta=current['page_meta'],
        draft_key=draft_key,draft_payload=checked_payload,draft=draft,
        draft_read=plan.read(cur,draft['draft_id']),
        record=dict(actual_bounded_job_done=True,actual_work_receipt=True,actual_checked_draft=True,
            no_stock_money_HPP_write_by_draft=True,source_request=key,work_request=work_key,
            checked_request=draft_key,operational_steps=len(current['calls'])))


def after_restore(cur,f):
    assert plan.staged.job_row(cur,f['request'])==f['job']
    original,pages,meta=plan.staged.fetch(cur,f['run'])
    assert original==f['original']and pages==f['pages']and meta==f['page_meta']
    assert plan.read(cur,f['draft']['draft_id'])==f['draft_read']
    held=_data(cur)
    assert bounded.work.save(cur,f['work_payload'],f['work_key'])==f['work_result']
    assert checked.save(cur,f['draft_payload'],f['draft_key'])==f['draft']
    assert _data(cur)==held
    return dict(bounded_reference_header_pages_all_exact=True,work_receipt_exact_replay=True,
        checked_draft_exact_replay=True,all_rows_sequences_unchanged_by_replays=True)


def purge_guard(cur,f,product,state):
    cur.execute('savepoint bounded_purge_guard')
    try:
        retention.age(cur,f['run'],timedelta(days=8))
        purged=retention.purge(cur)
        assert any(x['job_id']==str(f['job']['id'])for x in purged['purged'])
        # The saved business draft remains and does not become unused merely
        # because temporary analysis material was expired/purged.
        assert plan.read(cur,f['draft']['draft_id'])==f['draft_read']
        before=_data(cur);catalog=_catalog_rows(cur)
        try:product.rollback_preuse(cur,state)
        except ValueError as error:assert str(error)==product.USED_ERROR
        else:raise AssertionError('BOUNDED_PURGED_INSTALLATION_REMOVED')
        assert _data(cur)==before and _catalog_rows(cur)==catalog
        return dict(actual_K2_purge=True,used_guard_still_before_DDL=True,
            saved_draft_retained=True,synthetic_fixture='K2 finished timestamp minus8days only')
    finally:
        cur.execute('rollback to savepoint bounded_purge_guard')
        cur.execute('release savepoint bounded_purge_guard')
