"""Exact additive Global preparation, with explicit sparse observation."""
from hashlib import sha1, sha256
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('global_automatic_complete_source_fence', HERE / 'install_routes.py')
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)
ROOT, base = install.ROOT, install.base

UI_HEAD = '1c66a74295eae2f09b7535619325e4d023942e19'
UI_TREE = '587760d45b5026f27d19cf57adce92330fff3df3'
UI_BEFORE = '601afd5adbb167991b018eb24688d5ecb8fb3173'
UI_AFTER = '15dc4bde83e1ac74871f8d4aaf005e9e36445aeb'
UI_PATHS = frozenset(('src/ConnectedInitialImportPage.tsx', 'src/ConnectedPocketFabricPage.tsx', 'src/initial-import.css'))
BUILD_INPUTS = frozenset(('index.html', 'package-lock.json', 'package.json', 'tsconfig.app.json',
                         'tsconfig.contracts.json', 'tsconfig.json', 'vite.config.ts'))

SKU_HEAD = '3c5090e4dca207f8b8e5707a8895aa6d8d0f47f0'
SKU_TREE = '387484abf4103f5900e3cffb68e9410426ddfa2e'
SKU_BASE = '5f099fa6852c9088ab46daa0f1079a0f6a1f3185'
SKU_BASE_TREE = '3fd1bdb763a6d22a5aa455f5aea3a853b9782e4d'


def entries(tree):
    result = {}
    for item in base.git('ls-tree', '-rz', tree).split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        base.require(kind == 'blob' and mode in ('100644', '100755'),
                         'GLOBAL_AUTOMATIC_REGULAR_GIT_BLOB_REQUIRED')
        result[name.decode()] = dict(mode=mode, blob=blob)
    return result


def selective_ui(value, parent, approved):
    require = base.require
    require(value['head'] == UI_HEAD and value['tree'] == UI_TREE
            and value['before_src_tree'] == UI_BEFORE and value['after_src_tree'] == UI_AFTER,
            'GLOBAL_AUTOMATIC_ONLY_EXACT_SELECTIVE_B_UI_SOURCE')
    require(set(value['files']) == UI_PATHS and set(value['root_build_inputs']) == BUILD_INPUTS,
            'GLOBAL_AUTOMATIC_ONLY_THREE_SELECTIVE_UI_PATHS_AND_COMPLETE_BUILD_INPUTS')
    result = {}
    for name, row in value['files'].items():
        require(row['before'] == parent[name] and row['after'] == approved[name]
                and row['before']['mode'] == row['after']['mode'] == '100644',
                'GLOBAL_AUTOMATIC_EXACT_UI_BEFORE_AND_APPROVED_AFTER_BLOBS:' + name)
        path = ROOT / name
        require(path.is_file() and not path.is_symlink(), 'GLOBAL_AUTOMATIC_REGULAR_APPROVED_UI_FILE:' + name)
        raw = path.read_bytes()
        require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == row['pin']
                and sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['after']['blob'],
                'GLOBAL_AUTOMATIC_APPROVED_UI_EVERY_BYTE_REQUIRED:' + name)
        result[name] = row['after']
    for name, identity in value['root_build_inputs'].items():
        require(identity == parent[name] == approved[name], 'GLOBAL_AUTOMATIC_UI_BUILD_INPUT_CHANGED:' + name)
    return result


def pending_sku(value, baseline):
    """Copy the complete current prepared parent; grant no actual admission."""
    require = base.require
    require({key: value[key] for key in ('base_head', 'base_tree', 'head', 'tree')} ==
            dict(base_head=SKU_BASE, base_tree=SKU_BASE_TREE, head=SKU_HEAD, tree=SKU_TREE)
            and all(value[key] is None for key in ('actual_Root', 'actual_run', 'actual_job')),
            'GLOBAL_AUTOMATIC_ONLY_EXACT_UNQUALIFIED_CURRENT_SKU_SOURCE')
    require(base.git('rev-parse', SKU_HEAD + '^{tree}').decode().strip() == SKU_TREE
            and base.git('rev-parse', SKU_BASE + '^{tree}').decode().strip() == SKU_BASE_TREE,
            'GLOBAL_AUTOMATIC_CURRENT_SKU_IMMUTABLE_TREES_REQUIRED')
    before, after = entries(SKU_BASE_TREE), entries(SKU_TREE)
    paths = set(base.git('diff', '--name-only', SKU_BASE, SKU_HEAD, '--').decode().splitlines())
    require(len(paths) == 149 and set(value['files']) == paths,
            'GLOBAL_AUTOMATIC_COMPLETE_ONE_HUNDRED_FORTY_NINE_CURRENT_SKU_PATHS_REQUIRED')
    result = {}
    for name, row in value['files'].items():
        require(row['before'] == before.get(name) == baseline.get(name)
                and name in after and row['after'] == after[name],
                'GLOBAL_AUTOMATIC_CURRENT_SKU_EXACT_BEFORE_AND_AFTER:' + name)
        path = ROOT / name
        require(path.is_file() and not path.is_symlink(),
                'GLOBAL_AUTOMATIC_CURRENT_SKU_REGULAR_SOURCE_REQUIRED:' + name)
        raw = path.read_bytes()
        require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == row['pin']
                and sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['after']['blob'],
                'GLOBAL_AUTOMATIC_CURRENT_SKU_EVERY_SOURCE_BYTE_REQUIRED:' + name)
        result[name] = row['after']
    return result


