"""Source/ABI/privacy controls only. Local SQL models are separately labelled."""
from pathlib import Path
from hashlib import sha256
from unittest import TestCase,main
from unittest.mock import patch
import builtins
import importlib.util
import json
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
RUNTIME=ROOT/'scripts/cp7_global_nonpo_native_graph_adapter'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


class SourceControls(TestCase):
    def test_closed_before_any_ERP_DB_or_process(self):
        actual=builtins.__import__
        def imports(name,*args,**kw):
            if name.startswith(('psycopg','cp7_','cp6_')):raise AssertionError('ERP_IMPORTED_BEFORE_CLOSED')
            return actual(name,*args,**kw)
        with patch.object(builtins,'__import__',imports),patch.object(subprocess,'check_output',side_effect=AssertionError('CLOSED_PROCESS')):
            with self.assertRaisesRegex(ValueError,'CLOSED_READONLY_INSPECTOR_ONLY'):
                load('closed_source_control',RUNTIME/'source.py').runtime_entry()

    def test_exact_known_direct_and_transitive_readers_are_source_bound(self):
        proof=load('global_readonly_source_contract',RUNTIME/'source.py').source_contract()
        self.assertEqual(proof['known_source_functions'],19);self.assertEqual(proof['own_private_STABLE_functions'],4)
        self.assertFalse(proof['writer_or_phantom_lock_closed']);self.assertIsNone(proof['runtime_entry'])

    def test_SQL_authority_literal_matches_source_manifest_without_regeneration(self):
        expected=json.loads((RUNTIME/'AUTHORITY.json').read_bytes())['known_functions']
        sql=(RUNTIME/'authority.sql').read_text();literal=re.search(r"jsonb_each\('(.*?)'::jsonb\)",sql).group(1).replace("''", "'")
        self.assertEqual(json.loads(literal),expected)
        self.assertTrue(expected['erp.require_internal()']['inspection_only_never_called'])
        self.assertTrue(expected['erp.compute_non_po_product_hpp_book_v2620f(uuid)']['inspection_only_never_called'])

    def test_native_writers_are_retained_source_only_never_inspector_calls(self):
        sql='\n'.join((RUNTIME/name).read_text()for name in ('scope.sql','capture.sql','inspect.sql'))
        for name in ('be_nonpo_prepare_transfers_v1','be_nonpo_sync_all_v1','be_propagate_nonpo_v1','sync_non_po_product_hpp_to_gl_v2620f','require_internal','account_id'):
            self.assertNotRegex(sql,r'\berp\.'+name+r'\s*\(')
        self.assertNotRegex(sql,r'(?i)\b(nextval|gen_random_uuid|pg_advisory\w*)\s*\(')

    def test_existing_D1_and_generic_guard_bodies_unchanged_and_E06_not_copied(self):
        origin=json.loads((HERE/'ORIGIN.json').read_bytes())
        for name,pin in origin['current_D1_and_generic_guard_files'].items():
            raw=(ROOT/name).read_bytes();self.assertEqual(sha256(raw).hexdigest(),pin['sha256'])
        self.assertFalse(origin['E06_body_copied']);self.assertIsNone(origin['E_basis_runtime_parent'])
        self.assertIn('STOCK_HPP_CLASS_ADAPTER_REQUIRED',(ROOT/'scripts/cp7_credit_correction_de/owning.sql').read_text())
        self.assertIn('CP7_CREDIT_SOURCE_GLOBAL_HPP_GRAPH_UNQUALIFIED',(ROOT/'scripts/cp7_customer_credit/reconciliation/03_source_requests.sql').read_text())

    def test_known_metadata_includes_owner_config_return_type_language_and_raw_observation(self):
        authority=json.loads((RUNTIME/'AUTHORITY.json').read_bytes())
        self.assertEqual(authority['known_functions']['erp.be_nonpo_admitted_v1(uuid)']['return_type'],'boolean')
        for pin in authority['known_functions'].values():
            for key in ('owner','config','return_type','returns_set','language','volatility','prosrc_sha256'):self.assertIn(key,pin)
        sql=(RUNTIME/'authority.sql').read_text();self.assertIn('raw_schema_acl',sql);self.assertIn('owner_role',sql);self.assertIn('new_private_acl_closed',sql)

    def test_no_new_public_RPC_role_grant_or_runtime_installer(self):
        authority=json.loads((RUNTIME/'AUTHORITY.json').read_bytes())
        self.assertEqual(authority['new_roles'],[]);self.assertEqual(authority['new_public_RPC'],[])
        for name in ('authority.sql','scope.sql','capture.sql','inspect.sql'):
            sql=(RUNTIME/name).read_text();self.assertNotRegex(sql,r'(?im)^\s*grant\s');self.assertNotRegex(sql,r'(?i)create\s+function\s+public\.')
            self.assertRegex(sql,r'(?i)stable\s+security\s+definer');self.assertIn('owner to postgres',sql)
        self.assertFalse((RUNTIME/'composition.py').exists())

    def test_blueprint_is_not_executed_or_claimed_closed(self):
        b=json.loads((HERE/'LOCK_BLUEPRINT.json').read_bytes());self.assertFalse(b['executes_in_this_slice']);self.assertFalse(b['writer_or_phantom_lock_closed'])
        self.assertEqual(b['relations'],sorted(set(b['relations'])))
        self.assertIn('SHARE ROW EXCLUSIVE MODE NOWAIT',b['statement_blueprint'])
        self.assertIn('erp.journal_entries',b['relations']);self.assertIn('cp7_credit.consumption_events',b['relations'])

    def test_writer_census_distinguishes_exact_source_candidates_from_live_routes(self):
        census=json.loads((HERE/'WRITER_CENSUS.json').read_bytes());self.assertEqual(census['source_files']if'source_files'in census else census['input_files'],66)
        self.assertFalse(census['writer_or_phantom_lock_closed']);self.assertIsNone(census['runtime_entry'])
        self.assertTrue(any(x['function']=='erp.post_journal'and not x['literal_FG_HPP_SALES_lock_present']for x in census['writer_candidates']))
        self.assertTrue(census['not_closed'])

    def test_initial_and_later_unattributed_outputs_are_not_authorized_inputs(self):
        origin=json.loads((HERE/'ORIGIN.json').read_bytes());receipt=json.loads((HERE/'evidence/UNATTRIBUTED_WORKTREE_OUTPUTS.json').read_bytes())
        self.assertEqual(len(origin['initial_observed_status_surfaces']),3)
        self.assertNotIn('preexisting_untracked',origin);self.assertFalse(receipt['source_admitted'])
        self.assertEqual(receipt['later_file_count'],199);self.assertFalse(receipt['workspace_clean_or_full_source_admission_claimed'])

    def test_unknown_cli_does_not_enter_runtime_and_CI_cannot_reseal(self):
        result=subprocess.run([sys.executable,'-B',str(HERE/'check.py'),'--source','--unknown-flag'],text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('unrecognized arguments: --unknown-flag',result.stderr)
        self.assertNotIn('CLOSED_READONLY_INSPECTOR_ONLY',result.stderr)
        with patch.dict('os.environ',{'CI':'true'}):
            with self.assertRaisesRegex(ValueError,'SOURCE_FREEZE_IN_CI_FORBIDDEN'):load('global_no_CI_freeze',HERE/'freeze.py').freeze()


if __name__=='__main__':main(verbosity=2)
