"""Scoped fixture/source controls; local SQL doubles carry no Native credit."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import ast
import contextlib
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


class Fixture(unittest.TestCase):
    def test_original_exact10_callback_bodies_and_all_financial_assertions(self):
        raw=(ROOT/'scripts/cp7_accessory_standard_report/cases.py').read_bytes();locked=json.loads((HERE/'evidence/LOCKED_INITIAL_RCA.json').read_bytes())
        self.assertEqual(sha256(raw).hexdigest(),'e025be1280630dfb89f62261163194ce072b6f6ad6d909b56ff6c82f75778e98')
        text=raw.decode();parent=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef)and x.name=='cases')
        observed={x.name:sha256(ast.get_source_segment(text,x).encode()).hexdigest()for x in parent.body if isinstance(x,ast.FunctionDef)and x.name!='intervals'}
        self.assertEqual(observed,locked['original_callback_SHA256']);self.assertEqual(len(observed),10)
        self.assertEqual(text.count("'T00:00:00.000000+07:00'"),1);self.assertEqual(text.count("'T23:59:59.999999+07:00'"),1)

    def test_only_two_declared_fractional_inputs_map_to_same_supported_WIB_day(self):
        m=load('s05_fixture_formatter','fixture_adapter.py')
        for old,new in (('00:00:00.000000','00:00:00'),('23:59:59.999999','23:59:59')):
            self.assertEqual(m.exact_supported_timestamp('2026-01-15','2026-01-15T'+old+'+07:00'),'2026-01-15T'+new+'+07:00')
        for value in ('2026-01-15T00:00:00.001+07:00','2026-01-15T23:59:59+00:00','2026-01-16T00:00:00.000000+07:00'):
            with self.assertRaisesRegex(ValueError,'ONLY_TWO_ORIGINAL'):m.exact_supported_timestamp('2026-01-15',value)

    def test_private_scope_restores_after_all_exception_classes_and_refuses_nested(self):
        m=load('s05_fixture_scope','fixture_adapter.py');business=SimpleNamespace(fixture=lambda *a,**kw:None,issue_note=lambda *a,**kw:None)
        adapter=m.FixtureAdapter(business,{})
        for error in (RuntimeError('test'),SystemExit('test'),KeyboardInterrupt()):
            try:
                with adapter.case_scope(m.WIB_CASE):
                    self.assertEqual(adapter.active,m.WIB_CASE)
                    with self.assertRaisesRegex(ValueError,'EXACT_PRIVATE_CASE_SCOPE'): 
                        with adapter.case_scope(m.ACCESS_CASE):pass
                    raise error
            except BaseException as caught:self.assertIs(caught,error)
            self.assertIsNone(adapter.active)

    def test_unrelated_issue_payloads_forward_exactly_without_format_or_guard_adaptation(self):
        m=load('s05_fixture_forward','fixture_adapter.py');calls=[]
        def original(*args,**kw):calls.append((args,kw));return 'UNCHANGED'
        business=SimpleNamespace(fixture=original,issue_note=original);adapter=m.FixtureAdapter(business,{})
        self.assertEqual(adapter.issue_note('cursor',{'day':'2026-01-15'},'7',at='UNRELATED'),'UNCHANGED')
        self.assertEqual(calls[0][1]['at'],'UNRELATED');self.assertEqual(adapter.observations,[])

    def test_two_scope_bindings_only_and_no_shared_fixture_or_Native_replacement(self):
        source=(HERE/'factory.py').read_text()
        self.assertIn('private.fixture=adapter.fixture',source);self.assertIn('private.issue_note=adapter.issue_note',source)
        self.assertNotIn('retained.fixture=',source);self.assertNotIn('business.issues.bc.',source)
        self.assertIn('raw_callback_body_substitutions=0',source)
        adapter=(HERE/'fixture_adapter.py').read_text()
        self.assertNotIn('set_config(',adapter);self.assertNotIn('session_replication_role',adapter)
        for required in ('before_catalog=catalog._catalog_rows(cur)','before_data=catalog._data(cur)',
                         'after_catalog!=before_catalog or after_data!=before_data',"self.business.issues.bc.user(cur,'OWNER')"):
            self.assertIn(required,adapter)

    def test_actual602_canonical_Native_rows_and_both_committed_prosrc_bodies_exact(self):
        v=json.loads((HERE/'evidence/ACTUAL_602_NATIVE_INPUTS.json').read_bytes())
        pins={'erp._idempotency_begin(text,uuid,text)':'12ab0b5f14bed9f6514982975ea5c213fe0332d9b5e6cf2d6482b45b2ae404be',
              'erp.guard_last_active_owner()':'b9b8c205934b0cfd96ca774bbf6a76e697bc70e119226b24dce8d915e9ea0cc3',
              'erp.save_accessory_issue_action_v1(text,jsonb,uuid)':'db7ee460e6e7f532828c7e8c643ca9a26e28589e0ea8c6da6b6e757f1dcfcb49'}
        for signature,row in v['functions'].items():self.assertEqual(sha256(json.dumps(row,sort_keys=True,default=str).encode()).hexdigest(),pins[signature])
        for signature,name in (('erp.guard_last_active_owner()','erp_guard_last_active_owner.sql'),('erp.save_accessory_issue_action_v1(text,jsonb,uuid)','erp_save_accessory_issue_action_v1.sql')):
            ddl=v['functions'][signature][0];old=(HERE/'evidence'/name).read_text()
            self.assertEqual(ddl.split('$function$')[1],old.split('$function$')[1])
        self.assertFalse(v['actual52eed_catalog_capture'])

    def test_first_actual10_and_four_gates_remain_incomplete_not_prerequisite(self):
        proof=load('s05_exact_first_failure','first_failure.py').check(ROOT,HERE)
        self.assertEqual(proof['counts'],{'PASS':8,'INCOMPLETE':2});self.assertFalse(proof['usable_prerequisite']);self.assertFalse(proof['committed_business_witness_reached'])

    def test_local_SQL_11_proofs_are_explicit_doubles_not_current_Native_qualification(self):
        value=json.loads((HERE/'evidence/LOCAL_MODEL_FIRST.json').read_bytes())
        self.assertEqual(value['status'],'PASS_LOCAL_NATIVE_PARSER_AND_OWNER_GUARD_MODELS_ONLY');self.assertEqual(len(value['checks']),11)
        self.assertEqual(value['actual_Native'],0);self.assertEqual(value['captured_source_head_class'],'ACTUAL602_NOT52EED')
        self.assertTrue(all(x['Native_credit']==0 for x in value['checks']))


if __name__=='__main__':unittest.main()
