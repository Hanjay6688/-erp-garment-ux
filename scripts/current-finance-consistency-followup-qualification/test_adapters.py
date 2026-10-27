from pathlib import Path
from types import SimpleNamespace
import unittest
import adapters


class NativeInputsRemainScoped(unittest.TestCase):
    def retained(self,events,fail=None):
        def operation(key):
            def run():
                events.append(key)
                if key==fail:raise RuntimeError('ORIGINAL_NATIVE_FAILURE')
                return dict(status='PASS')
            return run
        return [(key,operation(key))for key in (*sorted(adapters.REPORT_IDS),'UNRELATED_CAPTURE_CASE')]

    def test_preparation_occurs_inside_selected_operation_and_other_case_is_exact(self):
        events=[];original=self.retained(events)
        def prepare(cur,today):events.append('NATIVE_HPP_PREPARATION');return dict(status='PASS')
        wrapped=adapters.prepared_cases(original,object(),object(),prepare)
        self.assertEqual(events,[])
        self.assertIs(wrapped[-1][1],original[-1][1])
        for key,run in wrapped:
            before=len(events);result=run()
            self.assertEqual(events[before:],['NATIVE_HPP_PREPARATION',key]if key in adapters.REPORT_IDS else[key])
            if key in adapters.REPORT_IDS:self.assertTrue(result['original_report_case_and_oracles_unchanged'])

    def test_missing_business_case_refuses_before_preparing_or_running(self):
        events=[]
        with self.assertRaisesRegex(ValueError,'THREE_BUSINESS_REPORT_CASES_REQUIRED'):
            adapters.prepared_cases(self.retained(events)[:-2],None,None,lambda *args:events.append('PREPARE'))
        self.assertEqual(events,[])

    def test_input_hooks_are_restored_when_original_case_fails(self):
        events=[];original_cases=lambda *args:self.retained(events)
        original_install=lambda *args:events.append('EXACT_INSTALL')
        old_cron=object();base=SimpleNamespace(install=original_install,capture=SimpleNamespace(cases=original_cases),
            cron=old_cron,EXPECTED_CATALOG={'exact':'catalog'},chain=SimpleNamespace(prepare_attendance_seed=lambda *args:{'status':'PASS'}))
        observed=[]
        with self.assertRaisesRegex(RuntimeError,'ORIGINAL_NATIVE_FAILURE'):
            with adapters.inputs(base,observed.append,capture=True,cron=object()):
                base.install();raise RuntimeError('ORIGINAL_NATIVE_FAILURE')
        self.assertIs(base.install,original_install);self.assertIs(base.capture.cases,original_cases);self.assertIs(base.cron,old_cron)
        self.assertEqual(observed,[{'exact':'catalog'}]);self.assertEqual(events,['EXACT_INSTALL'])


if __name__=='__main__':unittest.main()
