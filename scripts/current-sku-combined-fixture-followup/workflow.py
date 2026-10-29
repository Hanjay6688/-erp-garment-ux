"""Exact new execution leaf over the frozen complete c163 workflow."""
from copy import deepcopy

OLD = '.github/workflows/cp7-sku-combined-followup.yml'
NEW = '.github/workflows/cp7-sku-combined-unique-fixture.yml'
NS = 'scripts/current-sku-combined-fixture-followup'
BRANCH = 'astra-a/sku-combined-unique-fixture-20261029'


def derive(original):
    value = deepcopy(original)
    value['name'] = 'CP7 A SKU combined23 unique administrative fixture'
    value['on']['push'] = dict(branches=[BRANCH], paths=[NEW, NS + '/**'])
    value['concurrency']['group'] = 'cp7-sku-combined-unique-fixture-${{ github.run_id }}'
    job = value['jobs']['p21']
    job['if'] = "github.ref == 'refs/heads/" + BRANCH + "'"
    steps = job['steps']
    controls = next(s for s in steps if s.get('name') == 'Check combined local oracles and existing four browser preparations')
    anchor = "set -euo pipefail\n"
    assert controls['run'].count(anchor) == 1
    controls['run'] = controls['run'].replace(anchor, anchor + "python -B -m unittest discover -s " + NS + " -p 'test_*.py'\n", 1)
    admission = next(s for s in steps if s.get('name') == 'Admit retained Native21c and complete declared combined source before database')
    assert admission['run'] == 'python -B scripts/current-sku-combined-followup-qualification/check.py'
    admission['run'] = 'python -B ' + NS + '/check.py'
    runtime = next(s for s in steps if s.get('name') == 'Run one installed SKU base7 cost3 races3 Native waits6 Auth browser4 and complete restoration')
    assert runtime['run'] == "python '../auditor/scripts/current-sku-combined-followup-qualification/probe.py'"
    runtime['run'] = "python '../auditor/" + NS + "/probe.py'"
    upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-sku-combined-unique-fixture-${{ github.run_attempt }}'
    return value
