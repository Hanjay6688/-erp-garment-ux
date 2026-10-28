"""Exercise the actual runner entry before any expensive installation or DB use."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util,json,sys,unittest
import psycopg

HERE=Path(__file__).resolve().parent


def actual_runner():
    with patch.object(sys,'argv',[__file__]):
        spec=importlib.util.spec_from_file_location('runtime_entry_actual_probe',HERE/'probe.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.runner


class ActualRuntimeEntry(unittest.TestCase):
    def test_accepted_configuration_reaches_backend_check_before_database(self):
        with patch.object(psycopg,'connect',side_effect=AssertionError('UNEXPECTED_DATABASE')):
            runner=actual_runner()
            with patch.object(runner.product,'sources',side_effect=RuntimeError('NEXT_QUALIFIED_BACKEND_CHECK'))as source:
                with self.assertRaisesRegex(RuntimeError,'NEXT_QUALIFIED_BACKEND_CHECK'):
                    runner.exercise(None,None,None,None,{},None)
                source.assert_called_once_with()

    def test_closed_runtime_refuses_before_backend_or_database(self):
        with patch.object(psycopg,'connect',side_effect=AssertionError('UNEXPECTED_DATABASE')):
            runner=actual_runner()
            with TemporaryDirectory()as folder:
                closed=Path(folder);(closed/'CONFIG.json').write_text(json.dumps({'allow_database_execution':False}))
                with patch.object(runner,'HERE',closed),patch.object(runner.product,'sources',side_effect=AssertionError('UNADMITTED_BACKEND'))as source:
                    with self.assertRaisesRegex(ValueError,'ACTUAL_AF_FIRST_FAILURE_REQUIRED'):
                        runner.exercise(None,None,None,None,{},None)
                    source.assert_not_called()


if __name__=='__main__':unittest.main()
