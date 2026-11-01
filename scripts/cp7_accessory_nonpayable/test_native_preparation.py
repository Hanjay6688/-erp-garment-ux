"""Private fixture binding/parent gate controls; zero actual ERP case credit."""
from datetime import date
from contextlib import ExitStack
from types import ModuleType,SimpleNamespace
from unittest.mock import patch
import builtins,unittest,uuid
from cp7_accessory_nonpayable import native_fixture as fixture,native_cases as cases

def constructor():
    module=ModuleType('synthetic_physical_fixture_only')
    module.chain=SimpleNamespace(production=SimpleNamespace(CONTRACTOR='00000000-0000-4000-8000-000000000001'),other=object())
    exec('def two_size_fixture(cur,today,label,q1=6,q2=4,*,size_quantities=None,clock=None,work_setup=None,service_refs=None):\n'
         ' return (chain.production.CONTRACTOR,cur,today,label,q1,q2,size_quantities,clock,work_setup,service_refs)\n',module.__dict__)
    return module

class NativePreparationControls(unittest.TestCase):
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

    def test_read_only_source_control_has_eight_unique_cases_and_no_runtime_credit(self):
        value=cases.source_controls()
        self.assertEqual(len(set(value['case_ids'])),8);self.assertEqual(value['actual_Native_cases'],0)
        self.assertEqual(value['actual_SQL_executed'],0)
        self.assertFalse(value['inverse_Auth_two_session_browser_qualification_complete'])
        self.assertEqual(value['fixture_sources']['source_files'],7)

if __name__=='__main__':unittest.main()
