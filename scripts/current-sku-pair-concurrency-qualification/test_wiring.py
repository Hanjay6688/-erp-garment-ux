"""Synthetic wiring tests. No connection, dump, SQL, real Auth or race run."""
from collections import Counter
from contextlib import nullcontext
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib.util
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


runner = load('sku_synthetic_followup_wiring', HERE / 'runner.py')
always = load('sku_synthetic_existing_always', HERE.parent / 'current-factory-initial-stage/restoration.py').always


class Wiring(unittest.TestCase):
    def run_synthetic(self, *, partial_native=False, fail_restore=False):
        events, operations, admissions, report = [], [], [], {}
        native_ids = runner.ids(runner.CALLBACKS / 'cases.py')
        native7 = dict(status='PASS', used_guard_refused_before_DDL=True, actual_Native_cases=7,
                       native=dict(counts={'PASS': 6 if partial_native else 7}, cases={key: dict(status='PASS') for key in native_ids}))
        current = {'test_source': 'LOCAL_ONLY'}
        product = SimpleNamespace(sources=lambda: current, runtime=lambda: (None, None, None, None, object()), verify=lambda cur, state: None)
        package = ModuleType('cp7_sku_pair_conversion'); package.composition = product
        business = SimpleNamespace(IDS=runner.ids(runner.CALLBACKS / 'races.py'))
        def race(_tools, _today, *, same_uuid, first_commit):
            operations.append(('conversion', same_uuid, first_commit))
            return dict(status='PASS', local_synthetic_only=True)
        business.exercise = race
        permissions = SimpleNamespace(IDS=runner.ids(runner.CALLBACKS / 'auth_waits.py'))
        def permission_cases(tools, today):
            def operation(key):
                operations.append(('permission', key))
                return dict(status='PASS', local_synthetic_only=True)
            return [(key, lambda key=key: operation(key)) for key in permissions.IDS]
        permissions.cases = permission_cases
        def copy_database(name):
            admissions.append(dict(all22_groups_equal_original_install=True))
            return 'postgresql://LOCAL_ONLY/' + name
        adapter = SimpleNamespace(COPY_ADMISSIONS=admissions, copy_database=copy_database)
        original_copy = lambda name: 'LOCAL_ONLY_' + name
        tools = SimpleNamespace(admin='LOCAL_ONLY')
        modes = SimpleNamespace(copy_db=original_copy)
        def run_races(selected, verify, phase):
            modes.copy_db('cp6_auditor_race')
            planned = selected.races(tools, date(2026, 10, 29))
            rows = {}
            for i, (key, operation) in enumerate(planned):
                try:
                    if i:
                        modes.copy_db('cp6_auditor_race')
                    row = operation()
                except Exception as error:
                    row = dict(status='INCOMPLETE', error=str(error))
                rows[key] = dict(row, session_leaks=[])
            counts = dict(Counter(row['status'] for row in rows.values()))
            return dict(status='RUN_COMPLETE' if counts == {'PASS': 9} else 'INCOMPLETE',
                        races=rows, counts=counts, planned_race_ids=[key for key, _ in planned], database_remaining=0)
        modes.run_races = run_races
        deps = SimpleNamespace(modes=modes)
        class FakeBoundary:
            always = staticmethod(always)
            def __init__(self, tools, db, d, state, key):
                self.key = key; self.observed = {'local_synthetic_only': True}
            def capture(self):
                events.append(('capture_full', self.key))
            def observe(self):
                events.append(('observe', self.key)); return self.observed
            def restore(self):
                events.append(('full_restore', self.key))
                if fail_restore:
                    raise ValueError('LOCAL_RESTORE_FAILED')
                return {'only_pg_cron_errors': True}
            def verify(self, restored):
                return dict(**{key: True for key in runner.controls.RESTORE_GATES}, selected_table_cleanup=False)
            def cleanup(self):
                events.append(('cleanup_dump', self.key))
        def module(name, path):
            return adapter if path.name == 'copy_authority.py' else business if path.name == 'races.py' else permissions
        cursor = SimpleNamespace(execute=lambda _: SimpleNamespace(fetchone=lambda: ('cp6_rollback',)), close=lambda: events.append(('cursor_closed',)))
        connection = SimpleNamespace(info=SimpleNamespace(host='127.0.0.1', port=54322), rollback=lambda: None, close=lambda: events.append(('source_closed',)))
        with patch.dict(sys.modules, {'cp7_sku_pair_conversion': package}), \
             patch.object(runner, 'admit_sources', return_value={'local_synthetic_only': True}), \
             patch.object(runner, 'runtime', return_value=deps) as runtime, \
             patch.object(runner, 'handoff_source', return_value={'local_synthetic_only': True}) as handoff, \
             patch.object(runner, 'load', side_effect=module), patch.object(runner, 'CopyBoundary', FakeBoundary):
            try:
                runner.exercise(connection, cursor, None, 'postgresql://postgres@127.0.0.1:54322/cp6_rollback',
                                report, {'sources': current, 'after': {}}, native7=native7)
                failure = None
            except Exception as error:
                failure = error
            return SimpleNamespace(report=report, failure=failure, events=events, operations=operations,
                                   admissions=admissions, copies_hook_restored=modes.copy_db is original_copy,
                                   runtime_calls=runtime.call_count, handoff_calls=handoff.call_count)

    def test_partial_native_never_connects_copies_or_runs_a_fixture(self):
        result = self.run_synthetic(partial_native=True)
        self.assertIsInstance(result.failure, ValueError)
        self.assertEqual(result.runtime_calls, 0); self.assertEqual(result.handoff_calls, 0)
        self.assertEqual(result.operations, []); self.assertEqual(result.admissions, [])

    def test_exact_original_schedule_routes_nine_callbacks_and_restores_nine_times(self):
        result = self.run_synthetic()
        self.assertIsNone(result.failure)
        self.assertEqual(result.operations[:3], [('conversion', True, True), ('conversion', False, True), ('conversion', False, False)])
        self.assertEqual(len(result.operations), 9)
        self.assertEqual(len([event for event in result.events if event[0] == 'full_restore']), 9)
        self.assertEqual(len(result.admissions), 9)
        self.assertTrue(result.copies_hook_restored)
        self.assertEqual(result.report['actual_Auth_HTTP_cases'], 0)
        self.assertEqual(result.report['actual_Native_session_permission_waits'], 6)

    def test_failed_restore_closes_later_copy_and_fixture_before_they_run(self):
        result = self.run_synthetic(fail_restore=True)
        self.assertIsInstance(result.failure, ValueError)
        self.assertEqual(len(result.operations), 1)
        self.assertEqual(len(result.admissions), 1)
        self.assertTrue(result.copies_hook_restored)
        rows = list(result.report['concurrency']['races'].values())
        self.assertEqual(rows[0]['restore_error'], 'LOCAL_RESTORE_FAILED')
        self.assertTrue(all('NO_NEW_COPY' in row['error'] for row in rows[1:]))
        self.assertEqual(result.report['status'], 'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
