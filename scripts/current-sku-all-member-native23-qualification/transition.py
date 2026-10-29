"""Explicit source-pin transition; no product/catalog substitution or DB work."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import gzip
import importlib.util
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-sku-all-member-native23-qualification'
BASE = 'bd2cd02c0b724f87f6f1d8628f8227dd30c513a4'
TREE = 'cac694e11f5ab9f02476336b9ef42c20bd832894'
PRODUCT_HEAD = 'c05e3d689e0e4b770af40b6a6b7d7e5cd659a12b'
PRODUCT_TREE = '77d50d4b34287d5d17180b96a5506af379ddafa9'
SQL = 'scripts/cp7_sku_pair_conversion/conversion.sql'
OLD = dict(bytes=20061, sha256='4b26a65beae5defc877589dae756ce2adc9ecb19b3b9a3b68c86765a4c434961')
NEW = dict(bytes=22975, sha256='eece6fbed8cb13b73a49ec2e051478d6ba2a8b1002f6745b8c682db318595d72')
BRANCH = 'astra-a/sku-all-member-native23-20261030'
WORKFLOW = '.github/workflows/cp7-sku-all-member-native23.yml'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def scoped_argv():
    """Retained Native import guards see no qualifier CLI flags; restore identity."""
    prior = sys.argv
    contents = list(prior)
    sys.argv = prior[:1]
    try:
        yield
    finally:
        prior[:] = contents
        sys.argv = prior


def pin_for(name, pin):
    """Only an explicitly old conversion pin can become the reviewed new pin."""
    if name != SQL:
        return pin
    expected = pin['sha256'] if isinstance(pin, dict) else pin
    assert expected == OLD['sha256'], 'SKU23_UNREVIEWED_OLD_SQL_PIN'
    if isinstance(pin, dict):
        assert pin['bytes'] == OLD['bytes'], 'SKU23_UNREVIEWED_OLD_SQL_SIZE'
        return dict(pin, **NEW)
    return NEW['sha256']


def verify_pin(root, name, pin):
    expected = pin_for(name, pin)
    raw = (root / name).read_bytes()
    if isinstance(expected, dict):
        return len(raw) == expected['bytes'] and sha256(raw).hexdigest() == expected['sha256']
    return sha256(raw).hexdigest() == expected


def historical_path(root, name, head):
    old = subprocess.check_output(['git', '-C', str(root), 'show', head + ':' + name])
    if name == SQL:
        assert len(old) == OLD['bytes'] and sha256(old).hexdigest() == OLD['sha256']
        return verify_pin(root, name, OLD)
    return (root / name).read_bytes() == old


def runtime_files(old_files):
    assert old_files[SQL] == OLD['sha256']
    return {name: pin_for(name, digest) for name, digest in old_files.items()}


def historical_sources(product):
    """Retained21 gate receives its actual historical declaration, never a fake product."""
    folder = ROOT / 'scripts/current-sku-combined-followup-qualification'
    raw = gzip.decompress((folder / 'retained21/CP7_SKU_PAIR_CONVERSION_NATIVE.json.gz').read_bytes())
    prior = json.loads(raw)['source_declaration']['current_installation']
    cfg = json.loads((ROOT / 'scripts/current-sku-pair-native-adapter/CONFIG.json').read_bytes())
    assert prior['files'] == cfg['runtime_files'], 'SKU23_HISTORICAL_RUNTIME_SOURCE_MISMATCH'
    actual = product.sources()
    expected = dict(prior, predecessor=product.parent().sources(), files=runtime_files(prior['files']))
    assert prior['predecessor'] == actual['predecessor'] == expected['predecessor'], 'SKU23_PARENT_CHANGED'
    assert actual == expected, 'SKU23_CURRENT_PRODUCT_EXCEEDS_ONE_REVIEWED_SQL_TRANSITION'
    return prior


def fresh_native7_sha(first):
    """Bind the actual fresh strict-group bytes, not the historical21 report digest."""
    name = 'CP7_SKU_PAIR_CONVERSION_NATIVE7.json'
    raw = (ROOT / 'cp6-proof/t3' / name).read_bytes()
    digest = sha256(raw).hexdigest()
    found = [p for p in first['strict_group_originals'] if p['name'] == name]
    assert found == [dict(name=name, bytes=len(raw), sha256=digest)], 'SKU23_FRESH_NATIVE7_ORIGINAL_PIN_REQUIRED'
    assert json.loads(raw) == first['native'], 'SKU23_FRESH_NATIVE7_RAW_GROUP_DIFFERS'
    return digest


def bc_at(fixture, seconds):
    """BC accepts whole-second WIB timestamps; preserve the intended instant/order."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    at = datetime.fromisoformat(fixture['at']) + timedelta(seconds=seconds)
    assert at.tzinfo is not None, 'SKU23_BC_AWARE_FIXTURE_TIME_REQUIRED'
    return at.astimezone(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')


def source_receipt():
    return dict(product_source_commit=PRODUCT_HEAD, product_source_tree=PRODUCT_TREE,
                changed_functions=['cp7_sku_conversion.action_v1(text,jsonb,uuid)'],
                old_conversion=OLD, current_conversion=NEW, current_sources_are_actual=True,
                source_predicates_explicitly_rebound=True, actual_successor_cases=0)


def native_admission(raw):
    d = load('sku23_private_derivations', HERE / 'derive.py')
    text, proof = d.derive('native_admission', raw)
    return text, proof
