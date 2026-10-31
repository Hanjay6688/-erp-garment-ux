"""Bind only DE-specific routing to the unchanged tested process controller."""
from pathlib import Path
from hashlib import sha256
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGIN='e6684b07f98d753b5f78b24c7af52cd981971c0c'
PREFIX='scripts/current-s03-sku-s05-composite-qualification/'


def source_controls():
    records={}
    for name in ('runtime_supervisor.py','attempt_policy.py'):
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',ORIGIN+':'+PREFIX+name])
        value=raw.decode();changes=[]
        if name=='runtime_supervisor.py':
            changes=[('JOIN_RUNTIME_SUPERVISION.json','DE_RUNTIME_SUPERVISION.json'),
                ("os.environ.get('JOIN_CONFIRM')","os.environ.get('COMPLETE_DE_CONFIRM')"),
                ("os.environ['JOIN_JOB_START_MONOTONIC']","os.environ['DE_JOB_START_MONOTONIC']")]
        for before,after in changes:
            if value.count(before)!=1:raise ValueError('DE_SUPERVISION_EXACT_ROUTE_REQUIRED')
            value=value.replace(before,after,1)
        if value.encode()!=(HERE/name).read_bytes():raise ValueError('DE_SUPERVISION_UNDECLARED_SOURCE_CHANGE:'+name)
        for before,after in reversed(changes):
            if value.count(after)!=1:raise ValueError('DE_SUPERVISION_UNIQUE_REVERSE_REQUIRED')
            value=value.replace(after,before,1)
        if value.encode()!=raw:raise ValueError('DE_SUPERVISION_ORIGINAL_NOT_RECOVERED')
        records[name]=dict(original_sha256=sha256(raw).hexdigest(),route_changes=len(changes))
    return dict(status='DE_SUPERVISION_EXACT_REUSE_SOURCE_PASS',source_commit=ORIGIN,files=records,
        process_engine_unchanged=True,real_WIB_policy_unchanged=True,prior_process_controls_reused=10,
        actual_ERP_cases=0,production_go=False,independent_acceptance=False)


def receipt(p,value,head,run_id):
    p.fields(value,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=head,
        github_run_id=run_id,github_run_attempt='1',worker_exit=0,deadline_reached=False,
        external_signal=None,orphaned_child=False,process_group_empty=True,process_tree_empty=True,
        signals=[],actual_case_credit=0,production_go=False,job_budget_seconds=21600,
        work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600),
        'DE_COMPLETE_OWNED_PROCESS_REAP_BEFORE_DATABASE_REMOVAL')
    return dict(status='DE_SUPERVISION_ACCEPTED',actual_case_credit=0)
