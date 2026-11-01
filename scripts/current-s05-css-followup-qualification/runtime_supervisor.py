"""Use the unchanged subreaper with a distinct hard 120-minute job budget."""
from pathlib import Path
import importlib.util,json,math,os,subprocess,sys,time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp6-proof/t3/S05_FOLLOWUP_SUPERVISION.json'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def remaining(job_start,now,work):
    if not math.isfinite(job_start)or not math.isfinite(now)or not 0<job_start<=now:
        raise ValueError('FOCUSED_REAL_JOB_START_REQUIRED')
    budget=job_start+work-now
    if budget<=0:raise ValueError('FOCUSED_RUNTIME_BUDGET_EXHAUSTED_BEFORE_START')
    return budget

def main():
    if sys.argv[1:]==['--allow-database-stop']:
        if OUT.exists()and json.loads(OUT.read_text()).get('process_tree_empty')is not True:
            raise ValueError('FOCUSED_DATABASE_STOP_REFUSED_WHILE_RUNTIME_MAY_BE_ALIVE')
        return 0
    if sys.argv[1:]:raise ValueError('FOCUSED_FIXED_OWNING_RUNTIME_COMMAND_ONLY')
    if os.environ.get('JOIN_CONFIRM')!='cp6_rollback':raise ValueError('FOCUSED_EXPLICIT_DISPOSABLE_ONLY')
    policy=load('focused_declared_hard_budget',HERE/'attempt_policy.py')
    policy.require_window()
    budget=remaining(float(os.environ['JOIN_JOB_START_MONOTONIC']),time.monotonic(),policy.WORK_SECONDS)
    original=load('focused_unchanged_process_tree_subreaper',HERE.parent/'current-s03-sku-s05-composite-qualification/runtime_supervisor.py')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(dict(status='RUNTIME_STARTING',process_tree_empty=False))+'\n')
    try:
        result=original.supervise([sys.executable,'-u','-B',str(HERE/'probe.py'),'--runtime'],
            work_seconds=budget,recovery_seconds=policy.RECOVERY_SECONDS)
    except BaseException as error:
        result=dict(status='INCOMPLETE',process_tree_empty=False,
            supervisor_error=type(error).__name__+': '+str(error),actual_case_credit=0)
    result.update(job_budget_seconds=policy.JOB_SECONDS,work_budget_seconds=policy.WORK_SECONDS,
        recovery_reserve_seconds=policy.RECOVERY_SECONDS,artifact_reserve_seconds=policy.ARTIFACT_SECONDS,
        qualification_commit=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        github_run_id=os.environ.get('GITHUB_RUN_ID'),github_run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'))
    OUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    return 0 if result['status']=='WORKER_COMPLETED_AND_REAPED'else 124

if __name__=='__main__':sys.exit(main())
