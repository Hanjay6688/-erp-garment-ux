import unittest
import isolated_cases


class IsolationContract(unittest.TestCase):
    def test_failure_retained_and_next_runs_only_after_restore(self):
        order, report = [], {}
        def run(operation, result):
            order.append(operation)
            result['observed_money'] = '123.45'
            if operation == 'counterexample':
                raise AssertionError('mixed book escaped')
            result['status'] = 'PASS'
        def restore():
            order.append('restore')
            return {'all22_all_rows_all_sequences_roles_exact': True}
        with self.assertRaisesRegex(AssertionError, 'FIRST_FAILURES_RETAINED'):
            isolated_cases.exercise([('A', 'counterexample'), ('B', 'measurement')], run, restore, report)
        self.assertEqual(order, ['counterexample', 'restore', 'measurement', 'restore'])
        self.assertEqual(report['cases']['A']['error'], 'mixed book escaped')
        self.assertEqual(report['cases']['A']['observed_money'], '123.45')
        self.assertEqual(report['cases']['B']['status'], 'PASS')

    def test_restore_failure_stops_next_case_and_keeps_original_failure(self):
        report, calls = {}, []
        def run(operation, result):
            calls.append(operation)
            raise AssertionError('original failure')
        def restore():
            raise ValueError('restore mismatch')
        with self.assertRaisesRegex(ValueError, 'restore mismatch'):
            isolated_cases.exercise([('A', 1), ('B', 2)], run, restore, report)
        self.assertEqual(calls, [1])
        self.assertEqual(report['cases']['A']['error'], 'original failure')
        self.assertEqual(report['cases']['A']['restore_error'], 'restore mismatch')

    def test_partial_restore_cannot_authorize_next_case(self):
        calls = []
        def run(operation, result):
            calls.append(operation)
            result['status'] = 'PASS'
        with self.assertRaisesRegex(ValueError, 'RESTORE_PROOF_INCOMPLETE'):
            isolated_cases.exercise([('A', 1), ('B', 2)], run, lambda: {}, {})
        self.assertEqual(calls, [1])

    def test_cannot_overwrite_a_retained_result(self):
        report = {'cases': {'A': {'status': 'INCOMPLETE', 'error': 'first'}}}
        with self.assertRaisesRegex(ValueError, 'FIRST_RESULT_ALREADY_EXISTS'):
            isolated_cases.exercise([('A', None)], lambda *_: self.fail(), lambda: self.fail(), report)
        self.assertEqual(report['cases']['A']['error'], 'first')
