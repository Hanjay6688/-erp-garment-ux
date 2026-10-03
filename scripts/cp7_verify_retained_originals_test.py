"""Synthetic receipt corruption controls; no Native/business qualification."""
import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from cp7_verify_retained_originals import verify


class RetainedOriginalControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.gates = {'installed': True, 'primary_unchanged': True, 'backup_restore_drill': True, 'security_advisors': True, 'writer_runtime': True}
        self.package = {'run_identity': {'tool_head': 'a'*40, 'run_id': '1'}, 'gate': self.gates,
                        'primary_unchanged': True, 'auth_users_before': 0, 'auth_users_after': 0}
        self.report = {'status': 'PASS', 'source_sha256': 'b'*64, 'observed_case_count': 1, 'expected_case_count': 1,
                       'cp6_restored': True, 'restore_components': {'public': True}, 'advisor_gate': True,
                       'native': {'counts': {'PASS': 1}, 'planned_case_ids': ['ONE'], 'cases': {'ONE': {'status': 'PASS'}}}}
        self.receipt = {'status': 'NATIVE_WRITER_QUALIFIED', 'source_commit': 'a'*40, 'source_tree': 'c'*40,
                        'run_id': 1, 'job_id': 2, 'artifact_id': 3, 'zip_bytes': 4, 'zip_sha256': 'd'*64,
                        'runtime_report': 'RUNTIME.json', 'source_bundle_sha256': 'b'*64, 'expected_status': 'PASS',
                        'expected_case_count': 1, 'observed_case_count': 1, 'required_case_counts': {'native': 1},
                        'counts': {'native': {'PASS': 1}}, 'cp6_restored': True, 'restore_components': {'public': True},
                        'advisor_gate': True, 'package_gate': self.gates, 'primary_unchanged': True,
                        'auth_users_before': 0, 'auth_users_after': 0, 'full_family_acceptance': False,
                        'independent_acceptance': False, 'production_go': False}

    def write(self):
        originals = {name: json.dumps(value) for name, value in [('RUNTIME.json', self.report), ('T3_PACKAGE_INSTALL.json', self.package)]}
        members = {name: {'bytes': len(value.encode()), 'sha256': hashlib.sha256(value.encode()).hexdigest()} for name, value in originals.items()}
        compressed = gzip.compress(json.dumps({'contract': 'cp7.retained-originals.v1', 'source_commit': 'a'*40, 'root_json_utf8': originals}).encode(), mtime=0)
        self.receipt.update(original_reports_gzip_sha256=hashlib.sha256(compressed).hexdigest(), original_root_reports=members, all_zip_members=copy.deepcopy(members))
        (self.directory/'ORIGINAL_REPORTS.json.gz').write_bytes(compressed)
        (self.directory/'RECEIPT.json').write_text(json.dumps(self.receipt))

    def test_valid_is_read_only_and_zero_execution_credit(self):
        self.write()
        before = {path.name: path.read_bytes() for path in self.directory.iterdir()}
        result = verify(self.directory)
        self.assertEqual(result['validation_new_Native_execution_credit'], 0)
        self.assertFalse(result['Native_database_access'])
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.directory.iterdir()})

    def test_corrupt_compressed_original_refused(self):
        self.write()
        p = self.directory/'ORIGINAL_REPORTS.json.gz';p.write_bytes(p.read_bytes()+b'x')
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_forged_root_report_hash_refused(self):
        self.write()
        self.receipt['original_root_reports']['RUNTIME.json']['sha256'] = '0'*64
        (self.directory/'RECEIPT.json').write_text(json.dumps(self.receipt))
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_wrong_external_source_pin_refused(self):
        self.write()
        manifest = dict(self.receipt, source_commit='f'*40)
        with self.assertRaises(AssertionError): verify(self.directory, manifest)

    def test_false_gate_refused(self):
        self.package['gate']['backup_restore_drill'] = False
        self.write()
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_auth_user_leak_refused(self):
        self.package['auth_users_after'] = 1
        self.write()
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_missing_actual_case_despite_pass_counts_refused(self):
        self.report['native']['cases'] = {}
        self.write()
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_wrong_case_identity_refused(self):
        self.report['native']['cases'] = {'OTHER': {'status': 'PASS'}}
        self.write()
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_undeclared_extra_group_refused(self):
        self.report['http'] = {'cases': {'EXTRA': {'status': 'PASS'}}, 'counts': {'PASS': 1}}
        self.write()
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_failed_original_refused_even_if_receipt_calls_it_qualified(self):
        self.report['status'] = 'INCOMPLETE'
        self.write()
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_diagnostic_cannot_claim_product_credit(self):
        self.report.update(diagnostic_only=True, product_qualification=False, Native_product_exit_case_credit=1, full_family_acceptance=False)
        self.receipt.update(status='DIAGNOSTIC_EMISSION_COMPLETE', Native_product_exit_case_credit=0, full_P19_acceptance=False)
        self.write()
        with self.assertRaises(AssertionError): verify(self.directory)

    def test_missing_projection_refused_when_head_is_pinned(self):
        self.write()
        with self.assertRaises(AssertionError): verify(self.directory, projection_head='e'*40)


if __name__ == '__main__':
    unittest.main()
