"""Business-day control of the auditor runtime without a database (scripts/cp6_auditor_business_day.py).

Replays the first attempt of attention284 on 8116800c (run 37958882487, job 113916327717): planned 9 Oct, server
10 Oct, 30 browser PASS and 6 INCOMPLETE (audit/sol_k4_retest/evidence/ATTENTION_MIDNIGHT_REVIEW.json), and the controls
of ASF-F01 (Astra full CP7 audit of d0b9e9c2, run 38159947839): a date-independent FAIL or COUNTEREXAMPLE that crosses
the date is never rerun."""
from datetime import date
from pathlib import Path
import io
import contextlib
import re
import unittest

import cp6_auditor_business_day as bd

D9, D10 = date(2026, 10, 9), date(2026, 10, 10)
SCRIPTS = Path(__file__).resolve().parent


def row(status='PASS', **extra):
    return dict(status=status, **extra)


class Guard(unittest.TestCase):
    def test_same_day_keeps_status_and_records_the_dates(self):
        r = row()
        self.assertFalse(bd.guard(r, D9, D9, D9))
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['business_day'], dict(planned='2026-10-09', before='2026-10-09', after='2026-10-09'))
        self.assertNotIn('business_day_rollover', r)

    def test_case_started_after_midnight_is_not_a_pass(self):
        r = row()
        self.assertTrue(bd.guard(r, D9, D10, D10))
        self.assertEqual((r['status'], r['status_before_rollover'], r['error']), ('INCOMPLETE', 'PASS', 'AUDITOR_BUSINESS_DAY_ROLLOVER'))

    def test_date_change_while_the_case_runs_is_not_a_pass(self):
        r = row()
        self.assertTrue(bd.guard(r, D9, D9, D10))
        self.assertEqual(r['status'], 'INCOMPLETE')

    def test_non_pass_statuses_are_never_changed(self):
        for status in ('FAIL', 'COUNTEREXAMPLE', 'INCOMPLETE'):
            r = row(status, error='ORIGINAL')
            self.assertTrue(bd.guard(r, D9, D10, D10))
            self.assertEqual((r['status'], r['error']), (status, 'ORIGINAL'))
            self.assertNotIn('status_before_rollover', r)

    def test_date_and_text_compare_alike(self):
        r = row()
        self.assertFalse(bd.guard(r, D9, '2026-10-09', D9))
        self.assertEqual(r['status'], 'PASS')

    def test_the_control_reads_the_same_date_the_groups_are_planned_with(self):
        setup = "select (statement_timestamp() at time zone 'Asia/Jakarta')::date"
        self.assertEqual(bd.WIB_DAY, setup)
        for name in ('cp6_auditor_modes.py', 'cp6_auditor_runner.py'):
            self.assertIn('today=cur.execute("%s")' % setup, (SCRIPTS / name).read_text(), name)
        js = (SCRIPTS / 'cp6_auditor_business_day.mjs').read_text()
        self.assertEqual(re.search(r'WIB_DAY = "([^"]+)"', js).group(1), setup)


class RetryAllowed(unittest.TestCase):
    def rolled(self, status='INCOMPLETE', **extra):
        r = row(status, **extra)
        bd.guard(r, D9, D10, D10)
        return r

    def test_no_change_of_date_never_reruns(self):
        self.assertFalse(bd.retry_allowed({}, {'A': row('FAIL')}))
        self.assertFalse(bd.retry_allowed({}, {'A': row()}))

    def test_rerun_only_when_every_non_pass_is_a_pass_the_date_made_incomplete(self):
        self.assertTrue(bd.retry_allowed({}, {'A': row(), 'B': self.rolled('PASS'), 'C': self.rolled('PASS')}))

    def test_a_failure_of_the_case_that_crosses_the_date_is_not_rerun(self):
        # ASF-F01: the date changing around a FAIL does not show the date caused it.
        for status in ('FAIL', 'COUNTEREXAMPLE', 'INCOMPLETE'):
            failed = self.rolled(status, error='INJECTED_DATE_INDEPENDENT', expected_cents=10000, observed_cents=10001)
            self.assertEqual(failed['status'], status)
            self.assertFalse(bd.retry_allowed({}, {'A': failed}), status)
            self.assertFalse(bd.retry_allowed({}, {'A': self.rolled('PASS'), 'B': failed}), status)

    def test_an_unexplained_non_pass_keeps_the_first_result(self):
        self.assertFalse(bd.retry_allowed({}, {'A': row('FAIL'), 'B': self.rolled('PASS')}))

    def test_runtime_checks_and_malformed_results_are_never_explained_by_a_date(self):
        for extra in (dict(harness_check_failed=True), dict(status_outside_vocabulary='OK'),
                      dict(error='AUDITOR_CASE_RESULT_NOT_A_DICT'), dict(error='AUDITOR_CASE_RESULT_NOT_AN_OBJECT')):
            self.assertFalse(bd.retry_allowed({}, {'A': self.rolled('PASS', **extra)}), extra)

    def test_group_level_problems_keep_the_first_result(self):
        rows = {'A': self.rolled('PASS')}
        for report in (dict(error='X'), dict(missing=['B']), dict(database_remaining=1), dict(cleanup_failures=True),
                       dict(cleanup_failures=['user']), dict(complete_boundary_restored=False)):
            self.assertFalse(bd.retry_allowed(report, rows), report)
        self.assertTrue(bd.retry_allowed(dict(missing=[], database_remaining=0, cleanup_failures=[], complete_boundary_restored=True), rows))


