"""Preparation checks, not a browser, Auth or Native runtime qualification."""
from pathlib import Path
import ast,importlib.util,json,re,unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sku29_browser_source_guard_test',HERE/'source_guard.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)

class PlanTests(unittest.TestCase):
    def test_exact_two_cases_and_current_backend_source_binding(self):
        proof=guard.admitted();self.assertEqual(len(proof['case_ids']),2);self.assertFalse(proof['actual_runtime_execution'])
        self.assertEqual(proof['backend_candidate']['commit'],'21c69cf25defcee854beb08e998062d7e883d968')

    def test_no_fixture_posted_seeding_or_runtime_response_fabrication(self):
        fixture=(HERE/'fixture.py').read_text();browser=(HERE/'browser.mjs').read_text()
        self.assertNotRegex(fixture,re.compile(r'insert\s+into\s+erp\.(?:fg_stock_movements|hpp_versions|hpp_version_components|journal_entries|journal_lines|product_conversions)\b',re.I))
        self.assertNotRegex(fixture,re.compile(r'create\s+(?:or\s+replace\s+)?function',re.I))
        self.assertNotRegex(browser,r'fulfill\(\{(?:[^}]*)(?:body|json|status)\s*:')
        for value in('ui.login','route.fetch()','route.abort(\'failed\')','equalCensus(committed.census,recovered.census)','previewOracle(reviewed.preview,f)',
                      "getByRole('button',{name:'Reconcile transaksi'",'requireConsoleEvidence','page.reload()','await panel.screenshot'):
            self.assertIn(value,browser)

    def test_all22_native_rows_sequences_and_dependency_use_are_observed(self):
        source=(HERE/'fixture.py').read_text()
        for value in('catalog._catalog_rows(cur)','catalog._data(cur)','len(rows)==22','product.TABLES','f.native_ledgers(cur)',
                      "f.reserve(cur,fixture,fixture['target'],5",'used_conversion_lots=used','f.cancel_reservation(cur',"parsed.path=='/cp6_auditor_browser'",'sys.argv=sys.argv[:1]'):
            self.assertIn(value,source)
        self.assertNotIn('rollback_delta_preuse(',source)

if __name__=='__main__':unittest.main()
