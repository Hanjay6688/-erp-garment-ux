"""Reproduce the actual fresh-process bug and protect the retained money proof.

All database objects below are explicit test doubles. These source controls
execute no ERP, Native, real Auth or browser cases.
"""
from contextlib import contextmanager,nullcontext
from hashlib import sha256
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,copy,importlib.util,json,os,sys,tempfile,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('focused_browser2_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class BrowserObserver(unittest.TestCase):
    def setUp(self):
        self.module=load('persistent_browser_fixture');self.calls=[]
        self.state=dict(after=dict(schemas=dict(erp=['postgres',[]])),opaque_original_field={'retained':True})
        self.raw=json.dumps(self.state).encode();self.expected=['postgres',[]]
        self.schema=copy.deepcopy(self.expected);self.overlay=['authenticated','postgres','USAGE',False]
        self.fail_verify=False
        outer=self
        class Context:
            def __enter__(self):return self
            def __exit__(self,*_):return False
        class Cursor(Context):
            def execute(self,sql,*args):
                outer.calls.append(sql)
                if sql=='select current_database()':return SimpleNamespace(fetchone=lambda:('cp6_auditor_browser',))
                if sql=='actual-schema-query':return SimpleNamespace(fetchall=lambda:[('erp',copy.deepcopy(outer.schema))])
                if sql=='revoke usage on schema erp from authenticated':outer.schema[1].remove(outer.overlay)
                if sql=='grant usage on schema erp to authenticated':outer.schema[1].append(outer.overlay)
                return None
        self.cur=Cursor()
        class Connection(Context):
            def cursor(self):return outer.cur
            def rollback(self):outer.calls.append('rollback')
        self.conn=Connection()
        # Compile the actual unchanged frozen helper, without importing its ERP graph.
        tree=ast.parse((ROOT/'scripts/ow04-payment-source-qualification/source_probe.py').read_bytes())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='product_catalog')
        namespace=dict(contextmanager=contextmanager,STATE=None,
            business=SimpleNamespace(native=SimpleNamespace(b=SimpleNamespace(api=SimpleNamespace(admin=lambda cur:None)))),
            product=SimpleNamespace(catalog=SimpleNamespace(_catalog=lambda cur:nullcontext(),QUERIES={'schemas':'actual-schema-query'})))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual_frozen_product_catalog','exec'),namespace)
        class Control:
            @property
            def STATE(self):return namespace['STATE']
            @STATE.setter
            def STATE(self,value):namespace['STATE']=value
            product_catalog=staticmethod(namespace['product_catalog'])
        self.control=Control()
        def verify(cur,state):
            self.assertEqual(state,self.state);self.assertEqual(self.schema,self.expected)
            if self.fail_verify:raise ValueError('MODEL_FULL_READER_CATALOG_MISMATCH')
        catalog=SimpleNamespace(_catalog_rows=lambda cur:{str(i):{}for i in range(22)},
            _data=lambda cur:{'complete_model_sequence':['3',True]},digest=lambda rows:sha256(json.dumps(rows).encode()).hexdigest())
        stage=SimpleNamespace(verify=verify,parent=lambda:SimpleNamespace(runtime=lambda:(None,None,None,None,catalog)))
        def connect(*args,**kwargs):self.calls.append('connect');return self.conn
        self.imports={'psycopg':SimpleNamespace(connect=connect),
            'cp7_accessory_standard_report':SimpleNamespace(cases=SimpleNamespace()),
            'cp7_s05_s03_sku_composition':SimpleNamespace(stage=stage),
            'cp7_p21_current_chain_rehearsal_probe':SimpleNamespace(helper=SimpleNamespace(control=self.control))}

    def run_observer(self,wrong_hash=False):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);out=root/'cp6-proof/t3';out.mkdir(parents=True)
            (out/'S05_PERMANENT_BROWSER_READER_STATE.json').write_bytes(self.raw)
            util=SimpleNamespace(spec_from_file_location=lambda *a:None,
                module_from_spec=lambda *a:SimpleNamespace(preflight=lambda:None))
            util.spec_from_file_location=lambda *a:SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m:None))
            env={'S05_SKU_BROWSER_CONFIRM':'cp6_auditor_browser',
                'AUDITOR_BROWSER_DB_URL':'postgresql://model@127.0.0.1:54322/cp6_auditor_browser',
                'S05_SKU_BROWSER_READER_STATE_SHA256':'0'*64 if wrong_hash else sha256(self.raw).hexdigest()}
            with patch.object(self.module,'ROOT',root),patch.object(self.module,'importlib',SimpleNamespace(util=util)),\
                patch.dict(sys.modules,self.imports),patch.dict(os.environ,env,clear=True),\
                patch.object(sys,'argv',['fixture','observe']),patch.object(sys,'stdin',StringIO('{"label":"S05_SKU_DESKTOP_MODEL"}')),\
                patch.object(sys,'path',list(sys.path)):
                return self.module.main()

    def test_actual_old_none_state_error_then_real_fixture_main_initializes_verified_state(self):
        with self.assertRaisesRegex(TypeError,'NoneType'):
            with self.control.product_catalog(self.cur):pass
        result=self.run_observer()
        self.assertEqual(self.control.STATE,{'installed_catalog':self.state['after']})
        self.assertEqual(result['catalog_groups'],22)
        self.assertEqual(result['dropped_catalog_fields'],[]);self.assertEqual(result['dropped_data_or_sequence_keys'],[])
        self.assertEqual(self.calls.count('connect'),1);self.assertEqual(self.calls[-1],'rollback')

    def test_only_exact_sql_harness_usage_overlay_is_temporarily_removed_and_restored(self):
        self.schema[1].append(self.overlay);self.run_observer()
        self.assertEqual(self.schema,['postgres',[self.overlay]])
        self.assertEqual([s for s in self.calls if s.startswith(('revoke ','grant '))],
            ['revoke usage on schema erp from authenticated','grant usage on schema erp to authenticated'])

    def test_actual_helper_restores_usage_overlay_when_full_stage_verification_fails(self):
        self.schema[1].append(self.overlay);self.fail_verify=True
        with self.assertRaisesRegex(ValueError,'MODEL_FULL_READER_CATALOG_MISMATCH'):self.run_observer()
        self.assertEqual(self.schema,['postgres',[self.overlay]])

    def test_foreign_acl_is_refused_and_bad_original_hash_stops_before_connect(self):
        self.schema[1].extend([self.overlay,['foreign','postgres','USAGE',False]])
        with self.assertRaisesRegex(AssertionError,'NATIVE_TEST_SCHEMA_DELTA_NOT_EXACT_DECLARED_USAGE'):self.run_observer()
        self.calls=[];self.control.STATE=None
        with self.assertRaisesRegex(ValueError,'ORIGINAL_READER_STATE_CHANGED'):self.run_observer(wrong_hash=True)
        self.assertNotIn('connect',self.calls);self.assertIsNone(self.control.STATE)


