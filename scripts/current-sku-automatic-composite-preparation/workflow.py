"""Reviewable Native25 workflow data; never installs or dispatches itself."""
from copy import deepcopy
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-sku-automatic-composite-preparation/'
ORIGINAL = ROOT / 'scripts/current-sku-money-composite-preparation/sku-current-parent-money-native19.workflow.yml.txt'
PIN = dict(bytes=33997, sha256='baa5fd02b024837856276f9e7136ca555c2bb6bb9255b0c5f0c2068322494e5d')
TEMPLATE = HERE / 'sku-current-parent-money-automatic-native25.workflow.yml.txt'
ACTIVE = ROOT / '.github/workflows/cp7-sku-current-parent-money-automatic-native25.yml'
BRANCH = 'astra-a/sku-current-parent-money-automatic-native25-20261105'
ROUTED = (0, 2, 3, 64, 65, 66, 67, 72, 75, 76, 77, 78)


def runtime():
    spec = importlib.util.spec_from_file_location('automatic_workflow_owning_runtime', HERE / 'qualification.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(value, message):
    if not value:
        raise ValueError(message)


def derive(raw=None):
    import yaml
    owner = runtime()
    if raw is None:
        raw = ORIGINAL.read_bytes()
    require(owner.admission.pin(raw) == PIN, 'AUTOMATIC_EXACT_RETAINED_MONEY79_WORKFLOW_REQUIRED')
    original = yaml.safe_load(raw)
    require(set(original['jobs']) == {'p21'} and len(original['jobs']['p21']['steps']) == 79,
            'AUTOMATIC_COMPLETE_RETAINED_79_STEPS_REQUIRED')
    value = deepcopy(original)
    value['name'] = 'CP7 A current Mandor parent SKU money automatic Native25'
    value['on']['push'] = dict(branches=[BRANCH], paths=[str(ACTIVE.relative_to(ROOT)), NS + '**'])
    value['concurrency']['group'] = 'cp7-current-parent-money-automatic25-single-owning-qualification'
    job = value['jobs']['p21']
    job['name'] = 'Actual Mandor parent, full money and automatic Native25; complete restoration'
    job['if'] = "github.ref == 'refs/heads/" + BRANCH + "'"
    require(job['env'].pop('SKU_CURRENT_PARENT_MONEY_CONFIRM') == 'cp6_rollback',
            'AUTOMATIC_RETAINED_DISPOSABLE_DATABASE_CONFIRMATION_REQUIRED')
    job['env']['SKU_CURRENT_AUTOMATIC_CONFIRM'] = 'cp6_rollback'
    steps = job['steps']
    before = original['jobs']['p21']['steps']
    require(steps[0]['run'].count('SKU_CURRENT_PARENT_MONEY_JOB_START_MONOTONIC') == 1,
            'AUTOMATIC_ONE_REAL_JOB_START_REQUIRED')
    steps[0]['name'] = 'Record actual Native25 job start before setup and admission'
    steps[0]['run'] = steps[0]['run'].replace('SKU_CURRENT_PARENT_MONEY_JOB_START_MONOTONIC',
                                             'SKU_CURRENT_AUTOMATIC_JOB_START_MONOTONIC', 1)
    steps[2] = dict(name='Materialize exact Mandor, money, Afui and automatic trees without fetch or rewrite',
                    **{'working-directory': 'auditor'}, run='python -B ' + NS + 'execution.py materialize\n')
    steps[3]['name'] = 'Require genuine six-hour WIB window before Native25 setup'
    steps[64] = dict(name='Fetch exact accepted Afui, Mandor17, Native27 and moving6 inputs before database',
                     **{'working-directory': 'auditor'}, env={'GH_TOKEN': '${{ github.token }}'},
                     run='set -euo pipefail\npython -B ../qualified-mandor-parent/scripts/current-mandor-shop-native-qualification/fetch_parent.py\n'
                         'python -B ' + NS + 'execution.py fetch\n')
    steps[65] = dict(name='Verify complete actual owning source and reviewable workflow before database',
                     **{'working-directory': 'auditor'}, run='set -euo pipefail\npython -B ' + NS + 'check_source.py --runtime\n'
                         'python -B ' + NS + 'workflow.py --check\n')
    steps[66] = dict(name='Copy exact prerequisites into all four frozen trees before runtime admission',
                     **{'working-directory': 'auditor'}, run='python -B ' + NS + 'execution.py prepare\n')
    steps[67] = dict(name='Admit full money and natural Native25 graph under database network fence',
                     **{'working-directory': 'writer'}, run='set -euo pipefail\npython -B ../auditor/' + NS + 'execution.py check-money-source\n'
                         'python -B ../auditor/' + NS + 'qualification.py --check\n'
                         'python -B ../auditor/scripts/current-de-free-date-preparation/attempt_policy.py --require-window\n')
    steps[72] = dict(name='Run current-parent money automatic Native25 and real browser2 once with owning restoration',
                     **{'working-directory': 'writer'}, run='set -euo pipefail\npython -u -B ../auditor/' + NS + 'execution.py supervise\n'
                         'python -B ../auditor/' + NS + 'final_gate.py\n')
    steps[75] = dict(name='Retain every new or changed output in all four frozen trees even on failure',
                     **{'if': 'always()', 'working-directory': 'auditor'}, run='python -B ' + NS + 'execution.py retain\n')
    steps[76] = dict(name='Retain bounded hashes while complete Original files stay in the artifact',
                     **{'if': 'always()', 'working-directory': 'auditor'}, run='python -B ' + NS + 'execution.py receipts\n')
    old = 'scripts/current-sku-money-composite-preparation/money_current_parent_supervisor.py'
    require(steps[77]['run'].count(old) == 1, 'AUTOMATIC_ONE_GUARDED_DISPOSABLE_DATABASE_STOP_REQUIRED')
    steps[77]['run'] = steps[77]['run'].replace(old, NS + 'execution.py supervise', 1)
    steps[78]['with']['name'] = 'cp7-sku-current-parent-money-automatic-native25-${{ github.run_attempt }}'
    require([i for i in range(79) if steps[i] != before[i]] == list(ROUTED),
            'AUTOMATIC_ONLY_TWELVE_OWNING_WORKFLOW_STEPS_CHANGE')
    require(steps[1] == before[1] and steps[68:72] == before[68:72] and steps[73:75] == before[73:75],
            'AUTOMATIC_CHECKOUT_DATABASE_CLONE_RECOVERY_AND_ORIGINAL_RETENTION_UNCHANGED')
    require(job['timeout-minutes'] == 360 and value['permissions'] == original['permissions']
            and value['concurrency']['cancel-in-progress'] is False,
            'AUTOMATIC_ORIGINAL_BUDGET_AUTHORITY_AND_SINGLE_WRITER_REQUIRED')
    text = yaml.safe_dump(value, sort_keys=False, allow_unicode=True)
    require(yaml.safe_load(text) == value, 'AUTOMATIC_EXACT_WORKFLOW_YAML_ROUNDTRIP_REQUIRED')
    return text, dict(status='NATIVE25_WORKFLOW_DATA_ONLY_NOT_ACTIVATED', retained_template=PIN,
                      total_steps=79, unchanged_steps=67, owning_routes=12, frozen_source_trees=4,
                      database_rebuild_clone_recovery_and_full_artifact_upload_unchanged=True,
                      real_360_330_20_10_budgets_unchanged=True, workflow_dispatches=0, actual_ERP_cases=0,
                      actual_Auth_HTTP_cases=0, actual_browser_cases=0, production_go=False)


def check():
    text, proof = derive()
    require(TEMPLATE.is_file() and not TEMPLATE.is_symlink() and TEMPLATE.read_bytes() == text.encode(),
            'AUTOMATIC_EXACT_REVIEWABLE_WORKFLOW_TEMPLATE_REQUIRED')
    manifest = json.loads((HERE / 'SOURCE.json').read_bytes())
    if ACTIVE.exists() or ACTIVE.is_symlink():
        owner = runtime()
        owner.actual_inputs()
        require(manifest['active_workflow_added'] is True and not ACTIVE.is_symlink()
                and ACTIVE.read_bytes() == text.encode()
                and manifest.get('active_workflow_source') == owner.admission.pin(text.encode()),
                'AUTOMATIC_EXPLICIT_ACTUAL_BOUND_ACTIVE_WORKFLOW_REQUIRED')
        proof['status'] = 'NATIVE25_ACTUAL_BOUND_ACTIVE_WORKFLOW_MATCHES_REVIEWED_TEMPLATE'
    else:
        require(manifest['active_workflow_added'] is False and manifest.get('active_workflow_source') is None,
                'AUTOMATIC_PREPARED_WORKFLOW_MUST_REMAIN_INACTIVE')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(check(), sort_keys=True))
