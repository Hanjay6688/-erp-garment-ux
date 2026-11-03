"""Reviewable Mandor17 workflow data, never an activation or dispatch.

Retain the exact 75-step Afui installation/restoration prerequisite chain.
Eight owning step routes and four explicit parent/proof steps are added;
all gates still require an actually accepted Afui parent and source binding.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse,json,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NS='scripts/current-mandor-shop-native-qualification/'
ORIGINAL='scripts/cp7_accessory_nonpayable/afui15.workflow.yml.txt'
ORIGINAL_PIN=dict(bytes=33890,sha256='551e9f853a6307e791991926b714aa53578f95b69ee246e7c567ff213dc75799')
TEMPLATE='mandor17.workflow.yml.txt'
WORKFLOW='.github/workflows/cp7-mandor-shop-native17.yml'
BRANCH='astra-a/mandor-shop-native9-on-unified-20261103'
ROUTED=(0,2,63,64,69,72,73,74)


def require(value,message):
    if not value:raise ValueError(message)


def derive():
    import yaml
    raw=(ROOT/ORIGINAL).read_bytes()
    require(dict(bytes=len(raw),sha256=sha256(raw).hexdigest())==ORIGINAL_PIN,'MANDOR_WORKFLOW_EXACT_AFUI_TEMPLATE')
    original=yaml.safe_load(raw);value=deepcopy(original)
    require(set(value['jobs'])=={'p21'}and len(value['jobs']['p21']['steps'])==75,'MANDOR_WORKFLOW_COMPLETE_ORIGINAL75')
    value['name']='CP7 A Mandor Native9 session4 HTTP2 browser2 full17'
    value['on']['push']=dict(branches=[BRANCH],paths=[WORKFLOW,NS+'**','scripts/current-unified-candidate/**',
        'scripts/cp7_mandor_shop/**','src/**','scripts/check-source-ownership.mjs','scripts/check-access-catalog.mjs'])
    value['concurrency']['group']='cp7-mandor-shop17-single-owning-qualification'
    job=value['jobs']['p21'];job['name']='Mandor Native9 session4 HTTP2 browser2; complete restoration'
    job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    require(job['env'].pop('AFUI_CONFIRM')=='cp6_rollback','MANDOR_WORKFLOW_ORIGINAL_DISPOSABLE_CONFIRMATION')
    job['env']['MANDOR_NATIVE_CONFIRM']='cp6_rollback'
    steps=job['steps'];before=original['jobs']['p21']['steps']
    require(steps[0]['run'].count('AFUI_JOB_START_MONOTONIC')==1,'MANDOR_WORKFLOW_ONE_REAL_JOB_CLOCK')
    steps[0]['name']='Record monotonic Mandor job start before setup and admission'
    steps[0]['run']=steps[0]['run'].replace('AFUI_JOB_START_MONOTONIC','MANDOR_NATIVE_JOB_START_MONOTONIC',1)
    steps[2]['name']='Require genuine six-hour WIB window before Mandor setup'
    steps[63]=dict(name='Check complete unified Mandor source and prepared owning workflow before database',
        **{'working-directory':'auditor'},run='set -euo pipefail\npython -B '+NS+'workflow.py --check\npython -B scripts/current-unified-candidate/check_source.py\n')
    steps[64]=dict(name='Admit actual Afui15 and complete Mandor graph under database network fence',
        **{'working-directory':'writer'},run='python -B ../auditor/'+NS+'qualification.py --check\npython -B ../auditor/scripts/current-de-free-date-preparation/attempt_policy.py --require-window\n')
    steps[69]=dict(name='Run current Mandor17 once with owning full restoration and packet gate',
        **{'working-directory':'writer'},run="python -u -B '../auditor/"+NS+"runtime_supervisor.py'\npython -B '../auditor/"+NS+"final_gate.py'\n")
    # Preserve the original byte-receipt operation; select this exact package's
    # real filenames instead of carrying an obsolete Afui CASES label.
    for old,new in(
        ('CP7_AFUI_GOOD_NONPAYABLE_FULL15_CASES_BUSINESS_DAY_FIRST_ATTEMPT','CP7_FG_MANDOR_NATIVE9_STRICT_BUSINESS_DAY_FIRST_ATTEMPT'),
        ('CP7_AFUI_GOOD_NONPAYABLE_FULL15_CASES','CP7_FG_MANDOR_NATIVE9_STRICT'),
        ('CP7_AFUI_GOOD_NONPAYABLE_FULL15','CP7_FG_MANDOR_NATIVE9'),
        ('AFUI_FINAL_GATE','MANDOR_NATIVE9_FINAL_GATE'),
        ('FREE3_PARENT_ORIGINAL_ADMISSION','AFUI15_PARENT_ORIGINAL_ADMISSION'),
        ('AFUI_RUNTIME_SUPERVISION','MANDOR_RUNTIME_SUPERVISION')):
        before_name=repr(old+'.json');after_name=repr(new+'.json')
        require(steps[72]['run'].count(before_name)==1 and after_name not in steps[72]['run'],
            'MANDOR_WORKFLOW_EXACT_RECEIPT_ROUTE:'+old)
        steps[72]['run']=steps[72]['run'].replace(before_name,after_name,1)
    old='scripts/cp7_accessory_nonpayable/runtime_supervisor.py'
    require(steps[73]['run'].count(old)==1,'MANDOR_WORKFLOW_ONE_OWNED_DATABASE_STOP_ROUTE')
    steps[73]['run']=steps[73]['run'].replace(old,NS+'runtime_supervisor.py',1)
    steps[74]['with']['name']='cp7-mandor-shop-native17-${{ github.run_attempt }}'
    require([i for i in range(75)if steps[i]!=before[i]]==list(ROUTED),'MANDOR_WORKFLOW_ONLY_EIGHT_OWNING_STEP_ROUTES')
    additions={
        1:dict(name='Materialize exact accepted Afui parent without fetching or rewriting files',
            **{'working-directory':'auditor'},run='python -B '+NS+'materialize_parent.py\n'),
        62:dict(name='Fetch exact accepted Afui15 original archive before database',
            **{'working-directory':'auditor'},env={'GH_TOKEN':'${{ github.token }}'},run='python -B '+NS+'fetch_parent.py\n'),
        63:dict(name='Copy exact historical proof inputs into frozen Afui parent before source admission',
            **{'working-directory':'auditor'},run='python -B '+NS+'parent_artifacts.py --prepare\n'),
        71:dict(name='Retain every new or changed frozen-parent output in full even on failure',
            **{'if':'always()','working-directory':'auditor'},run='python -B '+NS+'parent_artifacts.py --retain\n'),
    }
    combined=[]
    for i,step in enumerate(steps):
        combined.append(step)
        if i in additions:combined.append(additions[i])
    job['steps']=combined
    require(len(combined)==79 and job['timeout-minutes']==360 and value['permissions']==original['permissions']
        and value['concurrency']['cancel-in-progress']is False,'MANDOR_WORKFLOW_ORIGINAL_BUDGET_AUTHORITY_AND_SINGLE_RUN')
    require(steps[1]==before[1]and steps[65:69]==before[65:69]
        and steps[70:72]==before[70:72],'MANDOR_WORKFLOW_ORIGINAL_CHECKOUT_DATABASE_CLONE_AND_RETENTION')
    text=yaml.safe_dump(value,sort_keys=False,allow_unicode=True)
    require(yaml.safe_load(text)==value,'MANDOR_WORKFLOW_EXACT_YAML_ROUNDTRIP')
    proof=dict(status='MANDOR17_WORKFLOW_DATA_ONLY_NOT_ACTIVATED',original_template=ORIGINAL_PIN,
        unchanged_parent_steps=67,routed_parent_steps=8,new_parent_and_artifact_steps=4,total_steps=79,
        real_360_minute_job_and_WIB_clock_policy_unchanged=True,process_supervision_330_20_10_retained=True,
        original_checkout_base_database_and_clone_unchanged=True,original_full_package_and_restore_entry_retained=True,
        named_job_cases=dict(Native=9,sessions=4,HTTP=2,browser=2),
        activation_requires_actual_parent_intake_component_and_unified_source_rebinding=True,
        workflow_dispatches=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)
    return text,proof


def check():
    text,proof=derive()
    require((HERE/TEMPLATE).read_bytes()==text.encode(),'MANDOR_WORKFLOW_EXACT_REVIEWABLE_TEMPLATE_REQUIRED')
    active=ROOT/WORKFLOW
    if active.exists():
        import qualification
        qualification.actual_parent()
        manifest=json.loads((ROOT/'scripts/current-unified-candidate/SOURCE.json').read_bytes())
        expected=dict(bytes=len(text.encode()),sha256=sha256(text.encode()).hexdigest())
        require(not active.is_symlink()and active.read_bytes()==text.encode()
            and manifest['files'].get(WORKFLOW)==expected,'MANDOR_WORKFLOW_EXPLICIT_BOUND_ACTIVE_SOURCE_REQUIRED')
        proof['status']='MANDOR17_EXPLICIT_ACTIVATED_SOURCE_MATCHES_TEMPLATE'
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true',required=True);parser.parse_args()
    print(json.dumps(check(),sort_keys=True))
