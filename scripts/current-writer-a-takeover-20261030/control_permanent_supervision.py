"""Prepared-source/receipt controls, without activating a runtime or archive."""
from pathlib import Path
from unittest.mock import patch
import argparse
import copy
import json
import intake_permanent6 as target
from intake_common import GitBytes, exact, pin


def check(root):
    with GitBytes(root,target.PREPARED_HEAD,target.PREPARED_TREE) as g:
        source=target.source(g)
        exact(source['own_paths'],57 if target.PARENT_RECEIPT is not None else 56,'PERMANENT_SUPERVISED_EXACT_OWN_SOURCE_PATHS')
    for name in ('HEAD','TREE','RUN','JOB'):
        exact(getattr(target,name),None,'PERMANENT_RUNTIME_STILL_UNARMED:'+name)
    try:target.intake(None,None,None)
    except ValueError as error:
        if 'ACTIVATED_EXACT_RUN_INTAKE_NOT_YET_PINNED' not in str(error):raise
    else:raise AssertionError('UNARMED_PERMANENT_INTAKE_OPENED')
    try:target.supervision({})
    except ValueError as error:
        if 'ACTUAL_IDENTITY_PENDING' not in str(error):raise
    else:raise AssertionError('UNARMED_PERMANENT_SUPERVISION_OPENED')
    good=dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit='process-control-head',
        github_run_id='17',github_run_attempt='1',worker_exit=0,signals=[],deadline_reached=False,
        external_signal=None,orphaned_child=False,process_group_empty=True,process_tree_empty=True,
        job_budget_seconds=21600,work_budget_seconds=19800,recovery_reserve_seconds=1200,
        artifact_reserve_seconds=600,actual_case_credit=0,production_go=False)
    negative=[]
    with patch.object(target,'HEAD','process-control-head'),patch.object(target,'RUN',17):
        accepted=target.supervision(good)
        for key in good:
            bad=copy.deepcopy(good);bad.pop(key)
            try:target.supervision(bad)
            except (ValueError,KeyError):negative.append('missing:'+key)
            else:raise AssertionError('ACCEPTED_MISSING_SUPERVISION:'+key)
            bad=copy.deepcopy(good)
            bad[key]=[{'signal':'SIGINT'}] if key=='signals' else ('changed' if good[key] is None else None)
            try:target.supervision(bad)
            except (ValueError,KeyError):negative.append('changed:'+key)
            else:raise AssertionError('ACCEPTED_CHANGED_SUPERVISION:'+key)
        for key in ('deadline_reached','orphaned_child','process_group_empty','process_tree_empty','production_go'):
            bad=copy.deepcopy(good);bad[key]=int(good[key])
            try:target.supervision(bad)
            except ValueError:negative.append('integer-boolean:'+key)
            else:raise AssertionError('ACCEPTED_UNTYPED_SUPERVISION:'+key)
    return dict(status='ROOT_PERMANENT_SUPERVISION_CONTROLS_PASS',head=target.PREPARED_HEAD,
        tree=target.PREPARED_TREE,source=source,positive=1,negative_controls=negative,
        accepted=accepted,unarmed_before_archive_or_Git=True,actual_SQL_executed=0,
        actual_ERP_cases=0,production_go=False,independent_acceptance=False,
        root_intake_source=pin(Path(target.__file__).read_bytes()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check(a.source);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],positive=result['positive'],
        negative=len(result['negative_controls']),own_paths=result['source']['own_paths'],
        unarmed_before_archive_or_Git=True,actual_ERP_cases=0)))
