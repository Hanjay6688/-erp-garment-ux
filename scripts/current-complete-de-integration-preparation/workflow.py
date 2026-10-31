"""Reviewable Native30 workflow data, with no activation or dispatch operation.

Seven original steps are routed to this owning qualification. The other 66
steps remain exact dictionaries; real-clock and process ownership guard setup.
"""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import argparse,importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGIN='a5944f25a5e3ba1f1f537a18abe923eb753f922f'
PATH='.github/workflows/cp7-final-s03-sku-s05.yml'
BYTES=33918
SHA256='11d398b373b478f49c366cd611ab0cd67a9e2cc8361b7a49cdaa92cc116c8af5'
BRANCH='astra-a/current-complete-de-native30-20261031'
WORKFLOW='.github/workflows/cp7-current-complete-de-native30.yml'
NS='scripts/current-complete-de-integration-preparation/'
TEMPLATE='native30.workflow.yml.txt'
REPLACED=(60,61,62,67,70,71,72)


def derive():
    import yaml
    raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',ORIGIN+':'+PATH],
        env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0'))
    if len(raw)!=BYTES or sha256(raw).hexdigest()!=SHA256:
        raise ValueError('COMPLETE_DE_EXACT_PARENT_WORKFLOW_SOURCE_REQUIRED')
    original=yaml.safe_load(raw);value=deepcopy(original)
    if set(value['jobs'])!={'p21'}or len(value['jobs']['p21']['steps'])!=73:
        raise ValueError('COMPLETE_DE_EXACT_ORIGINAL_WORKFLOW_STRUCTURE_REQUIRED')
    value['name']='CP7 A current complete D1 E Native30'
    value['on']['push']=dict(branches=[BRANCH],paths=[WORKFLOW,NS+'**',
        'scripts/cp7_complete_credit_de/**','scripts/cp7_credit_correction_de/**'])
    value['concurrency']['group']='cp7-current-complete-de30-single-owning-qualification'
    job=value['jobs']['p21'];job['name']='Original D1 Native13 and E Native17; complete restoration'
    job['timeout-minutes']=360;job['env']['COMPLETE_DE_CONFIRM']='cp6_rollback'
    job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    steps=job['steps']
    steps[60]=dict(name='Fetch canonical terminal permanent6 root intake and original archive before database',
        **{'working-directory':'auditor'},env={'GH_TOKEN':'${{ github.token }}'},
        run='python -B '+NS+'fetch_parent.py\n')
    steps[61]=dict(name='Check exact original D1 E Native30 sources and pending-parent controls before database',
        **{'working-directory':'auditor'},
        run='set -euo pipefail\npython -B '+NS+'check.py --source\n')
    steps[62]=dict(name='Admit complete natural D1 E source graph under DB network fence before database',
        **{'working-directory':'auditor'},
        run='python -B '+NS+'probe.py --check\npython -B '+NS+'attempt_policy.py --require-window\n')
    steps[67]=dict(name='Run original current D1 E Native30 and complete outer restoration',
        **{'working-directory':'writer'},
        run="python -u -B '../auditor/"+NS+"runtime_supervisor.py'\npython -B '../auditor/"+NS+"final_gate.py'\n")
    replacements=(('CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2.json','CP7_CURRENT_COMPLETE_D1_E_NATIVE30.json'),
        ('PERMANENT_FINAL_GATE.json','DE30_FINAL_GATE.json'),
        ('CP7_PERMANENT_S05_S03_FINANCIAL_NATIVE4','CP7_CURRENT_COMPLETE_D1_E_NATIVE30_CASES'),
        ('JOIN37_PARENT_ORIGINAL_ADMISSION.json','PERMANENT6_PARENT_ORIGINAL_ADMISSION.json'))
    for before,after in replacements:
        if before not in steps[70]['run']or after in steps[70]['run']:
            raise ValueError('COMPLETE_DE_EXACT_ORIGINAL_LOG_RECEIPT_ROUTE_REQUIRED:'+before)
        steps[70]['run']=steps[70]['run'].replace(before,after)
    steps[71]['run']='python -B ../auditor/'+NS+'runtime_supervisor.py --allow-database-stop\n'+steps[71]['run']
    steps[72]['with']['name']='cp7-current-complete-de-native30-${{ github.run_attempt }}'
    before=original['jobs']['p21']['steps']
    if [i for i in range(73)if steps[i]!=before[i]]!=list(REPLACED):
        raise ValueError('COMPLETE_DE_ONLY_SEVEN_WORKFLOW_STEP_ROUTES_ALLOWED')
    early=dict(name='Require genuine 360 minute WIB window before setup',
        **{'working-directory':'auditor'},
        run='python -B '+NS+'attempt_policy.py --require-window\n')
    steps.insert(1,early)
    steps.insert(0,dict(name='Record monotonic DE job start before setup and admission',
        run="python - <<'PY'\nimport os,time\nwith open(os.environ['GITHUB_ENV'],'a') as stream:\n    stream.write('DE_JOB_START_MONOTONIC='+str(time.monotonic())+'\\n')\nPY\n"))
    text=yaml.safe_dump(value,sort_keys=False,allow_unicode=True)
    if yaml.safe_load(text)!=value:raise ValueError('COMPLETE_DE_WORKFLOW_YAML_ROUNDTRIP_REQUIRED')
    return text,dict(status='DE30_WORKFLOW_DATA_ONLY_NOT_ACTIVATED',original_head=ORIGIN,original_path=PATH,
        original_bytes=BYTES,original_sha256=SHA256,unchanged_original_steps=66,routed_original_steps=7,
        new_pre_setup_real_clock_guards=1,new_process_ownership_start_markers=1,
        steps=75,job_minutes=360,original_policy_minutes=210,
        runtime_dispatches=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def source_control():
    text,proof=derive()
    if(HERE/TEMPLATE).read_bytes()!=text.encode():
        raise ValueError('COMPLETE_DE_EXACT_REVIEWABLE_WORKFLOW_TEMPLATE_REQUIRED')
    active=ROOT/WORKFLOW
    if active.exists():
        # A later activation must explicitly admit this exact path after the
        # actual permanent6 receipt exists; a stray local workflow cannot open it.
        spec=importlib.util.spec_from_file_location('complete_DE_actual_parent_before_workflow_path',HERE/'admission.py')
        admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission);admission.parent_receipt()
        declaration=json.loads((HERE/'SOURCE.json').read_bytes())
        if(active.is_symlink()or active.read_bytes()!=text.encode()
           or declaration['files'].get(WORKFLOW)!={'bytes':len(text.encode()),'sha256':sha256(text.encode()).hexdigest()}):
            raise ValueError('COMPLETE_DE_ACTIVATION_REQUIRES_EXACT_EXPLICITLY_ADMITTED_WORKFLOW_PATH')
        proof=dict(proof,status='DE30_EXPLICIT_ACTIVATED_WORKFLOW_SOURCE_MATCHES_TEMPLATE')
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true',required=True);parser.parse_args()
    print(json.dumps(source_control()))
