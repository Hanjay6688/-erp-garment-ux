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
PREPARATION_BRANCH='astra-a/afui-browser-runtime-prepared-20261105'
TEMPLATE='afui15.workflow.yml.txt'
ROUTED=(0,2,10,62,63,64,69,72,73,74)
ADDED=(65,66,72)
UPLOADER='ea165f8d65b6e75b540449e92b4886f43607fa02'

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
    value['on']['push']=dict(branches=[BRANCH,PREPARATION_BRANCH],paths=[WORKFLOW,NS+'**',
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
    setup=steps[10]
    key_get='sudo curl --fail --silent --show-error '
    if setup['name']!='Install pinned disposable runtime' or setup['run'].count(key_get)!=1:
        raise ValueError('NONPAYABLE_EXACT_PGDG_KEY_DOWNLOAD_ROUTE_REQUIRED')
    setup['run']=setup['run'].replace(key_get,'sudo curl --fail --no-progress-meter --show-error '
        '--retry 2 --retry-all-errors '
        '--retry-max-time 40 --connect-timeout 8 --max-time 15 --remove-on-error ',1)
    steps[62]=dict(name='Fetch actual accepted FREE3 canonical archive before database',
        **{'working-directory':'auditor'},env={'GH_TOKEN':'${{ github.token }}'},
        run='python -B '+NS+'fetch_parent.py\n')
    steps[63]=dict(name='Check complete Afui source and prepared owning workflow before database',
        **{'working-directory':'auditor'},
        run='set -euo pipefail\npython -B '+NS+'workflow.py --check\n'
            'python -B '+NS+'qualification.py --check-static\nnode --test '+NS+'durable_action.test.mjs\n')
    steps[64]=dict(name='Admit actual FREE3 and whole Afui graph under database network fence',
        **{'working-directory':'writer'},
        run='python -B ../auditor/'+NS+'qualification.py --check\npython -B ../auditor/scripts/current-de-free-date-preparation/attempt_policy.py --require-window\n')
    steps[69]=dict(name='Run current Afui15 once and retain complete Originals during owning restoration',
        uses='./auditor/'+NS,**{'with':{'mode':'runtime'}})
    for old,new in(('CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3','CP7_AFUI_GOOD_NONPAYABLE_FULL15'),
        ('FREE_DATE_FINAL_GATE','AFUI_FINAL_GATE'),('DE30_PARENT_ORIGINAL_ADMISSION','FREE3_PARENT_ORIGINAL_ADMISSION'),
        ('FREE_DATE_RUNTIME_SUPERVISION','AFUI_RUNTIME_SUPERVISION')):
        if old not in steps[72]['run']or new in steps[72]['run']:
            raise ValueError('NONPAYABLE_EXACT_CURRENT_PACKET_LOG_ROUTE_REQUIRED:'+old)
        steps[72]['run']=steps[72]['run'].replace(old,new)
    old='scripts/current-de-free-date-preparation/runtime_supervisor.py'
    if steps[73]['run'].count(old)!=1:raise ValueError('NONPAYABLE_EXACT_OWNED_DATABASE_STOP_ROUTE_REQUIRED')
    steps[73]['run']=steps[73]['run'].replace(old,NS+'runtime_supervisor.py',1)
    # The unarmed historical base predates the actual FREE41 cleanup repair.
    # Normalize only that exact old route; the accepted actual parent is clean.
    broken='../auditor/scripts/'+NS+'runtime_supervisor.py'
    if broken in steps[73]['run']:
        if steps[73]['run'].count(broken)!=1:
            raise ValueError('NONPAYABLE_EXACT_HISTORICAL_CLEANUP_REPAIR_REQUIRED')
        steps[73]['run']=steps[73]['run'].replace(broken,'../auditor/'+NS+'runtime_supervisor.py',1)
    steps[74]['with']['name']='cp7-afui-good-nonpayable-full15-${{ github.run_attempt }}'
    if [i for i in range(75)if steps[i]!=before[i]]!=list(ROUTED):
        raise ValueError('NONPAYABLE_ONLY_EXACT_WORKFLOW_STEP_ROUTES_ALLOWED')
    if(job['timeout-minutes']!=360 or steps[1]!=before[1]or value['permissions']!=original['permissions']
        or value['concurrency'].get('cancel-in-progress')is not False):
        raise ValueError('NONPAYABLE_ORIGINAL_BUDGET_CHECKOUT_AUTHORITY_AND_SINGLE_JOB_GUARDS_REQUIRED')
    # Pin the same official uploader already used by the final packet. The
    # preflight upload must succeed before the original database provisioning.
    if steps[74]['uses']!='actions/upload-artifact@'+UPLOADER:
        raise ValueError('NONPAYABLE_SAME_EXACT_OFFICIAL_UPLOADER_REQUIRED')
    routed_parent_steps=deepcopy(steps)
    steps[65:65]=[
        dict(name='Checkout the exact official complete-original uploader',uses=steps[1]['uses'],
            **{'with':{'repository':'actions/upload-artifact','ref':UPLOADER,
                'path':'afui-artifact-uploader','persist-credentials':False,'fetch-depth':1}}),
        dict(name='Confirm actual artifact transport before creating the database',
            uses='./auditor/'+NS,**{'with':{'mode':'preflight'}})]
    steps.insert(72,dict(name='Require complete Afui15 and full restoration in the final packet gate',
        **{'working-directory':'writer'},run='python -B ../auditor/'+NS+'final_gate.py\n'))
    if len(steps)!=78 or [step for i,step in enumerate(steps)if i not in ADDED]!=routed_parent_steps:
        raise ValueError('NONPAYABLE_THREE_EXACT_RETENTION_STEPS_REQUIRED')
    retained78=deepcopy(steps)
    steps[65:65]=[
        dict(name='Install pinned browser dependencies in both actual checkout roots',shell='bash',
            run='set -euo pipefail\nfor checkout in auditor writer; do\n'
                '  npm ci --include=dev --prefix "$checkout"\ndone\n'
                '(cd auditor && npx --no-install playwright install --with-deps chromium)\n'
                '(cd writer && npx --no-install playwright install chromium)\n'),
        dict(name='Open actual desktop and mobile browsers and compile candidate before database',
            run='node auditor/'+NS+'browser_prerequisites.mjs "$GITHUB_WORKSPACE"\n')]
    if len(steps)!=80 or [step for i,step in enumerate(steps)if i not in(65,66)]!=retained78:
        raise ValueError('NONPAYABLE_ONLY_TWO_PRE_DATABASE_BROWSER_PREREQUISITES_ALLOWED')
    checkout='actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683'
    value['jobs']['browser_prerequisites_only']=dict(
        name='Actual browser prerequisites only; no database or ERP cases',
        **{'if':"github.ref == 'refs/heads/"+PREPARATION_BRANCH+"'",'runs-on':'ubuntu-latest',
            'timeout-minutes':25,'steps':[
                dict(uses=checkout,**{'with':{'path':'auditor','fetch-depth':0,'persist-credentials':False}}),
                dict(uses=checkout,**{'with':{'path':'writer','fetch-depth':0,'persist-credentials':False}}),
                dict(uses='actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020',**{'with':{'node-version':'22'}}),
                deepcopy(steps[65]),deepcopy(steps[66]),
                dict(uses='actions/upload-artifact@'+UPLOADER,**{'if':'always()',
                    'with':{'name':'afui-browser-prerequisites-only-${{ github.run_attempt }}',
                        'path':'auditor/cp6-proof/t3/AFUI_BROWSER_PREREQUISITES.json',
                        'retention-days':30,'if-no-files-found':'error'}})]})
    text=yaml.safe_dump(value,sort_keys=False,allow_unicode=True)
    if yaml.safe_load(text)!=value:raise ValueError('NONPAYABLE_EXACT_WORKFLOW_YAML_ROUNDTRIP_REQUIRED')
    return text,dict(status='AFUI15_WORKFLOW_DATA_ONLY_NOT_ACTIVATED',parent_derivation=prior,
        parent_template_sha256=sha256(raw.encode()).hexdigest(),
        unchanged_parent_steps=len(before)-len(ROUTED),routed_parent_steps=len(ROUTED),
        steps=80,added_transport_steps=3,added_browser_prerequisite_steps=2,
        preparation_branch_database_free_browser_job=True,owning_financial_branch_guard_unchanged=True,
        all_current78_steps_retained=True,actual_browser_launch_before_database=True,
        monotonic_job_start_before_checkout=True,job_minutes=360,
        official_uploader=UPLOADER,complete_original_upload_before_database=True,
        runtime_supervisor_and_full_final_gate_retained=True,real_WIB_policy_unchanged=True,
        runtime_dispatches=0,actual_ERP_cases=0,production_go=False,independent_acceptance=False)

def admit_source(manifest):
    """An active workflow is source only after exact parent acceptance."""
    active=ROOT/WORKFLOW
    if WORKFLOW not in manifest['files']:
        if active.exists()or active.is_symlink():raise ValueError('NONPAYABLE_UNDECLARED_WORKFLOW_REFUSED')
        return None
    if not active.is_file():raise ValueError('NONPAYABLE_DECLARED_WORKFLOW_MISSING')
    from . import admission
    if any(p.is_symlink()for p in(active,*active.parents)):
        raise ValueError('NONPAYABLE_WORKFLOW_SYMLINK_REFUSED')
    raw=active.read_bytes()
    if manifest['files'][WORKFLOW]!=admission.pin(raw):
        raise ValueError('NONPAYABLE_EXACT_WORKFLOW_SOURCE_PIN_REQUIRED')
    if raw!=(HERE/TEMPLATE).read_bytes():
        raise ValueError('NONPAYABLE_WORKFLOW_MUST_EQUAL_REVIEWED_TEMPLATE')
    receipt=admission.parent_receipt()
    if receipt['head']!=manifest['base_head']or receipt['tree']!=manifest['base_tree']:
        raise ValueError('NONPAYABLE_WORKFLOW_REQUIRES_EXACT_SOURCE_BASE_QUALIFICATION')
    return dict(status='EXACT_AFUI_WORKFLOW_AND_ACTUAL_FREE3_PARENT_SOURCE',actual_ERP_cases=0)


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
