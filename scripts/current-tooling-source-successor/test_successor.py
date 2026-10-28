from pathlib import Path
from copy import deepcopy
import importlib.util,json,unittest
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('tooling_successor_tested',HERE/'tooling.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
class SuccessorTests(unittest.TestCase):
    def test_exact_tested_successor_and_original_derivation(self):
        self.assertFalse(t.checked()['historical_manifests_rewritten']);self.assertTrue(t.derivation())
    def test_each_unqualified_current_file_is_refused(self):
        for path in t.FILES:
            with self.subTest(path=path),self.assertRaises(AssertionError):t.checked(overrides={path:b'changed'})
        old=t.git('show','7657bbee5d55277855a0ab53126438c2e9c63118:'+t.SCRIPT)
        with self.assertRaises(AssertionError):t.checked(overrides={t.SCRIPT:old})
    def test_partial_or_other_head_evidence_is_refused(self):
        source=json.loads((t.ROOT/'docs/cp7/d17-14/ow15/A_B_OW10_FIRST_FAILURE_INTAKE_20261028.json').read_bytes())
        for key,value in [('head','0'*40),('filesystem_tests_passed',3),('codeql_results',1),('analysis_successful',False),('file_system_race_query_present',False)]:
            changed=deepcopy(source);changed['A_actual'][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):t.checked(receipt=changed)
    def test_other_source_checks_cannot_be_changed(self):
        with self.assertRaises(AssertionError):t.derivation(actual=(HERE/'check.py').read_text()+'\n# extra change\n')
if __name__=='__main__':unittest.main()