class WithRetry(unittest.TestCase):
    def run_attempts(self, attempts, keep=None):
        calls = []

        def once():
            calls.append(1)
            return attempts[len(calls) - 1]
        with contextlib.redirect_stdout(io.StringIO()) as log:
            out = bd.with_retry('G', once, lambda r: r['cases'], keep)
        return out, len(calls), log.getvalue()

    def test_reruns_once_and_keeps_the_first_attempt(self):
        first = dict(cases={'A': row()})
        bd.guard(first['cases']['A'], D9, D9, D10)
        second = dict(cases={'A': row()})
        kept = []
        out, calls, log = self.run_attempts([first, second], kept.append)
        self.assertEqual(calls, 2)
        self.assertIs(out, second)
        self.assertTrue(out['business_day_retried'])
        self.assertIs(out['business_day_first_attempt'], first)
        self.assertEqual(kept, [first])
        self.assertIn('RERUN_FROM_FRESH_COPY', log)

    def test_never_more_than_one_rerun(self):
        attempts = [dict(cases={'A': row()}) for _ in range(3)]
        for a in attempts:
            bd.guard(a['cases']['A'], D9, D10, D10)
        out, calls, _ = self.run_attempts(attempts)
        self.assertEqual(calls, 2)
        self.assertEqual(out['cases']['A']['status'], 'INCOMPLETE')

    def test_no_rerun_without_a_change_of_date(self):
        first = dict(cases={'A': row('FAIL')})
        out, calls, log = self.run_attempts([first, None])
        self.assertEqual((calls, log), (1, ''))
        self.assertIs(out, first)
        self.assertNotIn('business_day_retried', out)

    def test_a_failure_that_crosses_the_date_keeps_its_one_attempt(self):
        # ASF-10/11: the injected second attempt would PASS; the first attempt's FAIL/COUNTEREXAMPLE stays the result.
        for status in ('FAIL', 'COUNTEREXAMPLE'):
            first = dict(status=status, cases={'A': row(status, error='INJECTED_DATE_INDEPENDENT')})
            bd.guard(first['cases']['A'], D9, D10, D10)
            kept = []
            out, calls, log = self.run_attempts([first, dict(status='PASS', cases={'A': row()})], kept.append)
            self.assertEqual((calls, out['status'], out['cases']['A']['status']), (1, status, status), status)
            self.assertIs(out, first)
            self.assertNotIn('business_day_retried', out)
            self.assertEqual(kept, [])
            self.assertIn('KEPT_FIRST_RESULT', log)
            self.assertNotIn('RERUN_FROM_FRESH_COPY', log)


