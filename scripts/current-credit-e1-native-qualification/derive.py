"""The unchanged D1 six-substitution engine also installs D1 below E1.

product.predecessor is the actual D1 composition when product is e_composition.
No restoration, boundary, role, advisor or package body is replaced.
"""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def derive(raw):
    path = ROOT/'scripts/current-credit-de-native-qualification/derive.py'
    # The exact digest is frozen by CONFIG/SOURCE as well as this local check.
    spec = importlib.util.spec_from_file_location('e1_unchanged_D1_complete_engine_deriver', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    text, proof = module.derive(raw)
    if proof['counted_changes'] != 6 or text.count("'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL',product.predecessor.install,cur") != 1:
        raise ValueError('E1_UNCHANGED_D1_COMPLETE_ENGINE_DERIVATION_REQUIRED')
    return text, proof
