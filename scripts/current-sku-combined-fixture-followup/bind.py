"""Writer-only freeze. CI verifies these pins and never runs this binder."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def bind():
    c = load('sku_unique_writer_closure', HERE / 'closure.py')
    d = c.d
    entries = c.tree_entries()
    assert not c.git('diff', '--name-only', d.BASE, '--', '.', ':!'+d.NS, ':!.github/workflows/cp7-sku-combined-unique-fixture.yml').strip()
    parent = {}
    for name, entry in entries.items():
        raw = c.raw(ROOT / name, entry['mode'])
        # SHA1 is Git's exact blob identity, separate from content SHA256.
        from hashlib import sha1
        assert sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == entry['blob'], name
        parent[name] = dict(entry, bytes=len(raw), sha256=sha256(raw).hexdigest())
    (HERE / 'PARENT_SOURCE.json').write_text(json.dumps(dict(head=d.BASE, tree=d.TREE, files=parent), indent=2)+'\n')
    own = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != 'SOURCE.json']
    names = sorted(str(p.relative_to(ROOT)) for p in own) + ['.github/workflows/cp7-sku-combined-unique-fixture.yml']
    files = {name: dict(bytes=(ROOT/name).stat().st_size, sha256=sha256((ROOT/name).read_bytes()).hexdigest()) for name in sorted(names)}
    source = dict(status='PREPARED_UNIQUE_MASTER_FIXTURE_LOCAL_ONLY_NOT_NATIVE_PASS',
        base_head=d.BASE, base_tree=d.TREE, execution_branch=d.BRANCH,
        unchanged_parent_files=len(parent), files=files,
        allowed_changes=sorted(names+[d.NS+'/SOURCE.json']),
        derivations=d.inventory(), original_case_ids_and_financial_assertions_unchanged=True,
        original_full_package_engine_counted_changes=5, additional_fixture_derivation_changes=17,
        administrative_master_name_changes=1, actual_successor_execution=False,
        group_recovery_supported=False, production_go=False, independent_acceptance=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(source, indent=2)+'\n')
    return dict(status=source['status'], unchanged_parent_files=len(parent), child_pins=len(files), allowed_paths=len(source['allowed_changes']))


if __name__ == '__main__':
    assert sys.argv[1:] == ['--writer-freeze'], 'SKU_UNIQUE_BINDER_NOT_A_RUNTIME_ENTRYPOINT'
    print(json.dumps(bind()))
