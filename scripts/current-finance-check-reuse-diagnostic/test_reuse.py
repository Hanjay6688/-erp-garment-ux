"""Refuse source drift; retain the exact calculation outside one aggregation."""
from pathlib import Path
import sys,unittest
sys.dont_write_bytecode=True
import reuse

class ReuseTransformation(unittest.TestCase):
    def setUp(self):self.body,self.source=reuse.snapshot_source.expected()
    def test_only_the_duplicate_aggregation_changes(self):
        result=reuse.rewrite(self.body)
        self.assertEqual(result.replace(reuse.NEW,reuse.OLD,1),self.body)
        self.assertEqual(result.count('erp.run_v268_financial_report_checks()'),1)
        self.assertIn('filter(where c.issue_count>0)',result)
        self.assertIn('order by c.severity,c.check_name',result)
    def test_changed_arithmetic_authority_or_additional_call_refused(self):
        for changed in (self.body+'\n',self.body.replace('v_critical:=v_critical+1','v_critical:=v_critical'),
                        self.body.replace("severity='CRITICAL'","severity='WARNING'",1),
                        self.body+"\n perform erp.run_v268_financial_report_checks();"):
            with self.subTest(changed=changed[-100:]),self.assertRaises(ValueError):reuse.rewrite(changed)
    def test_no_new_result_parameter_or_cache(self):
        body=reuse.rewrite(self.body)
        self.assertNotIn('set_config',reuse.NEW)
        self.assertEqual(body.count('declare'),self.body.count('declare'))
        self.assertEqual(body.count('return '),self.body.count('return '))

    def test_uninstalled_native_body_and_missing_installed_readers_refused(self):
        native=(Path(__file__).parent/'original-snapshot-body.sql').read_text()
        for changed in (native,self.body.replace('cp7_note.report_lifecycle','cp7_note.missing_lifecycle',1),
                        self.body.replace('(select erp.account_id(','erp.account_id(',1)):
            with self.subTest(body=changed[:30]),self.assertRaises(ValueError):reuse.rewrite(changed)

    def test_composed_reference_uses_exact_installer_order(self):
        self.assertEqual(self.source['transform_order'],['cp7_note_report_bundle.patched_report','cp7_report_accounts_bundle.wrap'])
        self.assertEqual(len(self.body.encode()),12004)
        self.assertEqual(self.body.count('cp7_note.report_lifecycle('),2)
        self.assertEqual(self.body.count('cp7_sales_return_correction.report_lifecycle('),1)
        self.assertEqual(self.body.count('(select erp.account_id('),11)

if __name__=='__main__':unittest.main()
