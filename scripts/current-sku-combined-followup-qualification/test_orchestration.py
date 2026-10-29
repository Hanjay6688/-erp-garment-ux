"""Synthetic stage ordering/refusal tests; never an actual case result."""
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib.util
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
runner=load('unit_sku_combined_runner',HERE/'runner.py')
plan=load('unit_sku_combined_plan',HERE/'plan.py')


class Orchestration(unittest.TestCase):
    def exercise(self,broken=None):
        events=[];report={};state={'after':{'LOCAL_ONLY':True}}
        def native_group(ids):
            group=dict(counts={'PASS':len(ids)},cases={key:dict(status='PASS',full_boundary_restored=True)for key in ids})
            if len(ids)==7:
                group['cases'][runner.gate.MIXED_CASE].update(preview_caller_zones_checked=runner.gate.CALLER_ZONES,
                  all_preview_fields_equal_across_zones=True,preview_caller_setting_restored=True,posting_function_timezone='UTC')
            return group
        def native(*args):
            events.append('base7');out=args[-2]
            out.update(status='PASS',native=native_group(plan.NATIVE_IDS),used_guard_refused_before_DDL=True,actual_Native_cases=7)
            if broken=='base':out['native']['counts']={'PASS':6}
        def cost(state,first,retained,out):
            events.append('cost3');self.assertEqual(retained['original_sha256'],'a'*64)
            out.update(status='PASS',native=native_group(plan.COST_IDS),group_recovery_supported=False)
            if broken=='cost':out.update(status='INCOMPLETE')
        def follow(*args,**kwargs):
            events.append('callbacks9');out=args[-2]
            self.assertEqual(kwargs['native7']['native']['counts'],{'PASS':7})
            out.update(status='PASS',handoff={'LOCAL_ONLY':True},concurrency=dict(counts={'PASS':9},races={key:dict(status='PASS')for key in plan.RACE_IDS+plan.WAIT_IDS}))
            if broken=='callbacks':out['concurrency']['counts']={'PASS':8}
            out['copy_catalog_admissions']=[dict(all22_groups_equal_original_install=True,exact_catalog_sha256='LOCAL_CATALOG_DIGEST')for _ in range(9)]
            if broken=='copy_digest':out['copy_catalog_admissions'][0]['exact_catalog_sha256']='LOCAL_WRONG_CATALOG'
        def browser(*args):
            events.append('browser4');out=args[-2]
            out.update(status='PASS',browser=dict(status='RUN_COMPLETE',counts={'PASS':4},cases={key:dict(status='PASS')for key in plan.BROWSER_IDS},
              planned_case_ids=list(plan.BROWSER_IDS),host_status='RUN_COMPLETE',host_exit=0,real_auth=True,jwt_signed_by_runtime=False,test_only_usage_grant=False,database_remaining=0,
              cleanup_failures=False,session_leaks=[],console_errors=0,auth_counts={'restored':True},auth_cleanup_failures=[]))
            if broken=='browser':out['browser']['auth_counts']['restored']=False
            if broken=='jwt':out['browser']['jwt_signed_by_runtime']=True
            out['copy_catalog_admissions']=[dict(all22_groups_equal_original_install=True,exact_catalog_sha256='LOCAL_CATALOG_DIGEST')]
        admission=SimpleNamespace(retained=lambda product:{'original_sha256':'a'*64})
        def module(name,path):
            if path.name=='admission.py':return admission
            if path.parent.name=='current-sku-pair-conversion-qualification':return SimpleNamespace(exercise=native)
            if path.parent.name=='current-sku-pair-concurrency-qualification':return SimpleNamespace(exercise=follow)
            if path.name=='plan.py':return plan
            raise AssertionError(str(path))
        product=SimpleNamespace(runtime=lambda:(None,None,None,None,SimpleNamespace(digest=lambda value:'LOCAL_CATALOG_DIGEST')));package=ModuleType('cp7_sku_pair_conversion');package.composition=product
        connection=SimpleNamespace(cursor=lambda:nullcontext(object()))
        sql=SimpleNamespace(connect=lambda url:nullcontext(connection))
        def snapshot(*_):return {'catalog':state['after'],'data':{'LOCAL_SAME_ROW':True}}
        with patch.dict(sys.modules,{'psycopg':sql,'cp7_sku_pair_conversion':package}),patch.object(runner,'load',side_effect=module),\
             patch.object(runner,'cost_group',side_effect=cost),patch.object(runner,'browser_group',side_effect=browser),patch.object(runner,'snapshot',side_effect=snapshot):
            try:runner.exercise(None,None,None,'LOCAL_ONLY',report,state);error=None
            except Exception as e:error=e
        return report,events,error

    def test_base_failure_never_opens_cost_callbacks_or_browser(self):
        _,events,error=self.exercise('base');self.assertIsInstance(error,ValueError);self.assertEqual(events,['base7'])
    def test_cost_failure_never_opens_committed_callbacks_or_browser(self):
        _,events,error=self.exercise('cost');self.assertIsInstance(error,AssertionError);self.assertEqual(events,['base7','cost3'])
    def test_partial_callbacks_never_opens_real_auth_browser(self):
        _,events,error=self.exercise('callbacks');self.assertIsInstance(error,AssertionError);self.assertEqual(events,['base7','cost3','callbacks9'])
    def test_browser_auth_restore_failure_never_becomes_combined_pass(self):
        report,events,error=self.exercise('browser');self.assertIsInstance(error,ValueError);self.assertNotEqual(report['status'],'PASS')
    def test_copy_digest_mismatch_blocks_browser_before_any_real_auth_work(self):
        report,events,error=self.exercise('copy_digest');self.assertIsInstance(error,AssertionError);self.assertEqual(events,['base7','cost3','callbacks9'])
    def test_runtime_signed_jwt_cannot_be_relabelled_real_auth(self):
        report,events,error=self.exercise('jwt');self.assertIsInstance(error,ValueError);self.assertNotEqual(report['status'],'PASS')
    def test_complete_synthetic_scope_counts23_once_keeps_native_cost_and_admin_waits_separate(self):
        report,events,error=self.exercise();self.assertIsNone(error);self.assertEqual(events,['base7','cost3','callbacks9','browser4'])
        self.assertEqual(report['business_counts'],{'PASS':23});self.assertEqual(len(report['business_cases']),23)
        self.assertEqual((report['base_Native_cases'],report['cost_Native_cases'],report['actual_two_session_races'],report['actual_Native_session_permission_waits'],report['actual_browser_cases']),(7,3,3,6,4))
        self.assertEqual(report['actual_Auth_HTTP_cases'],0);self.assertFalse(report['group_recovery_supported'])


if __name__=='__main__':unittest.main()
