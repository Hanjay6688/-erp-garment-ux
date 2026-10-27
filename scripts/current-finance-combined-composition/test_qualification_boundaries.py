from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util,shutil,sys,unittest
from unittest.mock import patch
import qualification_admission as admission

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


class CombinedQualificationBoundaries(unittest.TestCase):
    def test_closed_qualification_refuses_before_loading_or_touching_database(self):
        class NoRuntime:
            def __getattr__(self,name):raise AssertionError('UNADMITTED_RUNTIME_TOUCH:'+name)
        with self.assertRaisesRegex(ValueError,'COMBINED_QUALIFICATION_NOT_ADMITTED'):
            admission.admitted(ROOT,HERE,(),NoRuntime(),NoRuntime())

    def test_unaccepted_combined_runner_refuses_before_database(self):
        # The retained executable rejects CLI arguments. Do not pass unittest's
        # discovery flags to that unchanged import-time command-line guard.
        with patch.object(sys,'argv',[__file__]):
            runner=admission.load('closed_combined_runner',HERE/'qualification_runner.py')
        class NoDatabase:
            def __getattr__(self,name):raise AssertionError('UNADMITTED_DATABASE_TOUCH:'+name)
        with self.assertRaisesRegex(ValueError,'COMBINED_QUALIFICATION_NOT_ADMITTED'):
            runner.exercise(NoDatabase(),NoDatabase(),NoDatabase(),'no-url',{}, {})

    def test_full_restore_and_factory_oracles_have_only_declared_changes(self):
        proof=admission.source_guard(ROOT,HERE)
        self.assertEqual(proof['qualification_factory.py']['unchanged_assertions'],36)
        self.assertEqual(proof['qualification_probe.py']['unchanged_assertions'],9)
        with TemporaryDirectory()as folder:
            copied=Path(folder)
            for name in ('QUALIFICATION_ORIGIN.json','qualification_factory.py','qualification_probe.py'):
                shutil.copy2(HERE/name,copied/name)
            target=copied/'qualification_factory.py'
            target.write_text(target.read_text().replace("financial=='READY'","financial!='RUNNING'",1))
            with self.assertRaisesRegex(AssertionError,'UNDECLARED_QUALIFICATION_CHANGE'):
                admission.source_guard(ROOT,copied)


if __name__=='__main__':unittest.main()