class AttentionMidnightReplay(unittest.TestCase):
    """The six browser rows of the kept first failure, under the control."""
    SIX = ('P16_RULE_LOCAL_BROWSER_DESKTOP', 'P16_RULE_LOCAL_BROWSER_MOBILE', 'P16_OTHER_BROWSER_DESKTOP',
           'P16_OTHER_BROWSER_MOBILE', 'P15_OBLIGATION_REPORT_BROWSER_DESKTOP', 'P15_OBLIGATION_REPORT_BROWSER_MOBILE')

    def rows(self, extra_fail=False):
        rows = {}
        for i in range(30):
            rows['PASSED_%02d' % i] = row()
            bd.guard(rows['PASSED_%02d' % i], D9, D9, D9)
        for k in self.SIX:
            rows[k] = row('INCOMPLETE', error="AssertionError [ERR_ASSERTION]: '2' !== '1'" if 'RULE' in k else 'CP7_NOTA_AFTER_PERIOD')
            bd.guard(rows[k], D9, D10, D10)
        if extra_fail:
            rows['UNRELATED'] = row('FAIL')
            bd.guard(rows['UNRELATED'], D9, D9, D9)
        return rows

    def test_first_failure_is_flagged_and_kept_for_a_person(self):
        # The six rows failed inside the case (assertion, CP7_NOTA_AFTER_PERIOD) while the date changed; that the date
        # caused them is not shown by the rows, so the group is not rerun (ASF-F01) and they stay flagged INCOMPLETE.
        rows = self.rows()
        self.assertEqual(sum(r['status'] == 'PASS' for r in rows.values()), 30)
        self.assertTrue(all(rows[k]['business_day_rollover'] and rows[k]['status'] == 'INCOMPLETE' for k in self.SIX))
        self.assertTrue(all('status_before_rollover' not in rows[k] for k in self.SIX))
        self.assertFalse(bd.retry_allowed(dict(status='RUN_COMPLETE', database_remaining=0), rows))

    def test_a_failure_before_midnight_is_not_hidden_by_the_rerun(self):
        self.assertFalse(bd.retry_allowed({}, self.rows(extra_fail=True)))


def load_runtime():
    """cp6_auditor_runner and cp6_auditor_modes with their database and CP6 imports replaced by fakes, so the real group
    code runs here without a stack. Only the date reader and the database answers are fake; the control is not."""
    import importlib
    import sys
    import types
    fake_psycopg = types.ModuleType('psycopg')
    fake_psycopg.Error = Exception
    fake_psycopg.sql = types.SimpleNamespace(SQL=None, Identifier=None)
    saved = {k: sys.modules.get(k) for k in ('psycopg', 'cp6_aw_probe', 'cp6_ao_ap_inventory', 'cp6_auditor_runner', 'cp6_auditor_modes')}
    sys.modules['psycopg'] = fake_psycopg
    sys.modules['cp6_aw_probe'] = types.SimpleNamespace(
        r1=types.SimpleNamespace(save=lambda name, report: None), api=types.SimpleNamespace(admin=lambda cur: None, seed=lambda cur: None),
        boundary=types.SimpleNamespace(ADMIN='fake://clone', PRIMARY_ADMIN='fake://primary', snapshot=lambda cur: {'erp': {'app_users': {'count': 1}}},
                                       historical=types.SimpleNamespace(prior=types.SimpleNamespace(set_open_period=lambda cur, d: None))))
    sys.modules['cp6_ao_ap_inventory'] = types.SimpleNamespace(function_pins=lambda cur: 'pins')
    for k in ('cp6_auditor_runner', 'cp6_auditor_modes'):
        sys.modules.pop(k, None)
    runner, modes = importlib.import_module('cp6_auditor_runner'), importlib.import_module('cp6_auditor_modes')
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v
    sys.modules['cp6_auditor_runner'] = runner
    return runner, modes, fake_psycopg


class Clock:
    """The WIB date the fake database answers: day 9 until `switch` date reads have been made, then day 10."""

    def __init__(self, switch):
        self.reads, self.switch = 0, switch

    def __call__(self, *_):
        self.reads += 1
        return D9 if self.reads <= self.switch else D10


class FakeCursor:
    def __init__(self, clock):
        self.clock, self.result = clock, None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, query, params=None):
        self.result = [(self.clock(),)] if query == bd.WIB_DAY else [(True,)]
        return self

    def fetchone(self):
        return self.result[0]


class FakeConnection(FakeCursor):
    def cursor(self):
        return FakeCursor(self.clock)

    def rollback(self):
        pass


