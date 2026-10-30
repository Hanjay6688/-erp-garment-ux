"""Exact successor of the complete bce workflow, with first-checkout admission."""
from copy import deepcopy
from pathlib import Path
import json
import os
import yaml

ROOT = Path(__file__).resolve().parents[2]
NS = 'scripts/current-de-sku-global-census-qualification'
PARENT = 'scripts/current-de-sku-parent-catalogue-qualification'
HELPER = 'scripts/current-global-actual-writer-census-qualification'
OLD = '.github/workflows/cp7-de-sku-parent-catalogue.yml'
NEW = '.github/workflows/cp7-de-sku-global-census.yml'
BRANCH = 'astra-a/de-sku-global-census-20261030'
NAME = 'CP7 A D1 E SKU global writer metadata and full restoration'


def derive(value):
    value = deepcopy(value); value['name'] = NAME
    value['concurrency']['group'] = 'cp7-de-sku-global-census-${{ github.run_id }}'
    value['on'] = {'push': {'branches': [BRANCH], 'paths': [NEW, NS + '/**']}, 'workflow_dispatch': {}}
    job = value['jobs']['p21']; job['if'] = "github.ref == 'refs/heads/" + BRANCH + "'"
    job['name'] = 'Actual writer metadata only, full preuse and outer restoration; Native0'
    changes = {
        'Check exact catalogue-stage source and preserved restoration engine': (
            'Check bounded metadata successor and strict mutation controls',
            'python -B -m unittest discover -s ' + NS + " -p 'test_*.py' -v\n" +
            'python -B -m unittest discover -s ' + HELPER + " -p 'test_*.py' -v"),
        'Check complete immutable parent and declared catalogue source before imports': (
            'Check complete immutable helper parent and declared metadata successor', 'python -B ' + NS + '/check.py --offline'),
        'Admit actual current parent-catalogue stage and full imported source before database': (
            'Admit exact metadata successor and full inherited Original source before database', 'python -B ' + NS + '/probe.py --check'),
        'Install preuse inverse reinstall and capture actual D1 E SKU catalogues then fully restore': (
            'Capture global writer metadata in committed composite READ ONLY then fully restore', "python -B '../auditor/" + NS + "/probe.py' --metadata-runtime"),
        'Require exact actual catalogue scope full outer restoration and all5': (
            'Require separate supplemental Original and full outer restoration all5', 'python -B ' + NS + '/result_gate.py'),
    }
    found = []
    for step in job['steps']:
        name = step.get('name', '')
        if name in changes:
            step['name'], step['run'] = changes[name]; found.append(name)
        elif name.startswith('Preserve exact original JSON report bytes'):
            before = "'CP7_D1_E_SKU_PARENT_CATALOGUE.json'"; after = "'CP7_D1_E_SKU_GLOBAL_CENSUS.json'"
            if step['run'].count(before) != 1: raise ValueError('GLOBAL_CENSUS_EXACT_RETENTION_TRANSITION_REQUIRED')
            step['name'] = 'Retain exact Original byte identities without report data in stdout'
            step['run'] = 'python -B ' + NS + '/retain.py'; found.append('retention')
        elif step.get('uses', '').startswith('actions/upload-artifact@'):
            step['with']['name'] = 'cp7-de-sku-global-census-${{ github.run_attempt }}'; found.append('artifact')
    if len(found) != 7 or len(job['steps']) != 71:
        raise ValueError('GLOBAL_CENSUS_EXACT_WORKFLOW_TRANSITION_REQUIRED')
    first = job['steps'][0]
    if not first.get('uses', '').startswith('actions/checkout@') or first['with'].get('path') != 'auditor':
        raise ValueError('GLOBAL_CENSUS_FIRST_AUDITOR_CHECKOUT_REQUIRED')
    job['steps'].insert(1, dict(name='Admit whole public helper tree and bounded successor before any old import',
        **{'working-directory': 'auditor', 'run': 'python3 -B ' + NS + '/check.py'}))
    return value


if __name__ == '__main__':
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS') == 'true':
        raise ValueError('GLOBAL_CENSUS_WORKFLOW_RESEAL_IN_CI_REFUSED')
    (ROOT / NEW).write_text(yaml.safe_dump(derive(yaml.safe_load((ROOT / OLD).read_bytes())), sort_keys=False, width=120))
    print(json.dumps(dict(status='PREPARED_COMPLETE71_PLUS_FIRST_SOURCE_ADMISSION', changed_steps=7, early_admission_steps=1,
        actual_Native_credit=0, runtime_entry=None)))
