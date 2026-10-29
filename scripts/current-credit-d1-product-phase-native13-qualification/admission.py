"""Use the byte-exact historical admission against this child's declarations."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admitted(repo, here, product, derivation):
    closure = load('d1_product_phase_exact_joined_source', here / 'source_check.py')
    joined = closure.check(repo, here, require_bound=True)
    original = load('d1_product_phase_unchanged_historical_admission',
                    repo / 'scripts/current-credit-de-native-qualification/admission.py')
    proof = original.admitted(repo, here, product, derivation)
    return dict(proof, joined_product_phase_source=joined,
                actual_augmentation_binding=joined['augmentation'],
                historical_D1_failures_are_prerequisites=False)
