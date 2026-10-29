"""Semantic derivative of exact public17ac workflow; complete setup/restoration retained."""
from copy import deepcopy

OLD = '.github/workflows/cp7-credit-d1-product-phase-native13.yml'
NEW = '.github/workflows/cp7-credit-d1-current-parent-continuation3.yml'
NS = 'scripts/current-credit-d1-current-parent-continuation3-qualification'
EARLY = 'Require exact successful current D1 parent before setup or GET'
FETCH = 'Acquire exact current D1 Native13 and five complete raw parent originals'
LOCAL = 'Check current-parent continuation3 source routing and retained financial controls'
ADMIT = 'Admit exact current D1 Native13 and continuation3 sources before database'
RUN = 'Run continuation3 and separate committed used witness with complete restoration'


def derive(original, branch):
    value = deepcopy(original)
    value['name'] = 'CP7 A D1 current-parent continuation Native3 gated by verified Native13'
    value['on']['push'] = dict(branches=[branch], paths=[NEW, NS + '/**',
        'scripts/current-credit-d1-continuation-qualification/**',
        'scripts/current-credit-d1-owner-followup-qualification/**'])
    value['concurrency']['group'] = 'cp7-credit-d1-current-continuation3-${{ github.run_id }}'
    job = value['jobs']['p21']
    job['name'] = 'D1 continuation3 above exact current Native13; complete restore'
    job['if'] = "github.ref == 'refs/heads/" + branch + "'"
    job['env']['D1_CONT_NATIVE_CONFIRM'] = 'cp6_rollback'
    steps = job['steps']
    steps.insert(1, dict(name=EARLY, **{'working-directory': 'auditor', 'run':
        "python -B - <<'PY'\nimport importlib.util,json\nfrom pathlib import Path\np=Path('" + NS + "');s=importlib.util.spec_from_file_location('current_continuation_closed_gate',p/'gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm.selected(json.loads((p/'CONFIG.json').read_bytes()))\nPY\n"}))
    at = next(i for i, step in enumerate(steps) if step.get('name') == 'Fetch and verify immutable actual Native32 original before DB')
    steps.insert(at, dict(name=FETCH, **{'working-directory': 'auditor', 'env': {'GH_TOKEN': '${{ github.token }}'},
        'run': 'python -B ' + NS + '/fetch_prerequisite.py'}))
    at = next(i for i, step in enumerate(steps) if step.get('name') == 'Admit exact vendor parent and declared D1 child before database')
    steps[at] = dict(name=ADMIT, **{'working-directory': 'auditor', 'run': 'python -B ' + NS + '/check.py'})
    steps.insert(at, dict(name=LOCAL, **{'working-directory': 'auditor', 'run':
        "python -B -m unittest discover -s " + NS + " -p 'test_*.py'\npython -B " + NS + "/check.py --source-only\n"}))
    runtime = next(step for step in steps if step.get('name') == 'Run actual D1 Native13 and complete restoration')
    runtime['name'] = RUN; runtime['run'] = "python '../auditor/" + NS + "/probe.py'"
    receipt = next(step for step in steps if step.get('name') == 'Preserve exact original JSON report bytes in a bounded compressed log receipt')
    receipt['run'] = 'python -B ' + NS + '/retain_reports.py'
    upload = next(step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-credit-d1-current-parent-continuation3-${{ github.run_attempt }}'
    return value