class ActualRetention(unittest.TestCase):
    def test_original_root_receipt_has_retained_four_without_aggregate_or_fresh_credit(self):
        m=load('retained4');value=m.receipt()
        self.assertEqual(value['retained_Native_cases'],4);self.assertFalse(value['package_all_five'])
        self.assertFalse(value['complete6_qualified']);self.assertFalse(value['failed_run_relabelled_PASS'])
        with self.assertRaisesRegex(ValueError,'ENTIRE_ACTUAL_PRODUCT_GRAPH_EQUALS_RETAINED4'):m.invariant_sources({})

    def test_corrupted_or_relabelled_actual_retention_receipt_refuses(self):
        m=load('retained4');original=m.receipt()
        for field,bad in [('retained_Native_cases',True),('actual_new_Native_cases',4),
            ('complete6_qualified',True),('package_all_five',True),('retained_original_run_conclusion','success'),
            ('failed_run_relabelled_PASS',True),('actual_outer_restoration_verified',False)]:
            value=copy.deepcopy(original);value[field]=bad;raw=json.dumps(value).encode()
            with self.subTest(field=field),patch.object(m,'ROOT_PIN',m.pin(raw)),self.assertRaises(ValueError):m.receipt(raw)
        with self.assertRaises(ValueError):m.receipt(b'{}')

    def test_own_source_connection_is_released_and_foreign_database_refused(self):
        m=load('retained4');events=[]
        cur=SimpleNamespace(closed=False);conn=SimpleNamespace(closed=False,
            info=SimpleNamespace(host='127.0.0.1',port=54322,dbname='cp6_rollback',backend_pid=77),
            rollback=lambda:events.append('rollback'))
        def close_cur():events.append('own_cursor_close');cur.closed=True
        def close_conn():events.append('own_connection_close');conn.closed=True
        cur.close=close_cur;conn.close=close_conn
        result=m.release_source(conn,cur)
        self.assertEqual(events,['rollback','own_cursor_close','own_connection_close'])
        self.assertEqual(result['foreign_backends_terminated'],0)
        conn.info.dbname='foreign';events=[]
        with self.assertRaisesRegex(ValueError,'EXACT_OWN_LOCAL_SOURCE_CONNECTION_REQUIRED'):m.release_source(conn,cur)
        self.assertEqual(events,[])


if __name__=='__main__':unittest.main()
