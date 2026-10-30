"""Bounded semantic child of the complete vendor qualification workflow."""
from copy import deepcopy
from pathlib import Path

NAMESPACE = 'scripts/current-attendance-choice-browser4-lawful-successor'
WORKFLOW = '.github/workflows/cp7-current-s03-browser4-lawful.yml'
BRANCH = 'astra-a/s03-browser4-lawful-qualification-20261030'
PARENT = '.github/workflows/cp7-current-vendor-receivable-native.yml'


def one(steps, name):
    found = [step for step in steps if step.get('name') == name]
    if len(found) != 1:
        raise ValueError('S03_BROWSER4_EXACT_PARENT_WORKFLOW_STEP_REQUIRED:' + name)
    return found[0]


def derive(original):
    value = deepcopy(original)
    value['name'] = 'CP7 S03 lawful fixture normal App real Auth browser4'
    value['on'] = {'push': {'branches': [BRANCH], 'paths': [WORKFLOW, NAMESPACE + '/**']}, 'workflow_dispatch': {}}
    value['concurrency']['group'] = 'cp7-s03-browser4-${{ github.run_id }}'
    job = value['jobs']['p21']
    job['name'] = 'S03 real browser4 and complete original restore'
    # Actual30ee exhausted120min after desktop and mobile. Keep four complete
    # journeys plus outer restoration; do not shorten financial observations.
    job['timeout-minutes'] = 240
    job['if'] = "github.ref == 'refs/heads/" + BRANCH + "'"
    job['env']['AUDITOR_UI_MODE'] = 'DISPOSABLE'
    steps = job['steps']
    checkout = next(step for step in steps if step.get('uses', '').startswith('actions/checkout@'))
    steps.insert(steps.index(checkout) + 1,
        dict(name='Verify exact qualified14 metadata and complete physical475 source before Original GET',
            **{'working-directory': 'auditor'}, run='python3 -B ' + NAMESPACE + '/attempt_policy.py --require-window\n'
                'python3 -B ' + NAMESPACE + '/source_guard.py'))
    steps.insert(steps.index(checkout) + 2, dict(
        name='Fetch immutable qualified actual14 archive and verify all six raw Originals',
        **{'working-directory': 'auditor', 'env': {'GH_TOKEN': '${{ github.token }}'}},
        run='python3 -B ' + NAMESPACE + '/fetch_originals.py'))
    steps.insert(steps.index(checkout) + 3, dict(
        name='Require all six actual Originals and complete Source475 before ERP GET or DB',
        **{'working-directory': 'auditor'},
        run='python3 -B ' + NAMESPACE + '/source_guard.py --require-actual'))
    source = one(steps, 'Admit exact backend3194 parent and declared vendor delta before database')
    source['name'] = 'Admit entire current source and exact actual backend14 graph before database'
    source['run'] = "python -B '../auditor/" + NAMESPACE + "/probe.py' --check-actual-source"
    steps.insert(steps.index(source), {'uses': 'actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020',
        'with': {'node-version-file': 'auditor/.nvmrc', 'cache': 'npm', 'cache-dependency-path': 'auditor/package-lock.json'}})
    steps.insert(steps.index(source), dict(name='Check normal App browser callbacks and locked browser dependencies',
        **{'working-directory': 'auditor'}, run='set -euo pipefail\n'
            'npm ci --no-audit --no-fund\n'
            'npx playwright install --with-deps chromium\n'
            'npx tsc --noEmit --project tsconfig.app.json\n'
            'python -B -m unittest discover -s ' + NAMESPACE + " -p 'test_*.py'\n"
            'node --check ' + NAMESPACE + '/cases.mjs\n'
            'node --test ' + NAMESPACE + '/test_oracles.mjs ' + NAMESPACE + '/test_lawful_oracles.mjs\n'))
    execute = one(steps, 'Run fresh Native7 then actual race3 AuthHTTP1 and complete restoration')
    execute['name'] = 'Run four real S03 normal App Auth browser cases and complete restoration'
    execute['run'] = "python -B '../auditor/" + NAMESPACE + "/probe.py'"
    steps.insert(steps.index(execute) + 1, dict(name='Require browser4 typed counts Auth cleanup outer restore and all5',
        **{'working-directory': 'auditor', 'if': 'always()'}, run='python -B ' + NAMESPACE + '/result_gate.py'))
    receipt = one(steps, 'Preserve exact original JSON report bytes in a bounded compressed log receipt')
    before = "('CP7_VENDOR_RECEIVABLE_COMBINED11.json','T3_PACKAGE_INSTALL.json','T3_BACKUP_RESTORE_DRILL.json','T3_PACKAGE_FILES_INSTALL.json')"
    after = "('CP7_S03_MOUNTED_FULL_APP_BROWSER4.json','S03_BROWSER4_FINAL_GATE.json','T3_PACKAGE_INSTALL.json','T3_BACKUP_RESTORE_DRILL.json','T3_PACKAGE_FILES_INSTALL.json')"
    if receipt['run'].count(before) != 1:
        raise ValueError('S03_BROWSER4_EXACT_ORIGINAL_RECEIPT_ANCHOR_REQUIRED')
    receipt['run'] = receipt['run'].replace(before, after, 1)
    upload = next(step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-s03-browser4-${{ github.run_attempt }}'
    return value


if __name__ == '__main__':
    import yaml
    root = Path(__file__).resolve().parents[2]
    original = yaml.safe_load((root / PARENT).read_text())
    (root / WORKFLOW).write_text(yaml.safe_dump(derive(original), sort_keys=False, width=120))
