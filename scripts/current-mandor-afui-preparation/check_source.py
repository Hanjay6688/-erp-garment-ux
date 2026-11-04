"""Whole current candidate fence; sparse observation never grants runtime."""
from hashlib import sha1, sha256
from pathlib import Path
import argparse
import ast
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('mandor_current_exact_caller_routes', HERE / 'routes.py')
routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routes)


def require(value, reason):
    if not value:
        raise ValueError(reason)


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))


def entries(tree):
    result = {}
    for item in git('ls-tree', '-rz', tree).split(b'\0'):
        if not item:
            continue
        meta, name = item.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        require(kind == 'blob' and mode in ('100644', '100755'), 'MANDOR_CURRENT_REGULAR_GIT_BLOB_REQUIRED')
        result[name.decode()] = dict(mode=mode, blob=blob)
    return result


def source(*, allow_sparse_observation=False):
    manifest = json.loads((HERE / 'SOURCE.json').read_bytes())
    require(manifest['classification'] == 'CURRENT_AFUI_MANDOR_SOURCE_PREPARATION_NOT_RUNTIME'
            and manifest['actual_ERP_cases'] == 0 and manifest['production_go'] is False,
            'MANDOR_CURRENT_SOURCE_ONLY_MANIFEST_REQUIRED')
    require(git('rev-parse', routes.BASE + '^{tree}').decode().strip() == routes.BASE_TREE
            and git('rev-parse', routes.AFUI + '^{tree}').decode().strip() == routes.AFUI_TREE,
            'MANDOR_CURRENT_EXACT_COMPLETE_BASE_AND_AFUI_TREES_REQUIRED')
    base, afui = entries(routes.BASE_TREE), entries(routes.AFUI_TREE)
    copied = set(git('diff', '--name-only', routes.PRIOR_AFUI, routes.AFUI, '--').decode().splitlines())
    require(copied == set(manifest['exact_current_Afui_files']) and len(copied) == 33,
            'MANDOR_CURRENT_COMPLETE_THIRTY_THREE_AFUI_SOURCE_PATHS_REQUIRED')
    for name in copied:
        require(name in afui and afui[name] == manifest['exact_current_Afui_files'][name],
                'MANDOR_CURRENT_EXACT_QUALIFIED_AFUI_BLOB_REQUIRED:' + name)
    caller_paths = {routes.NS + name for name in routes.PINS}
    for name in routes.PINS:
        path = routes.NS + name
        derived, proof = routes.derive(git('show', routes.BASE + ':' + path), name)
        require((ROOT / path).read_bytes() == derived and manifest['caller_derivations'][name] == proof,
                'MANDOR_CURRENT_EXACT_REVERSIBLE_CALLER_BYTES_REQUIRED:' + path)
    for name, expected in manifest['files'].items():
        path = ROOT / name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and path.is_file() and not path.is_symlink(),
                'MANDOR_CURRENT_REGULAR_DECLARED_SOURCE_REQUIRED:' + name)
        raw = path.read_bytes()
        require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == expected,
                'MANDOR_CURRENT_DECLARED_SOURCE_CHANGED:' + name)
    namespace = str(HERE.relative_to(ROOT)) + '/'
    declared = set(manifest['files']) | {namespace + 'SOURCE.json'}
    own = declared - caller_paths
    require(all(name.startswith(namespace) for name in own), 'MANDOR_CURRENT_SINGLE_ADDITIVE_PREPARATION_NAMESPACE')
    expected = dict(base)
    expected.update({name: afui[name] for name in copied})
    absent = []
    checked = 0
    for name, identity in expected.items():
        if name in caller_paths:
            continue
        path = ROOT / name
        require(not path.is_symlink(), 'MANDOR_CURRENT_PARENT_SYMLINK_REFUSED:' + name)
        if not path.is_file():
            absent.append(name)
            continue
        raw = path.read_bytes()
        require(sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == identity['blob'],
                'MANDOR_CURRENT_UNDECLARED_PARENT_CHANGE:' + name)
        checked += 1
    require(allow_sparse_observation or not absent, 'MANDOR_CURRENT_FULL_RUNTIME_SOURCE_MATERIALIZATION_REQUIRED')
    all_paths = {name.decode() for name in git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0') if name}
    require(all_paths == set(expected) | own, 'MANDOR_CURRENT_EXACT_WHOLE_CANDIDATE_FILE_SET_REQUIRED')
    # These are pending source targets, never fabricated acceptance. Opening
    # the actual Root requires a deliberate successor manifest/admission.
    tree = ast.parse((ROOT / routes.NS / 'admission.py').read_bytes())
    values = {target.id: ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
              for target in node.targets if isinstance(target, ast.Name)}
    require(values['PARENT_HEAD'] == routes.AFUI and values['PARENT_TREE'] == routes.AFUI_TREE
            and values['PARENT_RUN'] is None and values['PARENT_JOB'] is None
            and values['PARENT_ROOT_PIN'] is None and values['RUNTIME_ENTRY'] is None,
            'MANDOR_CURRENT_PENDING_AFUI_PARENT_MUST_REMAIN_CLOSED')
    return dict(status='CURRENT_AFUI_MANDOR_SOURCE_PREPARATION_NOT_RUNTIME', base_head=routes.BASE,
                pending_current_Afui_head=routes.AFUI, exact_current_Afui_paths=len(copied),
                exact_reversible_callers=len(routes.PINS), parent_blob_identities=len(expected),
                materialized_parent_files_checked=checked, absent_sparse_parent_files=len(absent),
                full_runtime_materialization_still_required=bool(absent), exact_additive_preparation_files=len(own),
                retained_current_UI_and_build_inputs_unchanged=True,
                historical_preparation_reports_relabelled=False, financial_assertions_and_recovery_unchanged=True,
                actual_parent_root_adopted=False, actual_ERP_cases=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--observe-sparse', action='store_true')
    args = parser.parse_args()
    print(json.dumps(source(allow_sparse_observation=args.observe_sparse), sort_keys=True))
