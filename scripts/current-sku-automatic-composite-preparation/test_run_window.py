from datetime import datetime
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch
import os
import sys
import unittest

import run_window as window


class RunWindow(unittest.TestCase):
    def observe(self, local_time, monotonic, env, *, record=False):
        with patch.dict(os.environ, env, clear=True), patch.object(window.time, 'monotonic', return_value=monotonic), \
                patch.object(window, 'datetime') as clock:
            clock.now.return_value = datetime.fromisoformat(local_time + '+07:00')
            return window.budget(record=record)

    def test_any_real_wib_evening_preserves_recovery_upload_and_setup_reserves(self):
        for day in ('2026-11-11', '2026-11-12', '2026-12-15'):
            with self.subTest(day=day):
                plan = self.observe(day + 'T20:00:00', 10000, {window.JOB_START: '9970'}, record=True)
                self.assertEqual(plan['business_day'], day)
                self.assertEqual(plan['mode'], 'SHORT_WIB_WINDOW')
                self.assertEqual(plan['work_seconds_remaining'], 14400 - 1200 - 600 - 35)
                self.assertEqual(plan['setup_reserve_seconds'], 1800)
                self.assertFalse(plan['product_clock_changed'])
                self.assertFalse(plan['automatic_group_retry'])
        plan = self.observe('2026-11-12T20:00:00', 10000, {window.JOB_START: '9970'}, record=True)
        self.assertEqual(plan['mode'], 'SHORT_WIB_WINDOW')
        env = {window.JOB_START: '9970', window.DAY: '2026-11-12',
               window.CUTOFF: str(plan['work_cutoff_monotonic'])}
        later = self.observe('2026-11-12T20:25:00', 11500, env)
        self.assertEqual(later['work_seconds_remaining'], plan['work_seconds_remaining'] - 1500)
        self.assertEqual(self.observe('2026-11-12T20:05:00', 11500, env), {
            **later, 'seconds_to_midnight': 14100})
        with self.assertRaisesRegex(ValueError, 'SKU27_ADMITTED_WIB_DAY_REQUIRED'):
            self.observe('2026-11-13T00:01:00', 24700, env)
        with self.assertRaisesRegex(ValueError, 'SKU27_SHORT_WINDOW_INSUFFICIENT_WORK_AND_SETUP_TIME'):
            self.observe('2026-11-12T23:40:00', 11500, env)

    def test_original_day_window_and_insufficient_short_setup(self):
        with self.assertRaisesRegex(ValueError, 'SKU27_SHORT_WINDOW_INSUFFICIENT_WORK_AND_SETUP_TIME'):
            self.observe('2026-11-11T23:00:00', 10000, {window.JOB_START: '9900'}, record=True)
        for day in ('2026-11-11', '2026-11-12'):
            plan = self.observe(day + 'T00:02:00', 10000, {window.JOB_START: '9970'}, record=True)
            self.assertEqual(plan['mode'], 'STANDARD')
            self.assertEqual(plan['business_day'], day)
            self.assertEqual(plan['required_seconds'], 21600)

    def test_admitted_standard_attempt_can_cross_18_without_renewing_six_hours(self):
        env = {window.JOB_START: '9970'}
        plan = self.observe('2026-11-12T17:59:00', 10000, env, record=True)
        self.assertEqual(plan['mode'], 'STANDARD')
        env[window.DAY] = plan['business_day']
        later = self.observe('2026-11-12T18:10:00', 10660, env)
        self.assertEqual(later, {**plan, 'seconds_to_midnight': 21000})
        with self.assertRaisesRegex(ValueError, 'SKU27_ADMITTED_STANDARD_WIB_WINDOW_EXHAUSTED'):
            self.observe('2026-11-12T18:13:00', 10660, env)
        with self.assertRaisesRegex(ValueError, 'SKU27_ADMITTED_STANDARD_WIB_WINDOW_EXHAUSTED'):
            self.observe('2026-11-12T23:28:30', 29770, env)

    def test_monotonic_start_and_cutoff_must_be_finite_and_bounded(self):
        for start in ('nan', 'inf', '0', '10001', 'bad', ''):
            with self.subTest(start=start), self.assertRaisesRegex(ValueError, 'SKU27_REAL_JOB_START_REQUIRED'):
                self.observe('2026-11-12T20:00:00', 10000, {window.JOB_START: start}, record=True)
        env = {window.JOB_START: '9970', window.DAY: '2026-11-12'}
        for invalid in ('1e5000', 'nan', 'bad', '10000'):
            with self.subTest(cutoff=invalid), self.assertRaisesRegex(ValueError, 'SKU27_SHORT_WINDOW_WORK_DEADLINE_EXHAUSTED'):
                self.observe('2026-11-12T20:00:00', 10000, {**env, window.CUTOFF: invalid})
        capped = self.observe('2026-11-12T18:27:00', 10000, {**env, window.CUTOFF: '1e100'})
        self.assertEqual(capped['work_seconds_remaining'], 5 * 3600 + 2 * 60 + 25)
        capped_by_job = self.observe('2026-11-12T17:00:00', 10000, {**env, window.CUTOFF: '1e100'})
        self.assertEqual(capped_by_job['work_cutoff_monotonic'], 9970 + 19800)

    def test_recorded_late_window_bounds_setup_and_rejects_stale_day(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'github.env'
            env = {window.JOB_START: '9970', 'GITHUB_ENV': str(output)}
            with patch.dict(os.environ, env, clear=True), patch.object(window.time, 'monotonic', return_value=10000), \
                    patch.object(window, 'datetime') as clock, patch.object(sys, 'argv', ['run_window.py', '--record']), \
                    redirect_stdout(StringIO()):
                clock.now.return_value = datetime.fromisoformat('2026-11-12T18:27:00+07:00')
                window.main()
            recorded = dict(line.split('=', 1) for line in output.read_text().splitlines())
            self.assertEqual(recorded, {window.DAY: '2026-11-12', window.CUTOFF: '28145.0'})
            with patch.dict(os.environ, {**env, **recorded}, clear=True), \
                    patch.object(window.time, 'monotonic', return_value=10000), patch.object(window, 'datetime') as clock, \
                    patch.object(sys, 'argv', ['run_window.py', '--setup-limit']), redirect_stdout(StringIO()) as stdout:
                clock.now.return_value = datetime.fromisoformat('2026-11-12T18:27:00+07:00')
                window.main()
                self.assertEqual(stdout.getvalue(), '18133s\n')
                clock.now.return_value = datetime.fromisoformat('2026-11-13T00:00:00+07:00')
                with self.assertRaisesRegex(ValueError, 'SKU27_ADMITTED_WIB_DAY_REQUIRED'):
                    window.main()

    def test_supervisor_uses_smaller_budget_preserving_failure_and_recovery(self):
        calls = Mock()
        calls.supervise.return_value = dict(status='INCOMPLETE', actual_case_credit=0, deadline_reached=True)
        supervisor = SimpleNamespace(supervise=calls.supervise, JOB_SECONDS=21600, WORK_SECONDS=19800)
        plan = dict(mode='SHORT_WIB_WINDOW', work_seconds_remaining=93)
        window.bind_supervisor(supervisor, calls.claim)
        with patch.object(window, 'budget', return_value=plan):
            result = supervisor.supervise(['worker'], work_seconds=800, recovery_seconds=1200)
        self.assertEqual([call[0] for call in calls.mock_calls], ['claim', 'supervise'])
        calls.supervise.assert_called_once_with(['worker'], work_seconds=92, recovery_seconds=1200)
        self.assertEqual(result, dict(status='INCOMPLETE', actual_case_credit=0, deadline_reached=True,
                                      wib_window=dict(plan, effective_worker_seconds=92)))

    def test_short_exhaustion_before_claim_and_original_budget_after_expiry(self):
        start, claim = Mock(return_value={}), Mock()
        supervisor = SimpleNamespace(supervise=start, JOB_SECONDS=21600, WORK_SECONDS=19800)
        window.bind_supervisor(supervisor, claim)
        with patch.object(window, 'budget', return_value=dict(mode='SHORT_WIB_WINDOW', work_seconds_remaining=1)):
            with self.assertRaisesRegex(ValueError, 'SKU27_SHORT_WINDOW_WORK_DEADLINE_EXHAUSTED'):
                supervisor.supervise(['worker'], work_seconds=800, recovery_seconds=1200)
        claim.assert_not_called()
        start.assert_not_called()
        with patch.object(window, 'budget', return_value=dict(mode='STANDARD')):
            self.assertEqual(supervisor.supervise(['worker'], work_seconds=800, recovery_seconds=1200), {})
        claim.assert_called_once_with()
        start.assert_called_once_with(['worker'], work_seconds=800, recovery_seconds=1200)


if __name__ == '__main__':
    unittest.main()
