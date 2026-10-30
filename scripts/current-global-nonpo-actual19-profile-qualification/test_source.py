"""Exact-source and closed-entry controls. No Native execution or DB acceptance."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from types import ModuleType
import builtins
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


class Source(unittest.TestCase):
    def test_closed_runtime_before_ERP_DB_or_subprocess(self):
        m=load('actual19_closed','check.py');real=builtins.__import__
        def imports(name,*args,**kwargs):
            if name.startswith(('psycopg','cp7_','cp6_')):raise AssertionError('UNAUTHORIZED_RUNTIME_IMPORT')
            return real(name,*args,**kwargs)
        with patch.object(builtins,'__import__',imports),patch.object(subprocess,'check_output',side_effect=AssertionError('UNAUTHORIZED_PROCESS')),patch.object(sys,'argv',['check.py','--runtime']):
            with self.assertRaisesRegex(ValueError,'CLOSED_NO_FINAL_PARENT'):m.main()

    def test_complete_immutable_parent_and_current_profile(self):
        m=load('actual19_source_admission','check.py');v=m.check(require_clean=False)
        self.assertGreater(v['unchanged_parent_files'],13000);self.assertEqual(v['full_function_catalog_rows'],19)
        self.assertEqual(v['actual_source_catalogues'],3);self.assertEqual(v['actual_Native_credit'],0)
        self.assertIsNone(v['runtime_entry']);self.assertFalse(v['writer_or_phantom_lock_closed'])

    def test_exact_two_changed_expected_bodies_preserve_seventeen_known_entries(self):
        d=load('actual19_source_transition','derive.py');cap=json.loads((HERE/'CAPTURE.json').read_bytes())
        old,new=d.authority(cap)
        changed={key for key in old['known_functions']if old['known_functions'][key]!=new['known_functions'][key]}
        self.assertEqual(changed,set(d.c.CHANGED))
        self.assertFalse(new['actual_source_profile']['raw_NULL_vs_explicit_acl_inferred'])
        extra=deepcopy(cap);signature='erp.be_nonpo_admitted_v1(uuid)'
        extra['functions'][signature][0]=extra['functions'][signature][0].replace('AS $function$','AS $function$\n-- unauthorized body change',1)
        with self.assertRaisesRegex(ValueError,'ACTUAL19_CAPTURED_BODY_CHANGED_IN_STATEMENT_ENCODING'):d.authority(extra)
        changed_meta=deepcopy(cap);changed_meta['functions'][signature][1]='service_role'
        with self.assertRaisesRegex(ValueError,'KNOWN_METADATA_CHANGED'):d.authority(changed_meta)

    def test_seven_SQL_changes_and_private_source_route_are_byte_reversible(self):
        d=load('actual19_source_reversibility','derive.py');a,b,p=d.bundle()
        self.assertEqual(p['authority_sql']['counted_reversible_substitutions'],7)
        self.assertEqual(p['source_proof_route']['count'],1)
        self.assertTrue(p['source_proof_route']['product_source_file_unchanged'])
        self.assertEqual(p['Native_runtime_source_changes'],0)

    def test_full_catalog_row_ABI_uses_actual_restore_query(self):
        d=load('actual19_actual_ABI','derive.py')
        text=d.c.frozen('scripts/cp7_ow04_restore_bundle.py').decode()
        # Execute only the literal _acl builder and QUERIES assignment from AST.
        import ast
        tree=ast.parse(text);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='_acl']
        nodes += [n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='QUERIES'for t in n.targets)]
        ns={'NAMESPACE':'DECLARED_FILTER_ONLY'};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<frozen catalog query definition>','exec'),ns)
        self.assertIn(d.function_row(),ns['QUERIES']['functions'])
        for name in ['procost::text','prorows::text','prosupport::regprocedure::text','pg_get_function_arguments','aclexplode']:
            self.assertIn(name,d.function_row())

    def test_duplicate_and_nonfinite_JSON_refuse(self):
        m=load('actual19_strict_json','check.py')
        for raw in ('{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}'):
            with self.assertRaises(ValueError):m.document(raw)

    def test_source_bytes_modes_links_and_path_escapes_refuse(self):
        m=load('actual19_path_boundary','check.py')
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);p=root/'source.py';p.write_bytes(b'actual\n');expected=dict(m.pin(p.read_bytes()),mode='100644')
            m.checked_file('source.py',expected,root)
            p.write_bytes(b'forged\n')
            with self.assertRaisesRegex(ValueError,'SOURCE_BYTES'):m.checked_file('source.py',expected,root)
            p.unlink();p.symlink_to(root/'missing')
            with self.assertRaisesRegex(ValueError,'SOURCE_LINK'):m.checked_file('source.py',expected,root)
            for name in('../escape','/absolute','a/../escape','a\\b'):
                with self.assertRaisesRegex(ValueError,'UNSAFE_SOURCE_PATH'):m.regular(name,root)

    def test_CI_cannot_reseal_or_regenerate(self):
        with patch.dict(os.environ,{'CI':'true'}):
            for file,function in [('freeze.py','write'),('derive.py','write')]:
                with self.assertRaisesRegex(ValueError,'CI'):getattr(load('actual19_no_'+file,file),function)()
            with self.assertRaisesRegex(ValueError,'CI'):load('actual19_no_capture','capture.py').write('UNREAD')

    def test_first_model_refusal_retained_with_no_native_credit(self):
        v=json.loads((HERE/'evidence/FIRST_OLD_AUTHORITY_REFUSAL.json').read_bytes())
        self.assertEqual(v['status'],'EXPECTED_OLD_PROFILE_REFUSAL_REPRODUCED');self.assertEqual(len(v['mismatches']),2)
        self.assertTrue(v['model_rows_sequence_and_new_catalog_directly_unchanged']);self.assertEqual(v['actual_Native_credit'],0)


if __name__=='__main__':unittest.main()
