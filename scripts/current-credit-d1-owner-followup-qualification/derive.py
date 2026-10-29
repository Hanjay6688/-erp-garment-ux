"""The exact current D1 six-substitution complete vendor package engine."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def derive(raw):
    path = ROOT/'scripts/current-credit-de-native-qualification/derive.py'
    spec = importlib.util.spec_from_file_location('continuation_frozen_six_delta', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    code, proof = module.derive(raw)
    if proof['counted_changes'] != 6 or code.count("'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL',product.predecessor.install,cur") != 1:
        raise ValueError('D1_CONT_EXACT_SIX_SUBSTITUTION_COMPLETE_ENGINE_REQUIRED')
    return code, proof
