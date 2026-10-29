"""Actual current product plus historical prerequisite; no historical fresh credit."""
from pathlib import Path
import importlib.util
from types import ModuleType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def historical():
    d = load('sku23_admission_deriver', HERE / 'derive.py')
    text, proof = d.derive('historical_admission')
    module = ModuleType('sku23_explicit_historical_admission')
    module.__file__ = str(ROOT / d.SOURCES['historical_admission'][0])
    exec(compile(text, module.__file__, 'exec'), module.__dict__)
    return module, proof


def retained(product):
    module, _ = historical()
    proof = module.retained(product)
    assert proof['fresh_cases_credited'] == 0
    return proof


def preflight(*, require_clean=True):
    source = load('sku23_preDB_closure', HERE / 'closure.py').source_only(require_clean=require_clean)
    first = load('sku23_preDB_negative', HERE / 'recovery.py').verified()
    return dict(source=source, retained_failed_bd2=first)


def admitted(product, derivation):
    before = preflight()
    module, private = historical()
    proof = module.admitted(product, derivation)
    t = load('sku23_admitted_transition', HERE / 'transition.py')
    t.historical_sources(product)
    return dict(status='SKU23_HISTORICAL21_AND_ACTUAL_ONE_FUNCTION_SUCCESSOR_ADMITTED',
        current_installation=product.sources(), source_transition=t.source_receipt(),
        full_source_closure=before['source'], retained_failed_bd2=before['retained_failed_bd2'],
        historical_admission=proof, historical_private_source_derivation=private,
        runner_derivation=derivation, actual_successor_cases=0,
        group_recovery_supported=False, production_go=False, independent_acceptance=False)
