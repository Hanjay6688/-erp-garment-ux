"""Component orchestration controls; explicit doubles earn zero Native credit."""
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,unittest

ROOT=Path(__file__).resolve().parents[2]

def module():
    path=ROOT/'scripts/cp7_current_s03_sku_s05/composition.py'
    spec=importlib.util.spec_from_file_location('prepared_complete_assembly_control',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class AssemblyControls(unittest.TestCase):
    def setUp(self):
        self.module=module();self.events=[];self.data={'rows':[1],'sequence':7}
        self.financial_state=dict(sources={'financial':'exact'},parent_binding='actual-bound-parent',
            after={'actual':'parent-catalog'},preinstall_data_and_sequences={'rows':[],'sequence':1})
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

if __name__=='__main__':unittest.main()
