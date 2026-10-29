"""Writer-only freeze; never generate source pins in runtime or CI."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bind():
    assert not os.environ.get('CI'), 'SKU23_CI_MUST_NOT_REGENERATE_PINS'
    t = load('sku23_writer_transition', HERE / 'transition.py')
    c = load('sku23_writer_closure', HERE / 'closure.py')
    d = load('sku23_writer_derivation', HERE / 'derive.py')
    historical = json.loads((ROOT / 'scripts/current-sku-combined-fixture-followup/PARENT_SOURCE.json').read_bytes())['files']
    additions = {}
    for entry in c.git('ls-tree', '-r', '-z', t.BASE).split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        name = name.decode()
        if name in historical:
            continue
        mode, kind, blob = metadata.decode().split()
        assert kind == 'blob'
        raw = c.raw(ROOT / name, mode)
        assert raw == c.git('show', t.BASE + ':' + name)
        additions[name] = dict(mode=mode, blob=blob, bytes=len(raw), sha256=sha256(raw).hexdigest())
    assert len(additions) == 42
    (HERE / 'BD2_ADDITIONS.json').write_text(json.dumps(dict(head=t.BASE, tree=t.TREE, files=additions), indent=2)+'\n')
    root_paths = c.git('diff', '--name-only', t.BASE, t.PRODUCT_HEAD).decode().splitlines()
    assert len(root_paths) == 8
    own = [str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p != HERE / 'SOURCE.json' and '__pycache__' not in p.parts and p.suffix != '.pyc']
    names = sorted(set(own + root_paths + [t.WORKFLOW]))
    pins = {name: dict(bytes=(ROOT/name).stat().st_size, sha256=sha256((ROOT/name).read_bytes()).hexdigest()) for name in names}
    source = dict(status='PREPARED_FRESH_NATIVE23_NOT_EXECUTED', base_head=t.BASE, base_tree=t.TREE,
        product_head=t.PRODUCT_HEAD, product_tree=t.PRODUCT_TREE,
        historical_c163_parent_files=13569, bd2_parent_files=13611, parent_SQL_exceptions=[t.SQL],
        root_frozen_paths=root_paths, files=pins,
        allowed_changes=sorted(set(names + [t.NS + '/SOURCE.json'])),
        private_derivations=d.inventory(), source_assertion_transitions_separately_declared=True,
        retained_original_Python_asserts=134, private_derived_Python_asserts=134,
        original_complete_package_engine_counted_changes=5, original_fixture_derivation_changes=17,
        BC_formatter_callsite_changes=3, atomic_metadata_block_changes=2,
        current_sources_actual_not_historical_projection=True,
        required_fresh_counts=dict(Native_base=7, Native_cost=3, races=3, Native_permission_waits=6, real_Auth_browser=4),
        actual_successor_cases=0, actual_Auth_HTTP_cases=0,
        group_recovery_supported=False, production_go=False, independent_acceptance=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(source, indent=2)+'\n')
    return dict(status=source['status'], source_files=len(pins), parent_files=13611, source_exceptions=1)


if __name__ == '__main__':
    assert sys.argv[1:] == ['--writer-freeze'], 'SKU23_BINDER_NOT_RUNTIME'
    print(json.dumps(bind(), sort_keys=True))
