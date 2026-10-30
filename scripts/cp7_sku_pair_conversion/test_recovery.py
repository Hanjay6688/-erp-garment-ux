"""Source/ABI/metadata controls. No server or Native financial acceptance."""
import ast
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='602b4e642a0afbb1acdcfd858b9f403dc14ec336'
spec=importlib.util.spec_from_file_location('managed_recovery_delta',HERE/'recovery_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)

class RecoveryTests(unittest.TestCase):
    def catalog(self):
        return json.loads((HERE/'recovery_local/NATIVE_PROFILE_CATALOG.json').read_bytes())

    def test_exact_actual_catalogue_profile_and_two_reversible_derivations(self):
        catalog=self.catalog();delta.validate(catalog)
        originals={sig:catalog['functions'][sig][0]for sig in delta.SIGNATURES}
        patched=delta.patched(originals)
        self.assertEqual(patched[delta.SIGNATURES[0]].replace(delta.GUARD,'',1),originals[delta.SIGNATURES[0]])
        self.assertEqual(patched[delta.SIGNATURES[1]].replace(delta.AUTH,'',1).replace('\n'+delta.AUTH.rstrip('\n'),'',1),originals[delta.SIGNATURES[1]])
        valuation=patched[delta.SIGNATURES[0]]
        self.assertLess(valuation.index('recovery_preflight_v1'),valuation.index('perform erp.bc_new_document_v1'))
        self.assertGreater(valuation.index('recovery_preflight_v1'),valuation.index('BC_DATE_BEFORE_SOURCE'))
        service=patched[delta.SIGNATURES[1]]
        positions=[service.index('recovery_auth_v1'),service.index('v_cached:=erp._idempotency_begin'),service.rindex('recovery_auth_v1'),service.index('if v_cached is not null')]
        self.assertEqual(positions,sorted(positions))

    def test_wrong_current_body_owner_acl_storage_and_view_fail_before_ddl(self):
        for mutation in('body','owner','acl','math','storage','view'):
            catalog=self.catalog()
            if mutation=='body':catalog['functions'][delta.SIGNATURES[0]][0]+='\n'
            elif mutation=='owner':catalog['functions'][delta.SIGNATURES[0]][1]='other_owner'
            elif mutation=='acl':catalog['functions'][delta.SIGNATURES[1]][-1].append(['anon','postgres','EXECUTE',False])
            elif mutation=='math':catalog['functions']['erp.be_propagate_nonpo_v1()'][0]+='\n'
            elif mutation=='storage':catalog['columns']['erp.hpp_versions:total_cost'][2]='numeric(24,2)'
            else:catalog['relations']['erp.v_current_hpp'][9]+='\n'
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,'SKU_RECOVERY_'):
                delta.validate(catalog)

    def test_unknown_missing_extra_or_changed_capture_is_not_derived(self):
        original={sig:self.catalog()['functions'][sig][0]for sig in delta.SIGNATURES}
        for kind in('missing','extra','body'):
            broken=deepcopy(original)
            if kind=='missing':broken.pop(delta.SIGNATURES[0])
            elif kind=='extra':broken['erp.other()']='select 1'
            else:broken[delta.SIGNATURES[0]]=broken[delta.SIGNATURES[0]].replace('v_qty*v_unit','v_qty+v_unit',1)
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'SKU_RECOVERY_'):delta.patched(broken)

    def test_original_business_and_captured_six_remain_byte_exact(self):
        for name in('pairs.sql','conversion.sql','native_delta.py','ri_catalog.py'):
            path='scripts/cp7_sku_pair_conversion/'+name
            expected=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
            self.assertEqual((ROOT/path).read_bytes(),expected,path)
        source=(HERE/'composition.py').read_text();tree=ast.parse(source)
        selected=[n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in('TABLES','FUNCTIONS')for t in n.targets)]
        namespace={'SCHEMA':'cp7_sku_conversion'}
        exec(compile(ast.Module(body=selected,type_ignores=[]),'<private declarations>','exec'),namespace)
        self.assertEqual(len(namespace['TABLES']),5);self.assertEqual(len(namespace['FUNCTIONS']),19)
        self.assertIn('recovery_delta.validate(before)',source)
        self.assertLess(source.index('recovery_delta.validate(before)'),source.index("cur.execute((HERE/'pairs.sql')"))
        self.assertIn('CAPTURE_SIGNATURES=native_delta.SIGNATURES+recovery_delta.SIGNATURES',source)

    def test_unchanged_native_witnesses_bind_actual_precision_and_root_scope(self):
        witnesses=json.loads((HERE/'recovery_local/NATIVE_UNCHANGED.json').read_bytes())['functions']
        for sig,pin in witnesses.items():
            self.assertEqual(pin['sha256'],sha256(pin['definition'].encode()).hexdigest())
            self.assertEqual(pin['definition'],self.catalog()['functions'][sig][0])
        nonpo=witnesses['erp.be_propagate_nonpo_v1()']['definition']
        self.assertIn('v_desired numeric(18,6)',nonpo);self.assertIn('v_desired<0',nonpo)
        self.assertIn('not erp.be_nonpo_admitted_v1(c.id)',nonpo)
        graph=(HERE/'recovery.sql').read_text()
        self.assertNotIn('nextval(',graph);self.assertNotIn('setval(',graph);self.assertNotIn('set_config(',graph)
        self.assertNotIn('pg_advisory_xact_lock(',graph)
        self.assertIn('v_total numeric(24,6)',graph)
        self.assertIn('v_pending:=round(p_qty*p_unit,2)',graph)
        self.assertIn('in share row exclusive mode nowait',graph)

if __name__=='__main__':unittest.main()
