"""Close new child before delegating exact c163/Native21c source admission."""
from pathlib import Path
from types import ModuleType
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admitted(product, derivation):
    closure = load('sku_unique_complete_source_closure', HERE / 'closure.py').source_only()
    recovery = load('sku_unique_retained_first_failure', HERE / 'recovery.py').verified()
    d = load('sku_unique_historical_scope_derivation', HERE / 'derive.py')
    original = ROOT / d.SOURCES['historical_admission'][0]
    text, proof = d.derive('historical_admission')
    historical = ModuleType('sku_unique_exact_c163_historical_admission')
    historical.__file__ = str(original)
    exec(compile(text, str(original), 'exec'), historical.__dict__)
    # Retained terminal21c Native7 + five package gates remain the only
    # prerequisite. c163's seven fresh PASS observations do not replace it.
    prior = historical.admitted(product, derivation)
    return dict(status='EXACT_C163_FROZEN_PARENT_UNIQUE_FIXTURE_CHILD_ADMITTED',
        current_installation=product.sources(), parent_admission=prior,
        source_closure=closure, retained_first_failure=recovery,
        historical_c163_endpoint_derivation=proof, production_go=False, independent_acceptance=False)
