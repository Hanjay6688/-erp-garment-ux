"""Component orchestration controls; explicit doubles earn zero Native credit."""
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,sys,unittest

ROOT=Path(__file__).resolve().parents[2]

def module():
    path=ROOT/'scripts/cp7_current_s03_sku_s05/composition.py'
    spec=importlib.util.spec_from_file_location('prepared_complete_assembly_control',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class AssemblyControls(unittest.TestCase):
    def setUp(self):
        self.module=module();self.events=[];self.data={'rows':[1],'sequence':7}
        self.financial_state=dict(sources={'financial':'exact'},parent_binding='actual-bound-parent',
            after={'actual':'parent-catalog'},preinstall_data_and_sequences={'rows':[],'sequence':1},
            preuse_data_and_sequences=deepcopy(self.data))
        self.reader_state=dict(sources={'reader':'exact'},parent_sources=self.financial_state['sources'],
            parent_binding='actual-bound-reader',before=self.financial_state['after'],
            after={'actual':'parent-plus-reader-catalog'},data=deepcopy(self.data))
        def event(name,result):
            def call(*args):self.events.append(name);return result
            return call
        catalog=SimpleNamespace(digest=lambda value:sha256(json.dumps(value,sort_keys=True).encode()).hexdigest(),
            _data=lambda cur:deepcopy(self.data),_lock_tables=event('lock_tables',None))
        base=SimpleNamespace(atomic=lambda cur:nullcontext(),predecessor=SimpleNamespace(
            predecessor=SimpleNamespace(_locks=event('native_locks',None))))
        self.financial=SimpleNamespace(sources=lambda:self.financial_state['sources'],
            verify=event('verify_financial',{'status':'ACTUAL_PARENT'}),
            runtime=lambda:(None,None,None,base,catalog),install=event('install_financial',self.financial_state),
            rollback_preuse=event('inverse_financial',{'status':'ORIGINAL_RESTORED'}))
        self.reader=SimpleNamespace(sources=lambda:self.reader_state['sources'],
            install_delta=event('install_reader',deepcopy(self.reader_state)),
            verify=event('verify_reader',{'status':'S05_EXACT_ADDITIVE_READER_ALL22'}),
            uninstall_delta=event('inverse_reader',{'status':'S03_RESTORED'}))
        self.parts_patch=patch.object(self.module,'parts',return_value=(self.financial,self.reader));self.parts_patch.start();self.addCleanup(self.parts_patch.stop)
        self.sources_patch=patch.object(self.module,'sources',return_value={'contract':self.module.CONTRACT,'actual':'complete-source'});self.sources_patch.start();self.addCleanup(self.sources_patch.stop)

    def test_full_install_keeps_reader_after_verification(self):
        state=self.module.install(object())
        self.assertEqual(self.events[:3],['install_financial','verify_financial','install_reader'])
        self.assertIn('verify_reader',self.events);self.assertNotIn('inverse_reader',self.events)
        self.assertEqual(state['reader'],self.reader_state)
        self.assertTrue(self.module.verify(object(),state)['reader_remains_installed'])

    def test_later_business_rows_can_change_but_preuse_inverse_refuses_before_DDL(self):
        state=self.module.install_delta(object(),self.financial_state);self.events.clear();self.data['rows'].append(2)
        self.assertTrue(self.module.verify(object(),state)['reader_remains_installed'])
        with self.assertRaisesRegex(ValueError,self.module.USED_ERROR):self.module.rollback_preuse(object(),state)
        self.assertNotIn('inverse_reader',self.events);self.assertNotIn('inverse_financial',self.events)

    def test_sequence_only_use_refuses_before_DDL(self):
        state=self.module.install_delta(object(),self.financial_state);self.events.clear();self.data['sequence']+=1
        with self.assertRaisesRegex(ValueError,self.module.USED_ERROR):self.module.rollback_preuse(object(),state)
        self.assertNotIn('inverse_reader',self.events)

    def test_unused_inverse_orders_reader_before_financial_parent(self):
        state=self.module.install_delta(object(),self.financial_state);self.events.clear()
        restored=self.module.rollback_preuse(object(),state)
        # Consumed by the unchanged owning package engine after preuse inverse.
        self.assertIs(restored['reader']['used_guard_before_DDL'],True)
        self.assertLess(self.events.index('lock_tables'),self.events.index('inverse_reader'))
        self.assertLess(self.events.index('inverse_reader'),self.events.index('inverse_financial'))

    def test_changed_parent_source_and_component_chain_refuse(self):
        state=self.module.install_delta(object(),self.financial_state)
        changed=deepcopy(state);changed['reader']['before']={'unreviewed':'catalog'}
        with self.assertRaisesRegex(ValueError,'STATE_CHAIN_CHANGED'):self.module.verify(object(),changed)
        changed=deepcopy(state);changed['component_binding']='unknown'
        with self.assertRaisesRegex(ValueError,'COMPONENT_BINDING_CHANGED'):self.module.verify(object(),changed)
        changed=deepcopy(state);changed['sources']={'unknown':'source'}
        with self.assertRaisesRegex(ValueError,'ACTUAL_SOURCE_CHANGED'):self.module.verify(object(),changed)

    def test_coordinated_guard_snapshot_changes_cannot_relabel_used_rows_as_preuse(self):
        state=self.module.install_delta(object(),self.financial_state)
        changed=deepcopy(state)
        changed['reader']['data']['rows'].append(2)
        changed['preuse_data_and_sequences']['rows'].append(2)
        with self.assertRaisesRegex(ValueError,'COMPONENT_BINDING_CHANGED'):self.module.verify(object(),changed)
        changed=deepcopy(state)
        changed['financial_parent']['preinstall_data_and_sequences']['sequence']=9
        changed['preinstall_data_and_sequences']['sequence']=9
        with self.assertRaisesRegex(ValueError,'COMPONENT_BINDING_CHANGED'):self.module.verify(object(),changed)

class NestedManifestControls(unittest.TestCase):
    def source(self):
        path=Path(__file__).resolve().parent/'persistent_source.py'
        spec=importlib.util.spec_from_file_location('current_nested_product_source_control',path)
        result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

    def test_current_three_nested_sources_admit_without_ERP_import(self):
        source=self.source();proof=source.product_sources()
        self.assertEqual(proof['source_files'],3);self.assertEqual(proof['actual_ERP_cases'],0)

    def test_stale_README_and_extra_manifest_path_refuse(self):
        source=self.source();actual=source.raw
        def changed_readme(name):
            return actual(name)+b'changed README'if name==source.PRODUCT+'README.md'else actual(name)
        with patch.object(source,'raw',side_effect=changed_readme):
            with self.assertRaisesRegex(ValueError,'NESTED_PRODUCT_SOURCE_CHANGED:.*README'):
                source.product_sources()
        def extra_path(name):
            raw=actual(name)
            if name==source.PRODUCT+'SOURCE.json':
                value=json.loads(raw);value['files']['scripts/unreviewed.py']='0'*64
                return json.dumps(value).encode()
            return raw
        with patch.object(source,'raw',side_effect=extra_path):
            with self.assertRaisesRegex(ValueError,'NESTED_PRODUCT_SOURCE_KEYS_CHANGED'):
                source.product_sources()

class PermanentReadObservationControls(unittest.TestCase):
    """A reader interval must exclude setup writes and catch actual changes."""
    def setUp(self):
        path=Path(__file__).resolve().parent/'persistent_financial.py'
        spec=importlib.util.spec_from_file_location('permanent_read_interval_control',path)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.data={'erp.app_users':[0,'no-owner-fixture'],'sequence:business':['7',True]}
        self.catalog={str(i):{}for i in range(22)};self.events=[];self.mutation=None
        def owner(cursor):
            self.events.append('prepare_owner');self.data['erp.app_users']=[1,'owner-fixture'];return 'fixture-owner'
        def snapshot(cursor):
            self.events.append('observe_data');return deepcopy(self.data)
        def execute(sql,args):
            self.events.append('actual_read')
            self.assertIn('select public.erp_cp7_get_accessory_standard_report_v1(',sql)
            if self.mutation=='row':self.data['erp.app_users']=[2,'unexpected-reader-write']
            if self.mutation=='sequence':self.data['sequence:business']=['8',True]
            if self.mutation=='catalog':self.catalog['0']={'unexpected':'reader-DDL'}
            version='wrong'if self.mutation=='response'else'cp7.accessory-standard-report.v1'
            return SimpleNamespace(fetchone=lambda:({'contract_version':version,'business_DML':False},))
        self.cursor=SimpleNamespace(execute=execute,connection=SimpleNamespace(
            info=SimpleNamespace(transaction_status=SimpleNamespace(name='INTRANS'))))
        hp=SimpleNamespace(owner=owner,auth=SimpleNamespace(actor=lambda cur,who:self.assertEqual(who,'fixture-owner')))
        self.core=SimpleNamespace(f=SimpleNamespace(admin=lambda cur:None,hp=hp))
        catalog=SimpleNamespace(_catalog_rows=lambda cur:deepcopy(self.catalog),_data=snapshot)
        self.complete=SimpleNamespace(runtime=lambda:(None,None,None,None,catalog),verify=lambda cur,state:None)
        helper=SimpleNamespace(control=SimpleNamespace(product_catalog=lambda cur:nullcontext()))
        context=patch.dict(sys.modules,{'cp7_p21_current_chain_rehearsal_probe':SimpleNamespace(helper=helper)})
        context.start();self.addCleanup(context.stop)

    def test_owner_fixture_precedes_first_read_observation(self):
        result=self.module.read_kept_reader(self.cursor,'2026-11-02',self.core,self.complete,{})
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(self.events,['prepare_owner','observe_data','actual_read','observe_data'])
        self.assertEqual(result['before'],result['after'])
        self.assertEqual(result['before']['full_data_and_sequences']['erp.app_users'],[1,'owner-fixture'])

    def test_actual_reader_row_sequence_and_catalog_changes_still_refuse(self):
        for mutation in ('row','sequence','catalog'):
            with self.subTest(mutation=mutation):
                self.data={'erp.app_users':[0,'no-owner-fixture'],'sequence:business':['7',True]}
                self.catalog={str(i):{}for i in range(22)};self.mutation=mutation
                with self.assertRaisesRegex(ValueError,'PERMANENT_S05_READ_CHANGED_ALL22_ROWS_OR_ANY_SEQUENCE'):
                    self.module.read_kept_reader(self.cursor,'2026-11-02',self.core,self.complete,{})

    def test_invalid_reader_response_still_refuses(self):
        self.mutation='response'
        with self.assertRaisesRegex(ValueError,'PERMANENT_S05_ACTUAL_NORMAL_OWNER_READER_REQUIRED'):
            self.module.read_kept_reader(self.cursor,'2026-11-02',self.core,self.complete,{})

if __name__=='__main__':unittest.main()
