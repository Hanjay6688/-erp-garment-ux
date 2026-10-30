"""Bounded same-engine successor of the exact ee145 72-step workflow."""
from copy import deepcopy
from pathlib import Path
import json
import os
import yaml

ROOT = Path(__file__).resolve().parents[2]
PARENT = 'scripts/current-de-sku-global-census-qualification'
NS = 'scripts/current-de-sku-global-census-multiset-qualification'
OLD = '.github/workflows/cp7-de-sku-global-census.yml'
NEW = '.github/workflows/cp7-de-sku-global-census-multiset.yml'
BRANCH = 'astra-a/de-sku-global-census-multiset-20261030'
NAME = 'CP7 A D1 E SKU dependency multiset metadata and full restoration'


def derive(value):
    if value['name'] != 'CP7 A D1 E SKU global writer metadata and full restoration':
        raise ValueError('GLOBAL_MULTISET_EXACT_PARENT_WORKFLOW_REQUIRED')
    value = deepcopy(value); value['name'] = NAME
    value['concurrency']['group'] = 'cp7-de-sku-global-census-multiset-${{ github.run_id }}'
    value['on'] = {'push': {'branches': [BRANCH], 'paths': [NEW, NS + '/**']}, 'workflow_dispatch': {}}
    job = value['jobs']['p21']; job['if'] = "github.ref == 'refs/heads/" + BRANCH + "'"
    job['name'] = 'Lossless dependency metadata only, raw Original and full restoration; Native0'
    expected = {
        'Admit whole public helper tree and bounded successor before any old import',
        'Check bounded metadata successor and strict mutation controls',
        'Check complete immutable helper parent and declared metadata successor',
        'Admit exact metadata successor and full inherited Original source before database',
        'Capture global writer metadata in committed composite READ ONLY then fully restore',
        'Require separate supplemental Original and full outer restoration all5',
        'Retain exact Original byte identities without report data in stdout',
    }
    found = set(); artifacts = 0
    for step in job['steps']:
        name = step.get('name')
        if name in expected:
            if step.get('run', '').count(PARENT) != 1 or name in found:
                raise ValueError('GLOBAL_MULTISET_EXACT_WORKFLOW_ROUTE_REQUIRED')
            step['run'] = step['run'].replace(PARENT, NS, 1); found.add(name)
        elif step.get('uses', '').startswith('actions/upload-artifact@'):
            if step['with']['name'] != 'cp7-de-sku-global-census-${{ github.run_attempt }}':
                raise ValueError('GLOBAL_MULTISET_EXACT_PARENT_ARTIFACT_REQUIRED')
            step['with']['name'] = 'cp7-de-sku-global-census-multiset-${{ github.run_attempt }}'; artifacts += 1
    if found != expected or artifacts != 1 or len(job['steps']) != 72:
        raise ValueError('GLOBAL_MULTISET_COMPLETE72_WORKFLOW_CHANGED')
    return value


if __name__ == '__main__':
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS') == 'true':
        raise ValueError('GLOBAL_MULTISET_CI_RESEAL_FORBIDDEN')
    (ROOT / NEW).write_text(yaml.safe_dump(derive(yaml.safe_load((ROOT / OLD).read_bytes())), sort_keys=False, width=120))
    print(json.dumps(dict(status='PREPARED_EXACT72_STEP_SUCCESSOR', changed_route_steps=7,
        actual_Native_credit=0, runtime_entry=None)))
