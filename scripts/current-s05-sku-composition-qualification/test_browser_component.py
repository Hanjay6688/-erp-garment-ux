"""Admission/cleanup controls only; no connection, fixture or runtime cases."""
from pathlib import Path
from unittest.mock import patch
import importlib.util
import os
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('s05_browser_component_controls', HERE/'browser_component.py')
component = importlib.util.module_from_spec(spec); spec.loader.exec_module(component)


def complete():
    return dict(status='RUN_COMPLETE', counts={'PASS': 2}, planned_case_ids=list(component.IDS),
        cases={case: {'status': 'PASS'} for case in component.IDS}, database_remaining=0,
        cleanup_failures=[], auth_counts={'restored': True}, session_leaks=[], console_errors=0,
        auth_cleanup_failures=[], host_exit=0, host_status='RUN_COMPLETE', real_auth=True, jwt_signed_by_runtime=False)


class BrowserAdmission(unittest.TestCase):
    def test_complete_host_vocabulary_and_each_incomplete_boundary(self):
        admissions = [dict(all22_groups_equal_original_install=True)]
        component.require_browser(complete(), admissions)
        for key, bad in [('status', 'PASS'), ('counts', {'PASS': 1, 'INCOMPLETE': 1}),
                         ('planned_case_ids', list(reversed(component.IDS))), ('cases', {}),
                         ('database_remaining', 1), ('cleanup_failures', ['failure']),
                         ('auth_counts', {'restored': False}), ('session_leaks', ['connection']),
                         ('console_errors', 1), ('auth_cleanup_failures', ['user']),
                         ('host_exit', 1), ('host_status', 'INCOMPLETE'), ('real_auth', False),
                         ('jwt_signed_by_runtime', True), ('error', 'first failure'), ('host_error', 'host failure'),
                         ('cases', {case: {'status': 'INCOMPLETE'} for case in component.IDS})]:
            actual = complete(); actual[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError): component.require_browser(actual, admissions)
        for bad in ([], admissions*2, [dict(all22_groups_equal_original_install=False)]):
            with self.assertRaises(ValueError): component.require_browser(complete(), bad)

    def test_browser_environment_restored_even_when_operation_fails(self):
        before = {'S05_SKU_BROWSER_CONFIRM': 'previous', 'OTHER_SETTING': 'unchanged'}
        report = {'browser_fixture_original': {'sha256': 'fixture'}, 'browser_reader_state_original': {'sha256': 'reader'}}
        with patch.dict(os.environ, before, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'first failure'):
                with component.environment(report):
                    self.assertEqual(os.environ['S05_SKU_BROWSER_CONFIRM'], 'cp6_auditor_browser')
                    self.assertEqual(os.environ['S05_SKU_BROWSER_FIXTURES_SHA256'], 'fixture')
                    self.assertEqual(os.environ['S05_SKU_BROWSER_READER_STATE_SHA256'], 'reader')
                    self.assertEqual(os.environ['AUDITOR_BROWSER_CASE_TIMEOUT_MS'], '600000')
                    raise RuntimeError('first failure')
            self.assertEqual(dict(os.environ), before)

    def test_refuses_unsafe_target_before_any_runtime_import(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_OUTER'):
                component.exercise('postgresql://localhost:54322/cp6_rollback', {}, {})
        with patch.dict(os.environ, {'S05_SKU_CONFIRM': 'cp6_rollback'}):
            for target in ('postgresql://remote:54322/cp6_rollback', 'postgresql://localhost:5432/cp6_rollback',
                           'postgresql://localhost:54322/postgres'):
                with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'LOCAL_INSTALLED_PARENT_ONLY'):
                    component.exercise(target, {}, {})


if __name__ == '__main__': unittest.main()
