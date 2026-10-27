from pathlib import Path
from tempfile import TemporaryDirectory
import json,shutil,sys,unittest
from unittest.mock import patch
import psycopg
import admission,source_guard

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


class CombinedBrowserSourceBoundaries(unittest.TestCase):
    def test_unqualified_backend_refuses_before_source_or_native_access(self):
        class NoRuntime:
            def __getattr__(self,name):raise AssertionError('UNQUALIFIED_BROWSER_RUNTIME_TOUCH:'+name)
        with TemporaryDirectory()as name:
            closed=Path(name);shutil.copy2(HERE/'evidence.py',closed/'evidence.py')
            (closed/'CONFIG.json').write_text(json.dumps(dict(allow_database_execution=False,accepted_combined=None)))
            with self.assertRaisesRegex(ValueError,'ACTUAL_COMBINED_RUNTIME_REQUIRED'):
                admission.admitted(ROOT,closed,(),NoRuntime(),NoRuntime(),{})

    def test_original_ui_oracles_and_current_B_are_exact(self):
        result=source_guard.check(ROOT,HERE)
        self.assertEqual(result['host_exact_files'],113)
        self.assertEqual(result['current_B_exact_files'],91)
        changed=(HERE/'browser.mjs').read_text().replace("route.abort('failed')","route.continue()",1)
        self.assertNotEqual(changed,(HERE/'browser.mjs').read_text())
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_ORACLE_CHANGE'):
            source_guard.check(ROOT,HERE,overrides={'browser.mjs':changed})

    def test_actual_full_probe_loads_and_refuses_before_any_database_connection(self):
        with patch.object(sys,'argv',[__file__]),patch.object(psycopg,'connect',side_effect=AssertionError('UNADMITTED_UI_DATABASE_CONNECTION')):
            probe=admission.load('closed_real_combined_UI_probe',HERE/'probe.py')
            with TemporaryDirectory()as name:
                closed=Path(name)
                for file in ('admission.py','evidence.py'):shutil.copy2(HERE/file,closed/file)
                (closed/'CONFIG.json').write_text(json.dumps(dict(allow_database_execution=False,accepted_combined=None)))
                with patch.object(probe,'HERE',closed),self.assertRaisesRegex(ValueError,'ACTUAL_COMBINED_RUNTIME_REQUIRED'):
                    probe.admitted()


if __name__=='__main__':unittest.main()
