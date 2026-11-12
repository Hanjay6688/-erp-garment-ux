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
AFUI_TEMPLATE = ROOT / 'scripts/cp7_accessory_nonpayable/afui15.workflow.yml.txt'
PGDG_SETUP_PIN = dict(bytes=1240, sha256='6500c7bbd60b461bbefd1ccbe7b3eb0b292a6600466a19cb3cc14d45666ac5c3')
BASELINE_TEMPLATE = HERE / 'sku-current-parent-money-automatic-native25-81.workflow.yml.txt'
TEMPLATE = HERE / 'sku-current-parent-money-automatic-native25-83.workflow.yml.txt'
ACTIVE = ROOT / '.github/workflows/cp7-sku-current-parent-money-automatic-native25.yml'
BRANCH = 'astra-a/sku-current-parent-money-automatic-native25-20261105'
ROUTED = (0, 2, 3, 11, 64, 65, 66, 67, 72, 75, 76, 77, 78)
SETUP_STEPS = ('Start disposable database', 'Rebuild to v2.6.20, align with hosted, continue the frozen path to AB',
               'Provision isolated rollback authority', 'Clone the aligned AB state for install')
SETUP_DELIMITER = 'CP7_WIB_DISPOSABLE_SETUP'
DIRECT_UBUNTU_ARCHIVE = '''ubuntu_sources=/etc/apt/sources.list.d/ubuntu.sources
if [ -r "$ubuntu_sources" ] && grep -qFx 'URIs: mirror+file:/etc/apt/apt-mirrors.txt' "$ubuntu_sources"; then
  sed 's|^URIs: mirror+file:/etc/apt/apt-mirrors.txt$|URIs: https://archive.ubuntu.com/ubuntu/|' \
    "$ubuntu_sources" > "$RUNNER_TEMP/cp7-ubuntu.sources"
  sudo -n install -m 0644 "$RUNNER_TEMP/cp7-ubuntu.sources" "$ubuntu_sources"
fi
'''


