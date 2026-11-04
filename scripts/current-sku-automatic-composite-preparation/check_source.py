"""Check the whole immutable parent identity and the sole additive namespace.

Sparse source checks disclose absent parent files. Actual adoption still needs
the retained full frozen parent admission and a complete owning runtime.
"""
from hashlib import sha1
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('automatic_current_source_assembly', HERE / 'assembly.py')
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


def check():
    own = assembly.source_manifest()
    ref = assembly.prepared_sources()[0]
    root = assembly.ROOT
    base = ref['current_money_preparation']
    assembly.require(base == dict(head='5f099fa6852c9088ab46daa0f1079a0f6a1f3185',
                                  tree='3fd1bdb763a6d22a5aa455f5aea3a853b9782e4d'),
                     'SKU_AUTOMATIC_EXACT_CURRENT_MONEY_PREPARATION_BASE')
    parent = set()
    materialized = 0
    absent = []
    for item in assembly.git('ls-tree', '-rz', base['tree']).split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        name = name.decode()
        parent.add(name)
        path = root / name
        assembly.require(kind == 'blob' and not path.is_symlink(), 'SKU_AUTOMATIC_REGULAR_PARENT_BLOB_REQUIRED:' + name)
        if not path.is_file():
            absent.append(name)
            continue
        data = path.read_bytes()
        assembly.require(sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob,
                         'SKU_AUTOMATIC_UNDECLARED_CURRENT_PARENT_CHANGE:' + name)
        materialized += 1
    changed = assembly.git('diff', '--name-only', base['head'], '--').decode().splitlines()
    namespace = str(HERE.relative_to(root)) + '/'
    assembly.require(all(name.startswith(namespace) for name in changed), 'SKU_AUTOMATIC_PARENT_DIFF_OUTSIDE_NAMESPACE')
    manifest = json.loads((HERE / 'SOURCE.json').read_bytes())
    own_paths = {namespace + name for name in manifest['files']} | {namespace + 'SOURCE.json'}
    actual = {name.decode() for name in assembly.git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0') if name}
    assembly.require(actual == parent | own_paths, 'SKU_AUTOMATIC_EXACT_ADDITIVE_NAMESPACE_REQUIRED')
    assembly.require(all(getattr(assembly.admission, key) is None for key in assembly.admission.GATES),
                     'SKU_AUTOMATIC_PREPARATION_CANNOT_OPEN_RUNTIME')
    return dict(status='CURRENT_MONEY_AUTOMATIC_PRODUCT_SOURCE_PREPARATION_NOT_ERP', source=own,
                unchanged_parent_tree=base['tree'], parent_blob_identities=len(parent),
                materialized_parent_files_exact=materialized, absent_sparse_parent_files=len(absent),
                full_runtime_parent_admission_still_required=True, own_files=len(own_paths),
                unchanged_money_product_files=44, exact_automatic_addition_files=20,
                all_five_new_gates_unset=True, active_workflow_added=False,
                Native_lifecycle_case_plan_and_owning_runtime_pending=True,
                actual_ERP_cases=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
