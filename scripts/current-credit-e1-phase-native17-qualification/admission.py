"""Whole publicfe2/source319 first, then explicit historical source reader routes."""
from pathlib import Path
from types import ModuleType
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CURRENT = ROOT/'scripts/current-credit-e1-current-d1-native17-qualification'


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def phase_expected_pin(path, historical):
    transition = json.loads((HERE/'PRODUCT_TRANSITION.json').read_bytes())
    item = transition['product_changes'].get(path)
    if item is None:
        return historical
    if historical['sha256'] != item['before']['sha256']:
        raise ValueError('E_PHASE_REVIEWED_OLD_PRODUCT_PIN_REQUIRED')
    return item['after']


def current():
    text, proof = load('e_phase_counted_read_routes', HERE/'derive.py').current_admission((CURRENT/'admission.py').read_bytes())
    m = ModuleType('e_phase_explicit_current_E_private_source_reader')
    m.__file__ = str(HERE/'admission.py')
    m.phase_expected_pin = phase_expected_pin
    exec(compile(text, str(CURRENT/'admission.py'), 'exec'), m.__dict__)
    return m, proof


def source_only():
    load('e_phase_complete_public_source_before_legacy', HERE/'source_check.py').check()
    m, proof = current()
    return m.source_only()


def admitted(product, derivation):
    load('e_phase_parent_before_runtime', HERE/'gate.py').selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    source_only()
    m, proof = current()
    result = m.admitted(product, derivation)
    return dict(result, current_E_phase_source_derivation=proof,
                public_prepared_backend='fe2ae370c00e68437c4951c28c3a1038ce35fb38',
                old_failed_E17_prerequisite=False, fresh_actual_cases_credited_by_source=0)
