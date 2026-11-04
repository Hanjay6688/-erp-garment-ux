"""Exact additive Global preparation, with explicit sparse observation."""
from hashlib import sha1
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('global_automatic_complete_source_fence', HERE / 'install_routes.py')
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)
ROOT, base = install.ROOT, install.base


def check(*, observe_sparse=False):
    manifest = install.check_sources()
    reference = json.loads((HERE / 'SOURCE_REFERENCE.json').read_bytes())
    source = reference['parent_global']
    base.require(source == dict(head='15fbb651708e6590be0ecf103454ef1e15401dc4',
                                tree='34df5f0a23f3fc5063f8f98260d0e937010fbcaf'), 'GLOBAL_AUTOMATIC_EXACT_PREPARED_PARENT_REQUIRED')
    base.require(base.git('rev-parse', source['head'] + '^{tree}').decode().strip() == source['tree'],
                 'GLOBAL_AUTOMATIC_PARENT_TREE_CHANGED')
    parent = set()
    absent = []
    checked = 0
    for item in base.git('ls-tree', '-rz', source['tree']).split(b'\0'):
        if not item:
            continue
        meta, name = item.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        name = name.decode()
        parent.add(name)
        path = ROOT / name
        base.require(kind == 'blob' and not path.is_symlink(), 'GLOBAL_AUTOMATIC_REGULAR_PARENT_BLOB_REQUIRED:' + name)
        if not path.is_file():
            absent.append(name)
            continue
        raw = path.read_bytes()
        base.require(sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob,
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
                actual_ERP_cases=0, runtime_admission=False, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--observe-sparse', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(observe_sparse=args.observe_sparse), sort_keys=True))
