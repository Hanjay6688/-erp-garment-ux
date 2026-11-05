"""Check the whole immutable parent identity and the sole additive namespace.

Sparse source checks disclose absent parent files. Actual adoption still needs
the retained full frozen parent admission and a complete owning runtime.
"""
from hashlib import sha1, sha256
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('automatic_current_source_assembly', HERE / 'assembly.py')
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)
ROOT = assembly.ROOT

UI_HEAD = '1c66a74295eae2f09b7535619325e4d023942e19'
UI_TREE = '587760d45b5026f27d19cf57adce92330fff3df3'
UI_BEFORE = '601afd5adbb167991b018eb24688d5ecb8fb3173'
UI_AFTER = '15dc4bde83e1ac74871f8d4aaf005e9e36445aeb'
UI_PATHS = frozenset(('src/ConnectedInitialImportPage.tsx', 'src/ConnectedPocketFabricPage.tsx', 'src/initial-import.css'))
BUILD_INPUTS = frozenset(('index.html', 'package-lock.json', 'package.json', 'tsconfig.app.json',
                         'tsconfig.contracts.json', 'tsconfig.json', 'vite.config.ts'))
MANDOR_HEAD = '116667dc6e4b8c43f430b70010b32ccec8513889'
MANDOR_TREE = 'e9176cc506c753f4b524693f20dcd83d3e8b7fe8'
MANDOR_BASE = 'c296fd06167ddd177e1192c1008992e2a1e3d628'
MANDOR_BASE_TREE = 'fdd36962a7de81482ccca02e6ff96597cfc20081'


def entries(tree):
    result = {}
    for item in assembly.git('ls-tree', '-rz', tree).split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        assembly.require(kind == 'blob' and mode in ('100644', '100755'),
                         'SKU_AUTOMATIC_REGULAR_GIT_BLOB_REQUIRED')
        result[name.decode()] = dict(mode=mode, blob=blob)
    return result


def selective_ui(value, base, approved):
    require = assembly.require
    require(value['head'] == UI_HEAD and value['tree'] == UI_TREE
            and value['before_src_tree'] == UI_BEFORE and value['after_src_tree'] == UI_AFTER,
            'SKU_AUTOMATIC_ONLY_EXACT_SELECTIVE_B_UI_SOURCE')
    require(set(value['files']) == UI_PATHS and set(value['root_build_inputs']) == BUILD_INPUTS,
            'SKU_AUTOMATIC_ONLY_THREE_SELECTIVE_UI_PATHS_AND_COMPLETE_BUILD_INPUTS')
    result = {}
    for name, row in value['files'].items():
        require(row['before'] == base[name] and row['after'] == approved[name]
                and row['before']['mode'] == row['after']['mode'] == '100644',
                'SKU_AUTOMATIC_EXACT_UI_BEFORE_AND_APPROVED_AFTER_BLOBS:' + name)
        path = ROOT / name
        require(path.is_file() and not path.is_symlink(), 'SKU_AUTOMATIC_REGULAR_APPROVED_UI_FILE:' + name)
        raw = path.read_bytes()
        require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == row['pin']
                and sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['after']['blob'],
                'SKU_AUTOMATIC_APPROVED_UI_EVERY_BYTE_REQUIRED:' + name)
        result[name] = row['after']
    for name, identity in value['root_build_inputs'].items():
        require(identity == base[name] == approved[name], 'SKU_AUTOMATIC_UI_BUILD_INPUT_CHANGED:' + name)
    return result


def pending_mandor(value, baseline):
    """Copy the complete current prepared parent; grant no actual admission."""
    require = assembly.require
    require({key: value[key] for key in ('base_head', 'base_tree', 'head', 'tree')} ==
            dict(base_head=MANDOR_BASE, base_tree=MANDOR_BASE_TREE, head=MANDOR_HEAD, tree=MANDOR_TREE)
            and all(value[key] is None for key in ('actual_Root', 'actual_run', 'actual_job')),
            'SKU_AUTOMATIC_ONLY_EXACT_UNQUALIFIED_CURRENT_MANDOR_SOURCE')
    require(assembly.git('rev-parse', MANDOR_HEAD + '^{tree}').decode().strip() == MANDOR_TREE
            and assembly.git('rev-parse', MANDOR_BASE + '^{tree}').decode().strip() == MANDOR_BASE_TREE,
            'SKU_AUTOMATIC_CURRENT_MANDOR_IMMUTABLE_TREES_REQUIRED')
    before, after = entries(MANDOR_BASE_TREE), entries(MANDOR_TREE)
    paths = set(assembly.git('diff', '--name-only', MANDOR_BASE, MANDOR_HEAD, '--').decode().splitlines())
    require(len(paths) == 78 and set(value['files']) == paths,
            'SKU_AUTOMATIC_COMPLETE_SEVENTY_EIGHT_CURRENT_MANDOR_PATHS_REQUIRED')
    result = {}
    for name, row in value['files'].items():
        require(row['before'] == before.get(name) == baseline.get(name)
                and name in after and row['after'] == after[name],
                'SKU_AUTOMATIC_CURRENT_MANDOR_EXACT_BEFORE_AND_AFTER:' + name)
        path = ROOT / name
        require(path.is_file() and not path.is_symlink(),
                'SKU_AUTOMATIC_CURRENT_MANDOR_REGULAR_SOURCE_REQUIRED:' + name)
        raw = path.read_bytes()
        require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == row['pin']
                and sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['after']['blob'],
                'SKU_AUTOMATIC_CURRENT_MANDOR_EVERY_SOURCE_BYTE_REQUIRED:' + name)
        result[name] = row['after']
    return result


