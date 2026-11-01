"""Read-only source admission; never imports ERP or opens a connection."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from cp7_accessory_nonpayable import admission, composition, settings_stage, ui_derivation, workflow

PREPARED_BASE = '10ac4e74cfcc66db7d1f2b166f3da0fc479f127b'
PREPARED_TREE = 'a0b0108113b9b4d43d57483f291383229a37d4ad'


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), *args])


def entries(ref):
    result = {}
    for row in git('ls-tree', '-rz', '--full-tree', ref).split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            key = name.decode()
            if key in result:
                raise ValueError('NONPAYABLE_DUPLICATE_GIT_PATH')
            result[key] = metadata.decode()
    return result


def preflight():
    source = composition.source_manifest()
    ui = ui_derivation.source_manifest()
    body_count = len(settings_stage.function_bodies())
    bindings = (admission.PARENT_HEAD, admission.PARENT_TREE, admission.PARENT_RUN,
        admission.PARENT_JOB, admission.PARENT_RECEIPT)
    if any(value is not None for value in bindings):
        receipt = admission.parent_receipt()
        base, tree = receipt['head'], receipt['tree']
    else:
        base, tree = PREPARED_BASE, PREPARED_TREE
    if source['base_head'] != base or source['base_tree'] != tree:
        raise ValueError('NONPAYABLE_EXACT_DECLARED_PARENT_SOURCE_REQUIRED')
    if git('rev-parse', base + '^{tree}').decode().strip() != tree:
        raise ValueError('NONPAYABLE_EXACT_PARENT_GIT_TREE_REQUIRED')
    before, after = entries(base), entries('HEAD')
    for name, row in before.items():
        if name in ui_derivation.CHANGED:
            proof = ui['UI_derivations'][name]
            if (row != '100644 blob ' + proof['original_blob_sha']
                or after.get(name) != '100644 blob ' + proof['derived_blob_sha']):
                raise ValueError('NONPAYABLE_ONLY_EXACT_COUNTED_UI_PARENT_CHANGE_ALLOWED:' + name)
            continue
        if after.get(name) != row:
            raise ValueError('NONPAYABLE_EXISTING_PARENT_BLOB_OR_MODE_CHANGED:' + name)
    added = set(after) - set(before)
    if not added or any(not name.startswith('scripts/cp7_accessory_nonpayable/')
                        and name not in ui_derivation.ADDED
                        and not(name == workflow.WORKFLOW and name in source['files'])for name in added):
        raise ValueError('NONPAYABLE_ONLY_DECLARED_ADDITIVE_COMPONENT_ALLOWED')
    if not set(source['files']).issubset(added):
        raise ValueError('NONPAYABLE_ALL_EXECUTABLE_SOURCE_MUST_BE_TRACKED_OWN_ADDITION')
    return dict(status='NONPAYABLE_SOURCE_ONLY_ADMITTED_PARENT_ACCEPTANCE_PENDING'
        if all(value is None for value in bindings) else 'NONPAYABLE_SOURCE_BOUND_TO_ACTUAL_FREE3_PARENT',
        base_head=base, base_tree=tree, unchanged_parent_paths=len(before)-len(ui_derivation.CHANGED), own_paths=len(added),
        own_source_pins=len(source['files']), exact_counted_Native_derivations=4,
        exact_counted_existing_UI_paths=len(ui_derivation.CHANGED), new_UI_paths=len(ui_derivation.ADDED),
        prepared_public_facade_functions=2, exact_settings_function_bodies=body_count,
        accepted_parent_bound=all(value is not None for value in bindings), actual_SQL_executed=0,
        actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
        production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-source', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(preflight(), sort_keys=True))
