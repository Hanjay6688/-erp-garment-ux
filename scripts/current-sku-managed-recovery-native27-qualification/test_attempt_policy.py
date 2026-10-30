"""Reproduce actual58c8 duplicate copies without DB, Auth or a new CI run."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import contextlib
import importlib.util
import io
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load('sku27_test_attempt_policy', HERE / 'attempt_policy.py')
day = load('sku27_test_retained_business_day', ROOT / 'scripts/cp6_auditor_business_day.py')


class AttemptPolicy(unittest.TestCase):
    def setUp(self):
        self.first = dict(status='INCOMPLETE', database_remaining=0, races={})
        for index in range(11):
            row = dict(status='PASS', full_restore=True)
            day.guard(row, '2026-10-30', '2026-10-30',
                      '2026-10-30' if index < 2 else '2026-10-31')
            self.first['races'][str(index)] = row

    def test_retained_retry_reproduces_twenty_two_copies_and_new_path_keeps_first_eleven(self):
        copies = []
        def run_once():
            copies.extend(range(11))
            return self.first if len(copies) == 11 else dict(status='RUN_COMPLETE',
                races={str(i): dict(status='PASS') for i in range(11)})
        with contextlib.redirect_stdout(io.StringIO()):
            old = day.with_retry('SKU27', run_once, lambda r: r['races'])
        self.assertEqual(len(copies), 22)
        self.assertTrue(old['business_day_retried'])
        self.assertIs(old['business_day_first_attempt'], self.first)
        copies.clear()
        original = deepcopy(self.first)
        with contextlib.redirect_stdout(io.StringIO()), policy.single_attempt(day):
            actual = day.with_retry('SKU27', run_once, lambda r: r['races'])
        self.assertEqual(len(copies), 11)
        self.assertIs(actual, self.first)
        self.assertEqual(actual, original)
        self.assertEqual(sum(r['status'] == 'INCOMPLETE' for r in actual['races'].values()), 9)

    def test_real_failure_pass_and_empty_report_are_never_retried_or_relabelled(self):
        for report in [dict(status='INCOMPLETE', races={}, error='RESTORE_FAILED'),
                       dict(status='RUN_COMPLETE', races={'one': dict(status='PASS')}),
                       dict(status='INCOMPLETE', races={'one': dict(status='FAIL', error='BAD_AMOUNT')})]:
            with self.subTest(report=report), policy.single_attempt(day):
                calls = []
                def once():
                    calls.append(1)
                    return report
                self.assertIs(day.with_retry('SKU27', once, lambda r: r['races']), report)
                self.assertEqual(calls, [1])

    def test_caller_restored_on_failure(self):
        original = day.with_retry
        with self.assertRaisesRegex(RuntimeError, 'ORIGINAL_FAILURE'):
            with policy.single_attempt(day):
                day.with_retry('SKU27', lambda: (_ for _ in ()).throw(RuntimeError('ORIGINAL_FAILURE')), lambda r: r)
        self.assertIs(day.with_retry, original)

    def test_wib_window_uses_unchanged_aware_clock_and_full_job_budget(self):
        allowed = policy.require_window(datetime.fromisoformat('2026-10-30T13:29:59+00:00'))
        self.assertEqual(allowed['seconds_to_midnight'], 12601)
        self.assertFalse(allowed['product_clock_changed'])
        for stamp in ['2026-10-30T13:30:00+00:00', '2026-10-30T16:59:59+00:00']:
            with self.subTest(stamp=stamp), self.assertRaisesRegex(ValueError, 'INSUFFICIENT_WIB_DAY_WINDOW'):
                policy.require_window(datetime.fromisoformat(stamp))
        self.assertEqual(policy.require_window(datetime.fromisoformat('2026-10-30T17:00:00+00:00'))['business_day'], '2026-10-31')
        with self.assertRaisesRegex(ValueError, 'AWARE_REAL_CLOCK'):
            policy.require_window(datetime(2026, 10, 30))

    def test_actual_probe_refuses_short_day_before_runtime_import(self):
        probe = load('sku27_test_probe_early_window', HERE / 'probe.py')
        with patch.object(probe, 'load', return_value=policy), patch.object(probe, 'runtime') as runtime:
            with patch.object(policy, 'require_window', side_effect=ValueError('SHORT_DAY')):
                with self.assertRaisesRegex(ValueError, 'SHORT_DAY'):
                    probe.main(['--runtime'])
        runtime.assert_not_called()

    def test_actual_probe_scopes_policy_over_package_and_restores_even_on_failure(self):
        probe = load('sku27_test_probe_single_attempt', HERE / 'probe.py')
        original_load = probe.load
        original_retry = day.with_retry
        calls = []
        def package_run(mode):
            self.assertEqual(mode, 'install')
            self.assertIsNot(day.with_retry, original_retry)
            result = day.with_retry('PACKAGE', lambda: calls.append(1) or self.first, lambda r: r['races'])
            self.assertIs(result, self.first)
            raise RuntimeError('ORIGINAL_PACKAGE_FAILURE')
        runtime = SimpleNamespace(admitted=lambda: None, engine=SimpleNamespace(
            package=SimpleNamespace(run=package_run), run=lambda: None))
        def loader(name, path):
            return policy if path.name == 'attempt_policy.py' else original_load(name, path)
        with patch.object(probe, 'load', side_effect=loader), patch.object(probe, 'runtime', return_value=runtime), \
             patch.object(policy, 'require_window', return_value={'automatic_group_retry': False}), \
             patch.dict(sys.modules, {'cp6_auditor_business_day': day}), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'ORIGINAL_PACKAGE_FAILURE'):
                probe.main(['--runtime'])
        self.assertEqual(calls, [1])
        self.assertIs(day.with_retry, original_retry)


if __name__ == '__main__':
    unittest.main()
