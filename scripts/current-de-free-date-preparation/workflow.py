"""Reviewable FREE3 workflow data; no ref update, dispatch or activation."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import argparse,importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NS='scripts/current-de-free-date-preparation/'
WORKFLOW='.github/workflows/cp7-current-complete-de-free-date-native3.yml'
BRANCH='astra-a/current-complete-de-free-date-native3-20261101'
TEMPLATE='native3.workflow.yml.txt'
ROUTED=(61,62,63,68,71,73)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def derive():
    import yaml
    raw,prior=load('free_date_exact_DE_workflow_data',
        ROOT/'scripts/current-complete-de-integration-preparation/workflow.py').derive()
    original=yaml.safe_load(raw);value=deepcopy(original)
    if set(value['jobs'])!={'p21'}or len(value['jobs']['p21']['steps'])!=74:
        raise ValueError('FREE_DATE_EXACT_PARENT_74_STEP_WORKFLOW_REQUIRED')
    value['name']='CP7 A current complete DE FREE date Native3'
    value['on']['push']=dict(branches=[BRANCH],paths=[WORKFLOW,NS+'**',
        'scripts/current-special-free-date-boundary/**','scripts/cp7_special_free_date_on_de/**',
        'scripts/cp7_current_de_free_date/**'])
    value['concurrency']['group']='cp7-current-complete-de-free-date3-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']='Native FREE date3; real posting and complete restoration'
    job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    job['env'].pop('COMPLETE_DE_CONFIRM');job['env']['FREE_DATE_CONFIRM']='cp6_rollback'
    steps=job['steps']
    steps[61]=dict(name='Fetch canonical terminal DE30 root intake and original archive before database',
        **{'working-directory':'auditor'},env={'GH_TOKEN':'${{ github.token }}'},
        run='python -B '+NS+'fetch_parent.py\n')
    steps[62]=dict(name='Check Native FREE3 sources and pending-parent controls before database',
        **{'working-directory':'auditor'},
        run='set -euo pipefail\npython -B '+NS+'check.py --source\n')
    steps[63]=dict(name='Admit complete DE FREE date source graph under database network fence',
        **{'working-directory':'auditor'},
        run='python -B '+NS+'probe.py --check\npython -B scripts/current-sku-managed-recovery-native27-qualification/attempt_policy.py --require-window\n')
    steps[68]=dict(name='Run Native FREE date3 and complete outer restoration',
        **{'working-directory':'writer'},
        run="python -u -B '../auditor/"+NS+"probe.py' --runtime\npython -B '../auditor/"+NS+"final_gate.py'\n")
    for before,after in(('CP7_CURRENT_COMPLETE_D1_E_NATIVE30','CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3'),
                         ('DE30_FINAL_GATE','FREE_DATE_FINAL_GATE'),
                         ('PERMANENT6_PARENT_ORIGINAL_ADMISSION','DE30_PARENT_ORIGINAL_ADMISSION')):
        if before not in steps[71]['run']or after in steps[71]['run']:
            raise ValueError('FREE_DATE_EXACT_PARENT_LOG_RECEIPT_ROUTE_REQUIRED:'+before)
        steps[71]['run']=steps[71]['run'].replace(before,after)
    steps[73]['with']['name']='cp7-current-complete-de-free-date-native3-${{ github.run_attempt }}'
    before=original['jobs']['p21']['steps']
    if [i for i in range(74)if steps[i]!=before[i]]!=list(ROUTED):
        raise ValueError('FREE_DATE_ONLY_SIX_PARENT_WORKFLOW_STEPS_MAY_ROUTE')
    if job['timeout-minutes']!=210 or steps[1]!=before[1]:
        raise ValueError('FREE_DATE_UNCHANGED_REAL_210_MINUTE_GUARD_REQUIRED')
    text=yaml.safe_dump(value,sort_keys=False,allow_unicode=True)
    if yaml.safe_load(text)!=value:raise ValueError('FREE_DATE_WORKFLOW_DATA_YAML_ROUNDTRIP_REQUIRED')
    return text,dict(status='FREE_DATE_NATIVE3_WORKFLOW_DATA_NOT_ACTIVATED',parent_derivation=prior,
        parent_template_sha256=sha256(raw.encode()).hexdigest(),unchanged_parent_steps=68,
        routed_parent_steps=6,steps=74,job_minutes=210,real_clock_guard_unchanged=True,
        runtime_dispatches=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def source_control():
    text,proof=derive()
    if(HERE/TEMPLATE).read_bytes()!=text.encode():
        raise ValueError('FREE_DATE_EXACT_REVIEWABLE_WORKFLOW_TEMPLATE_REQUIRED')
    active=ROOT/WORKFLOW
    if active.exists():
        load('free_date_actual_DE_parent_before_workflow_admission',HERE/'admission.py').parent_receipt()
        manifest=json.loads((HERE/'SOURCE.json').read_bytes())
        if(active.is_symlink()or active.read_bytes()!=text.encode()
           or manifest['files'].get(WORKFLOW)!={'bytes':len(text.encode()),'sha256':sha256(text.encode()).hexdigest()}):
            raise ValueError('FREE_DATE_ACTIVATION_REQUIRES_EXACT_EXPLICITLY_ADMITTED_WORKFLOW_PATH')
        proof=dict(proof,status='FREE_DATE_EXPLICIT_ACTIVATED_WORKFLOW_SOURCE_MATCHES_TEMPLATE')
    return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true',required=True);p.parse_args()
    print(json.dumps(source_control()))
