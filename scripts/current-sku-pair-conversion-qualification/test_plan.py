"""Prepared-source controls, without importing Native runtime dependencies."""
from pathlib import Path
import ast,re,unittest

HERE=Path(__file__).resolve().parent

def literal(name,path):
    tree=ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in node.targets):return ast.literal_eval(node.value)
    raise AssertionError(name)

class PlanTests(unittest.TestCase):
    def test_seven_unique_native_cases_and_three_unique_races(self):
        native=literal('IDS',HERE/'cases.py');races=literal('IDS',HERE/'races.py');auth=literal('IDS',HERE/'auth_waits.py')
        self.assertEqual(len(native),7);self.assertEqual(len(races),3)
        self.assertEqual(len(auth),6);self.assertEqual(len(set(native+races+auth)),16)

    def test_no_posted_ledger_seeding_or_Native_function_doubles(self):
        for path in (HERE/'fixture.py',HERE/'cases.py',HERE/'races.py'):
            text=path.read_text()
            self.assertNotRegex(text,re.compile(r'insert\s+into\s+erp\.(?:fg_stock_movements|hpp_versions|hpp_version_components|journal_entries|journal_lines|product_conversions)\b',re.I))
            self.assertNotRegex(text,re.compile(r'create\s+(?:or\s+replace\s+)?function\s+erp\.',re.I))
        self.assertIn("'post_opening_balance'",(HERE/'fixture.py').read_text())
        self.assertIn("'save_sale_draft_v2'",(HERE/'fixture.py').read_text())

    def test_actual_component_requires_exact_source_and_full_outer_restoration(self):
        runner=(HERE/'runner.py').read_text()
        for required in("state['sources']!=product.sources()",'SKU29_LOCAL_DISPOSABLE_ONLY','cp6_rollback',
                         'product.USED_ERROR','catalog._catalog_rows(cursor)==before and catalog._data(cursor)==data',
                         'acceptance_requires_complete_outer_restore_and_package=True'):
            self.assertIn(required,runner)
        self.assertIn('full_manual_group_accessory_recovery_claim=False',runner)
        self.assertIn('expected_returns_first_child_limitation_not_closed=True',(HERE/'cases.py').read_text())
        self.assertIn('NULL_blank_unknown_public_commands_existing_group_zero_effect',(HERE/'cases.py').read_text())

    def test_auth_waits_are_real_blocking_observation_and_scope_after_role_change(self):
        source=(HERE/'auth_waits.py').read_text()
        for required in('pg_blocking_pids','holder.commit()','catalog._data(cur)==expected','OWNER or ADMIN access required',
                         "role_code='ADMIN'","role_code='STAFF'",'actor_fixture=\'NEW_USER_EXISTING_ADMIN_NOT_OWNER\''):
            self.assertIn(required,source)

if __name__=='__main__':unittest.main()
