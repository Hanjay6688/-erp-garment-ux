from pathlib import Path
import unittest
import source_guard

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


class FocusedProbeGuard(unittest.TestCase):
    def test_declared_focus_preserves_original_oracles(self):
        source_guard.check(REPO, HERE)

    def test_removed_baseline_equality_refused(self):
        text = (HERE / 'probe.py').read_text()
        anchor = 'assert predecessor.catalog._data(cur)==baseline_data'
        self.assertEqual(text.count(anchor), 1)
        with self.assertRaisesRegex(AssertionError, 'UNDECLARED_PROBE'):
            source_guard.check(REPO, HERE, text.replace(anchor, 'pass', 1))

    def test_false_full_inverse_credit_refused(self):
        text = (HERE / 'probe.py').read_text()
        anchor = 'full_parent_inverse_repeated=False'
        self.assertEqual(text.count(anchor), 1)
        with self.assertRaisesRegex(AssertionError, 'UNDECLARED_PROBE'):
            source_guard.check(REPO, HERE, text.replace(anchor, 'full_parent_inverse_repeated=True', 1))

    def test_removed_work_identity_assertion_refused(self):
        text = (HERE / 'choice_fixture.py').read_text()
        anchor = "assert work['job_id']==initial['job_id'] and work['created_at']==initial['created_at']"
        self.assertEqual(text.count(anchor), 1)
        with self.assertRaisesRegex(AssertionError, 'UNDECLARED_HELPER'):
            source_guard.check(REPO, HERE, helper_overrides={'choice_fixture.py': text.replace(anchor, 'pass', 1)})


if __name__ == '__main__':
    unittest.main()
