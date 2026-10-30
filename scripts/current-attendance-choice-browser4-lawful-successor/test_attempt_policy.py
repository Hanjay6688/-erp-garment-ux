"""Local controls for S03's actual entry scheduling, with no DB/Auth execution."""
from contextlib import contextmanager, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import io
import sys
import unittest
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


policy = load('s03_attempt_policy_test', HERE / 'attempt_policy.py')
day = load('s03_retained_business_day_test', ROOT / 'scripts/cp6_auditor_business_day.py')


class AttemptPolicy(unittest.TestCase):
    def test_full_job_window_uses_real_wib_and_refuses_boundary(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/cp7-current-s03-browser4-lawful.yml').read_bytes())
        self.assertEqual(policy.JOB_BUDGET_SECONDS, workflow['jobs']['p21']['timeout-minutes'] * 60)
        self.assertEqual(policy.require_window(datetime.fromisoformat('2026-10-30T12:59:59+00:00'))['seconds_to_midnight'], 14401)
        for date in ['2026-10-30T13:00:00+00:00', '2026-10-30T16:59:59+00:00']:
            with self.subTest(date=date), self.assertRaisesRegex(ValueError, 'INSUFFICIENT_WIB_DAY_WINDOW'):
                policy.require_window(datetime.fromisoformat(date))
        self.assertEqual(policy.require_window(datetime.fromisoformat('2026-10-30T17:00:00+00:00'))['business_day'], '2026-10-31')
        with self.assertRaisesRegex(ValueError, 'AWARE_REAL_CLOCK'):
            policy.require_window(datetime(2026, 10, 30))

    def test_real_entry_refuses_short_day_before_runtime(self):
        probe = load('s03_attempt_probe_refusal', HERE / 'probe.py')
        with patch.object(probe, 'load', return_value=policy), patch.object(probe, 'runtime') as runtime, \
             patch.object(policy, 'require_window', side_effect=ValueError('SHORT_DAY')):
            with self.assertRaisesRegex(ValueError, 'SHORT_DAY'):
                probe.main([])
        runtime.assert_not_called()

    def test_real_entry_keeps_first_failure_and_restores_all_callers_on_success_and_exception(self):
        for raise_error in [False, True]:
            probe = load('s03_attempt_probe_execution_' + str(raise_error), HERE / 'probe.py')
            original = day.with_retry
            writer = lambda: None
            first = dict(status='INCOMPLETE', cases={'mobile': dict(status='INCOMPLETE',
                status_before_rollover='PASS', error='AUDITOR_BUSINESS_DAY_ROLLOVER', business_day_rollover=True)})
            calls = []
            def package_run(mode):
                self.assertEqual(mode, 'install'); self.assertIsNot(day.with_retry, original)
                actual = day.with_retry('S03', lambda: calls.append(1) or first, lambda r: r['cases'])
                self.assertIs(actual, first)
                if raise_error: raise RuntimeError('ORIGINAL_FAILURE')
            engine = SimpleNamespace(package=SimpleNamespace(_writer_runtime=writer, run=package_run), run=lambda: None)
            @contextmanager
            def runtime():
                yield engine
            with patch.object(probe, 'load', return_value=policy), patch.object(probe, 'runtime', runtime), \
                 patch.object(policy, 'require_window', return_value={'automatic_group_retry': False}), \
                 patch.dict(sys.modules, {'cp6_auditor_business_day': day}), redirect_stdout(io.StringIO()):
                if raise_error:
                    with self.assertRaisesRegex(RuntimeError, 'ORIGINAL_FAILURE'): probe.main([])
                else: probe.main([])
            self.assertEqual(calls, [1]); self.assertIs(day.with_retry, original)
            self.assertIs(engine.package._writer_runtime, writer)

    def test_source_only_entry_does_not_apply_runtime_clock_or_scheduling(self):
        probe = load('s03_attempt_source_only', HERE / 'probe.py')
        engine = SimpleNamespace(admitted=lambda: dict(status='EXACT_SOURCE'))
        @contextmanager
        def runtime():
            yield engine
        original = day.with_retry
        with patch.object(probe, 'runtime', runtime), patch.object(probe, 'load') as loader, redirect_stdout(io.StringIO()):
            probe.main(['--check-actual-source'])
        loader.assert_not_called(); self.assertIs(day.with_retry, original)


if __name__ == '__main__':
    unittest.main()
