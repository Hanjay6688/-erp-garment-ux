"""Labelled state/lifecycle models only; no Native SQL or financial oracle."""
from pathlib import Path
from types import SimpleNamespace
from hashlib import sha256
from contextlib import nullcontext
from copy import deepcopy
from unittest.mock import patch
import ast,importlib.util,json,subprocess,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('complete_de_lifecycle_model',ROOT/'scripts/cp7_complete_credit_de/composition.py')
product=importlib.util.module_from_spec(spec);spec.loader.exec_module(product)


class Catalog:
    @staticmethod
    def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    @staticmethod
    def _authority(cur):pass
    @staticmethod
    def _data(cur):return deepcopy(cur.data)
    @staticmethod
    def _catalog_rows(cur):return deepcopy(cur.catalog)
    @staticmethod
    def _lock_tables(cur):cur.events.append('TABLE_LOCK')


class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',
            'a6cc41ec58e4d0d0c8191f1b1fe5c27309fff559:scripts/cp7_current_s03_sku_s05/composition.py'])
        assert sha256(raw).hexdigest()=='d0cf9005d7322dbd57e332d90e156f168ceee4425edc9a6092879153c89b6beb'
        nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='binding']
        namespace={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'exact-complete-parent-binding-model','exec'),namespace)
        cls.complete_binding=staticmethod(namespace['binding'])

    def fixture(self):
        catalog=Catalog();c0={'MODEL_CATALOG':'COMPLETE'};c1={'MODEL_CATALOG':'D1'};c2={'MODEL_CATALOG':'E'}
        original={'MODEL_ROW':1,'MODEL_SEQUENCE':[7,True]};data1=dict(original,MODEL_D1=[]);data2=dict(data1,MODEL_E=[])
        financial=dict(sources={'MODEL':'financial'},parent_binding='financial',after=c0,
            preinstall_data_and_sequences={'MODEL_BASE':True},preuse_data_and_sequences=deepcopy(original))
        reader=dict(sources={'MODEL':'reader'},parent_binding='reader',after=c0,data=deepcopy(original))
        complete_state=dict(sources={'MODEL':'complete'},financial_parent=financial,reader=reader,after=c0,
            preinstall_data_and_sequences={'MODEL_BASE':True},preuse_data_and_sequences=deepcopy(original))
        complete_state['component_binding']=self.complete_binding(catalog,complete_state)
        d1_state=dict(sources={'MODEL':'D1'},predecessor=complete_state,parent_binding='D1',before=c0,after=c1,
            preinstall_data_and_sequences={'MODEL_BASE':True},preuse_data_and_sequences=deepcopy(data1))
        e_state=dict(sources={'MODEL':'E'},predecessor=d1_state,parent_binding='E',before=c1,after=c2,
            preinstall_data_and_sequences={'MODEL_BASE':True},preuse_data_and_sequences=deepcopy(data2))
        cur=SimpleNamespace(catalog=deepcopy(c2),data=deepcopy(data2),layer='E',events=[],raw={'MODEL_NATIVE':['42','postgres',None]})
        def checked(layer,current,state):
            if current.layer!=layer or current.catalog!=state['after']:raise AssertionError('PROJECTED_OR_WRONG_LAYER')
            current.events.append('VERIFY_'+layer);return {'MODEL_VERIFIED':layer}
        complete=SimpleNamespace(binding=self.complete_binding,verify=lambda c,s:checked('COMPLETE',c,s))
        def remove_e(c,s):
            checked('E',c,s);c.events.append('REMOVE_E');c.layer='D1';c.catalog=deepcopy(c1);c.data=deepcopy(data1)
            return {'MODEL_REMOVED':'E'}
        def remove_d1(c,s):
            checked('D1',c,s);c.events.append('REMOVE_D1');c.layer='COMPLETE';c.catalog=deepcopy(c0);c.data=deepcopy(original)
            return {'MODEL_REMOVED':'D1'}
        d1=SimpleNamespace(verify=lambda c,s:checked('D1',c,s),rollback_delta_preuse=remove_d1)
        e=SimpleNamespace(verify=lambda c,s:checked('E',c,s),rollback_delta_preuse=remove_e)
        base=SimpleNamespace(atomic=lambda c:nullcontext(),predecessor=SimpleNamespace(
            predecessor=SimpleNamespace(_locks=lambda c:c.events.append('PARENT_LOCK'))))
        state=dict(sources={'MODEL':'top'},complete_parent=complete_state,D1=d1_state,E=e_state,before=c0,after=c2,
            raw_existing_function_authority=deepcopy(cur.raw),preinstall_data_and_sequences={'MODEL_BASE':True},
            preuse_data_and_sequences=deepcopy(data2))
        with patch.object(product,'parts',return_value=(complete,d1,e)):
            state['component_binding']=product.binding(catalog,state)
        return cur,state,catalog,base,complete,d1,e,original

    def inverse(self,values):
        cur,state,catalog,base,complete,d1,e,_=values
        # Only this isolated module's model dependencies are supplied. No
        # imported product or ERP method is changed and no database exists.
        with patch.object(product,'parts',return_value=(complete,d1,e)),\
             patch.object(product,'runtime',return_value=(None,None,None,base,catalog)),\
             patch.object(product,'sources',return_value={'MODEL':'top'}),\
             patch.object(product,'raw_authority',side_effect=lambda c,signatures:c.raw):
            return product.rollback_delta_preuse(cur,state)

    def test_pending_parent_refuses_before_ERP_import_or_database(self):
        with patch.object(product,'parts',side_effect=AssertionError('ERP_TOO_EARLY')):
            with self.assertRaisesRegex(ValueError,'PERMANENT_PARENT_INTAKE_PENDING'):
                product.install_delta(object(),{})

    def test_inverse_removes_E_then_D1_and_verifies_actual_complete_parent(self):
        values=self.fixture();cur,state,*_=values;result=self.inverse(values)
        self.assertIs(result['used_guard_before_DDL'],True)
        self.assertEqual(cur.data,values[-1]);self.assertEqual(cur.catalog,state['before'])
        self.assertLess(cur.events.index('REMOVE_E'),cur.events.index('REMOVE_D1'))
        self.assertEqual(cur.events[-1],'VERIFY_COMPLETE')

    def test_used_row_refuses_before_either_child_removal(self):
        values=self.fixture();cur=values[0];cur.data['MODEL_ROW']=2
        with self.assertRaisesRegex(ValueError,product.USED_ERROR):self.inverse(values)
        self.assertFalse(any(x.startswith('REMOVE')for x in cur.events));self.assertEqual(cur.layer,'E')

    def test_used_sequence_refuses_before_either_child_removal(self):
        values=self.fixture();cur=values[0];cur.data['MODEL_SEQUENCE'][0]=8
        with self.assertRaisesRegex(ValueError,product.USED_ERROR):self.inverse(values)
        self.assertFalse(any(x.startswith('REMOVE')for x in cur.events))

    def test_coordinated_complete_preinstall_changes_refuse_original_binding(self):
        values=self.fixture();cur,state=values[:2]
        state['preinstall_data_and_sequences']['MODEL_BASE']=False
        state['complete_parent']['preinstall_data_and_sequences']['MODEL_BASE']=False
        with self.assertRaisesRegex(ValueError,'STATE_CHAIN_CHANGED'):self.inverse(values)
        self.assertFalse(any(x.startswith('REMOVE')for x in cur.events))

    def test_explicit_empty_raw_ACL_cannot_replace_NULL(self):
        values=self.fixture();cur=values[0];cur.raw['MODEL_NATIVE'][2]='{}'
        with self.assertRaisesRegex(ValueError,'RAW_ACL_CHANGED'):self.inverse(values)
        self.assertFalse(any(x.startswith('REMOVE')for x in cur.events))


if __name__=='__main__':unittest.main()
