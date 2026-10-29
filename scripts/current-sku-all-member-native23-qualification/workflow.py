"""Structural child of frozen bd2 workflow; all unaffected steps stay identical."""
from copy import deepcopy

OLD = '.github/workflows/cp7-sku-combined-unique-fixture.yml'
NEW = '.github/workflows/cp7-sku-all-member-native23.yml'
NS = 'scripts/current-sku-all-member-native23-qualification'
BRANCH = 'astra-a/sku-all-member-native23-20261030'


def derive(original):
    value = deepcopy(original)
    value['name'] = 'CP7 A SKU all-member preflight fresh Native23'
    value['on']['push'] = dict(branches=[BRANCH], paths=[NEW, NS + '/**'])
    value['concurrency']['group'] = 'cp7-sku-all-member-native23-${{ github.run_id }}'
    job = value['jobs']['p21']
    job['if'] = "github.ref == 'refs/heads/" + BRANCH + "'"
    steps = job['steps']
    controls = next(s for s in steps if s.get('name') == 'Check combined local oracles and existing four browser preparations')
    run = controls['run']
    # Whole old unit modules execute privately. Only old source predicates are
    # explicitly transitioned; decimal/quantity/conservation test bodies stay.
    import re
    replacements = (
      (r"python -B -m unittest discover -s scripts/current-sku-combined-fixture-followup\s+-p 'test_\*\.py'", 'python -B ' + NS + '/inherited_controls.py unique'),
      (r"python -B -m unittest discover -s scripts/current-sku-combined-followup-qualification\s+-p 'test_\*\.py'", 'python -B ' + NS + '/inherited_controls.py combined'),
      (r'python -B scripts/current-sku-group-cost-qualification/test_oracle.py', 'python -B ' + NS + '/inherited_controls.py cost'),
      (r'python -B scripts/current-sku-pair-browser-qualification/test_plan.py', 'python -B ' + NS + '/inherited_controls.py browser'),
    )
    for before, after in replacements:
        run, count = re.subn(before, after, run)
        assert count == 1, 'SKU23_EXACT_WORKFLOW_CONTROL_ANCHOR_REQUIRED'
    controls['run'] = run.replace('set -euo pipefail\n', 'set -euo pipefail\npython -B -m unittest discover -s ' + NS + " -p 'test_*.py'\n", 1)
    admit = next(s for s in steps if s.get('name') == 'Admit retained Native21c and complete declared combined source before database')
    assert admit['run'] == 'python -B scripts/current-sku-combined-fixture-followup/check.py'
    admit['run'] = 'python -B ' + NS + '/check.py'
    runtime = next(s for s in steps if s.get('name') == 'Run one installed SKU base7 cost3 races3 Native waits6 Auth browser4 and complete restoration')
    assert runtime['run'] == "python '../auditor/scripts/current-sku-combined-fixture-followup/probe.py'"
    runtime['run'] = "python '../auditor/" + NS + "/probe.py' --runtime"
    preserve = next(s for s in steps if s.get('name') == 'Preserve exact original JSON report bytes in a bounded compressed log receipt')
    anchor = 'CP7_SKU_COMBINED_FOLLOWUP23.json'
    assert preserve['run'].count(anchor) == 1
    preserve['run'] = preserve['run'].replace(anchor, 'CP7_SKU_ALL_MEMBER_NATIVE23.json')
    preserve['run'] = preserve['run'].replace("'T3_PACKAGE_FILES_INSTALL.json')", "'T3_PACKAGE_FILES_INSTALL.json','SKU_COST_ARTIFACT_COPY_RECEIPT.json')")
    steps.insert(steps.index(preserve), dict(
        name='Retain exact writer-CWD SKU cost full census even on failure',
        **{'if': 'always()'},
        run='python -B auditor/' + NS + '/retain_outputs.py --workspace "$GITHUB_WORKSPACE"'))
    upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-sku-all-member-native23-${{ github.run_attempt }}'
    assert upload['with']['path'] == 'auditor/cp6-proof/t3'
    # The parent uploads t3 already, yet bd2 ZIP omitted generated cost census.
    # The always-run copy above retains the actual writer-CWD files under the
    # canonical artifact directory without changing other archive member roots.
    upload['with']['path'] = '\n'.join((
        'auditor/cp6-proof/t3',
        'auditor/cp6-proof/t3/SKU_COST_*.json',
        'auditor/cp6-proof/t3/SKU_COST_*FULL_CURRENT_CENSUS.json',
    ))
    return value
