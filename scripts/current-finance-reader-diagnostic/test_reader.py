import unittest
from pathlib import Path
import reader

class ReaderTransformation(unittest.TestCase):
    def setUp(self):self.body=Path(__file__).with_name('original-opening-hpp-body.sql').read_text()
    def test_arithmetic_and_guards_retained(self):
        changed=reader.readonly_body(self.body)
        for text in ("perform erp.require_internal();", "v_hpp:=round(v_price*i.hpp_percent_of_price/100.0,6);", "v_hpp:=coalesce(i.unit_cost_snapshot,0);", "if v_price is null then", "if i.id is null or i.balance_type<>'FINISHED_GOODS' then"):
            self.assertIn(text,changed)
        self.assertNotIn('for update',changed)
        self.assertNotIn('update erp.',changed)
        self.assertEqual(changed.count('return v_hpp;'),2)
    def test_native_drift_refused(self):
        for altered in (self.body+'\n',self.body.replace('/100.0','/1000.0'),self.body.replace('perform erp.require_internal();','null;')):
            with self.subTest(altered=altered[-60:]),self.assertRaises(ValueError):reader.readonly_body(altered)
    def test_report_call_must_be_single(self):
        h='CREATE OR REPLACE FUNCTION erp.run_v268_financial_report_checks()\n STABLE SECURITY DEFINER\n'
        self.assertEqual(reader.report_definition(h+reader.OLD_CALL),h+reader.NEW_CALL)
        for body in ('',reader.OLD_CALL*2):
            with self.assertRaises(ValueError):reader.report_definition(h+body)
    def test_report_identity_and_authority_refused(self):
        h='CREATE OR REPLACE FUNCTION erp.run_v268_financial_report_checks()\n STABLE SECURITY DEFINER\n'+reader.OLD_CALL
        for body in (h.replace('erp.run_','public.run_'),h.replace('STABLE','VOLATILE'),h.replace('SECURITY DEFINER','SECURITY INVOKER')):
            with self.assertRaises(ValueError):reader.report_definition(body)

if __name__=='__main__':unittest.main()
