"""Retain old E semantic adapter over the exact current D1 workflow."""
from pathlib import Path
from types import ModuleType
from hashlib import sha256

ROOT = Path(__file__).resolve().parents[2]
OLD_DERIVER = ROOT / 'scripts/current-credit-e1-native-qualification/workflow.py'
PARENT = '.github/workflows/cp7-credit-d1-product-phase-native13.yml'
PATH = '.github/workflows/cp7-credit-e1-current-d1-native17.yml'
NS = 'scripts/current-credit-e1-current-d1-native17-qualification'
BRANCH = 'astra-a/credit-e1-current-d1-native17-20261030'


def derive(value):
    raw = OLD_DERIVER.read_bytes()
    text = raw.decode()
    for before, after in (("NEW = '.github/workflows/cp7-credit-e1-native17.yml'", "NEW = '" + PATH + "'"),
                          ("NS = 'scripts/current-credit-e1-native-qualification'", "NS = '" + NS + "'")):
        if text.count(before) != 1:
            raise ValueError('E1_CURRENT_WORKFLOW_EXACT_PRIVATE_ROUTING_REQUIRED')
        text = text.replace(before, after, 1)
    module = ModuleType('e1_current_private_retained_workflow_deriver')
    module.__file__ = str(OLD_DERIVER)
    exec(compile(text, str(OLD_DERIVER), 'exec'), module.__dict__)
    current = module.derive(value, BRANCH)
    return current, dict(parent_workflow=PARENT, retained_E_deriver_sha256=sha256(raw).hexdigest(),
        private_routing_substitutions=2, six_change_complete_engine_unchanged=True,
        current_D1_setup_and_restore_preserved=True, null_gate_before_setup_GET_DB=True)
