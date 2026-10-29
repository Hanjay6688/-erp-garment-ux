"""Complete unchanged c163 tree and separately declared new-child closure."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = load('sku_unique_closure_deriver', HERE / 'derive.py')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def tree_entries():
    assert git('rev-parse', d.BASE + '^{tree}').decode().strip() == d.TREE
    result = {}
    for entry in git('ls-tree', '-r', '-z', d.BASE).split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        assert kind == 'blob', 'SKU_UNIQUE_UNHANDLED_PARENT_GIT_TYPE'
        result[name.decode()] = dict(mode=mode, blob=blob)
    return result


def raw(path, mode='100644'):
    return os.readlink(path).encode() if mode == '120000' else path.read_bytes()


def verify_files(root, files):
    for name, pin in files.items():
        value = raw(root / name, pin.get('mode', '100644'))
        if len(value) != pin['bytes'] or sha256(value).hexdigest() != pin['sha256']:
            raise ValueError('SKU_UNIQUE_DECLARED_BYTES_CHANGED:' + name)


def source_only(*, require_clean=True):
    source = json.loads((HERE / 'SOURCE.json').read_bytes())
    assert source['base_head'] == d.BASE and source['base_tree'] == d.TREE
    verify_files(ROOT, source['files'])
    parent = json.loads((HERE / 'PARENT_SOURCE.json').read_bytes())
    assert parent['head'] == d.BASE and parent['tree'] == d.TREE
    actual = tree_entries()
    assert {name: {k: pin[k] for k in ('mode', 'blob')} for name, pin in parent['files'].items()} == actual
    assert source['unchanged_parent_files'] == len(actual)
    verify_files(ROOT, parent['files'])
    paths = git('diff', '--name-only', d.BASE, 'HEAD').decode().splitlines()
    assert set(paths) <= set(source['allowed_changes']), 'SKU_UNIQUE_UNDECLARED_CHILD_PATH'
    if require_clean:
        assert not git('status', '--porcelain', '--untracked-files=no').strip(), 'SKU_UNIQUE_DIRTY_TRACKED_WORKTREE'
        assert set(paths) == set(source['allowed_changes']), 'SKU_UNIQUE_UNCOMMITTED_DECLARED_CHILD'
    assert all(name.startswith(d.NS + '/') or name == '.github/workflows/cp7-sku-combined-unique-fixture.yml'
               for name in source['allowed_changes'])
    return dict(status='ALL_C163_FILES_UNCHANGED_AND_NEW_CHILD_CLOSED', parent_head=d.BASE,
        unchanged_parent_files=len(actual), child_source_files=len(source['files']),
        declared_child_paths=len(source['allowed_changes']), private_derivations=d.inventory(),
        product_or_oracle_changes=False, actual_successor_execution=False)
