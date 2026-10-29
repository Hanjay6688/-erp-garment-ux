"""Local synthetic orchestration checks only; no Native/SQL/Auth/race credit."""
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
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


runner = load('sku_local_concurrency_plan', HERE / 'runner.py')
control = runner.controls
always = load('sku_local_real_always_restore', HERE.parent / 'current-factory-initial-stage/restoration.py').always


def native():
    ids = tuple('LOCAL_ONLY_' + str(i) for i in range(7))
    report = dict(status='PASS', native=dict(counts={'PASS': 7}, cases={key: dict(status='PASS') for key in ids}),
                  used_guard_refused_before_DDL=True, actual_Native_cases=7)
    return ids, report


def proof():
    return dict(**{key: True for key in control.RESTORE_GATES}, selected_table_cleanup=False)


class Boundary:
    always = staticmethod(always)
    def __init__(self, events, observe_error=False, restore_error=False, verification=None):
        self.events, self.observe_error, self.restore_error = events, observe_error, restore_error
        self.verification = proof() if verification is None else verification
        self.observed = dict(complete=False)
    def observe(self):
        self.events.append('observe')
        if self.observe_error:
            raise ValueError('LOCAL_OBSERVER_FIRST_FAILURE')
        self.observed['complete'] = True
        return self.observed
    def restore(self):
        self.events.append('full_restore')
        if self.restore_error:
            raise ValueError('LOCAL_FULL_RESTORE_FAILURE')
        return dict(only_pg_cron_errors=True)
    def verify(self, restored):
        self.events.append('verify_full22_data_sequences_roles_CP6_advisors')
        return self.verification


class Controls(unittest.TestCase):
    def test_exact_plan_three_original_races_six_original_native_actor_waits(self):
        plan = runner.plan()
        self.assertEqual(len(plan['race_ids']), 3)
        self.assertEqual(len(plan['permission_wait_ids']), 6)
        self.assertEqual(len(set(plan['race_ids'] + plan['permission_wait_ids'])), 9)
        self.assertEqual(plan['status'], 'PREPARED')
        self.assertEqual(plan['actual_Auth_HTTP_cases'], 0)
        self.assertIn('no real Auth login', plan['permission_actor_fixture'])

    def test_gate_refuses_failed_partial_wrong_identity_or_missing_used_guard(self):
        ids, good = native()
        self.assertEqual(control.prerequisite(good, ids, {'source': 'local'}, {'source': 'local'})['status'], 'SAME_CALL_NATIVE7_AND_USED_GUARD_ADMITTED')
        for mutation in [lambda r: r.update(status='INCOMPLETE'), lambda r: r['native'].update(counts={'PASS': 6}),
                         lambda r: r['native']['cases'].pop(ids[0]),
                         lambda r: r['native']['cases'][ids[0]].update(status='FAIL'),
                         lambda r: r.update(actual_Native_cases=6), lambda r: r.update(used_guard_refused_before_DDL=False)]:
            wrong = deepcopy(good); mutation(wrong)
            with self.assertRaises(ValueError):
                control.prerequisite(wrong, ids, {}, {})
        with self.assertRaisesRegex(ValueError, 'EXACT_CURRENT_INSTALLATION'):
            control.prerequisite(good, ids, {'source': 'other'}, {'source': 'local'})

    def test_business_failure_preserved_and_full_restore_still_runs(self):
        events = []
        def operation():
            events.append('business')
            raise ValueError('LOCAL_BUSINESS_FIRST_FAILURE')
        row = control.execute(operation, Boundary(events))
        self.assertEqual(events, ['business', 'observe', 'full_restore', 'verify_full22_data_sequences_roles_CP6_advisors'])
        self.assertEqual(row['status'], 'INCOMPLETE')
        self.assertEqual(row['error'], 'LOCAL_BUSINESS_FIRST_FAILURE')
        self.assertTrue(row['installed_baseline_restoration']['complete_database_dump_restored'])

    def test_observation_failure_does_not_skip_restore_or_manufacture_pass(self):
        events = []
        row = control.execute(lambda: {'status': 'PASS', 'local_only': True}, Boundary(events, observe_error=True))
        self.assertEqual(events, ['observe', 'full_restore', 'verify_full22_data_sequences_roles_CP6_advisors'])
        self.assertEqual(row['status'], 'INCOMPLETE')
        self.assertEqual(row['observation_error'], 'LOCAL_OBSERVER_FIRST_FAILURE')
        self.assertEqual(row['original_case_result'], {'status': 'PASS', 'local_only': True})

    def test_restore_failure_preserves_business_failure_and_blocks_pass(self):
        events = []
        row = control.execute(lambda: {'status': 'FAIL', 'reason': 'LOCAL_STOCK_WRONG'}, Boundary(events, restore_error=True))
        self.assertEqual(row['status'], 'INCOMPLETE')
        self.assertEqual(row['original_case_result'], {'status': 'FAIL', 'reason': 'LOCAL_STOCK_WRONG'})
        self.assertEqual(row['restore_error'], 'LOCAL_FULL_RESTORE_FAILURE')
        self.assertNotIn('verify_full22_data_sequences_roles_CP6_advisors', events)

    def test_each_restore_gate_is_required_and_selective_cleanup_is_rejected(self):
        for key in control.RESTORE_GATES:
            wrong = proof(); wrong[key] = False
            row = control.execute(lambda: {'status': 'PASS'}, Boundary([], verification=wrong))
            self.assertEqual(row['status'], 'INCOMPLETE', key)
            self.assertIn('restore_error', row)
        wrong = proof(); wrong['selected_table_cleanup'] = True
        with self.assertRaisesRegex(ValueError, 'SELECTED_TABLE'):
            control.restored(wrong)

    def test_aggregation_requires_every_id_restore_and_cleanup_and_claims_no_real_auth(self):
        ids = tuple('LOCAL_RACE_' + str(i) for i in range(9))
        group = dict(status='RUN_COMPLETE', counts={'PASS': 9}, planned_race_ids=list(ids), database_remaining=0,
                     races={key: dict(status='PASS', session_leaks=[], installed_baseline_restoration=proof()) for key in ids})
        result = control.complete(group, ids)
        self.assertEqual(result['actual_two_session_conversion_races'], 3)
        self.assertEqual(result['actual_Native_session_permission_waits'], 6)
        self.assertFalse(result['real_Auth_claim'])
        for mutation in [lambda r: r.update(counts={'PASS': 8}), lambda r: r['races'].pop(ids[0]),
                         lambda r: r.update(database_remaining=1),
                         lambda r: r['races'][ids[0]].update(session_leaks=[['local-only']]),
                         lambda r: r['races'][ids[0]]['installed_baseline_restoration'].update(cp6_restored=False)]:
            wrong = deepcopy(group); mutation(wrong)
            with self.assertRaises(ValueError):
                control.complete(wrong, ids)

    def test_local_url_plan_refuses_hosted_or_noncopy_targets(self):
        runner.require_local('postgresql://postgres@127.0.0.1:54322/cp6_auditor_race', 'cp6_auditor_race')
        for wrong in ['postgresql://remote:54322/cp6_auditor_race', 'postgresql://localhost:54321/cp6_auditor_race', 'postgresql://localhost:54322/postgres']:
            with self.assertRaises(ValueError):
                runner.require_local(wrong, 'cp6_auditor_race')

    def test_every_new_source_and_reused_callback_is_pinned(self):
        declaration = runner.admit_sources()
        self.assertFalse(declaration['actual_concurrency_executed'])
        self.assertGreaterEqual(declaration['files'], 12)


if __name__ == '__main__':
    unittest.main()
