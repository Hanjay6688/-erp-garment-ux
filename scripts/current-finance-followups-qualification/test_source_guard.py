from pathlib import Path
import unittest
import admission
import source_guard

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class FollowupSourceContract(unittest.TestCase):
    def test_exact_outer_restore_derivation(self):
        proof = source_guard.check(ROOT, HERE)
        self.assertTrue(proof['outer_full_baseline_restore_retained'])
        self.assertFalse(proof['full_parent_inverse_repeated'])

    def test_weakened_outer_restore_is_refused(self):
        raw = (HERE / 'probe.py').read_text()
        for anchor in ('assert drill.data_hashes(database.SOURCE)==pre_data',
                       "assert predecessor.catalog._data(cur)==baseline_data",
                       "assert case['used_guard_refused_before_DDL'] is True"):
            self.assertEqual(raw.count(anchor), 1)
            with self.subTest(anchor=anchor), self.assertRaisesRegex(AssertionError, 'UNDECLARED_PROBE_CHANGE'):
                source_guard.check(ROOT, HERE, raw.replace(anchor, 'pass'))

    def test_closed_gate_refuses_before_product_or_database(self):
        # Pending configuration cannot even ask the product for its sources.
        for allowed, state in ((False, 'PASS'), (True, 'RUNNING_NOT_PASS'), (False, 'INCOMPLETE')):
            with self.subTest(allowed=allowed, state=state), self.assertRaisesRegex(ValueError, 'DATABASE_GATE_CLOSED'):
                admission.check_gate({'allow_database_execution': allowed, 'parent': {'status': state}})