def check(*, observe_sparse=False):
    manifest = install.check_sources()
    reference = json.loads((HERE / 'SOURCE_REFERENCE.json').read_bytes())
    source = reference['parent_global']
    base.require(source == dict(head='15fbb651708e6590be0ecf103454ef1e15401dc4',
                                tree='34df5f0a23f3fc5063f8f98260d0e937010fbcaf'), 'GLOBAL_AUTOMATIC_EXACT_PREPARED_PARENT_REQUIRED')
    base.require(base.git('rev-parse', source['head'] + '^{tree}').decode().strip() == source['tree'],
                 'GLOBAL_AUTOMATIC_PARENT_TREE_CHANGED')
    base.require(base.git('rev-parse', UI_HEAD + '^{tree}').decode().strip() == UI_TREE
                 and base.git('rev-parse', source['head'] + ':src').decode().strip() == UI_BEFORE
                 and base.git('rev-parse', UI_HEAD + ':src').decode().strip() == UI_AFTER,
                 'GLOBAL_AUTOMATIC_COMPLETE_APPROVED_UI_TREE_IDENTITIES_REQUIRED')
    selected = selective_ui(manifest['selective_B_UI'], entries(source['tree']), entries(UI_TREE))
    expected = entries(source['tree'])
    current_sku = pending_sku(manifest['pending_current_SKU_preparation'], expected)
    base.require(all(current_sku[name] == identity for name, identity in selected.items()),
                 'GLOBAL_AUTOMATIC_SELECTED_UI_MUST_MATCH_CURRENT_SKU')
    expected.update(current_sku)
    parent = set()
    absent = []
    checked = 0
    for name, identity in expected.items():
        parent.add(name)
        path = ROOT / name
        base.require(not path.is_symlink(), 'GLOBAL_AUTOMATIC_REGULAR_PARENT_BLOB_REQUIRED:' + name)
        if not path.is_file():
            absent.append(name)
            continue
        raw = path.read_bytes()
        expected_blob = identity['blob']
        base.require(sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == expected_blob,
                     'GLOBAL_AUTOMATIC_UNDECLARED_PARENT_CHANGE:' + name)
        checked += 1
    base.require(observe_sparse or not absent, 'GLOBAL_AUTOMATIC_FULL_RUNTIME_PARENT_MATERIALIZATION_REQUIRED')
    actual = {name.decode() for name in base.git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0') if name}
    own = set(manifest['files']) | {str((HERE / 'SOURCE.json').relative_to(ROOT))}
    base.require(actual == parent | own and all(name.startswith(str(HERE.relative_to(ROOT)) + '/') for name in own),
                 'GLOBAL_AUTOMATIC_SINGLE_EXACT_ADDITIVE_NAMESPACE_REQUIRED')
    base.require(all(getattr(install.admission, name) is None for name in install.GATES),
                 'GLOBAL_AUTOMATIC_ALL_EIGHT_ADMISSION_GATES_MUST_STAY_CLOSED')
    _, proof = install.routes.derive()
    base.require(proof['derived_helpers'] == manifest['derived_helpers'], 'GLOBAL_AUTOMATIC_DECLARED_HELPERS_CHANGED')
    return dict(status='GLOBAL_AUTOMATIC_EXACT_SOURCE_PREPARATION_NOT_RUNTIME', parent=source,
                parent_blob_identities=len(parent), materialized_parent_files_checked=checked,
                absent_sparse_parent_files=len(absent), full_runtime_materialization_required=bool(absent),
                own_source_paths=len(own), new_complete_rowsets=2, new_typed_identity_edges=8,
                existing_nineteen_authority_references_and_inspector_unchanged=True,
                relation_lower_bound_only=len(install.callbacks.requirements()['required_relation_lower_bound']),
                actual_complete_catalogue_and_all_writer_review_still_required=True,
                whole_parent_unchanged=False, exact_approved_B_UI_files=3,
                complete_approved_UI_src_tree=UI_AFTER,
                all_other_parent_sources_and_build_inputs_unchanged=True,
                exact_current_SKU_preparation_paths=len(current_sku),
                pending_current_SKU_head=SKU_HEAD, actual_current_SKU_Root_adopted=False,
                actual_ERP_cases=0, runtime_admission=False, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--observe-sparse', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(observe_sparse=args.observe_sparse), sort_keys=True))
