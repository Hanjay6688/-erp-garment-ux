"""Pure structurally checked derivation from the frozen actual D1 workflow."""
from copy import deepcopy

OLD = '.github/workflows/cp7-credit-de-native.yml'
NEW = '.github/workflows/cp7-credit-e1-native17.yml'
NS = 'scripts/current-credit-e1-native-qualification'
EARLY = 'Require explicitly qualified D1 successor pin before setup or downloads'
FETCH = 'Acquire exact terminal D1 Native13 Original group and all package gates before database'
LOCAL = 'Check E1 closed prerequisite source and orchestration controls'
ADMIT = 'Admit exact terminal D1 and unchanged E1 Native17 child before database'
RUN = 'Run unchanged E1 Native17 and committed used witness with complete restoration'
CLIENT = 'Run exact targeted E1 client and shared contract controls before database'


def derive(original, branch):
    value = deepcopy(original)
    value['name'] = 'CP7 A incoming credit E1 Native17 gated by exact successful D1'
    value['on']['push'] = dict(branches=[branch], paths=[NEW, NS+'/**'])
    value['concurrency']['group'] = 'cp7-credit-e1-native17-${{ github.run_id }}'
    job = value['jobs']['p21']
    job['name'] = 'E1 Native17 above qualified D1; full restore'
    job['timeout-minutes'] = 180
    job['if'] = "github.ref == 'refs/heads/"+branch+"'"
    job['env']['E1_NATIVE_CONFIRM'] = 'cp6_rollback'
    steps = job['steps']
    steps.insert(1, dict(name=EARLY, **{'working-directory': 'auditor',
        'run': "python -B - <<'PY'\nimport importlib.util,json\nfrom pathlib import Path\np=Path('"+NS+"');s=importlib.util.spec_from_file_location('closed_E1_gate',p/'gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm.selected(json.loads((p/'CONFIG.json').read_bytes()))\nPY\n"}))
    at = next(i for i, step in enumerate(steps) if step.get('name') == 'Fetch and verify immutable actual Native32 original before DB')
    steps.insert(at, dict(name=FETCH, **{'working-directory': 'auditor', 'env': {'GH_TOKEN': '${{ github.token }}'},
        'run': 'python -B '+NS+'/fetch_prerequisite.py'}))
    at = next(i for i, step in enumerate(steps) if step.get('name') == 'Admit exact vendor parent and declared D1 child before database')
    steps[at] = dict(name=ADMIT, **{'working-directory': 'auditor', 'run': 'python -B '+NS+'/check.py'})
    steps.insert(at, dict(name=LOCAL, **{'working-directory': 'auditor',
        'run': "python -B -m unittest discover -s "+NS+" -p 'test_*.py'"}))
    command = ('npx vitest run src/NoteCreditCarrySection.dom.test.tsx src/noteCreditCarryContract.test.ts '
               'src/customerCreditContract.test.ts src/SalesDraftPanel.dom.test.tsx src/ConnectedSalesPage.dom.test.tsx '
               'src/ConnectedCustomerCredit.dom.test.tsx src/SalesReturnCorrectionPanel.dom.test.tsx src/lib/clientError.test.ts '
               '--maxWorkers=1 --reporter=json --outputFile=cp6-proof/t3/E1_TARGETED_CLIENT.json')
    steps.insert(at, dict(name=CLIENT, **{'working-directory': 'auditor', 'run': 'set -euo pipefail\n'+command+'\nnpx tsc -b --pretty false\n'}))
    runtime = next(step for step in steps if step.get('name') == 'Run actual D1 Native13 and complete restoration')
    runtime['name'] = RUN; runtime['run'] = "python '../auditor/"+NS+"/probe.py'"
    receipt = next(step for step in steps if step.get('name') == 'Preserve exact original JSON report bytes in a bounded compressed log receipt')
    receipt['run'] = 'python -B '+NS+'/retain_reports.py'
    upload = next(step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-credit-e1-native17-${{ github.run_attempt }}'
    return value
