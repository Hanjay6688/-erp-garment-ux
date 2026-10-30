"""Explicit output-profile successor; old readers/profiles stay byte exact."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

PARENT = 'scripts/current-de-sku-parent-catalogue-qualification'
NS = 'scripts/current-de-sku-global-census-qualification'
WORKFLOW = '.github/workflows/cp7-de-sku-global-census.yml'
NAME = 'CP7 A D1 E SKU global writer metadata and full restoration'
FILES = ('GENERATED_RECEIPTS.json', 'LATER_GENERATED_RECEIPTS.json', 'SKU_GENERATED_RECEIPTS.json')


def derive(value, filename, workflow_raw):
    if filename not in FILES: raise ValueError('GLOBAL_CENSUS_EXACT_PRODUCER_PROFILE_REQUIRED')
    value = deepcopy(value)
    if WORKFLOW in value['producer_files']: raise ValueError('GLOBAL_CENSUS_PRODUCER_ALREADY_TRANSITIONED')
    value['producer_files'][WORKFLOW] = dict(bytes=len(workflow_raw), sha256=sha256(workflow_raw).hexdigest())
    if filename == 'LATER_GENERATED_RECEIPTS.json':
        if value['package_workflow_name'] != 'CP7 A D1 E SKU actual parent catalogue and preuse restoration':
            raise ValueError('GLOBAL_CENSUS_OLD_PACKAGE_WORKFLOW_IDENTITY_CHANGED')
        value['package_workflow_name'] = NAME
    return value


def validate(root):
    root = Path(root); workflow_raw = (root / WORKFLOW).read_bytes(); result = {}
    for filename in FILES:
        expected = derive(json.loads((root / PARENT / filename).read_bytes()), filename, workflow_raw)
        actual = json.loads((root / NS / filename).read_bytes())
        if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise ValueError('GLOBAL_CENSUS_UNDECLARED_OUTPUT_POLICY_TRANSITION:' + filename)
        result[filename] = dict(new_workflow_producer=True,
            changed_package_workflow_name=filename == 'LATER_GENERATED_RECEIPTS.json', old_readers_unchanged=True)
    return result
