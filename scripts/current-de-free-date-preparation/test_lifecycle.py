"""Explicit synthetic lifecycle models; no ERP module, SQL or case credit."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
from contextlib import nullcontext
from copy import deepcopy
from unittest.mock import patch
import ast,importlib.util,json,subprocess,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


product=load('synthetic_date_DE_composition',ROOT/'scripts/cp7_current_de_free_date/composition.py')
stage=load('synthetic_date_DE_original_stage',ROOT/'scripts/cp7_special_free_date_on_de/composition.py')
admission=load('synthetic_date_DE_receipt_parser',HERE/'admission.py')


class Catalog:
    @staticmethod
    def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    @staticmethod
    def _authority(cur):pass
    @staticmethod
    def _catalog_rows(cur):return deepcopy(cur.catalog)
    @staticmethod
    def _data(cur):return deepcopy(cur.data)
    @staticmethod
    def _lock_tables(cur):cur.events.append('MODEL_TABLE_LOCK')


class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_binding_sources={}
        def original(path,namespace):
            raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',
                '674a700096eab400e9b75700e4a2704f799d69b8:'+path])
            cls.original_binding_sources[path]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
            nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='binding']
            if len(nodes)!=1:raise AssertionError('ONE_ACTUAL_PARENT_BINDING_REQUIRED')
            exec(compile(ast.Module(body=nodes,type_ignores=[]),path,'exec'),namespace)
            return namespace['binding']
        cls.complete_binding=staticmethod(original('scripts/cp7_current_s03_sku_s05/composition.py',{}))
        complete=SimpleNamespace(binding=cls.complete_binding)
        cls.de_binding=staticmethod(original('scripts/cp7_complete_credit_de/composition.py',{'parent':lambda:complete}))

    def fixture(self):
        before_sql,after_sql,_=stage.prepared()
        groups=('schemas','relations','columns','constraints','indexes','triggers','functions','aggregates','types',
            'enums','sequences','policies','extensions','roles','memberships','event_triggers','rules','inheritance',
            'default_privileges','database_authority','type_implementation','sequence_ownership')
        before={key:{}for key in groups};before['functions'][stage.SIGNATURE]=[before_sql,'postgres','MODEL_ONLY_METADATA']
        after=deepcopy(before);after['functions'][stage.SIGNATURE][0]=after_sql
        data={'MODEL_ROW':1,'sequence:MODEL.seq':['7',True]};preinstall={'MODEL_BASE':True}
        financial=dict(sources={'MODEL':'financial'},parent_binding='MODEL_FINANCIAL',after=deepcopy(before),
            preuse_data_and_sequences=deepcopy(data),preinstall_data_and_sequences=deepcopy(preinstall))
        reader=dict(sources={'MODEL':'reader'},parent_binding='MODEL_READER',after=deepcopy(before),data=deepcopy(data))
        complete=dict(sources={'MODEL':'complete'},financial_parent=financial,reader=reader,after=deepcopy(before),
            preuse_data_and_sequences=deepcopy(data),preinstall_data_and_sequences=deepcopy(preinstall))
        catalog=Catalog();complete['component_binding']=self.complete_binding(catalog,complete)
        d1=dict(sources={'MODEL':'D1'},parent_binding='MODEL_D1',after=deepcopy(before),
            preuse_data_and_sequences=deepcopy(data),preinstall_data_and_sequences=deepcopy(preinstall))
        e=dict(sources={'MODEL':'E'},parent_binding='MODEL_E',after=deepcopy(before),
            preuse_data_and_sequences=deepcopy(data),preinstall_data_and_sequences=deepcopy(preinstall))
        parent=dict(sources={'MODEL':'complete-DE','lower':{'retained':True}},complete_parent=complete,D1=d1,E=e,
            before=deepcopy(before),after=deepcopy(before),raw_existing_function_authority={'MODEL':['42','postgres',None]},
            qualified_complete_sources={'MODEL_ONLY':True},preuse_data_and_sequences=deepcopy(data),
            preinstall_data_and_sequences=deepcopy(preinstall))
        parent['component_binding']=self.de_binding(catalog,parent)
        raw=json.dumps(parent['sources'],sort_keys=True,separators=(',',':')).encode()
        receipt={'qualified_complete_DE_sources':dict(bytes=len(raw),sha256=sha256(raw).hexdigest())}
        cur=SimpleNamespace(catalog=deepcopy(after),data=deepcopy(data),events=[],authority=['MODEL_OID','postgres',None])
        def execute(sql,*,prepare):
            if sql!=before_sql or prepare is not False:raise AssertionError('ONLY_ORIGINAL_MODEL_INVERSE_ALLOWED')
            cur.events.append('MODEL_DATE_INVERSE');cur.catalog=deepcopy(before)
        cur.execute=execute
        def verify(c,s):
            if c.catalog!=s['after']:raise AssertionError('OLD_PARENT_VERIFIER_CALLED_ON_CHANGED_CATALOGUE')
            c.events.append('MODEL_PARENT_VERIFY');return {'MODEL_PARENT_VERIFIED':True}
        def remove(c,s):
            verify(c,s);c.events.append('MODEL_PARENT_INVERSE');c.catalog=deepcopy(s['before']);c.data=deepcopy(s['preinstall_data_and_sequences'])
            return {'MODEL_PARENT_REMOVED':True}
        p=SimpleNamespace(sources=lambda:parent['sources'],binding=self.de_binding,verify=verify,rollback_preuse=remove)
        date=dict(sources={'MODEL':'date-stage'},parent_sources=parent['sources'],parent_proof={'MODEL_PARENT_VERIFIED':True},
            parent_binding=parent['component_binding'],before=deepcopy(before),after=deepcopy(after),
            raw_native_authority=deepcopy(cur.authority),preuse_data_and_sequences=deepcopy(data),
            preinstall_data_and_sequences=deepcopy(preinstall))
        date['binding']=stage.binding(catalog,date)
        state=dict(sources={'MODEL':'date-whole'},predecessor=parent,date=date,
            qualified_parent_sources=receipt['qualified_complete_DE_sources'],before=deepcopy(before),after=deepcopy(after),
            preuse_data_and_sequences=deepcopy(data),preinstall_data_and_sequences=deepcopy(preinstall))
        base=SimpleNamespace(atomic=lambda c:nullcontext(),predecessor=SimpleNamespace(
            predecessor=SimpleNamespace(_locks=lambda c:c.events.append('MODEL_PARENT_LOCK'))))
        runtime=(None,None,None,base,catalog)
        return cur,state,parent,p,receipt,runtime

    def invoke(self,cur,state,parent,p,receipt,runtime,full=False):
        # Only these synthetic modules are patched. No imported ERP code or
        # real product state is patched, connected, installed or qualified.
        with patch.object(product,'qualification',return_value=receipt),patch.object(product,'parent',return_value=p),\
            patch.object(product,'stage',return_value=stage),patch.object(product,'runtime',return_value=runtime),\
            patch.object(product,'sources',return_value={'MODEL':'date-whole'}),\
            patch.object(stage,'parent',return_value=p),patch.object(stage,'runtime',return_value=runtime),\
            patch.object(stage,'sources',return_value={'MODEL':'date-stage'}),\
            patch.object(stage,'raw_authority',side_effect=lambda c:list(c.authority)):
            if 'component_binding'not in state:state['component_binding']=product.binding(runtime[4],state)
            return(product.rollback_preuse if full else product.rollback_delta_preuse)(cur,state)

    def test_unused_date_inverse_restores_before_parent_verification(self):
        cur,state,parent,p,receipt,runtime=self.fixture();data=deepcopy(cur.data)
        result=self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertTrue(result['used_guard_before_DDL']);self.assertEqual(cur.data,data)
        self.assertEqual(cur.catalog,parent['after'])
        self.assertLess(cur.events.index('MODEL_DATE_INVERSE'),cur.events.index('MODEL_PARENT_VERIFY'))

    def test_used_row_refuses_before_any_date_or_parent_DDL(self):
        cur,state,parent,p,receipt,runtime=self.fixture();cur.data['MODEL_ROW']=2;before=deepcopy(cur.catalog)
        with self.assertRaisesRegex(ValueError,stage.USED_ERROR):self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertNotIn('MODEL_DATE_INVERSE',cur.events);self.assertEqual(cur.catalog,before)

    def test_used_sequence_refuses_before_DDL(self):
        cur,state,parent,p,receipt,runtime=self.fixture();cur.data['sequence:MODEL.seq'][0]='8'
        with self.assertRaisesRegex(ValueError,stage.USED_ERROR):self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertNotIn('MODEL_DATE_INVERSE',cur.events)

    def test_coordinated_preuse_snapshot_change_cannot_rebind_actual_DE_parent(self):
        cur,state,parent,p,receipt,runtime=self.fixture()
        for value in(state,state['date'],parent):value['preuse_data_and_sequences']['MODEL_ROW']=2
        with self.assertRaisesRegex(ValueError,'QUALIFIED_PARENT_STATE'):self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertEqual(cur.events,[])

    def test_coordinated_preinstall_snapshot_change_cannot_rebind_actual_DE_parent(self):
        cur,state,parent,p,receipt,runtime=self.fixture()
        for value in(state,state['date'],parent):value['preinstall_data_and_sequences']['MODEL_BASE']=False
        with self.assertRaisesRegex(ValueError,'QUALIFIED_PARENT_STATE'):self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertEqual(cur.events,[])

    def test_nested_complete_parent_snapshot_change_is_refused(self):
        cur,state,parent,p,receipt,runtime=self.fixture();parent['complete_parent']['financial_parent']['preuse_data_and_sequences']['MODEL_ROW']=2
        with self.assertRaisesRegex(ValueError,'QUALIFIED_PARENT_STATE'):self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertEqual(cur.events,[])

    def test_changed_lower_source_is_refused_against_exact_root_pin(self):
        cur,state,parent,p,receipt,runtime=self.fixture();parent['sources']['lower']['retained']=False
        with self.assertRaisesRegex(ValueError,'ENTIRE_PARENT_SOURCE'):self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertEqual(cur.events,[])

    def test_raw_NULL_to_explicit_ACL_change_is_refused(self):
        cur,state,parent,p,receipt,runtime=self.fixture();cur.authority[2]='{}'
        with self.assertRaisesRegex(ValueError,'RAW_OWNER_OID_OR_ACL'):self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertNotIn('MODEL_DATE_INVERSE',cur.events)

    def test_full_inverse_removes_date_before_parent(self):
        cur,state,parent,p,receipt,runtime=self.fixture();self.invoke(cur,state,parent,p,receipt,runtime,full=True)
        self.assertLess(cur.events.index('MODEL_DATE_INVERSE'),cur.events.index('MODEL_PARENT_INVERSE'))
        self.assertEqual(cur.data,parent['preinstall_data_and_sequences'])

    def test_boolean_parent_source_byte_count_is_refused(self):
        cur,state,parent,p,receipt,runtime=self.fixture();receipt['qualified_complete_DE_sources']['bytes']=False
        with self.assertRaisesRegex(ValueError,'ENTIRE_PARENT_SOURCE'):self.invoke(cur,state,parent,p,receipt,runtime)
        self.assertEqual(cur.events,[])

    def test_duplicate_receipt_key_refuses(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):admission.strict('{"a":1,"a":2}')

    def test_nonfinite_receipt_number_refuses(self):
        for raw in('{"n":NaN}','{"n":1e999}'):
            with self.assertRaisesRegex(ValueError,'NONFINITE'):admission.strict(raw)


if __name__=='__main__':unittest.main()
