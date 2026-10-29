"""New child source closure; original Native21c SOURCE/workflow stay unchanged."""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


gate = load('sku_combined_retained_gate', HERE / 'gate.py')


def cfg(): return json.loads((HERE / 'CONFIG.json').read_bytes())


def retained(product):
    config = cfg(); pin = gate.selected(config)
    folder = Path(os.environ['CP7_SKU_NATIVE7_ORIGINALS'])
    return gate.admitted(config, (folder / pin['original']['name']).read_bytes(),
                         (folder / pin['package']['name']).read_bytes(), product.sources(),
                         load('sku_combined_ids', HERE / 'plan.py').NATIVE_IDS)


def source_only():
    source = json.loads((HERE / 'SOURCE.json').read_bytes())
    for path, expected in source['files'].items():
        raw = (ROOT / path).read_bytes()
        assert len(raw) == expected['bytes'] and sha256(raw).hexdigest() == expected['sha256'], path
    changed = subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--name-only', gate.BASE, 'HEAD'], text=True).splitlines()
    assert set(changed) <= set(source['allowed_changes']), 'SKU_COMBINED_UNDECLARED_CHILD_PATH'
    assert not subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=no']).strip()
    # Current published Native21c files and workflow must remain exact.
    for path in source['unchanged_native21c_files']:
        assert (ROOT / path).read_bytes() == subprocess.check_output(['git', '-C', str(ROOT), 'show', gate.BASE + ':' + path]), path
    return source


def historical_native_admission(raw):
    old = "changed = git('diff', '--name-only', cfg['base_head'], 'HEAD').decode().splitlines()"
    new = "changed = git('diff', '--name-only', cfg['base_head'], '" + gate.BASE + "').decode().splitlines()"
    text = raw.decode()
    if text.count(old) != 1:
        raise ValueError('SKU_COMBINED_EXACT_HISTORICAL_NATIVE_ADMISSION_ANCHOR_REQUIRED')
    # Only the historical scope-diff endpoint is fixed to its own published
    # Native21c head. Every old SOURCE hash still checks current actual bytes;
    # source_only separately closes every newly added child path since21c.
    return text.replace(old, new, 1), dict(counted_changes=1, original_sha256=sha256(raw).hexdigest(),
                                          fixed_historical_diff_head=gate.BASE, current_old_source_hash_checks_retained=True)


def admitted(product, derivation):
    retained_proof = retained(product)  # Placeholder fails before DB or fixtures.
    source = source_only()
    original = ROOT / 'scripts/current-sku-pair-native-adapter/admission.py'
    text, scope = historical_native_admission(original.read_bytes())
    prior = ModuleType('sku_combined_historical_Native21c_admission'); prior.__file__ = str(original)
    exec(compile(text, str(original), 'exec'), prior.__dict__)
    native_derive = load('sku_combined_exact_old_native_derivation', ROOT / 'scripts/current-sku-pair-native-adapter/derive.py')
    _, old_proof = native_derive.derive((ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes())
    prior_proof = prior.admitted(ROOT, original.parent, product, old_proof)
    return dict(status='EXACT_NATIVE21C_PREREQUISITE_AND_NEW_COMBINED_CHILD_ADMITTED', qualification=source,
                current_installation=product.sources(), retained21c=retained_proof, native21c_admission=prior_proof,
                historical_scope_derivation=scope, runner_derivation=derivation, production_go=False, independent_acceptance=False)
