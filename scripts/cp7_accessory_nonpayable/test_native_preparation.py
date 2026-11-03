"""Private fixture binding/parent gate controls; zero actual ERP case credit."""
from datetime import date
from contextlib import ExitStack,nullcontext
from types import ModuleType,SimpleNamespace
from unittest.mock import Mock,patch
from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import builtins,json,sys,unittest,uuid
from cp7_accessory_nonpayable import native_fixture as fixture,native_cases as cases

def constructor():
    module=ModuleType('synthetic_physical_fixture_only')
    module.chain=SimpleNamespace(production=SimpleNamespace(CONTRACTOR='00000000-0000-4000-8000-000000000001'),other=object())
    exec('def two_size_fixture(cur,today,label,q1=6,q2=4,*,size_quantities=None,clock=None,work_setup=None,service_refs=None):\n'
         ' return (chain.production.CONTRACTOR,cur,today,label,q1,q2,size_quantities,clock,work_setup,service_refs)\n',module.__dict__)
    return module

class NativePreparationControls(unittest.TestCase):
    def test_financial_failure_retains_actual_detector_delta_and_completed_economics(self):
        cursor=object();before={'existing:OLD':2};after={'existing:OLD':2,'current:NEW':1}
        admin=[]
        bc=SimpleNamespace(api=SimpleNamespace(admin=lambda cur:admin.append(cur)),
            findings=lambda cur:after,new_findings=lambda old,new:{'current:NEW':1})
        observations=dict(lot='actual-lot',booked={'WIP':'20','CONTRACTOR_PAYABLE':'0'},
            physical_date=date(2026,11,3),expected_reimbursement='0')
        with self.assertRaises(ValueError)as caught:
            cases.finish(cursor,SimpleNamespace(bc=bc),before,**observations)
        code,detail=str(caught.exception).split(':',1)
        self.assertEqual(code,'NONPAYABLE_NATIVE_NEW_FINANCIAL_INTEGRITY_FINDINGS')
        self.assertEqual(json.loads(detail),dict(financial_findings_before=before,
            financial_findings_after=after,new_financial_findings={'current:NEW':1},
            completed_observations=dict(observations,physical_date='2026-11-03')))
        self.assertEqual(admin,[cursor])

    def test_financial_success_preserves_observations_and_no_new_findings_gate(self):
        before={'existing:OLD':2};after={'existing:OLD':2}
        bc=SimpleNamespace(api=SimpleNamespace(admin=lambda cur:None),findings=lambda cur:after,
            new_findings=lambda old,new:{})
        value=cases.finish(object(),SimpleNamespace(bc=bc),before,booked={'WIP':'20'})
        self.assertEqual(value['status'],'PASS');self.assertEqual(value['booked'],{'WIP':'20'})
        self.assertEqual(value['financial_findings_before'],before)
        self.assertEqual(value['financial_findings_after'],after)
        self.assertEqual(value['new_financial_findings'],{})
        self.assertFalse(value['production_go']);self.assertFalse(value['independent_acceptance'])

    def test_private_master_binding_preserves_original_code_and_all_default_arguments(self):
        module=constructor();old_chain=module.chain;old_prod=old_chain.production
        identity=str(uuid.uuid4());private=fixture.contractor_constructor(module,identity)
        self.assertIs(private.__code__,module.two_size_fixture.__code__)
        self.assertIs(module.chain,old_chain);self.assertIs(module.chain.production,old_prod)
        self.assertEqual(private('cursor',date(2026,11,1),'label',size_quantities=[('S',10)]),
            (identity,'cursor',date(2026,11,1),'label',6,4,[('S',10)],None,None,None))
        self.assertEqual(module.two_size_fixture(None,None,None)[0],old_prod.CONTRACTOR)

    def test_existing_mandor_wrong_constructor_global_or_noncanonical_identity_refuses(self):
        for mode in ('same','global','invalid'):
            module=constructor();identity=str(uuid.uuid4())
            if mode=='same':identity=module.chain.production.CONTRACTOR
            elif mode=='global':module=SimpleNamespace(chain=SimpleNamespace(production=module.chain.production),
                two_size_fixture=module.two_size_fixture)
            else:identity='not-a-mandor-uuid'
            with self.subTest(mode=mode),self.assertRaises(ValueError):fixture.contractor_constructor(module,identity)

    def test_missing_actual_parent_refuses_before_any_domain_import_or_cursor_use(self):
        from cp7_accessory_nonpayable import admission
        original=builtins.__import__
        def guarded(name,*args,**kwargs):
            if name.startswith(('cp6_','cp7_p21_','cp7_invoice_')):raise AssertionError('DOMAIN_IMPORT_BEFORE_PARENT')
            return original(name,*args,**kwargs)
        with ExitStack()as scope:
            for name in('PARENT_HEAD','PARENT_TREE','PARENT_RUN','PARENT_JOB','PARENT_RECEIPT'):
                scope.enter_context(patch.object(admission,name,None))
            scope.enter_context(patch.object(builtins,'__import__',guarded))
            with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
                cases.cases(object(),date(2026,11,1),{})

    def test_read_only_source_control_has_nine_unique_cases_and_no_runtime_credit(self):
        value=cases.source_controls()
        self.assertEqual(len(set(value['case_ids'])),9);self.assertEqual(value['actual_Native_cases'],0)
        self.assertEqual(value['actual_SQL_executed'],0)
        self.assertFalse(value['inverse_Auth_two_session_browser_qualification_complete'])
        self.assertEqual(value['fixture_sources']['source_files'],7)

