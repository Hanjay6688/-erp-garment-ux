"""All10 original continuation controls plus9 unchanged raw-parent gate controls.

Only local source/business routing is privately derived. Synthetic source/report
objects remain labelled unit doubles and never enter runtime admission.
"""
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONT = ROOT / 'scripts/current-credit-d1-continuation-qualification'
OLD = ROOT / 'scripts/current-credit-d1-owner-followup-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


scope = load('d1_cont_current_retained_test_argv_scope', HERE / 'argv_scope.py')
with scope.inherited_arguments(), patch('psycopg.connect', side_effect=AssertionError('D1_CONT_CURRENT_LOCAL_CONTROLS_FORBID_DATABASE')):
    helper = load('d1_cont_current_retained_test_deriver', HERE / 'derive.py')
    code, _ = helper.local_controls((CONT / 'test_local.py').read_bytes())
    retained = ModuleType('d1_cont_current_private_exact_retained_controls')
    retained.__file__ = str(CONT / 'test_local.py')
    retained.CURRENT_HERE = HERE
    retained.CURRENT_BUSINESS = load('d1_cont_current_test_private_business', HERE / 'business.py').load_business
    exec(compile(code, retained.__file__, 'exec'), retained.__dict__)
    Arithmetic, Gate, Sources = retained.Arithmetic, retained.Gate, retained.Sources
    old_tests = load('d1_cont_current_retained_raw_parent_gate_tests', OLD / 'test_preparation.py')
    ClosedGate = old_tests.ClosedGate
