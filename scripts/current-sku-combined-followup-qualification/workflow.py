"""Pure child derivation from the unchanged Native21c workflow."""
from copy import deepcopy

OLD = '.github/workflows/cp7-sku-pair-native.yml'
NEW = '.github/workflows/cp7-sku-combined-followup.yml'
NS = 'scripts/current-sku-combined-followup-qualification'


def derive(original, branch):
    value = deepcopy(original)
    value['name'] = 'CP7 A SKU Native cost concurrency and Auth browser followup'
    value['on']['push'] = dict(branches=[branch], paths=[NEW, NS + '/**',
        'scripts/current-sku-pair-concurrency-qualification/**', 'scripts/current-sku-pair-browser-qualification/**',
        'scripts/current-staged-ai-browser-qualification/**', 'scripts/current-sku-group-cost-qualification/**'])
    value['concurrency']['group'] = 'cp7-sku-combined-followup-${{ github.run_id }}'
    job = value['jobs']['p21']; job['name'] = 'Native7 cost3 races3 Native waits6 and Auth browser4; complete restore'
    job['timeout-minutes'] = 210
    job['if'] = "github.ref == 'refs/heads/" + branch + "'"
    job['env']['D17_18_SELECTED_BACKEND_ROOT'] = '${{ github.workspace }}/auditor'
    steps = job['steps']
    fetch_index = next(i for i, step in enumerate(steps) if step.get('name') == 'Fetch and verify immutable actual Native32 original before DB')
    steps.insert(fetch_index, dict(name='Require terminal exact Native21c Original and package before any database',
        **{'working-directory': 'auditor', 'env': {'GH_TOKEN': '${{ github.token }}'},
           'run': 'python -B ' + NS + '/fetch_prerequisite.py'}))
    admission = next(step for step in steps if step.get('name') == 'Admit exact vendor parent and declared SKU child before database')
    admission['name'] = 'Admit retained Native21c and complete declared combined source before database'
    admission['run'] = 'python -B ' + NS + '/check.py'
    at = steps.index(admission)
    steps.insert(at, dict(name='Check combined local oracles and existing four browser preparations', **{'working-directory': 'auditor',
        'run': "set -euo pipefail\npython -B -m unittest discover -s " + NS + " -p 'test_*.py'\npython -B -m unittest discover -s scripts/current-sku-pair-concurrency-qualification -p 'test_*.py'\npython -B scripts/current-sku-group-cost-qualification/test_oracle.py\npython -B scripts/current-sku-pair-browser-qualification/test_plan.py\nnode --test scripts/current-sku-pair-browser-qualification/evidence.test.mjs scripts/current-staged-ai-browser-qualification/plan.test.mjs\npython -B scripts/current-staged-ai-browser-qualification/fixture_plan_test.py\nnpx playwright install --with-deps chromium\n"}))
    runtime = next(step for step in steps if step.get('name') == 'Run actual SKU Native cases and complete restoration')
    runtime['name'] = 'Run one installed SKU base7 cost3 races3 Native waits6 Auth browser4 and complete restoration'
    runtime['run'] = "python '../auditor/" + NS + "/probe.py'"
    receipt = next(step for step in steps if step.get('name') == 'Preserve exact original JSON report bytes in a bounded compressed log receipt')
    old_names = "('CP7_SKU_PAIR_CONVERSION_NATIVE.json',"
    assert receipt['run'].count(old_names) == 1
    receipt['run'] = receipt['run'].replace(old_names, "('CP7_SKU_COMBINED_FOLLOWUP23.json','CP7_SKU_GROUP_COST_NATIVE3.json','CP7_SKU_GROUP_COST_NATIVE3_BUSINESS_DAY_FIRST_ATTEMPT.json','CP7_SKU_PAIR_CONVERSION_NATIVE.json',", 1)
    upload = next(step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-sku-combined-followup-${{ github.run_attempt }}'
    return value