class FailedNativeObservationControls(unittest.TestCase):
    def setUp(self):
        self.temporary=TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.events=[]
        self.before=dict(actual_all22={str(i):[]for i in range(22)},
            full_data_and_sequences={'erp.ledger':[0,'before-hash'],'erp.unchanged':[1,'same-hash'],
                'auth.users':[0,'before-auth-hash'],'sequence:erp.journal':['1',True]})
        self.after_data={'erp.ledger':[1,'after-hash'],'erp.unchanged':[1,'same-hash'],
            'auth.users':[1,'after-auth-hash'],'sequence:erp.journal':['2',True]}
        self.raw_row='{"debit": 123456789012.123456, "credit": 0.00}'
        class SQL(str):
            def format(self,identifier):return SQL(self.replace('{}',identifier))
        def rows(cur):self.events.append('catalog');return self.before['actual_all22']
        def data(cur):self.events.append('data');return self.after_data
        self.catalog=SimpleNamespace(_catalog_rows=rows,_data=data,_catalog=lambda cur:nullcontext(),
            sql=SimpleNamespace(SQL=SQL,Identifier=lambda *parts:'.'.join('"'+p+'"'for p in parts)))
        self.bc=ModuleType('cp6_bc_probe')
        self.bc.api=SimpleNamespace(admin=lambda cur:self.events.append('admin'))
        self.control=SimpleNamespace(product_catalog=lambda cur:nullcontext())
        package=ModuleType('_afui_failure_observation_test');package.__path__=[]
        assembly=ModuleType(package.__name__+'.assembly')
        assembly.runtime=lambda:(None,None,None,None,self.catalog)
        boundary=ModuleType(package.__name__+'.case_boundary')
        boundary.capture_generated=Mock(return_value={'observed':'passed-operation'})
        boundary.validate=Mock(return_value={'status':'PASS'})
        native=ModuleType(package.__name__+'.native_cases')
        native.boundary=Mock(return_value=self.before)
        package.assembly=assembly;package.case_boundary=boundary;package.native_cases=native
        self.modules=SimpleNamespace(bc=self.bc,control=self.control)
        self.boundary=boundary
        self.patches=patch.dict(sys.modules,{package.__name__:package,
            assembly.__name__:assembly,boundary.__name__:boundary,native.__name__:native,
            'cp6_bc_probe':self.bc})
        self.patches.start();self.addCleanup(self.patches.stop)
        spec=spec_from_file_location(package.__name__+'.qualification_component',
            Path(__file__).with_name('qualification_component.py'))
        self.component=module_from_spec(spec);spec.loader.exec_module(self.component)
        self.component.ROOT=Path(self.temporary.name)
        self.cursor=SimpleNamespace(connection=SimpleNamespace(info=SimpleNamespace(
            transaction_status=SimpleNamespace(name='INTRANS'))),execute=self.execute)

    def execute(self,sql):
        self.events.append(sql)
        if str(sql).startswith('select to_jsonb'):
            self.assertIn('"erp"."ledger"',sql)
            return SimpleNamespace(fetchall=lambda:[(self.raw_row,)])

    def failure_path(self):
        return self.component.ROOT/'cp6-proof/t3/AFUI_NATIVE_FIRST_FAILURE_TEST.json'

    def test_failed_world_is_written_before_rollback_and_original_failure_survives(self):
        error=ValueError('ACTUAL_FINANCIAL_ORACLE_FAILURE')
        def execute(sql):
            if sql.startswith('rollback to savepoint'):
                self.assertTrue(self.failure_path().is_file(),'Failed state was not saved before rollback')
            return self.execute(sql)
        self.cursor.execute=execute
        def operation():self.events.append('operation');raise error
        with self.assertRaises(ValueError)as caught:
            self.component.full_case(self.cursor,'TEST',operation,{},self.control)
        self.assertIs(caught.exception,error)
        self.assertEqual(str(error),'ACTUAL_FINANCIAL_ORACLE_FAILURE')
        saved=json.loads(self.failure_path().read_text())
        self.assertEqual(saved['before'],self.before)
        self.assertEqual(saved['after_operation']['full_data_and_sequences'],self.after_data)
        self.assertEqual(saved['after_operation']['actual_all22'],self.before['actual_all22'])
        self.assertEqual(saved['after_operation']['raw_business_rows'],{'erp.ledger':[self.raw_row]})
        self.assertEqual(saved['after_operation']['full_data_and_sequences']['auth.users'],[1,'after-auth-hash'])
        self.assertEqual(saved['actual_case_credit'],0);self.assertFalse(saved['production_go'])
        self.assertLess(self.events.index('operation'),self.events.index('data'))
        self.assertLess(self.events.index('data'),self.events.index('rollback to savepoint afui_full_current_case'))
        self.assertEqual(self.events[-1],'release savepoint afui_full_current_case')
        self.boundary.capture_generated.assert_not_called()

    def test_aborted_sql_transaction_is_never_queried(self):
        self.cursor.connection.info.transaction_status.name='INERROR'
        original=self.component.retain_failed_case(self.cursor,'TEST',ValueError('PRIMARY'),
            self.before,self.modules,self.catalog)
        self.assertIsNotNone(original);self.assertEqual(self.events,[])
        saved=json.loads(self.failure_path().read_text())
        self.assertEqual(saved['observation_unavailable'],'FAILED_TRANSACTION_NOT_QUERYABLE:INERROR')
        self.assertNotIn('after_operation',saved)

    def test_capture_error_is_retained_without_masking_the_primary_failure(self):
        error=ValueError('PRIMARY')
        self.catalog._data=Mock(side_effect=RuntimeError('read failed'))
        original=self.component.retain_failed_case(self.cursor,'TEST',error,self.before,self.modules,self.catalog)
        self.assertIsNotNone(original);self.assertEqual(str(error),'PRIMARY')
        saved=json.loads(self.failure_path().read_text())
        self.assertEqual(saved['error'],'PRIMARY')
        self.assertEqual(saved['observation_error'],dict(error_type='RuntimeError',error='read failed'))
        self.assertNotIn('after_operation',saved)

    def test_raw_row_failure_keeps_fingerprints_and_original_error_without_more_queries(self):
        error=ValueError('PRIMARY')
        def execute(sql):
            self.events.append(sql)
            if str(sql).startswith('select to_jsonb'):raise RuntimeError('row read failed')
        self.cursor.execute=execute
        result=self.component.retain_failed_case(self.cursor,'TEST',error,self.before,self.modules,self.catalog)
        self.assertIsNotNone(result);self.assertEqual(str(error),'PRIMARY')
        saved=json.loads(self.failure_path().read_text())
        self.assertEqual(saved['after_operation']['full_data_and_sequences'],self.after_data)
        self.assertEqual(saved['after_operation']['raw_business_rows'],{})
        self.assertEqual(saved['observation_error']['error'],'row read failed')
        self.assertEqual(len([e for e in self.events if str(e).startswith('select to_jsonb')]),1)

    def test_capture_or_disk_failure_does_not_replace_original_or_prevent_rollback(self):
        error=ValueError('PRIMARY')
        self.catalog._data=Mock(side_effect=RuntimeError('read failed'))
        with patch.object(self.component,'save',side_effect=OSError('disk unavailable')):
            with self.assertRaises(ValueError)as caught:
                self.component.full_case(self.cursor,'TEST',lambda:(_ for _ in ()).throw(error),{},self.control)
        self.assertIs(caught.exception,error);self.assertEqual(str(error),'PRIMARY')
        self.assertEqual(self.events[-2:],['rollback to savepoint afui_full_current_case',
            'release savepoint afui_full_current_case'])
        self.assertTrue(any('SAVE_FAILED:disk unavailable'in note for note in error.__notes__))

    def test_success_path_does_not_take_an_extra_failed_world_snapshot(self):
        with patch.object(self.component,'retain_failed_case')as failed:
            result=self.component.full_case(self.cursor,'TEST',lambda:{'status':'PASS'},{},self.control)
        self.assertEqual(result['status'],'PASS');failed.assert_not_called()
        self.assertFalse(self.failure_path().exists())


if __name__=='__main__':unittest.main()
