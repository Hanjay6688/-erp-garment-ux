from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util,json,shutil,sys,unittest
from unittest.mock import patch
import qualification_admission as admission

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


class CombinedQualificationBoundaries(unittest.TestCase):
    def test_closed_qualification_refuses_before_loading_or_touching_database(self):
        class NoRuntime:
            def __getattr__(self,name):raise AssertionError('UNADMITTED_RUNTIME_TOUCH:'+name)
        with TemporaryDirectory()as folder:
            closed=Path(folder);(closed/'QUALIFICATION_CONFIG.json').write_text('{"allow_database_execution":false}')
            with self.assertRaisesRegex(ValueError,'COMBINED_QUALIFICATION_NOT_ADMITTED'):
                admission.admitted(ROOT,closed,(),NoRuntime(),NoRuntime())

    def test_unaccepted_combined_runner_refuses_before_database(self):
        # The retained executable rejects CLI arguments. Do not pass unittest's
        # discovery flags to that unchanged import-time command-line guard.
        with patch.object(sys,'argv',[__file__]):
            runner=admission.load('closed_combined_runner',HERE/'qualification_runner.py')
        class NoDatabase:
            def __getattr__(self,name):raise AssertionError('UNADMITTED_DATABASE_TOUCH:'+name)
        with TemporaryDirectory()as folder:
            closed=Path(folder);(closed/'QUALIFICATION_CONFIG.json').write_text('{"allow_database_execution":false}')
            with patch.object(runner,'HERE',closed):
                with self.assertRaisesRegex(ValueError,'COMBINED_QUALIFICATION_NOT_ADMITTED'):
                    runner.exercise(NoDatabase(),NoDatabase(),NoDatabase(),'no-url',{}, {})

    def test_fetch_cannot_use_network_before_accepted_prerequisite(self):
        fetch=admission.load('closed_combined_fetch',HERE/'fetch_consistency.py')
        with TemporaryDirectory()as folder:
            closed=Path(folder);(closed/'PREREQUISITES.json').write_text('{"allow_database_execution":false,"accepted_consistency":null}')
            with patch.object(fetch,'HERE',closed),patch.object(fetch.subprocess,'check_output',side_effect=AssertionError('UNADMITTED_NETWORK')):
                with self.assertRaisesRegex(ValueError,'ACTUAL_CONSISTENCY_PASS_REQUIRED'):
                    fetch.fetch()

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
