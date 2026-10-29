"""Independent decimal gold, gate sensitivity and source-only local controls."""
from decimal import Decimal as D
from pathlib import Path
import ast,importlib.util,json,re,unittest

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
o=load('sku_cost_local_oracle',HERE/'oracle.py')
guard=load('sku_cost_local_source_guard',HERE/'source_guard.py')

class OracleTests(unittest.TestCase):
    def test_first_part_recovery_negative_while_group_positive_is_only_safety_scope(self):
        expected=o.recovery_limit()
        self.assertEqual(expected['first_part'],D('20.02'));self.assertEqual(expected['whole_group'],D('60.06'))
        self.assertEqual(expected['recovery'],D('30.03'));self.assertEqual(expected['desired_first_unit'],D('-5.005'))
        self.assertEqual(expected['whole_group_arithmetic_remainder'],D('30.03'))
        self.assertTrue(expected['Native_safety_refusal_required']);self.assertFalse(expected['whole_group_recovery_capability'])

    def test_exact_two_part_usage_and_supplier_recost_have_independent_fixed_values(self):
        for part in(0,1):
            expected=o.gold(part)
            self.assertEqual(expected['after_usage'],(D('22.02'),D('44.04')))
            self.assertEqual(expected['after_invoice'],(D('23.02'),D('46.04')))
            self.assertEqual((expected['group_before'],expected['group_after_usage'],expected['group_after_invoice']),(D('60.06'),D('66.06'),D('69.06')))
            self.assertEqual(expected['remaining_material_qty'],97)
            self.assertEqual((expected['descendant_before'],expected['descendant_after']),(D('22.02'),D('23.02')))

    def test_sold_part_alternatives_conserve_all_three_sourced_currency_units(self):
        for part,fg,cogs in((0,'2.50','0.50'),(1,'2.00','1.00')):
            expected=o.gold(part)
            self.assertEqual(expected['FG_invoice_delta'],D(fg));self.assertEqual(expected['COGS_invoice_delta'],D(cogs))
            self.assertEqual(expected['FG_invoice_delta']+expected['COGS_invoice_delta'],D('3.00'))
        with self.assertRaises(ValueError):o.gold(2)

    def test_actual_native7_admission_is_fail_closed_to_missing_failed_or_unrestored_cases(self):
        tree=ast.parse((HERE/'cases.py').read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='admit_native7']
        literal=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='NATIVE7_IDS'for t in n.targets))
        ns=dict(re=re,NATIVE7_IDS=literal,NATIVE7_ADMISSION=None)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<admission-under-test>','exec'),ns)
        # Explicit local gate inputs, never written as a runtime admission.
        group=dict(counts={'PASS':7},cases={key:dict(status='PASS',full_boundary_restored=True)for key in literal})
        args=dict(original_report_sha256='a'*64,backend_commit=guard.BACKEND)
        for change in(lambda value:value['cases'].pop(literal[0]),lambda value:value['cases'][literal[0]].update(status='INCOMPLETE'),
                      lambda value:value['cases'][literal[0]].update(full_boundary_restored=False),lambda value:value.update(error='original failed')):
            bad=json.loads(json.dumps(group));change(bad)
            with self.assertRaises(AssertionError):ns['admit_native7'](bad,**args)
        with self.assertRaises(AssertionError):ns['admit_native7'](group,**dict(args,backend_commit='unaccepted'))
        self.assertIsNone(ns['NATIVE7_ADMISSION'])

    def test_prepared_source_and_entrypoint_remain_exact_three_and_without_posted_seeds(self):
        admitted=guard.admitted();self.assertEqual(len(admitted['case_ids']),3);self.assertFalse(admitted['actual_Native_execution'])
        for name in('cases.py','native_fixture.py'):
            source=(HERE/name).read_text()
            self.assertNotRegex(source,re.compile(r'insert\s+into\s+erp\.(?:fg_stock_movements|hpp_versions|hpp_version_components|journal_entries|journal_lines|product_conversions|product_conversion_allocations)\b',re.I))
            self.assertNotRegex(source,re.compile(r'create\s+(?:or\s+replace\s+)?function\b',re.I))
            self.assertNotRegex(source,r'connection\.(?:commit|rollback)\(')
        source=(HERE/'cases.py').read_text()
        for text in('order by line_no desc','predicted=sorted(range(2)','n.immutable(cur','n.source_hpp(cur',"n.f.b.internal(cur,'post_material_supplier_invoice_v2'",'n.reverse_invoice(cur,invoice)','n.unchanged(cur,frozen'):
            self.assertIn(text,source)

if __name__=='__main__':unittest.main()
