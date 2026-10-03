"""Counter-integrity stand-ins only: no PostgreSQL, Native timing or product credit."""
import copy
import unittest

from cp7_note_command_function_profile import summarize


def row(oid, name, calls, total, own, schema='cp7_note'):
    return dict(function_oid=str(oid), schema_name=schema, function_name=name,
                identity_arguments='jsonb', calls=str(calls),
                total_time_ms=str(total), self_time_ms=str(own))


class ProfileIntegrity(unittest.TestCase):
    def setUp(self):
        self.before = [row(2, 'access_now', 3, 6, 6)]
        self.after = [row(1, 'erp_cp7_correct_note_v1', 1, 100, 20, 'public'),
                      row(2, 'access_now', 5, 16, 16), row(3, 'restatement', 1, 70, 60)]

    def summary(self, before=None, after=None, completed=True):
        return summarize(self.before if before is None else before,
                         self.after if after is None else after, '1',
                         command_completed=completed)

    def test_nested_times_keep_root_and_rank_self_without_inclusive_sum(self):
        originals = copy.deepcopy((self.before, self.after))
        result = self.summary()
        self.assertEqual([r['function_oid'] for r in result['functions_by_self_elapsed_ms']],
                         ['3', '1', '2'])
        self.assertEqual(result['root_function_delta']['delta_total_time_ms'], '100')
        self.assertEqual(result['functions_by_self_elapsed_ms'][2]['delta_calls'], '2')
        self.assertTrue(result['inclusive_times_not_summed'])
        self.assertFalse(result['product_qualification'])
        self.assertEqual(result['Native_exit_case_credit'], 0)
        self.assertEqual((self.before, self.after), originals)

    def test_duplicate_oid_in_either_snapshot_is_refused(self):
        for before, after in ((self.before * 2, self.after), (self.before, self.after * 2)):
            with self.subTest(before=before), self.assertRaisesRegex(ValueError, 'DUPLICATE_OID'):
                self.summary(before, after)

    def test_disappeared_counter_is_not_silently_zeroed(self):
        with self.assertRaisesRegex(ValueError, 'DISAPPEARED'):
            self.summary(after=self.after[:1])

    def test_oid_reuse_with_different_signature_is_refused(self):
        changed = copy.deepcopy(self.after)
        changed[1]['identity_arguments'] = 'text'
        with self.assertRaisesRegex(ValueError, 'IDENTITY_CHANGED'):
            self.summary(after=changed)

    def test_resets_in_calls_and_each_time_are_refused(self):
        for field in ('calls', 'total_time_ms', 'self_time_ms'):
            changed = copy.deepcopy(self.after)
            changed[1][field] = '0'
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.summary(after=changed)

    def test_nonfinite_boolean_missing_and_out_of_scope_values_are_refused(self):
        for field, value in (('total_time_ms', 'NaN'), ('self_time_ms', 'Infinity'),
                             ('calls', True), ('function_oid', '01'),
                             ('schema_name', 'auth'), ('total_time_ms', '-1')):
            changed = copy.deepcopy(self.after)
            changed[1][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.summary(after=changed)
        changed = copy.deepcopy(self.after)
        del changed[1]['calls']
        with self.assertRaisesRegex(ValueError, 'INVALID_FIELDS'):
            self.summary(after=changed)

    def test_complete_command_requires_original_root_once(self):
        for root in (None, row(1, 'erp_cp7_correct_note_v1', 2, 100, 20, 'public'),
                     row(1, 'unrelated', 1, 100, 20, 'erp')):
            after = [r for r in self.after if r['function_oid'] != '1']
            if root:
                after.append(root)
            with self.subTest(root=root), self.assertRaises(ValueError):
                self.summary(after=after)

    def test_interrupted_command_with_no_completed_root_stays_partial(self):
        result = self.summary(after=self.after[1:], completed=False)
        self.assertEqual(result['status'], 'PARTIAL_COUNTERS_COMMAND_NOT_COMPLETED')
        self.assertIsNone(result['root_function_delta'])
        self.assertFalse(result['command_completed'])

    def test_over_cap_or_self_exceeding_total_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'OVER_CAP'):
            self.summary(after=[row(i + 10, 'f', 1, 1, 1) for i in range(1001)])
        changed = copy.deepcopy(self.after)
        changed[1]['self_time_ms'] = '17'
        with self.assertRaisesRegex(ValueError, 'SELF_EXCEEDS_TOTAL'):
            self.summary(after=changed)


if __name__ == '__main__':
    unittest.main()
