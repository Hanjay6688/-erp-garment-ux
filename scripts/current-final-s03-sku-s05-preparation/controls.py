"""Only new source/caller contracts; no fabricated Native or browser results."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess,yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def controls():
    policy_record=json.loads((HERE/'ATTEMPT_POLICY_DERIVATION.json').read_bytes())
    original_policy=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',
        policy_record['source_commit']+':'+policy_record['source_path']])
    if(len(original_policy)!=policy_record['original_bytes']
       or sha256(original_policy).hexdigest()!=policy_record['original_sha256']):
        raise ValueError('PERMANENT_S05_EXACT_ORIGINAL_ATTEMPT_POLICY_REQUIRED')
    value=original_policy.decode()
    for change in policy_record['changes']:
        if value.count(change['before'])!=change['count']:raise ValueError('PERMANENT_S05_EXACT_ATTEMPT_BUDGET_CHANGE_REQUIRED')
        value=value.replace(change['before'],change['after'],change['count'])
    if value.encode()!=(HERE/'attempt_policy.py').read_bytes():
        raise ValueError('PERMANENT_S05_ONLY_DECLARED_ATTEMPT_POLICY_CHANGE_ALLOWED')
    diagnostics=json.loads((HERE/'RUNTIME_DIAGNOSTICS_SOURCE.json').read_bytes())
    raw_diagnostics=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',
        diagnostics['source_commit']+':'+diagnostics['source_path']])
    if(raw_diagnostics!=(HERE/'runtime_note.py').read_bytes()
       or sha256(raw_diagnostics).hexdigest()!=diagnostics['sha256']):
        raise ValueError('PERMANENT_S05_EXACT_PUBLISHED_DIAGNOSTICS_REQUIRED')
    declaration=json.loads((HERE/'PERSISTENT_BROWSER_DERIVATIONS.json').read_bytes())
    for name,item in declaration['files'].items():
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',item['source_commit']+':'+item['source_path']])
        if len(raw)!=item['original_bytes']or sha256(raw).hexdigest()!=item['original_sha256']:
            raise ValueError('PERMANENT_S05_IMMUTABLE_BROWSER_SOURCE_CHANGED:'+name)
        value=raw.decode()
        for change in item['changes']:
            if value.count(change['before'])!=change['count']:
                raise ValueError('PERMANENT_S05_EXACT_BROWSER_ROUTE_REQUIRED:'+name)
            value=value.replace(change['before'],change['after'],change['count'])
        current=(HERE/name).read_bytes()
        if value.encode()!=current or sha256(current).hexdigest()!=item['derived_sha256']:
            raise ValueError('PERMANENT_S05_COMPLETE_BROWSER_DERIVATION_CHANGED:'+name)
        for change in reversed(item['changes']):
            if value.count(change['after'])!=change['count']:
                raise ValueError('PERMANENT_S05_UNIQUE_BROWSER_REVERSE_REQUIRED:'+name)
            value=value.replace(change['after'],change['before'],change['count'])
        if value.encode()!=raw:raise ValueError('PERMANENT_S05_ORIGINAL_BROWSER_BYTES_NOT_RECOVERED:'+name)
    financial=load('permanent_actual_complete_financial_source_control',HERE/'persistent_financial.py').prepared_sources()[1]
    engine=load('permanent_actual_complete_package_engine_control',HERE/'engine.py')
    text,engine_proof=engine.derive((ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes())
    compile(text,'complete_permanent_package_engine_source_control','exec')
    if engine_proof['counted_changes']!=2 or engine_proof['complete_original_recovered']is not True:
        raise ValueError('PERMANENT_S05_COMPLETE_PACKAGE_ENGINE_REQUIRED')
    record=json.loads((HERE/'WORKFLOW_DERIVATION.json').read_bytes())
    original=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',record['source_commit']+':'+record['source_path']])
    if sha256(original).hexdigest()!=record['source_sha256']:
        raise ValueError('PERMANENT_S05_FROZEN_WORKFLOW_SOURCE_CHANGED')
    old=yaml.safe_load(original)['jobs']['p21']['steps']
    workflow=yaml.safe_load((ROOT/'.github/workflows/cp7-final-s03-sku-s05.yml').read_bytes())
    job=workflow['jobs']['p21'];steps=job['steps']
    for i in record['unchanged_step_indices']:
        if steps[i]!=old[i]:raise ValueError('PERMANENT_S05_UNDECLARED_WORKFLOW_STEP_CHANGE:'+str(i))
    branch=record['branch']
    if workflow['on']['push']['branches']!=[branch]or job['if']!="github.ref == 'refs/heads/"+branch+"'":
        raise ValueError('PERMANENT_S05_EXACT_RUNTIME_BRANCH_REQUIRED')
    policy=load('permanent_exact_own_full_job_day_window',HERE/'attempt_policy.py')
    if(job['timeout-minutes']!=120 or policy.JOB_BUDGET_SECONDS!=job['timeout-minutes']*60
       or job['env']['PERMANENT_S05_CONFIRM']!='cp6_rollback'):
        raise ValueError('PERMANENT_S05_DISPOSABLE_WINDOW_AND_CONFIRMATION_REQUIRED')
    start=next(i for i,s in enumerate(steps)if s.get('name')=='Start disposable database')
    for marker in('fetch_parent37.py','controls.py','probe.py --check'):
        if not any(marker in s.get('run','')for s in steps[:start]):
            raise ValueError('PERMANENT_S05_ADMISSION_MUST_PRECEDE_DATABASE:'+marker)
    runtime=next(s for s in steps if s.get('name','').startswith('Run actual permanent'))
    if runtime['working-directory']!='writer'or 'final_gate.py'not in runtime['run']:
        raise ValueError('PERMANENT_S05_EXACT_OWNING_PACKAGE_CWD_AND_FINAL_GATE_REQUIRED')
    return dict(status='PERMANENT_READER_SOURCE_AND_CALLER_CONTROLS_PASS_NOT_NATIVE',
        complete_unchanged_browser_source_derivations=len(declaration['files']),
        unchanged_financial_callback_ASTs=financial['original_financial_callback_ASTs_unchanged'],
        selected_persistent_financial_cases=4,complete_package_engine=engine_proof,
        exact_original_workflow_steps_retained=len(record['unchanged_step_indices']),
        exact_job_and_WIB_guard_budget_seconds=policy.JOB_BUDGET_SECONDS,
        original_single_attempt_and_real_day_behavior_unchanged=True,published_diagnostics_byte_exact=True,
        actual_Native_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    fence=load('permanent_actual_source_DB_network_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read()as guard:result=controls()
    result['source_DB_network_guard']=guard
    print(json.dumps(result,sort_keys=True))
