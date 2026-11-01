"""Reviewable whole Afui15 workflow data. No activation, ref move or dispatch."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import argparse,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NS='scripts/cp7_accessory_nonpayable/'
WORKFLOW='.github/workflows/cp7-afui-good-nonpayable.yml'
BRANCH='astra-a/afui-good-nonpayable-20261102'
TEMPLATE='afui15.workflow.yml.txt'
ROUTED=(0,2,62,63,64,69,72,73,74)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def derive():
    import yaml
    raw,prior=load('afui_exact_complete_FREE3_supervised_workflow',
        ROOT/'scripts/current-de-free-date-preparation/workflow.py').derive()
    original=yaml.safe_load(raw);value=deepcopy(original)
    if set(value['jobs'])!={'p21'}or len(value['jobs']['p21']['steps'])!=75:
        raise ValueError('NONPAYABLE_EXACT_ORIGINAL_SUPERVISED_75_STEP_WORKFLOW_REQUIRED')
    value['name']='CP7 A Afui GOOD date nonpayable full15'
    from cp7_accessory_nonpayable import ui_derivation
    value['on']['push']=dict(branches=[BRANCH],paths=[WORKFLOW,NS+'**',
        *sorted(ui_derivation.CHANGED|ui_derivation.ADDED)])
    value['concurrency']['group']='cp7-afui-good-nonpayable15-single-owning-qualification'
    job=value['jobs']['p21'];job['name']='Afui Native9 Auth2 session2 browser2; complete restoration'
    job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    job['env'].pop('FREE_DATE_CONFIRM');job['env']['AFUI_CONFIRM']='cp6_rollback'
    steps=job['steps'];before=original['jobs']['p21']['steps']
    if steps[0]['run'].count('FREE_DATE_JOB_START_MONOTONIC')!=1:
        raise ValueError('NONPAYABLE_EXACT_EARLIEST_REAL_JOB_CLOCK_REQUIRED')
    steps[0]['name']='Record monotonic Afui job start before setup and admission'
    steps[0]['run']=steps[0]['run'].replace('FREE_DATE_JOB_START_MONOTONIC','AFUI_JOB_START_MONOTONIC',1)
    # The real six-hour WIB policy and every financial clock remain unchanged.
    steps[2]['name']='Require genuine six-hour WIB window before Afui setup'
    steps[62]=dict(name='Fetch actual accepted FREE3 canonical archive before database',
        **{'working-directory':'auditor'},env={'GH_TOKEN':'${{ github.token }}'},
        run='python -B '+NS+'fetch_parent.py\n')
    steps[63]=dict(name='Check complete Afui source and prepared owning workflow before database',
        **{'working-directory':'auditor'},
        run='set -euo pipefail\npython -B '+NS+'workflow.py --check\npython -B '+NS+'qualification.py --check-static\n')
    steps[64]=dict(name='Admit actual FREE3 and whole Afui graph under database network fence',
        **{'working-directory':'auditor'},
        run='python -B '+NS+'qualification.py --check\npython -B scripts/current-de-free-date-preparation/attempt_policy.py --require-window\n')
    steps[69]=dict(name='Run current Afui15 once with owning full restoration and packet gate',
        **{'working-directory':'writer'},
        run="python -u -B '../auditor/"+NS+"runtime_supervisor.py'\npython -B '../auditor/"+NS+"final_gate.py'\n")
    for old,new in(('CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3','CP7_AFUI_GOOD_NONPAYABLE_FULL15'),
        ('FREE_DATE_FINAL_GATE','AFUI_FINAL_GATE'),('DE30_PARENT_ORIGINAL_ADMISSION','FREE3_PARENT_ORIGINAL_ADMISSION'),
        ('FREE_DATE_RUNTIME_SUPERVISION','AFUI_RUNTIME_SUPERVISION')):
        if old not in steps[72]['run']or new in steps[72]['run']:
            raise ValueError('NONPAYABLE_EXACT_CURRENT_PACKET_LOG_ROUTE_REQUIRED:'+old)
        steps[72]['run']=steps[72]['run'].replace(old,new)
    old='scripts/current-de-free-date-preparation/runtime_supervisor.py'
    if steps[73]['run'].count(old)!=1:raise ValueError('NONPAYABLE_EXACT_OWNED_DATABASE_STOP_ROUTE_REQUIRED')
    steps[73]['run']=steps[73]['run'].replace(old,NS+'runtime_supervisor.py',1)
    steps[74]['with']['name']='cp7-afui-good-nonpayable-full15-${{ github.run_attempt }}'
    if [i for i in range(75)if steps[i]!=before[i]]!=list(ROUTED):
        raise ValueError('NONPAYABLE_ONLY_NINE_EXACT_WORKFLOW_STEP_ROUTES_ALLOWED')
    if(job['timeout-minutes']!=360 or steps[1]!=before[1]or value['permissions']!=original['permissions']
        or value['concurrency'].get('cancel-in-progress')is not False):
        raise ValueError('NONPAYABLE_ORIGINAL_BUDGET_CHECKOUT_AUTHORITY_AND_SINGLE_JOB_GUARDS_REQUIRED')
    text=yaml.safe_dump(value,sort_keys=False,allow_unicode=True)
    if yaml.safe_load(text)!=value:raise ValueError('NONPAYABLE_EXACT_WORKFLOW_YAML_ROUNDTRIP_REQUIRED')
    return text,dict(status='AFUI15_WORKFLOW_DATA_ONLY_NOT_ACTIVATED',parent_derivation=prior,
        parent_template_sha256=sha256(raw.encode()).hexdigest(),unchanged_parent_steps=66,routed_parent_steps=9,
        steps=75,job_minutes=360,monotonic_job_start_before_checkout=True,real_WIB_policy_unchanged=True,
        runtime_dispatches=0,actual_ERP_cases=0,production_go=False,independent_acceptance=False)

def source_control():
    text,proof=derive()
    if(HERE/TEMPLATE).is_symlink()or(HERE/TEMPLATE).read_bytes()!=text.encode():
        raise ValueError('NONPAYABLE_EXACT_REVIEWABLE_WORKFLOW_TEMPLATE_REQUIRED')
    active=ROOT/WORKFLOW
    if active.exists():
        from cp7_accessory_nonpayable import admission
        admission.parent_receipt()  # A template never opens the absent actual parent.
        manifest=admission.strict((HERE/'SOURCE.json').read_bytes())
        if(active.is_symlink()or active.read_bytes()!=text.encode()
            or manifest['files'].get(WORKFLOW)!=admission.pin(text.encode())):
            raise ValueError('NONPAYABLE_ACTIVATION_REQUIRES_EXACT_EXPLICITLY_ADMITTED_WORKFLOW_PATH')
        proof=dict(proof,status='AFUI15_EXPLICIT_ACTIVATED_WORKFLOW_SOURCE_MATCHES_TEMPLATE')
    return proof

if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'scripts'))
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true',required=True);parser.parse_args()
    print(json.dumps(source_control(),sort_keys=True))
