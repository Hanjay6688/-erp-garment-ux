import importlib.util,json,unittest
from pathlib import Path
from source_guard import check
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

class SourceGuard(unittest.TestCase):
    def test_exact_composition_preserves_prior_guards(self):
        self.assertTrue(check(ROOT,HERE)['unchanged300_second_window'])
    def test_longer_deadline_refused(self):
        text=(HERE/'runner.py').read_text().replace('deadline=started+300','deadline=started+600')
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_CRON'):
            check(ROOT,HERE,{'runner.py':text})
    def test_relaxed_restore_gate_refused(self):
        text=(HERE/'probe.py').read_text().replace("assert drill.data_hashes(database.SOURCE)==pre_data","assert True")
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_CRON'):
            check(ROOT,HERE,{'probe.py':text})
    def test_ignored_choice_completion_refused(self):
        text=(HERE/'runner.py').read_text().replace("and choice_state=='READY'",'and True')
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_CRON'):
            check(ROOT,HERE,{'runner.py':text})

if __name__=='__main__':unittest.main()