class Wiring(unittest.TestCase):
    """The control as it sits in the native group (cp6_auditor_runner.strict_group) and in the race/HTTP rows
    (cp6_auditor_modes.strict_rows)."""

    @classmethod
    def setUpClass(cls):
        cls.runner, cls.modes, cls.psycopg = load_runtime()
        cls.runner.public_state = lambda cur: {}
        cls.runner.session_state = lambda cur: {}
        cls.runner.leaks = lambda cur, before: dict(advisory_locks=0, other_sessions=[])
        cls.modes.session_leaks = lambda database, exclude=(): []

    def native(self, switch, outcome=lambda key: dict(status='PASS')):
        clock, planned_with = Clock(switch), []
        self.psycopg.connect = lambda url: FakeConnection(clock)
        saved = []
        self.runner.r1.save = lambda name, report: saved.append(name)

        def factory(cur, today):
            planned_with.append(today)
            return [(k, (lambda k=k: outcome(k))) for k in ('A', 'B', 'C')]
        with contextlib.redirect_stdout(io.StringIO()):
            report = self.runner.strict_group('G', factory, lambda cur: 'runtime')
        return report, planned_with, saved

    def test_native_group_without_a_change_of_date_runs_once(self):
        report, planned_with, _ = self.native(switch=10 ** 6)
        self.assertEqual((report['status'], planned_with), ('PASS', [D9]))
        self.assertEqual(report['cases']['A']['business_day'], dict(planned='2026-10-09', before='2026-10-09', after='2026-10-09'))
        self.assertNotIn('business_day_retried', report)

    def test_native_group_crossing_midnight_is_rerun_with_the_new_date(self):
        # Reads: setup, then before/after per case. Day 10 from the 4th read: case B starts on another day.
        report, planned_with, saved = self.native(switch=3)
        first = report['business_day_first_attempt']
        self.assertEqual(planned_with, [D9, D10])
        self.assertEqual({k: r['status'] for k, r in first['cases'].items()}, dict(A='PASS', B='INCOMPLETE', C='INCOMPLETE'))
        self.assertEqual(first['cases']['B']['status_before_rollover'], 'PASS')
        self.assertEqual(first['status'], 'INCOMPLETE')
        self.assertEqual((report['status'], report['business_day_retried']), ('PASS', True))
        self.assertTrue(all(r['business_day']['planned'] == '2026-10-10' for r in report['cases'].values()))
        self.assertIn('G_BUSINESS_DAY_FIRST_ATTEMPT', saved)
        self.assertEqual(saved[-1], 'G')

    def test_native_failure_before_midnight_is_not_rerun(self):
        report, planned_with, _ = self.native(switch=3, outcome=lambda key: dict(status='FAIL' if key == 'A' else 'PASS'))
        self.assertEqual(planned_with, [D9])
        self.assertEqual(report['status'], 'INCOMPLETE')
        self.assertEqual(report['cases']['A']['status'], 'FAIL')
        self.assertNotIn('business_day_retried', report)

    def test_native_runtime_check_failure_is_not_rerun(self):
        self.runner.leaks = lambda cur, before: dict(advisory_locks=1, other_sessions=[])
        try:
            report, planned_with, _ = self.native(switch=1)
        finally:
            self.runner.leaks = lambda cur, before: dict(advisory_locks=0, other_sessions=[])
        self.assertEqual(planned_with, [D9])
        self.assertTrue(all(r['harness_check_failed'] and r['business_day_rollover'] for r in report['cases'].values()))

    def test_race_and_http_rows_get_the_control(self):
        clock = Clock(switch=2)
        self.modes.wib_day = clock
        planned = [(k, (lambda: dict(status='PASS'))) for k in ('A', 'B')]
        with contextlib.redirect_stdout(io.StringIO()):
            rows, refusal = self.modes.strict_rows('G', planned, lambda i, key, op: op(), 'copy', today=D9)
        self.assertIsNone(refusal)
        self.assertEqual({k: r['status'] for k, r in rows.items()}, dict(A='PASS', B='INCOMPLETE'))
        self.assertEqual(rows['B']['business_day'], dict(planned='2026-10-09', before='2026-10-10', after='2026-10-10'))

    def test_race_http_and_browser_groups_rerun_through_the_control(self):
        for group, once, key in (('run_races', '_run_races_once', 'races'), ('run_http', '_run_http_once', 'cases'),
                                 ('run_browser', '_run_browser_once', 'cases')):
            attempts = []

            def fake_once(*args, key=key):
                attempts.append(args)
                r = row()
                bd.guard(r, D9, D10 if len(attempts) == 1 else D9, D10 if len(attempts) == 1 else D9)
                return {key: {'A': r}}
            original = getattr(self.modes, once)
            setattr(self.modes, once, fake_once)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    report = getattr(self.modes, group)('module', 'verify', 'phase')
            finally:
                setattr(self.modes, once, original)
            self.assertEqual(len(attempts), 2, group)
            self.assertEqual(report[key]['A']['status'], 'PASS', group)
            self.assertEqual(report['business_day_first_attempt'][key]['A']['status'], 'INCOMPLETE', group)


if __name__ == '__main__':
    unittest.main()
