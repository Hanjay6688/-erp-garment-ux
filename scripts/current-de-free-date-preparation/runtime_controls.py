"""Exact process/policy reuse and a pinned supervised workflow generator."""
from pathlib import Path
from hashlib import sha256
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGIN='927ee03213a80e854fda30779d824c5c617644bd'
PREFIX='scripts/current-complete-de-integration-preparation/'


def source_controls():
    records={}
    for name in ('runtime_supervisor.py','attempt_policy.py','retained_de_workflow.py'):
        source_name='workflow.py' if name=='retained_de_workflow.py' else name
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',ORIGIN+':'+PREFIX+source_name])
        value=raw.decode();changes=[]
        if name=='runtime_supervisor.py':
            changes=[('DE_RUNTIME_SUPERVISION.json','FREE_DATE_RUNTIME_SUPERVISION.json'),
                ("os.environ.get('COMPLETE_DE_CONFIRM')","os.environ.get('FREE_DATE_CONFIRM')"),
                ("os.environ['DE_JOB_START_MONOTONIC']","os.environ['FREE_DATE_JOB_START_MONOTONIC']")]
        for before,after in changes:
            if value.count(before)!=1:raise ValueError('FREE_DATE_SUPERVISION_EXACT_ROUTE_REQUIRED')
            value=value.replace(before,after,1)
        if value.encode()!=(HERE/name).read_bytes():raise ValueError('FREE_DATE_SUPERVISION_UNDECLARED_SOURCE_CHANGE:'+name)
        for before,after in reversed(changes):
            if value.count(after)!=1:raise ValueError('FREE_DATE_SUPERVISION_UNIQUE_REVERSE_REQUIRED')
            value=value.replace(after,before,1)
        if value.encode()!=raw:raise ValueError('FREE_DATE_SUPERVISION_ORIGINAL_NOT_RECOVERED')
        records[name]=dict(original_sha256=sha256(raw).hexdigest(),route_changes=len(changes))
    return dict(status='FREE_DATE_SUPERVISION_EXACT_REUSE_SOURCE_PASS',source_commit=ORIGIN,files=records,
        process_engine_unchanged=True,real_WIB_policy_unchanged=True,prior_process_controls_reused=10,
        retained_generator_matches_927=True,workflow_source_is_not_actual_parent_acceptance=True,
        actual_ERP_cases=0,production_go=False,independent_acceptance=False)


def receipt(p,value,head,run_id):
    p.fields(value,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=head,
        github_run_id=run_id,github_run_attempt='1',worker_exit=0,deadline_reached=False,
        external_signal=None,orphaned_child=False,process_group_empty=True,process_tree_empty=True,
        signals=[],actual_case_credit=0,production_go=False,job_budget_seconds=21600,
        work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600),
        'FREE_DATE_COMPLETE_OWNED_PROCESS_REAP_BEFORE_DATABASE_REMOVAL')
    return dict(status='FREE_DATE_SUPERVISION_ACCEPTED',actual_case_credit=0)
