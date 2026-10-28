from pathlib import Path
from copy import deepcopy
import importlib.util,json,unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('profile_terminal_evidence_tested',HERE/'evidence.py')
evidence=importlib.util.module_from_spec(spec);spec.loader.exec_module(evidence)
class ActualTerminalTests(unittest.TestCase):
    def setUp(self):self.actual=json.loads((HERE/'FIRST_4AC_FAILURE.json').read_bytes())['terminal']
    def test_actual_terminal_failure_is_diagnostic_input_only(self):
        self.assertEqual(evidence.terminal(self.actual)['SQLSTATE'],'57014')
    def test_different_failures_or_progress_cannot_be_substituted(self):
        changes=[('state','RUNNING'),('units_done',1),('unit_count',2),('plan_final',True),('failure_unit',1),
                 ('unit_attempts',2),('failure_sqlstate','42501'),('failure_code','OTHER'),('failure_message','other')]
        for key,value in changes:
            with self.subTest(field=key):
                d=deepcopy(self.actual);d['job_rows'][0][key]=value
                with self.assertRaises(AssertionError):evidence.terminal(d)
    def test_incomplete_finance_is_not_the_retained_result(self):
        for key,value in [('state','RUNNING'),('units_done',6),('units_total',None),('failure_code','STOPPED')]:
            with self.subTest(field=key):
                d=deepcopy(self.actual);d['finance_capture_rows'][0][key]=value
                with self.assertRaises(AssertionError):evidence.terminal(d)
    def test_changed_or_duplicate_jobs_are_refused(self):
        d=deepcopy(self.actual);d['job_rows'][1]=d['job_rows'][0]
        with self.assertRaises(AssertionError):evidence.terminal(d)
        d=deepcopy(self.actual);d['manual_steps']=1
        with self.assertRaises(AssertionError):evidence.terminal(d)
        d=deepcopy(self.actual);d['job_or_capture_state_changed']=True
        with self.assertRaises(AssertionError):evidence.terminal(d)
if __name__=='__main__':unittest.main()
