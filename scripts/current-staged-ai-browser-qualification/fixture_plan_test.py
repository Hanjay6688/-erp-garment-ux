"""Local safety/source controls only; no database, Native, Auth or browser run."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('staged_ai_fixture_plan', HERE / 'fixture.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class FixturePlan(unittest.TestCase):
    def test_no_runtime_claim_or_partial_census_exclusion(self):
        plan = fixture.plan()
        self.assertEqual(plan['status'], 'PREPARED')
        self.assertFalse(plan['actual_native_auth_browser_executed'])
        self.assertFalse(plan['browser_job_created'])
        self.assertFalse(plan['financial_results_fabricated'])
        self.assertEqual(plan['excluded_catalog_keys'], [])
        self.assertEqual(plan['controlled_check_keys'], ['cp7_analysis_stage.source_checks', 'sequence:cp7_analysis_stage.source_checks_id_seq'])

    def test_only_exact_disposable_loopback_database(self):
        for valid in ['postgresql://postgres@127.0.0.1:54322/cp6_auditor_browser', 'postgres://postgres@localhost/cp6_auditor_browser']:
            self.assertEqual(fixture.disposable_url(valid), valid)
        for invalid in ['postgresql://example.com/cp6_auditor_browser', 'postgresql://127.0.0.1/erp', 'https://localhost/cp6_auditor_browser', 'postgresql://localhost/cp6_auditor_browser?host=example.com', 'postgresql://localhost/cp6_auditor_browser#other']:
            with self.assertRaises(ValueError):
                fixture.disposable_url(invalid)

    def test_runtime_uses_unfiltered_catalog_helper_and_retained_native_setup(self):
        source = (HERE / 'fixture.py').read_text()
        tree = ast.parse(source)
        functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        state = ast.get_source_segment(source, functions['state'])
        self.assertIn('data = catalog._data(cur)', state)
        # Key-count metadata may inspect names; the returned census is the same
        # entire dictionary, with no five-table filter or ignored namespaces.
        self.assertIn('data=data', state)
        main = ast.get_source_segment(source, functions['main'])
        self.assertIn('native.setup(cur, today)', main)
        self.assertIn('conn.rollback()', main)
        self.assertNotIn('create_user', main)
        self.assertNotIn('request_staged', main)

    def test_state_keeps_every_business_namespace_and_sequence_from_catalog(self):
        from types import SimpleNamespace
        data = {'erp.fg_stock_movements': [4, 'fg'], 'cp7_credit.applications': [2, 'credit'],
                'sequence:erp.invoice_seq': ['7', True], 'auth.users': [1, 'auth'],
                fixture.CHECK_TABLE: [0, 'empty'], fixture.CHECK_SEQUENCE: ['1', False]}
        class Cursor:
            def execute(self, query):
                self.query = query
                return self
            def fetchone(self):
                return (fixture.CHECK_SEQUENCE.removeprefix('sequence:'),)
            def fetchall(self):
                return []
        native = SimpleNamespace(staged=SimpleNamespace(b=SimpleNamespace(api=SimpleNamespace(admin=lambda cur: None))))
        result = fixture.state(Cursor(), native, SimpleNamespace(_data=lambda cur: data))
        self.assertIs(result['data'], data)
        self.assertEqual(result['census_keys'], 6)
        self.assertEqual(result['sequence_keys'], 2)
        self.assertEqual(result['excluded_catalog_keys'], [])


if __name__ == '__main__':
    unittest.main()
