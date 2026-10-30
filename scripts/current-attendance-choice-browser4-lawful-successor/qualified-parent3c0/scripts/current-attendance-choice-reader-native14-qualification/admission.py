"""Actual current closure, then byte-exact parameterized Original intake."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def admitted(root, here, product, derivation):
    current = load('s03_native14_full_current_closure', here / 'source_check.py').check(root, here, require_bound=True)
    original = load('s03_native14_byte_exact_original_parent_intake',
        root / 'scripts/current-attendance-period-choice-native11-qualification/admission.py')
    prior = original.admitted(root, here, product, derivation)
    return dict(prior, status='EXACT_VENDOR41C_CURRENT_SOURCE15_AND_FRESH_NATIVE11_PLUS_READER3_ADMITTED',
        current_qualification=current, current_Native_case_ids=prior['actual_Native_case_ids'],
        historical_inner_label=prior['status'], accepted_successful_Native11_prerequisite_required=False,
        fresh_groups=[11, 3], fresh_Native_case_count=14, actual_Native_cases=0)
