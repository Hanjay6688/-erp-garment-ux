"""Refuse source drift and prove every original rule survives the transformation."""
from pathlib import Path
import sys,unittest
sys.dont_write_bytecode=True
import readiness_reuse as reuse

class ReadinessTransformation(unittest.TestCase):
    def setUp(self):self.bodies,self.source=reuse.snapshot_source.expected()
    def test_exact_installed_reference_matches_actual_failure(self):
        self.assertEqual(self.source['derived']['installed_snapshot_bytes'],14417)
        self.assertEqual(self.source['actual_f038_live_body_sha256'],'5687c8b4805f73baa68197121f9a4a90f5f123d6ff7da683e88301a485e3aab2')
        self.assertEqual(self.bodies['snapshot'].count('erp.period_readiness_v1('),1)
        self.assertEqual(self.bodies['snapshot'].count('erp.run_v268_financial_report_checks()'),1)
    def test_all_workspace_guards_and_filings_unchanged(self):
        body=self.bodies['workspace'];result=reuse.rewrite(body)
        recovered=result.replace(reuse.NEW_PREFLIGHT,reuse.OLD_PREFLIGHT,1).replace(reuse.NEW_SNAPSHOT,reuse.OLD_SNAPSHOT,1)
        recovered=recovered.replace('snapshot jsonb;preflight jsonb:=null;shared_report jsonb;','snapshot jsonb;preflight jsonb:=null;',1)
        self.assertEqual(recovered,body)
        for guard in ('CP7_FINANCE_QUERY','CP7_FINANCE_REPORT_INCOMPLETE','CP7_FINANCE_FILING_INCOMPLETE','CP7_FINANCE_FILING_DATE_MISMATCH','perform cp7_finance.access_now();'):
            self.assertIn(guard,result)
    def test_entire_snapshot_arithmetic_and_warnings_unchanged(self):
        original=self.bodies['snapshot'];result=reuse.sibling_body(original,self.bodies['preflight'])
        snapshot=result.split("\n  if erp.has_permission('finance.period_close.manage') then\n")[0]+'\nend\n'
        snapshot=snapshot.replace('declare\n  d17_snapshot jsonb;d17_preflight jsonb:=null;\n','declare\n',1)
        snapshot=snapshot.replace('  d17_snapshot:=jsonb_build_object(\n','  return jsonb_build_object(\n',1)
        self.assertEqual(snapshot,original)
    def test_preflight_authority_dates_and_close_state_are_exact(self):
        result=reuse.sibling_body(self.bodies['snapshot'],self.bodies['preflight'])
        nested=result.split("\n  if erp.has_permission('finance.period_close.manage') then\n")[1].split(';\n  end if;\n')[0]
        recovered=nested.replace('d17_preflight:=v_readiness','return '+reuse.READINESS,1)
        # The substitution introduced p_through in READINESS already; every
        # remaining parameter reference must recover its original spelling.
        recovered=recovered.replace('p_as_of','p_through')
        self.assertEqual(recovered,self.bodies['preflight'].strip())
        self.assertEqual(result.count('erp.period_readiness_v1('),1)
    def test_changed_arithmetic_authority_and_dates_refused(self):
        examples={
            'snapshot':[self.bodies['snapshot']+'\n',self.bodies['snapshot'].replace('v_critical:=','v_critical:=1+',1)],
            'preflight':[self.bodies['preflight'].replace('perform erp.require_owner_admin();',''),self.bodies['preflight'].replace('p_through>=v_closed','true')],
            'workspace':[self.bodies['workspace'].replace('1000000','1000001',1),self.bodies['workspace'].replace("erp.has_permission('finance.period_close.manage')","true",1)]}
        for kind,variants in examples.items():
            for changed in variants:
                with self.subTest(kind=kind),self.assertRaises(ValueError):reuse.exact(changed,kind)
    def test_previous_wrong_references_remain_rejected(self):
        raw=(Path(__file__).parent/'original-snapshot-body.sql').read_text()
        old=reuse.load('old_wrong_reference',Path(__file__).parent/'snapshot_source.py').expected()[0]
        for body in(raw,old):
            with self.subTest(length=len(body)),self.assertRaises(ValueError):reuse.exact(body,'snapshot')
    def test_private_helper_has_only_dates_and_no_result_cache(self):
        sql=reuse.definition(self.bodies['snapshot'],self.bodies['preflight'])
        self.assertTrue(sql.startswith('create function '+reuse.PRIVATE_NAME+'(p_from date,p_to date,p_as_of date)returns jsonb\n'))
        self.assertIn('stable security definer',sql)
        self.assertNotIn('set_config(',sql)
        self.assertNotIn('current_setting(',sql)
        self.assertEqual(sql.count('erp.require_owner_admin()'),2)

if __name__=='__main__':unittest.main()
