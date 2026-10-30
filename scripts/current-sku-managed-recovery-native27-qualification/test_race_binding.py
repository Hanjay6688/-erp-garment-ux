"""Real module-loading regression for c397's unused schedule; no DB calls."""
from pathlib import Path
from types import FunctionType
from unittest.mock import patch
import importlib.util
import sys
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
binding=load('sku27_route_test_binding',HERE/'race_binding.py')


class ActualLoader(unittest.TestCase):
    def setUp(self):
        self.previous_path=list(sys.path);sys.path.insert(0,str(ROOT/'scripts'))
        context=load('sku27_route_test_fence',HERE/'source_context.py')
        self.context=context.fenced_source_read();self.guard=self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None,None,None);sys.path[:]=self.previous_path
        self.assertEqual(self.guard['attempts'],[]);self.assertEqual(self.guard['network_nonGit_attempts'],[])

    def test_actual_current_loader_imports_complete_correct_module(self):
        # Execute the real caller's one loader assignment with its actual
        # module globals; this is the callee selected at runtime, not a lookup
        # invented independently from the concurrency function.
        import ast
        caller=load('sku27_route_test_actual_concurrency',HERE/'concurrency.py')
        text,_=binding.deriver().derive('concurrency')
        f=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        statement=next(n for n in f.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='business'for t in n.targets))
        scope=dict(vars(caller));exec(compile(ast.Module(body=[statement],type_ignores=[]),'<real caller loader statement>','exec'),scope)
        proof=binding.require_runtime_module(scope['business'])
        self.assertEqual(proof['status'],'ACTUAL_CURRENT_RACE_MODULE_BOUND_BEFORE_CALLBACKS')
        self.assertTrue(proof['compiled_function_identity']);self.assertEqual(proof['actual_two_session_races'],0)

    def test_exact_c397_old_route_and_old_runtime_module_refuse(self):
        d=binding.deriver();old=d.legacy.derive('concurrency')[0].replace(d.OLD_NS,d.NS)
        self.assertIn("ROOT / 'scripts/current-sku-combined-fixture-followup/races.py'",old)
        with self.assertRaisesRegex(ValueError,'CURRENT_RACE_CALLER_ROUTE_REQUIRED'):binding._route(old)
        business=load('sku27_route_test_old_c397',ROOT/'scripts/current-sku-combined-fixture-followup/races.py')
        with self.assertRaisesRegex(ValueError,'ACTUAL_CURRENT_RACE_CODE_REQUIRED'):binding.require_runtime_module(business)

    def test_missing_runtime_gate_and_unknown_destination_refuse(self):
        text,_=binding.deriver().derive('concurrency')
        with self.assertRaisesRegex(ValueError,'ACTUAL_RACE_CALLABLE_GATE_REQUIRED'):
            binding._route(text.replace('race_binding.require_runtime_module(business)','dict()'))
        with self.assertRaisesRegex(ValueError,'CURRENT_RACE_CALLER_ROUTE_REQUIRED'):
            binding._route(text.replace(binding.LOADER,binding.LOADER.replace('/races.py','/foreign.py')))

    def test_derived_proof_schedule_and_runtime_code_cannot_be_substituted(self):
        business=load('sku27_route_test_current',HERE/'races.py')
        with patch.object(business,'SKU27_DERIVATION',{}),self.assertRaisesRegex(ValueError,'CURRENT_RACE_DERIVATION_REQUIRED'):
            binding.require_runtime_module(business)
        with patch.object(business,'schedule',None),self.assertRaisesRegex(ValueError,'RACE_SCHEDULE_GLOBAL_REQUIRED'):
            binding.require_runtime_module(business)
        schedule=business.schedule
        code=compile('def run(*args,**kwargs):return None',str(HERE/'race_schedule.py'),'exec')
        scope={};exec(code,scope)
        with patch.object(schedule,'run',scope['run']),self.assertRaisesRegex(ValueError,'RACE_SCHEDULE_CODE_REQUIRED:run'):
            binding.require_runtime_module(business)
        other=FunctionType(business.exercise.__code__,dict(business.exercise.__globals__,schedule=None))
        with patch.object(business,'exercise',other),self.assertRaisesRegex(ValueError,'RACE_SCHEDULE_GLOBAL_REQUIRED'):
            binding.require_runtime_module(business)
        self.assertEqual(binding.require_runtime_module(business)['status'],'ACTUAL_CURRENT_RACE_MODULE_BOUND_BEFORE_CALLBACKS')


if __name__=='__main__':unittest.main()
