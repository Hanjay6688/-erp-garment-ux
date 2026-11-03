"""Reviewable current-parent SKU workflow data; never installs or dispatches."""
from copy import deepcopy
from pathlib import Path
import argparse,json
import sku_current_parent_admission as admission

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NS='scripts/current-sku-composite-preparation/'
ORIGINAL='scripts/current-mandor-shop-native-qualification/mandor17.workflow.yml.txt'
ORIGINAL_PIN=dict(bytes=34828,sha256='a29ba9cf681c11f38d4057e8446abf96f33f3e223b7b55810d9830cffec61902')
TEMPLATE='sku-current-parent-native6.workflow.yml.txt'
WORKFLOW='.github/workflows/cp7-sku-current-parent-native6.yml'
BRANCH='astra-a/sku-current-parent-native6-20261103'
ROUTED=(0,2,3,64,65,66,67,72,75,76,77,78)


def require(value,message):
    if not value:raise ValueError(message)


def derive():
    import yaml
    raw=(ROOT/ORIGINAL).read_bytes()
    require(admission.pin(raw)==ORIGINAL_PIN,'SKU_COMPOSITE_EXACT_MANDOR79_TEMPLATE')
    original=yaml.safe_load(raw);value=deepcopy(original)
    require(set(value['jobs'])=={'p21'}and len(value['jobs']['p21']['steps'])==79,'SKU_COMPOSITE_COMPLETE_ORIGINAL79')
    value['name']='CP7 A current Mandor parent SKU Native6'
    value['on']['push']=dict(branches=[BRANCH],paths=[WORKFLOW,NS+'**'])
    value['concurrency']['group']='cp7-current-parent-sku6-single-owning-qualification'
    job=value['jobs']['p21'];job['name']='Current accepted Mandor parent and SKU Native6; complete restoration'
    job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    require(job['env'].pop('MANDOR_NATIVE_CONFIRM')=='cp6_rollback','SKU_COMPOSITE_ORIGINAL_DISPOSABLE_CONFIRMATION')
    job['env']['SKU_CURRENT_PARENT_CONFIRM']='cp6_rollback'
    steps=job['steps'];before=original['jobs']['p21']['steps']
    require(steps[0]['run'].count('MANDOR_NATIVE_JOB_START_MONOTONIC')==1,'SKU_COMPOSITE_ONE_REAL_JOB_CLOCK')
    steps[0]['name']='Record actual current-parent SKU job start before setup and admission'
    steps[0]['run']=steps[0]['run'].replace('MANDOR_NATIVE_JOB_START_MONOTONIC','SKU_CURRENT_PARENT_JOB_START_MONOTONIC',1)
    steps[2]=dict(name='Materialize exact accepted Mandor, SKU and Afui trees without fetch or rewrite',
        **{'working-directory':'auditor'},run='python -B '+NS+'sku_current_parent_materialize.py\n')
    steps[3]['name']='Require genuine six-hour WIB window before current-parent SKU setup'
    steps[64]=dict(name='Fetch exact accepted Afui, Mandor17 and SKU6 canonical archives before database',
        **{'working-directory':'auditor'},env={'GH_TOKEN':'${{ github.token }}'},
        run='set -euo pipefail\npython -B ../qualified-mandor-parent/scripts/current-mandor-shop-native-qualification/fetch_parent.py\n'
            'python -B '+NS+'sku_current_parent_fetch.py\n')
    steps[65]=dict(name='Verify complete owning source and exact prepared workflow before database',
        **{'working-directory':'auditor'},run='set -euo pipefail\npython -B '+NS+'check_source.py\n'
            'python -B '+NS+'sku_current_parent_workflow.py --check\n')
    steps[66]=dict(name='Copy exact prerequisites into all three frozen trees before runtime admission',
        **{'working-directory':'auditor'},run='python -B '+NS+'sku_current_parent_artifacts.py --prepare\n')
    steps[67]=dict(name='Admit complete current-parent SKU graph under database network fence',
        **{'working-directory':'writer'},run='set -euo pipefail\npython -B ../auditor/'+NS+'sku_current_parent_runtime.py --check\n'
            'python -B ../auditor/scripts/current-de-free-date-preparation/attempt_policy.py --require-window\n')
    steps[72]=dict(name='Run current-parent SKU Native6 once with owning restoration and final gate',
        **{'working-directory':'writer'},run='set -euo pipefail\npython -u -B ../auditor/'+NS+'sku_current_parent_supervisor.py\n'
            'python -B ../auditor/'+NS+'sku_current_parent_final_gate.py\n')
    steps[75]=dict(name='Retain every new or changed output in all frozen trees even on failure',
        **{'if':'always()','working-directory':'auditor'},run='python -B '+NS+'sku_current_parent_artifacts.py --retain\n')
    steps[76]=dict(name='Retain bounded original hash receipts without printing full report bodies',
        **{'if':'always()','working-directory':'auditor'},run='python -B '+NS+'sku_current_parent_receipts.py\n')
    old='scripts/current-mandor-shop-native-qualification/runtime_supervisor.py'
    require(steps[77]['run'].count(old)==1,'SKU_COMPOSITE_ONE_OWNED_DATABASE_STOP_ROUTE')
    steps[77]['run']=steps[77]['run'].replace(old,NS+'sku_current_parent_supervisor.py',1)
    steps[78]['with']['name']='cp7-sku-current-parent-native6-${{ github.run_attempt }}'
    require([i for i in range(79)if steps[i]!=before[i]]==list(ROUTED),'SKU_COMPOSITE_ONLY_TWELVE_OWNING_STEP_ROUTES')
    require(steps[1]==before[1]and steps[68:72]==before[68:72]and steps[73:75]==before[73:75],
        'SKU_COMPOSITE_ORIGINAL_CHECKOUT_DATABASE_CLONE_AND_RETENTION')
    require(job['timeout-minutes']==360 and value['permissions']==original['permissions']
        and value['concurrency']['cancel-in-progress']is False,'SKU_COMPOSITE_ORIGINAL_AUTHORITY_AND_BUDGETS')
    text=yaml.safe_dump(value,sort_keys=False,allow_unicode=True)
    require(yaml.safe_load(text)==value,'SKU_COMPOSITE_EXACT_YAML_ROUNDTRIP')
    return text,dict(status='CURRENT_PARENT_SKU_NATIVE6_WORKFLOW_DATA_ONLY_NOT_ACTIVATED',
        original_template=ORIGINAL_PIN,total_steps=79,unchanged_parent_steps=67,routed_parent_steps=12,
        original_database_rebuild_clone_and_recovery_unchanged=True,job_budget_minutes=360,
        supervision_330_20_10_unchanged=True,report_bodies_printed=False,complete_artifact_upload_retained=True,
        workflow_dispatches=0,actual_composite_cases=0,production_go=False,independent_acceptance=False)


def check():
    text,proof=derive()
    require((HERE/TEMPLATE).read_bytes()==text.encode(),'SKU_COMPOSITE_EXACT_REVIEWABLE_TEMPLATE_REQUIRED')
    manifest=json.loads((HERE/'SOURCE.json').read_bytes());active=ROOT/WORKFLOW
    if active.exists():
        import sku_current_parent_runtime as runtime
        runtime.actual_inputs()
        require(manifest['active_workflow_added']is True and not active.is_symlink()
            and active.read_bytes()==text.encode()and manifest.get('active_workflow_source')==admission.pin(text.encode()),
            'SKU_COMPOSITE_EXPLICIT_BOUND_ACTIVE_WORKFLOW_SOURCE')
        proof['status']='CURRENT_PARENT_SKU_EXPLICIT_ACTIVATED_SOURCE_MATCHES_TEMPLATE'
    else:require(manifest['active_workflow_added']is False and manifest.get('active_workflow_source')is None,
        'SKU_COMPOSITE_PREPARED_WORKFLOW_STAYS_INACTIVE')
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true',required=True);parser.parse_args()
    print(json.dumps(check(),sort_keys=True))