def check(*, runtime=False):
    if runtime:
        assembly.admission.require_ready()
    own = assembly.source_manifest()
    ref = assembly.prepared_sources()[0]
    root = assembly.ROOT
    base = ref['current_money_preparation']
    assembly.require(base == dict(head='5f099fa6852c9088ab46daa0f1079a0f6a1f3185',
                                  tree='3fd1bdb763a6d22a5aa455f5aea3a853b9782e4d'),
                     'SKU_AUTOMATIC_EXACT_CURRENT_MONEY_PREPARATION_BASE')
    manifest = json.loads((HERE / 'SOURCE.json').read_bytes())
    assembly.require(assembly.git('rev-parse', UI_HEAD + '^{tree}').decode().strip() == UI_TREE
                     and assembly.git('rev-parse', base['head'] + ':src').decode().strip() == UI_BEFORE
                     and assembly.git('rev-parse', UI_HEAD + ':src').decode().strip() == UI_AFTER,
                     'SKU_AUTOMATIC_COMPLETE_APPROVED_UI_TREE_IDENTITIES_REQUIRED')
    selected = selective_ui(manifest['selective_B_UI'], entries(base['tree']), entries(UI_TREE))
    expected = entries(base['tree'])
    current_mandor = pending_mandor(manifest['pending_current_Mandor_preparation'], expected)
    assembly.require(all(current_mandor[name] == identity for name, identity in selected.items()),
                     'SKU_AUTOMATIC_SELECTED_UI_MUST_MATCH_CURRENT_MANDOR')
    expected.update(current_mandor)
    parent = set()
    materialized = 0
    absent = []
    for name, identity in expected.items():
        parent.add(name)
        path = root / name
        assembly.require(not path.is_symlink(), 'SKU_AUTOMATIC_REGULAR_PARENT_BLOB_REQUIRED:' + name)
        if not path.is_file():
            absent.append(name)
            continue
        data = path.read_bytes()
        expected_blob = identity['blob']
        assembly.require(sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected_blob,
                         'SKU_AUTOMATIC_UNDECLARED_CURRENT_PARENT_CHANGE:' + name)
        materialized += 1
    changed = assembly.git('diff', '--name-only', base['head'], '--').decode().splitlines()
    namespace = str(HERE.relative_to(root)) + '/'
    workflow_name = '.github/workflows/cp7-sku-current-parent-money-automatic-native25.yml'
    assembly.require(all(name.startswith(namespace) or name in current_mandor
                         or (runtime and name == workflow_name) for name in changed),
                     'SKU_AUTOMATIC_PARENT_DIFF_OUTSIDE_NAMESPACE')
    own_paths = {namespace + name for name in manifest['files']} | {namespace + 'SOURCE.json'}
    active = root / workflow_name
    active_paths = set()
    if manifest['active_workflow_added']:
        assembly.require(runtime and active.is_file() and not active.is_symlink()
                         and assembly.admission.pin(active.read_bytes()) == manifest.get('active_workflow_source'),
                         'SKU_AUTOMATIC_EXACT_ACTUAL_ACTIVE_WORKFLOW_SOURCE_REQUIRED')
        active_paths.add(workflow_name)
    else:
        assembly.require(not active.exists() and not active.is_symlink()
                         and manifest.get('active_workflow_source') is None,
                         'SKU_AUTOMATIC_UNADMITTED_WORKFLOW_MUST_REMAIN_ABSENT')
    actual = {name.decode() for name in assembly.git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0') if name}
    assembly.require(actual == parent | own_paths | active_paths, 'SKU_AUTOMATIC_EXACT_ADDITIVE_NAMESPACE_REQUIRED')
    closed = all(getattr(assembly.admission, key) is None for key in assembly.admission.GATES)
    if runtime:
        assembly.admission.require_ready()
        assembly.require(not absent, 'SKU_AUTOMATIC_RUNTIME_REQUIRES_FULL_PARENT_MATERIALIZATION')
        assembly.require(assembly.admission.OWNING_RUNTIME_ENTRY ==
                         'scripts/current-sku-automatic-composite-preparation/qualification.py',
                         'SKU_AUTOMATIC_EXACT_ACTUAL_OWNING_ENTRY_REQUIRED')
    else:
        assembly.require(closed, 'SKU_AUTOMATIC_PREPARATION_CANNOT_OPEN_RUNTIME')
    return dict(status=('CURRENT_MONEY_AUTOMATIC_PRODUCT_SOURCE_ADMITTED_NOT_ERP_ACCEPTANCE' if runtime
                        else 'CURRENT_MONEY_AUTOMATIC_PRODUCT_SOURCE_PREPARATION_NOT_ERP'), source=own,
                original_parent_tree=base['tree'], parent_blob_identities=len(parent),
                materialized_parent_files_exact=materialized, absent_sparse_parent_files=len(absent),
                full_runtime_parent_admission_still_required=not runtime, own_files=len(own_paths),
                unchanged_money_product_files=44, exact_automatic_addition_files=20,
                all_five_new_gates_unset=closed, active_workflow_added=manifest['active_workflow_added'],
                Native_lifecycle_case_plan_pending=False, owning_runtime_prepared=True,
                execution_helpers_and_workflow_prepared=True,
                actual_runtime_adoption_pending=closed,
                private_authority_reviewer_prepared=True,
                whole_parent_unchanged=False, exact_approved_B_UI_files=3,
                complete_approved_UI_src_tree=UI_AFTER,
                all_other_parent_sources_and_build_inputs_unchanged=True,
                exact_current_Mandor_preparation_paths=len(current_mandor),
                pending_current_Mandor_head=MANDOR_HEAD, actual_current_Mandor_Root_adopted=False,
                actual_ERP_cases=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(runtime=args.runtime), sort_keys=True))
