from copy import deepcopy
from pathlib import Path
import unittest
import infra_source_guard as guard

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


class UnchangedERPDiagnostics(unittest.TestCase):
    def test_declared_infrastructure_changes_retain_original_business_sources(self):
        result=guard.check(ROOT,HERE)
        self.assertTrue(result['ERP_SQL_and_business_cases_unchanged'])
        self.assertTrue(result['original_probe_and_all_restoration_assertions_unchanged'])

    def test_replacing_the_actual_ERP_probe_with_green_command_is_refused(self):
        workflow=guard.expected(ROOT,HERE)
        steps=workflow['jobs']['p21']['steps']
        actual=[s for s in steps if s.get('name')=='Run seven isolated report book consistency diagnostics with full database restoration']
        self.assertEqual(len(actual),1);actual[0]['run']='true'
        with self.assertRaisesRegex(AssertionError,'INFRA_UNDECLARED_WORKFLOW_CHANGE'):
            guard.check(ROOT,HERE,workflow=workflow)

    def test_admission_production_flag_cannot_be_changed_with_infrastructure(self):
        current=(HERE/'admission.py').read_text()
        with self.assertRaisesRegex(AssertionError,'INFRA_UNDECLARED_ADMISSION_CHANGE'):
            guard.check(ROOT,HERE,admission_body=current.replace('production_go=False','production_go=True',1))


if __name__=='__main__':unittest.main()
