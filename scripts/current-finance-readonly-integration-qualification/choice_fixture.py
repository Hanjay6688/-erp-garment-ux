"""One queued preparation completed only by the real minute scheduler.

The already-completed source analysis is a retained Native fixture. Its manual
fixture steps precede the measured schedule and are disclosed separately.
"""
from copy import deepcopy
import cp7_ow12b_choice_preparation_cases as B
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location('readonly_choice_work_observer',Path(__file__).with_name('work_observer.py'))
observer=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(observer)


def work_snapshot(cur,f,observations):
    return observer.read(cur,lambda:B.work(cur,f),observations)


def prepare(cur,today):
    observations={}
    f=B.parent.prepare(cur,today,observations)
    B.reader.purge(cur,f)
    first=B.call(cur,'request',f,observations)
    assert first['state']=='QUEUED' and first['units_done']==0
    assert B.call(cur,'request',f,observations)==first
    assert B.call(cur,'get',f,observations)==first
    work=work_snapshot(cur,f,observations)
    assert work['payload']is None and work['attempts']==0
    before=dict(metadata=B.choice.metadata(cur),money=B.plan.monetary_state(cur))
    return dict(f=f,before=before,work=work,first=first,observations=observations,
        source_fixture_manual_steps=len(f['calls']))


def state(cur,prepared):
    rows=cur.execute('select state from cp7_frozen_choice_preparation.work where job_id=%s',
        (prepared['work']['job_id'],)).fetchall()
    assert len(rows)==1,'CHOICE_CRON_WORK_IDENTITY_LOST'
    return rows[0][0]


def verified(cur,prepared):
    f=prepared['f'];observations=prepared['observations'];initial=prepared['work']
    ready=B.call(cur,'get',f,observations)
    assert ready['state']=='READY' and ready['units_done']==ready['unit_count']==1
    work=work_snapshot(cur,f,observations)
    assert work['job_id']==initial['job_id'] and work['created_at']==initial['created_at']
    assert work['payload']['inputs']==f['expected']
    assert work['attempts']==0
    assert B.call(cur,'request',f,observations)==ready
    assert B.call(cur,'get',f,observations)==ready
    assert work_snapshot(cur,f,observations)==work,'REPLAY_CHANGED_COMPLETED_CHOICE_WORK'
    assert B.choice.metadata(cur)==prepared['before']['metadata']
    assert B.plan.monetary_state(cur)==prepared['before']['money']
    assert all(c['phase'] in ('request','get')for c in observations.get('calls',[]))
    return dict(state='READY',source_request=f['key'],job_id=work['job_id'],
        same_work_on_reopen_and_replay=True,whole_inputs_equal_original_compiler=True,
        manual_preparation_steps=0,fixture_source_analysis_manual_steps=prepared['source_fixture_manual_steps'],
        fixture_steps_precede_measured_schedule=True,choice_not_saved=True,
        money_stock_HPP_unchanged=True,calls=deepcopy(observations.get('calls',[])),
        work_reads=deepcopy(observations['work_reads']))
