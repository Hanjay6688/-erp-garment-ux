"""Synthetic orchestration controls only, not business or Auth qualification."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import patch
import importlib.util,unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('combined_vendor_orchestration',HERE/'runner.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class Gating(unittest.TestCase):
    def run_synthetic(self,native_count=7,native_error=False,follow_status='PASS'):
        report={};events=[]
        def native(*args):
            events.append('native')
            if native_error:raise ValueError('SYNTHETIC_NATIVE_FAILURE')
            args[-2].update(status='PASS',native=dict(counts={'PASS':native_count},cases={f'N{i}':dict(status='PASS')for i in range(native_count)}))
        def follow(*args):
            events.append('followup')
            args[-2].update(status=follow_status,races=dict(races={f'R{i}':dict(status='PASS')for i in range(3)}),http=dict(cases={'H0':dict(status='PASS')}))
        def load(name,path):return SimpleNamespace(exercise=native if path.name=='native_runner.py'else follow)
        connection=SimpleNamespace(cursor=lambda:nullcontext(object()))
        with patch.object(runner,'load',side_effect=load),patch.object(runner,'handoff_source'),patch.object(runner.psycopg,'connect',return_value=nullcontext(connection))as connect:
            try:runner.exercise(None,None,None,'SYNTHETIC_LOCAL_ONLY',report,{})
            except Exception as error:return report,events,connect.call_count,error
        return report,events,connect.call_count,None

    def test_native_failure_never_opens_followup_or_connection(self):
        report,events,calls,error=self.run_synthetic(native_error=True)
        self.assertIsInstance(error,ValueError);self.assertEqual(events,['native']);self.assertEqual(calls,0)

    def test_partial_native_result_never_opens_followup(self):
        report,events,calls,error=self.run_synthetic(native_count=6)
        self.assertIsInstance(error,AssertionError);self.assertEqual(events,['native']);self.assertEqual(calls,0)

    def test_incomplete_followup_never_becomes_pass(self):
        report,events,calls,error=self.run_synthetic(follow_status='INCOMPLETE')
        self.assertIsInstance(error,AssertionError);self.assertNotEqual(report.get('status'),'PASS')

    def test_complete_synthetic_contract_counts_eleven_once(self):
        report,events,calls,error=self.run_synthetic()
        self.assertIsNone(error);self.assertEqual(events,['native','followup'])
        self.assertEqual(report['business_counts'],{'PASS':11});self.assertEqual(len(report['business_cases']),11)
        self.assertEqual(report['actual_browser_cases'],0)


if __name__=='__main__':unittest.main()