def runtime():
    spec = importlib.util.spec_from_file_location('automatic_workflow_owning_runtime', HERE / 'qualification.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(value, message):
    if not value:
        raise ValueError(message)


def setup_with_window(command):
    require(SETUP_DELIMITER not in command, 'AUTOMATIC_SETUP_SCRIPT_DELIMITER_REQUIRED')
    return ('set -euo pipefail\n'
            'limit="$(python -B "$GITHUB_WORKSPACE/auditor/' + NS + 'run_window.py" --setup-limit)"\n'
            'bounded=()\n'
            'if [ -n "$limit" ]; then bounded=(timeout --kill-after=10s "$limit"); fi\n'
            '"${bounded[@]}" bash -e -u -o pipefail -c "$(cat <<\'' + SETUP_DELIMITER + '\'\n'
            + command.rstrip('\n') + '\n' + SETUP_DELIMITER + '\n)"\n')


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
    pgdg_setup = yaml.safe_load(AFUI_TEMPLATE.read_bytes())['jobs']['p21']['steps'][10]
    require(pgdg_setup['name'] == steps[11]['name'] == 'Install pinned disposable runtime'
            and owner.admission.pin(pgdg_setup['run'].encode()) == PGDG_SETUP_PIN,
            'AUTOMATIC_EXACT_Afui_PGDG_RETRY_SOURCE_REQUIRED')
    steps[11]['run'] = pgdg_setup['run']
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
                         'node ../auditor/' + NS + 'browser.mjs --check-browser-source\n'
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
            'AUTOMATIC_ONLY_EXACT_OWNING_WORKFLOW_STEPS_CHANGE')
    require(steps[1] == before[1] and steps[68:72] == before[68:72] and steps[73:75] == before[73:75],
            'AUTOMATIC_CHECKOUT_DATABASE_CLONE_RECOVERY_AND_ORIGINAL_RETENTION_UNCHANGED')
    require(job['timeout-minutes'] == 360 and value['permissions'] == original['permissions']
            and value['concurrency']['cancel-in-progress'] is False,
            'AUTOMATIC_ORIGINAL_BUDGET_AUTHORITY_AND_SINGLE_WRITER_REQUIRED')
    retained_steps = deepcopy(steps)
    prerequisites = [
        dict(name='Install pinned browser dependencies in both actual checkout roots before database',
             run='set -euo pipefail\nfor checkout in auditor writer; do\n'
                 '  (cd "$GITHUB_WORKSPACE/$checkout" && npm ci --include=dev && npx --no-install playwright install --with-deps chromium)\n'
                 'done\n'),
        dict(name='Open actual desktop and mobile browsers and compile exact SKU candidate before database',
             **{'working-directory': 'auditor'},
             run='set -euo pipefail\npython -B ' + NS + 'browser_runtime.py --check\n'
                 'node ' + NS + 'browser_prerequisites.mjs "$GITHUB_WORKSPACE"\n'),
    ]
    require(steps[68]['name'] == 'Start disposable database', 'AUTOMATIC_EXACT_DATABASE_SETUP_BOUNDARY')
    steps[68:68] = prerequisites
    require(len(steps) == 81 and steps[:68] + steps[70:] == retained_steps,
            'AUTOMATIC_ALL_ORIGINAL_79_STEPS_MUST_REMAIN_EXACT')
    baseline = yaml.safe_dump(value, sort_keys=False, allow_unicode=True).encode()
    require(not BASELINE_TEMPLATE.is_symlink() and BASELINE_TEMPLATE.read_bytes() == baseline,
            'AUTOMATIC_EXACT_PRIOR_81_STEP_WORKFLOW_REQUIRED')
    checkpoint_steps = [
        dict(name='Write diagnostic source checkpoint before Native25',
             **{'working-directory': 'auditor'},
             run='set -euo pipefail\n'
                 'python -B -m unittest discover -s ' + NS + ' -p test_runtime_receipt.py\n'
                 'python -B -m unittest discover -s ' + NS + ' -p test_run_window.py\n'
                 'python -B -m unittest discover -s ' + NS + ' -p test_setup_sequences.py\n'
                 'python -B ' + NS + 'checkpoint.py --source . '
                 '--output "$RUNNER_TEMP/cp7-source-checkpoint/CP7_DIAGNOSTIC_CHECKPOINT.json"\n'),
        {'name': 'Persist diagnostic checkpoint before long runtime',
         'uses': 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',
         'with': {'name': 'cp7-sku-admission-checkpoint-${{ github.run_id }}-${{ github.run_attempt }}',
                  'path': '${{ runner.temp }}/cp7-source-checkpoint/CP7_DIAGNOSTIC_CHECKPOINT.json',
                  'retention-days': 30, 'if-no-files-found': 'error'}},
    ]
    steps[70:70] = checkpoint_steps
    old_window = 'scripts/current-de-free-date-preparation/attempt_policy.py --require-window'
    require(steps[3]['run'].count(old_window) == steps[67]['run'].count(old_window) == 1,
            'AUTOMATIC_EXACT_RETAINED_WINDOW_CHECKS_REQUIRED')
    steps[3]['name'] = 'Record the real WIB work deadline and restoration reserves'
    steps[3]['run'] = steps[3]['run'].replace(old_window, NS + 'run_window.py --record', 1)
    steps[67]['run'] = steps[67]['run'].replace(old_window, NS + 'run_window.py --require', 1)
    require(tuple(step['name'] for step in steps[72:76]) == SETUP_STEPS,
            'AUTOMATIC_EXACT_DISPOSABLE_DATABASE_SETUP_STEPS_REQUIRED')
    for step in steps[72:76]:
        step['run'] = setup_with_window(step['run'])
    # The hosted image already lists this official archive as a fallback.
    # Address it directly while preserving the source suites and signing keys.
    header = 'set -euo pipefail\n'
    require(steps[11]['run'].startswith(header), 'AUTOMATIC_PINNED_RUNTIME_STRICT_SHELL_REQUIRED')
    steps[11]['run'] = header + DIRECT_UBUNTU_ARCHIVE + steps[11]['run'].removeprefix(header)
    steps[68]['run'] = setup_with_window('''for checkout in auditor writer; do
  (cd "$GITHUB_WORKSPACE/$checkout" && npm ci --include=dev)
done
(cd "$GITHUB_WORKSPACE/auditor" && npx --no-install playwright install --with-deps chromium)
(cd "$GITHUB_WORKSPACE/writer" && npx --no-install playwright install chromium)
''')
    require(steps[81]['name'] == 'Remove disposable database' and steps[81]['if'] == 'always()'
            and steps[82]['with']['name'] == 'cp7-sku-current-parent-money-automatic-native25-${{ github.run_attempt }}',
            'AUTOMATIC_EXACT_CLEANUP_AND_UPLOAD_BOUNDARIES_REQUIRED')
    steps[72]['id'] = 'cp7_disposable_start'
    steps[76]['id'] = 'cp7_sku_runtime'
    steps[81]['id'] = 'cp7_disposable_cleanup'
    steps[81]['if'] = ("${{ always() && (steps.cp7_disposable_start.outcome == 'success' || "
                       "steps.cp7_disposable_start.outcome == 'failure' || "
                       "steps.cp7_disposable_start.outcome == 'cancelled') }}")
    steps[82]['with']['name'] = (
        "${{ job.status == 'success' && steps.cp7_sku_runtime.outcome == 'success' && "
        "steps.cp7_disposable_cleanup.outcome == 'success' && "
        "format('cp7-sku-current-parent-money-automatic-native25-{0}', github.run_attempt) || "
        "format('cp7-sku-failure-{0}-{1}', github.run_id, github.run_attempt) }}")
    text = yaml.safe_dump(value, sort_keys=False, allow_unicode=True)
    require(yaml.safe_load(text) == value, 'AUTOMATIC_EXACT_WORKFLOW_YAML_ROUNDTRIP_REQUIRED')
    return text, dict(status='NATIVE25_WORKFLOW_DATA_ONLY_NOT_ACTIVATED', retained_template=PIN,
                      total_steps=83, retained_steps=79, unchanged_steps=len(before) - len(ROUTED) - len(SETUP_STEPS),
                      owning_routes=len(ROUTED) + len(SETUP_STEPS),
                      added_browser_prerequisite_steps=2, added_diagnostic_checkpoint_steps=2,
                      frozen_source_trees=4,
                      actual_both_checkout_browser_prerequisites_before_database=True,
                      database_rebuild_clone_recovery_and_artifact_members_unchanged=True,
                      direct_signed_ubuntu_archive_and_two_locked_browser_installs=True,
                      database_cleanup_requires_attempted_start_and_original_receipt=True,
                      canonical_archive_name_requires_completed_worker_and_cleanup=True,
                      real_WIB_window_caps_short_setup_and_worker=True,
                      normal_360_330_20_10_budgets_unchanged=True, workflow_dispatches=0, actual_ERP_cases=0,
                      actual_Auth_HTTP_cases=0, actual_browser_cases=0, production_go=False)


def check():
    text, proof = derive()
    require(TEMPLATE.is_file() and not TEMPLATE.is_symlink() and TEMPLATE.read_bytes() == text.encode(),
            'AUTOMATIC_EXACT_REVIEWABLE_WORKFLOW_TEMPLATE_REQUIRED')
    manifest = json.loads((HERE / 'SOURCE.json').read_bytes())
    require(manifest['reviewable_workflow_steps'] == proof['total_steps']
            and manifest['files'][TEMPLATE.name] == runtime().admission.pin(text.encode()),
            'AUTOMATIC_WORKFLOW_TEMPLATE_MANIFEST_PIN_REQUIRED')
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
