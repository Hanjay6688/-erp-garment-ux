"""All bd2 blobs, all historical13569, one reviewed SQL exception, new files."""
from hashlib import sha1, sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('sku23_closure_transition', HERE / 'transition.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def raw(path, mode='100644'):
    return os.readlink(path).encode() if mode == '120000' else path.read_bytes()


def verify_files(root, files):
    for name, pin in files.items():
        value = raw(root / name, pin.get('mode', '100644'))
        if len(value) != pin['bytes'] or sha256(value).hexdigest() != pin['sha256']:
            raise ValueError('SKU23_DECLARED_BYTES_CHANGED:' + name)


def parent_files():
    historical = json.loads((ROOT / 'scripts/current-sku-combined-fixture-followup/PARENT_SOURCE.json').read_bytes())
    assert historical['head'] == 'c163c1e9ff8f00b8dd8859c32aee0c2069766ad6'
    assert historical['tree'] == 'c986f32ad995d69ff1d0a5fba63689b543172f77'
    assert len(historical['files']) == 13569
    additions = json.loads((HERE / 'BD2_ADDITIONS.json').read_bytes())
    assert additions['head'] == t.BASE and additions['tree'] == t.TREE
    assert not set(historical['files']) & set(additions['files'])
    files = dict(historical['files'], **additions['files'])
    assert len(files) == 13611
    assert git('rev-parse', t.BASE + '^{tree}').decode().strip() == t.TREE
    entries = {}
    for entry in git('ls-tree', '-r', '-z', t.BASE).split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        assert kind == 'blob', 'SKU23_UNSUPPORTED_GIT_ENTRY'
        entries[name.decode()] = dict(mode=mode, blob=blob)
    assert {name: dict(mode=p['mode'], blob=p['blob']) for name, p in files.items()} == entries
    return files


def historical_proof_paths():
    """Only the24 existing retired workflow inputs may be untracked, byte exact."""
    archive = json.loads((ROOT / 'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes())
    assert len(archive['files']) == 24
    names = set()
    present = 0
    for pin in archive['files']:
        name = pin['path']
        assert name.startswith('.github/workflows/') and name.endswith('.yml')
        assert name not in names
        names.add(name)
        path = ROOT / name
        if path.exists():
            assert not path.is_symlink() and path.is_file(), 'SKU23_HISTORICAL_PROOF_TYPE_CHANGED'
            value = path.read_bytes()
            assert len(value) == pin['bytes'] and sha256(value).hexdigest() == pin['sha256'], 'SKU23_HISTORICAL_PROOF_BYTES_CHANGED:' + name
            assert value == (ROOT / pin['archive']).read_bytes(), name
            present += 1
    return names, present


def generated_proof_paths(names):
    """Closed producer-bound output classes; no source or financial authority."""
    accepted, classifications = {}, {}
    for label, filename in (('preDB','generated_receipts.py'),('SKU','generated_sku.py'),('later','generated_later.py')):
        module = t.load('sku23_closed_generated_' + label, HERE / filename)
        pins, summary = module.admit(ROOT, HERE, names)
        assert not set(accepted) & set(pins), 'SKU23_DUPLICATE_GENERATED_OUTPUT_CLASS'
        accepted.update(pins); classifications[label] = summary
    return accepted, classifications


def source_only(*, require_clean=True):
    source = json.loads((HERE / 'SOURCE.json').read_bytes())
    assert source['base_head'] == t.BASE and source['base_tree'] == t.TREE
    assert source['product_head'] == t.PRODUCT_HEAD and source['product_tree'] == t.PRODUCT_TREE
    assert git('rev-parse', t.PRODUCT_HEAD + '^{tree}').decode().strip() == t.PRODUCT_TREE
    assert git('rev-parse', t.PRODUCT_HEAD + '^').decode().strip() == t.BASE, 'SKU23_PUBLIC_PRODUCT_PARENT_CHANGED'
    verify_files(ROOT, source['files'])
    files = parent_files()
    for name, pin in files.items():
        value = raw(ROOT / name, pin['mode'])
        expected = t.pin_for(name, pin)
        assert len(value) == expected['bytes'] and sha256(value).hexdigest() == expected['sha256'], 'SKU23_PARENT_BYTES_CHANGED:' + name
        if name != t.SQL:
            assert sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest() == pin['blob'], name
    root_paths = source['root_frozen_paths']
    assert len(root_paths) == 8 and root_paths.count(t.SQL) == 1
    changed_product = set(git('diff', '--name-only', t.BASE, t.PRODUCT_HEAD).decode().splitlines())
    assert changed_product == set(root_paths), 'SKU23_ROOT_TRANSITION_SCOPE_CHANGED'
    for name in root_paths:
        assert (ROOT / name).read_bytes() == git('show', t.PRODUCT_HEAD + ':' + name), name
    product = t.load('sku23_frozen_one_function_transition', ROOT / 'scripts/current-sku-all-member-preflight/source_check.py').source_only()
    changed = set(git('diff', '--name-only', t.BASE, 'HEAD').decode().splitlines())
    assert changed <= set(source['allowed_changes']), 'SKU23_UNDECLARED_COMMITTED_PATH'
    assert all(name in root_paths or name == t.WORKFLOW or name.startswith(t.NS + '/') for name in source['allowed_changes'])
    proof_paths, proof_count = historical_proof_paths()
    generated = {}
    if require_clean:
        assert not git('status', '--porcelain', '--untracked-files=no').strip(), 'SKU23_DIRTY_SOURCE'
        untracked = {name.decode() for name in git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if name}
        outputs, generated = generated_proof_paths(untracked - proof_paths)
        assert untracked <= proof_paths | set(outputs), 'SKU23_UNDECLARED_UNTRACKED_SOURCE'
        assert changed == set(source['allowed_changes']), 'SKU23_COMMITTED_CLOSURE_INCOMPLETE'
    return dict(status='SKU23_EXACT_BD2_AND_ONE_FUNCTION_TRANSITION_ADMITTED',
        historical_parent_files=13569, unchanged_parent_files=len(files), parent_sql_exceptions=1,
        actually_unchanged_bd2_files=len(files)-1, child_source_files=len(source['files']),
        root_frozen_paths=root_paths, product_transition=product,
        exact_untracked_historical_proofs_present=proof_count,
        generated_non_source_output_classes=generated,
        product_changed_functions=['cp7_sku_conversion.action_v1(text,jsonb,uuid)'],
        financial_quantity_fullcensus_oracles_changed=False, actual_successor_execution=False,
        production_go=False, independent_acceptance=False)
