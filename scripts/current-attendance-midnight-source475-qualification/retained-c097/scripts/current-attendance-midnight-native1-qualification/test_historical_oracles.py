"""Run exact historical pure-oracle/API models only; no old prerequisite factory."""
import importlib.util
import unittest
from midnight_common import HERE


def load_tests(loader, tests, pattern):
    path=HERE/'historical-midnight-c0/test_preparation.py'
    spec=importlib.util.spec_from_file_location('midnight_immutable_pure_controls',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite=loader.loadTestsFromTestCase(module.OracleControls)
    for name in ('test_timezone_is_UTC_inside_and_original_zone_restored_on_success',
                 'test_SQL_error_rolls_back_zone_scope_restores_and_preserves_original_error',
                 'test_contractor_fixture_value_restores_even_when_native_chain_refuses',
                 'test_occupied_fixed_pair_refuses_before_any_fixture_and_has_no_retry'):
        suite.addTest(module.ApiControls(name))
    return suite
