"""Explicit lifecycle models, exact parent binding source, zero ERP SQL cases."""
from pathlib import Path
from types import SimpleNamespace
from hashlib import sha256
from contextlib import nullcontext
from copy import deepcopy
from unittest.mock import patch
import ast
import importlib.util
import json
import subprocess
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('free_date_lifecycle_model',HERE/'composition.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)


class ModelCatalog:
    @staticmethod
    def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    @staticmethod
    def _authority(cur):pass
    @staticmethod
    def _catalog_rows(cur):return deepcopy(cur.catalog)
    @staticmethod
    def _data(cur):return deepcopy(cur.data)
    @staticmethod
    def _lock_tables(cur):cur.events.append('TABLE_LOCK')


class StateBindingControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',
            'a42f666a4cdd0b62d7ed759a9ed58abdf7fa2fa0:scripts/cp7_current_s03_sku_s05/composition.py'])
        if sha256(raw).hexdigest()!='d0cf9005d7322dbd57e332d90e156f168ceee4425edc9a6092879153c89b6beb':
            raise AssertionError('EXACT_PARENT_BINDING_SOURCE_CHANGED')
        nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='binding']
        namespace={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'exact-parent-binding-model','exec'),namespace)
        cls.actual_parent_binding=staticmethod(namespace['binding'])

    def fixture(self):
        before_text,after_text,_=stage.prepared()
        before={'functions':{stage.SIGNATURE:[before_text,'postgres','MODEL_RETAINED_METADATA']}}
        before.update({'MODEL_GROUP_'+str(i):{}for i in range(21)})
        after=deepcopy(before);after['functions'][stage.SIGNATURE][0]=after_text
        data={'MODEL_ROW':{'value':1},'MODEL_SEQUENCE':{'last_value':7,'is_called':True}}
        financial=dict(sources={'qualified':'financial'},parent_binding='MODEL_FINANCIAL_BINDING',after=deepcopy(before),
            preuse_data_and_sequences=deepcopy(data),preinstall_data_and_sequences={'MODEL_BASE':True})
        reader=dict(sources={'qualified':'reader'},parent_binding='MODEL_READER_BINDING',after=deepcopy(before),data=deepcopy(data))
        parent=dict(sources={'qualified':'complete'},financial_parent=financial,reader=reader,
            after=deepcopy(before),preuse_data_and_sequences=deepcopy(data),preinstall_data_and_sequences={'MODEL_BASE':True})
        catalog=ModelCatalog();parent['component_binding']=self.actual_parent_binding(catalog,parent)
        state=dict(sources={'qualified':'date'},parent_sources=parent['sources'],parent_proof={'MODEL_PROOF':True},
            parent_binding=parent['component_binding'],before=before,after=after,
            raw_native_authority=['MODEL_OID','postgres',None],preuse_data_and_sequences=deepcopy(data),
            preinstall_data_and_sequences=deepcopy(parent['preinstall_data_and_sequences']))
        state['binding']=stage.binding(catalog,state)
        class Cursor:
            def __init__(self):self.catalog=deepcopy(after);self.data=deepcopy(data);self.events=[]
            def execute(self,sql,*,prepare):
                if sql!=before_text or prepare is not False:raise AssertionError('UNDECLARED_MODEL_SQL')
                self.events.append('RESTORE_DDL');self.catalog=deepcopy(before)
        cur=Cursor()
        base=SimpleNamespace(atomic=lambda c:nullcontext(),
            predecessor=SimpleNamespace(predecessor=SimpleNamespace(_locks=lambda c:c.events.append('PARENT_LOCK'))))
        p=SimpleNamespace(binding=self.actual_parent_binding,sources=lambda:parent['sources'],
            verify=lambda c,s:{'MODEL_PARENT_VERIFIED':True})
        return cur,state,parent,catalog,base,p

    def invoke(self,cur,state,parent,catalog,base,p):
        # These are isolated model dependencies only. No imported ERP module
        # or real product function is patched, and no database is present.
        with patch.object(stage,'runtime',return_value=(None,None,None,base,catalog)),\
             patch.object(stage,'parent',return_value=p),patch.object(stage,'sources',return_value={'qualified':'date'}),\
             patch.object(stage,'raw_authority',return_value=['MODEL_OID','postgres',None]):
            return stage.rollback_delta_preuse(cur,state,parent)

    def test_unused_inverse_keeps_rows_sequences_and_restores_exact_catalog(self):
        cur,state,parent,catalog,base,p=self.fixture();original=deepcopy(cur.data)
        value=self.invoke(cur,state,parent,catalog,base,p)
        self.assertIs(value['used_guard_before_DDL'],True)
        self.assertEqual(cur.data,original);self.assertEqual(cur.catalog,state['before'])
        self.assertEqual(cur.events.count('RESTORE_DDL'),1)

    def test_used_row_refuses_before_DDL(self):
        cur,state,parent,catalog,base,p=self.fixture();cur.data['MODEL_ROW']['value']=2
        before=deepcopy(cur.catalog)
        with self.assertRaisesRegex(ValueError,stage.USED_ERROR):self.invoke(cur,state,parent,catalog,base,p)
        self.assertNotIn('RESTORE_DDL',cur.events);self.assertEqual(cur.catalog,before)

    def test_used_sequence_refuses_before_DDL(self):
        cur,state,parent,catalog,base,p=self.fixture();cur.data['MODEL_SEQUENCE']['last_value']=8
        with self.assertRaisesRegex(ValueError,stage.USED_ERROR):self.invoke(cur,state,parent,catalog,base,p)
        self.assertNotIn('RESTORE_DDL',cur.events)

    def test_changed_preinstall_bound_is_refused(self):
        cur,state,parent,catalog,base,p=self.fixture();state['preinstall_data_and_sequences']['MODEL_BASE']=False
        with self.assertRaisesRegex(ValueError,'QUALIFIED_PARENT_STATE'):self.invoke(cur,state,parent,catalog,base,p)
        self.assertEqual(cur.events,[])

    def test_coordinated_preuse_changes_still_refuse_parent_binding(self):
        cur,state,parent,catalog,base,p=self.fixture()
        for value in(state,parent):value['preuse_data_and_sequences']['MODEL_ROW']['value']=2
        with self.assertRaisesRegex(ValueError,'QUALIFIED_PARENT_STATE'):self.invoke(cur,state,parent,catalog,base,p)
        self.assertEqual(cur.events,[])

    def test_coordinated_preinstall_changes_still_refuse_parent_binding(self):
        cur,state,parent,catalog,base,p=self.fixture()
        for value in(state,parent):value['preinstall_data_and_sequences']['MODEL_BASE']=False
        with self.assertRaisesRegex(ValueError,'QUALIFIED_PARENT_STATE'):self.invoke(cur,state,parent,catalog,base,p)
        self.assertEqual(cur.events,[])


if __name__=='__main__':unittest.main()
