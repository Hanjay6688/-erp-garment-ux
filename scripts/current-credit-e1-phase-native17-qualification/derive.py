"""Counted private source readers; no ERP, financial or catalog substitutions."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def replace(raw, changes, label):
    text = raw.decode()
    for before, after in changes:
        if text.count(before) != 1:
            raise ValueError('E_PHASE_EXACT_SOURCE_READER_ANCHOR_REQUIRED:' + label)
        text = text.replace(before, after, 1)
    return text, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(text.encode()).hexdigest(),
                      counted_changes=len(changes), classification='SOURCE_METADATA_READER_ONLY')


def admission(raw):
    # Retain both previous current-D1 routes exactly.
    path = ROOT/'scripts/current-credit-e1-current-d1-native17-qualification/derive.py'
    return load('e_phase_exact_prior_D1_routing', path).admission(raw)


def current_admission(raw):
    return replace(raw, (
        ("        if path in exceptions:\n            continue\n        raw = (ROOT / path).read_bytes()", "        if path in exceptions:\n            continue\n        pin = phase_expected_pin(path, pin)\n        raw = (ROOT / path).read_bytes()"),
        ("/ name).read_bytes()).hexdigest() != expected:\n            raise ValueError('E1_CURRENT_NINE_E_FINANCIAL_LEAVES_MUST_REMAIN_EXACT:'", "/ name).read_bytes()).hexdigest() != cfg['E_runtime_files'][name]:\n            raise ValueError('E1_CURRENT_NINE_E_FINANCIAL_LEAVES_MUST_REMAIN_EXACT:'"),
        ("deps['runtime_sources'] != cfg['E_runtime_files']", "deps['runtime_sources'] != cfg['E_historical_runtime_files']"),
    ), 'current_E_two_reviewed_SQL_pins_and_historical_dependency_metadata')


def prepared_check(raw):
    return replace(raw, (
        ('def check(root=ROOT, here=HERE):', 'def check(root=ROOT, here=HERE, additive_paths=frozenset()):'),
        ('if not tracked <= set(entries) | own or not untracked <= own | set(proofs):',
         'if not tracked <= set(entries) | own | additive_paths or not untracked <= own | set(proofs) | additive_paths:'),
        ('(tracked | untracked) - set(entries) - own - set(proofs)',
         '(tracked | untracked) - set(entries) - own - set(proofs) - additive_paths'),
    ), 'complete319_closure_after_exact_additive_source_validation')


def fetch(raw):
    return replace(raw, (("for key in ('original', 'native_group', 'package'):",
                          "for key in ('original', 'native_group', 'package', 'package_files', 'backup_drill'):"),),
                   'retain_all_five_current_parent_raw_outputs')
