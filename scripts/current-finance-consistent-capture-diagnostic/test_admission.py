from copy import deepcopy
from hashlib import sha256
import json,unittest
import admission


class RetainedDiagnostics(unittest.TestCase):
    def setUp(self):
        restored=dict(all22_all_rows_all_sequences_roles_exact=True,
            complete_database_dump_restored=True,used_guard_refused_before_DDL=True)
        self.actual=dict(qualification_commit='exact',source_declaration={'exact':'source'},
            status='INCOMPLETE',error='FOLLOWUP_FIRST_FAILURES_RETAINED',
            production_go=False,independent_acceptance=False,
            cp6_restored=True,advisor_gate=True,baseline_full22_all_rows_all_sequences_equal=True,
            baseline_advisors_equal=True,committed={'outer':{'cases':{
                admission.VISIBILITY:dict(status='PASS',changed_source_refused_before_seal=True,
                    unsafe_ready_observed=False,result_escaped=False,
                    installed_baseline_restoration=deepcopy(restored)),
                admission.SINGLE:dict(status='INCOMPLETE',
                    restore_traceback='READONLY_FINANCE_ACTUAL_FULL22_CHANGED',
                    pairs={key:dict(status='PASS',entire_accepted_current_report_equal=True)
                        for key in ('SMALL','PRICE_PERCENT','FACTORY_1200X3')})}}})
        self.package={'gate':dict(installed=True,primary_unchanged=True,
            backup_restore_drill=True,security_advisors=True,writer_runtime=False)}

    def call(self,actual=None,package=None,alter=None):
        raw=json.dumps(actual or self.actual).encode();other=json.dumps(package or self.package).encode()
        binding=dict(head='exact',bytes=len(raw),sha256=sha256(raw).hexdigest(),
            package_bytes=len(other),package_sha256=sha256(other).hexdigest())
        if alter:alter(binding)
        return admission.retained_diagnostics(binding,raw,other,{'exact':'source'})

    def test_first_failure_is_retained_and_never_called_pass(self):
        result=self.call()
        self.assertEqual(result['retained_actual_status'],'INCOMPLETE')
        self.assertTrue(result['failed_writer_runtime_not_relabelled'])

    def test_closed_or_unbound_gate_stops_before_source_or_database(self):
        for config,prepared in (({},{}),({'allow_database_execution':True},
            {'allow_database_execution':True}),({'allow_database_execution':True,'first_diagnostic':{}},
            {'allow_database_execution':True})):
            with self.assertRaisesRegex(ValueError,'FIRST_ACTUAL_DIAGNOSTIC_REQUIRED'):
                admission.check_gate(config,prepared)

    def test_each_original_hash_and_length_required(self):
        for key in ('bytes','sha256','package_bytes','package_sha256'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'FIRST_ORIGINAL_CHANGED'):
                self.call(alter=lambda binding:binding.update({key:'tampered'}))

    def test_pass_label_instead_of_retained_counterexample_refused(self):
        actual=deepcopy(self.actual);actual['status']='PASS'
        with self.assertRaises(AssertionError):self.call(actual)
        package=deepcopy(self.package);package['gate']['writer_runtime']=True
        with self.assertRaises(AssertionError):self.call(package=package)

    def test_changed_source_or_relabelled_first_case_refused(self):
        actual=deepcopy(self.actual);actual['source_declaration']={}
        with self.assertRaisesRegex(AssertionError,'FIRST_SOURCE_CHANGED'):self.call(actual)
        actual=deepcopy(self.actual)
        actual['committed']['outer']['cases'][admission.VISIBILITY]['status']='INCOMPLETE'
        with self.assertRaises(AssertionError):self.call(actual)

    def test_outer_and_each_child_restore_required(self):
        for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):
            actual=deepcopy(self.actual);actual[key]=False
            with self.subTest(key=key),self.assertRaisesRegex(AssertionError,'FIRST_RESTORATION_MISSING'):
                self.call(actual)
        for key in (admission.VISIBILITY,):
            actual=deepcopy(self.actual)
            actual['committed']['outer']['cases'][key]['installed_baseline_restoration']['complete_database_dump_restored']=False
            with self.subTest(child=key),self.assertRaises(AssertionError):self.call(actual)

    def test_partial_second_restoration_not_promoted(self):
        actual=deepcopy(self.actual)
        actual['committed']['outer']['cases'][admission.SINGLE]['installed_baseline_restoration']={}
        with self.assertRaises(AssertionError):self.call(actual)


if __name__=='__main__':unittest.main()
