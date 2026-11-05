"""Reviewable current Mandor84 workflow, inactive until actual Afui adoption.

Preserve the current 80-step Afui chain, including its real upload preflight.
Eleven owning routes and four exact parent/output steps replace no database,
installer, clone, recovery, supervisor or financial case implementation.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-mandor-shop-native-qualification/'
OWN = 'scripts/current-mandor-afui-preparation/'
ORIGINAL = ROOT / 'scripts/cp7_accessory_nonpayable/afui15.workflow.yml.txt'
PIN = dict(bytes=36800, sha256='d45d02395bccc2226c1eda637ab3e4a998deaddc52025390870335bddeb667f5')
TEMPLATE = HERE / 'current-mandor84.workflow.yml.txt'
ACTIVE = ROOT / '.github/workflows/cp7-mandor-shop-native17.yml'
BRANCH = 'astra-a/mandor-shop-native9-on-unified-20261103'
ROUTED = (0, 2, 62, 63, 64, 68, 73, 74, 77, 78, 79)


def require(value, message):
    if not value:
        raise ValueError(message)


def derive(raw=None):
    import yaml
    if raw is None:
        raw = ORIGINAL.read_bytes()
    require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == PIN, 'MANDOR84_EXACT_CURRENT_AFUI80_TEMPLATE_REQUIRED')
    original = yaml.safe_load(raw);value = deepcopy(original)
    require(set(value['jobs']) == {'p21','browser_prerequisites_only'} and len(value['jobs']['p21']['steps']) == 80, 'MANDOR84_COMPLETE_CURRENT_AFUI80_CHAIN')
    value['name'] = 'CP7 A current Afui parent Mandor Native9 session4 HTTP2 browser2 full17'
    value['on']['push'] = dict(branches=[BRANCH], paths=[str(ACTIVE.relative_to(ROOT)), NS + '**', OWN + '**',
        'scripts/cp7_mandor_shop/**', 'src/**', 'scripts/check-source-ownership.mjs', 'scripts/check-access-catalog.mjs'])
    value['concurrency']['group'] = 'cp7-mandor-shop17-single-owning-qualification'
    job = value['jobs']['p21'];job['name'] = 'Current Mandor17 with complete Originals and owning restoration'
    job['if'] = "github.ref == 'refs/heads/" + BRANCH + "'"
    require(job['env'].pop('AFUI_CONFIRM') == 'cp6_rollback', 'MANDOR84_ORIGINAL_DISPOSABLE_CONFIRMATION')
    job['env']['MANDOR_NATIVE_CONFIRM'] = 'cp6_rollback'
    steps, before = job['steps'], original['jobs']['p21']['steps']
    require(steps[0]['run'].count('AFUI_JOB_START_MONOTONIC') == 1, 'MANDOR84_ONE_REAL_ORIGINAL_JOB_CLOCK')
    steps[0]['name'] = 'Record monotonic Mandor job start before setup and admission'
    steps[0]['run'] = steps[0]['run'].replace('AFUI_JOB_START_MONOTONIC', 'MANDOR_NATIVE_JOB_START_MONOTONIC', 1)
    steps[2]['name'] = 'Require genuine six-hour WIB window before current Mandor setup'
    steps[62] = dict(name='Fetch exact independently accepted current Afui15 archive before database',
        **{'working-directory': 'auditor'}, env={'GH_TOKEN': '${{ github.token }}'},
        run='python -B ' + NS + 'fetch_parent.py\n')
    steps[63] = dict(name='Verify complete current Mandor source, transport and owning workflow before database',
        **{'working-directory': 'auditor'}, run='set -euo pipefail\npython -B ' + OWN + 'workflow.py --check\n'
            'python -B ' + OWN + 'transport.py --check\npython -B ' + OWN + 'check_source.py\n'
            'python -B scripts/cp7_accessory_nonpayable/qualification.py --check-static\n'
            'node --test ' + OWN + 'durable_action.test.mjs\n')
    steps[64] = dict(name='Admit genuine Afui15 and whole current Mandor graph under database network fence',
        **{'working-directory': 'writer'}, run='set -euo pipefail\npython -B ../auditor/' + NS + 'qualification.py --check\n'
            'python -B ../auditor/scripts/current-de-free-date-preparation/attempt_policy.py --require-window\n')
    for index, mode in ((68, 'preflight'), (73, 'runtime')):
        steps[index] = dict(name=('Confirm actual Mandor Original upload before database' if mode == 'preflight' else
            'Run current Mandor17 once and retain complete Originals during owning restoration'),
            uses='./auditor/' + OWN, **{'with': dict(mode=mode)})
    steps[74] = dict(name='Require complete Mandor17, all five gates, restoration and reaped worker',
        **{'working-directory': 'writer'}, run='python -B ../auditor/' + NS + 'final_gate.py\n')
    for old, new in (
            ('CP7_AFUI_GOOD_NONPAYABLE_FULL15_CASES_BUSINESS_DAY_FIRST_ATTEMPT', 'CP7_FG_MANDOR_NATIVE9_STRICT_BUSINESS_DAY_FIRST_ATTEMPT'),
            ('CP7_AFUI_GOOD_NONPAYABLE_FULL15_CASES', 'CP7_FG_MANDOR_NATIVE9_STRICT'),
            ('CP7_AFUI_GOOD_NONPAYABLE_FULL15', 'CP7_FG_MANDOR_NATIVE9'),
            ('AFUI_FINAL_GATE', 'MANDOR_NATIVE9_FINAL_GATE'),
            ('FREE3_PARENT_ORIGINAL_ADMISSION', 'AFUI15_PARENT_ORIGINAL_ADMISSION'),
            ('AFUI_RUNTIME_SUPERVISION', 'MANDOR_RUNTIME_SUPERVISION')):
        first, second = repr(old + '.json'), repr(new + '.json')
        require(steps[77]['run'].count(first) == 1 and second not in steps[77]['run'], 'MANDOR84_ONE_EXACT_COMPLETE_RECEIPT_ROUTE')
        steps[77]['run'] = steps[77]['run'].replace(first, second, 1)
    old = 'scripts/cp7_accessory_nonpayable/runtime_supervisor.py'
    require(steps[78]['run'].count(old) == 1, 'MANDOR84_ONE_GUARDED_DATABASE_STOP')
    steps[78]['run'] = steps[78]['run'].replace(old, NS + 'runtime_supervisor.py', 1)
    steps[79]['with']['name'] = 'cp7-mandor-shop-native17-${{ github.run_attempt }}'
    require([i for i in range(80) if steps[i] != before[i]] == list(ROUTED), 'MANDOR84_ONLY_ELEVEN_OWNING_ROUTES')
    additions = {
        1: dict(name='Materialize only the exact independently accepted Afui parent without fetching or rewriting',
                **{'working-directory': 'auditor'}, run='python -B ' + NS + 'materialize_parent.py\n'),
        62: dict(name='Copy exact prerequisite Originals into the frozen Afui worktree before source admission',
                 **{'working-directory': 'auditor'}, run='python -B ' + NS + 'parent_artifacts.py --prepare\n'),
        76: dict(name='Retain every complete changed or new frozen-parent output even after failure',
                 **{'if': 'always()', 'working-directory': 'auditor'}, run='python -B ' + NS + 'parent_artifacts.py --retain\n'),
        77: dict(name='Retain current Mandor transport and copy Original byte receipts',
                 **{'if': 'always()', 'working-directory': 'auditor'}, run='python -B ' + OWN + 'receipts.py\n'),
    }
    job['steps'] = [item for index, step in enumerate(steps) for item in ([step, additions[index]] if index in additions else [step])]
    require(len(job['steps']) == 84 and job['timeout-minutes'] == 360 and value['permissions'] == original['permissions']
            and value['concurrency']['cancel-in-progress'] is False, 'MANDOR84_EXACT_BUDGET_AUTHORITY_AND_SINGLE_OWNER')
    require(steps[1] == before[1] and steps[65:68] == before[65:68] and steps[69:73] == before[69:73]
            and steps[75:77] == before[75:77], 'MANDOR84_COMPLETE_CHECKOUT_OFFICIAL_UPLOADER_DATABASE_CLONE_AND_RETENTION_UNCHANGED')
    require(value['jobs']['browser_prerequisites_only'] == original['jobs']['browser_prerequisites_only'], 'MANDOR84_PARENT_READ_ONLY_JOB_UNCHANGED')
    text = yaml.safe_dump(value, sort_keys=False, allow_unicode=True)
    require(yaml.safe_load(text) == value, 'MANDOR84_EXACT_YAML_ROUNDTRIP')
    return text, dict(status='CURRENT_MANDOR84_WORKFLOW_PREPARED_NOT_ACTIVATED', original=PIN,
        original_steps=80, unchanged_steps=69, owning_routes=11, added_parent_and_receipt_steps=4, total_steps=84,
        original_database_clone_recovery_and_complete_final_artifact_upload_unchanged=True,
        actual_360_330_20_10_budgets_and_first_attempt_identity_required=True,
        current_Afui15_Root_both_admission_families_and_successor_source_fence_rebinding_still_required=True,
        workflow_dispatches=0, actual_ERP_cases=0, production_go=False, independent_acceptance=False)


def check():
    text, proof = derive()
    require(TEMPLATE.is_file() and not TEMPLATE.is_symlink() and TEMPLATE.read_bytes() == text.encode(),
            'MANDOR84_EXACT_REVIEWABLE_COMPLETE_TEMPLATE')
    require(not ACTIVE.exists() and not ACTIVE.is_symlink(), 'MANDOR84_ACTUAL_AFUI_ADOPTION_AND_SOURCE_FENCE_REBINDING_PENDING')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--check', action='store_true', required=True);parser.parse_args()
    print(json.dumps(check(), sort_keys=True))
