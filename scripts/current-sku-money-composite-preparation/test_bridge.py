"""Source/interface models only; no ERP, acceptance receipt, or install is run."""
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('money_composite_control_subject',HERE/'assembly.py')
assembly=importlib.util.module_from_spec(spec);spec.loader.exec_module(assembly)


class Forbidden:
    def __getattribute__(self,name):raise AssertionError('closed gate inspected object: '+name)


def function(source,name,namespace):
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'explicit-interface-model','exec'),namespace)
    return namespace[name]


class CurrentMoneyBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference,cls.moving,cls.money,cls.proof=assembly.prepared_sources()
        cls.original=assembly.git(assembly.ROOT,'show',cls.reference['candidate_tree']+':scripts/cp7_sku_cost_components/composition.py')

    def test_both_exact_derivations_recover_originals(self):
        self.assertEqual(self.proof['moving']['counted_changes'],6)
        self.assertEqual(self.proof['money']['counted_changes'],5)
        self.assertTrue(self.proof['moving']['original_recovered_exactly'])
        self.assertTrue(self.proof['money']['original_recovered_exactly'])
        self.assertEqual(assembly.money_derive.derive(self.original)[0],self.money)
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_COMPOSITION_REQUIRED'):
            assembly.money_derive.derive(self.original+b'\n')

    def test_every_financial_verifier_and_inverse_body_is_unchanged(self):
        before={n.name:n for n in ast.parse(self.original).body if isinstance(n,ast.FunctionDef)}
        after={n.name:n for n in ast.parse(self.money).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(set(before),set(after));changed=set()
        for name in before:
            self.assertEqual(ast.dump(before[name].args),ast.dump(after[name].args),name)
            if ast.dump(before[name])!=ast.dump(after[name]):changed.add(name)
        self.assertEqual(changed,{'sources','binding','install_delta'})
        self.assertEqual(len(set(before)-changed),7)
        self.assertIn('parent_verified=parent().verify(cur,state[\'predecessor\'])',self.money)

    def test_closed_and_partial_gates_refuse_before_any_receipt_or_module_access(self):
        a=assembly.admission
        self.assertTrue(all(getattr(a,name)is None for name in a.GATES))
        with self.assertRaisesRegex(ValueError,'ACTUAL_MANDOR17_MONEY19_AND_OWNING_ENTRY_PENDING'):
            assembly.load_prepared(Forbidden(),Forbidden(),Forbidden(),Forbidden())
        for missing in a.GATES:
            values={name:None if name==missing else 'explicit gate model'for name in a.GATES}
            with self.subTest(missing=missing),patch.multiple(a,**values):
                with self.assertRaisesRegex(ValueError,'ACTUAL_MANDOR17_MONEY19_AND_OWNING_ENTRY_PENDING'):
                    assembly.load_prepared(Forbidden(),Forbidden(),Forbidden(),Forbidden())

    def test_whole_nested_mandor_and_moving_state_is_bound(self):
        digest=lambda v:assembly.admission.pin(assembly.admission.canonical(v))
        current=function(self.money,'binding',{})
        original=function(self.original,'binding',{})
        parent={k:{}for k in ('sources','before','after','parent_binding','definitions','originals',
            'preinstall_data_and_sequences','preuse_data_and_sequences')}
        parent['parent']={'complete_afui':{'roles':{'private_role':'expected'},'sequences':{'one':13}},
            'complete_mandor':{'native_identity':['owner','raw_acl']}}
        changed=deepcopy(parent);changed['parent']['complete_afui']['sequences']['one']=14
        catalog=SimpleNamespace(digest=digest);proof={'actual_model_only':True}
        self.assertEqual(original(catalog,parent,proof),original(catalog,changed,proof))
        self.assertNotEqual(current(catalog,parent,proof),current(catalog,changed,proof))
        changed=deepcopy(parent);changed['parent']['complete_mandor']['native_identity'][1]='changed_raw_acl'
        self.assertNotEqual(current(catalog,parent,proof),current(catalog,changed,proof))

    def test_changed_full_current_parent_refuses_before_any_ddl_builder(self):
        actual={'functions':{'untouched':'changed'},'roles':{'private_role':'expected'}}
        expected={'functions':{'untouched':'expected'},'roles':{'private_role':'expected'}}
        seen=[]
        catalog=SimpleNamespace(_catalog_rows=lambda cur:actual,_data=lambda cur:{'rows':'modeled'})
        prior=SimpleNamespace(atomic=lambda cur:nullcontext(),
            predecessor=SimpleNamespace(predecessor=SimpleNamespace(_locks=lambda cur:seen.append('lock'))))
        parent=SimpleNamespace(verify=lambda cur,state:seen.append('verify')or{'model':True})
        def forbidden(*args):raise AssertionError('unexpected DDL/product construction')
        run=function(self.money,'install_delta',dict(runtime=lambda:(None,None,None,prior,catalog),
            parent=lambda:parent,prepared=forbidden))
        with self.assertRaisesRegex(ValueError,'FULL_CURRENT_PARENT_CATALOGUE_REQUIRED'):
            run(Forbidden(),dict(after=expected))
        self.assertEqual(seen,['lock','verify'])

    def test_gate_refuses_old_six_case_or_aggregate_or_synthetic_evidence(self):
        a=assembly.admission;cases=self.reference['native_case_ids']
        # In-memory protocol examples only. No accepted Root file is created.
        parent=dict(status='ROOT_VERIFIED_CURRENT_MANDOR17_ALL5',head='model-parent',tree='model-parent-tree',
            actual_Native_cases=9,actual_Native_session_cases=4,actual_Auth_HTTP_cases=2,actual_browser_cases=2,
            actual_business_cases=17,complete17_qualified=True,package_all_five=True,prior_runs_aggregated=False,
            assembly_source={'model_only':True},production_go=False,independent_acceptance=False,
            qualified_current_Mandor_sources={'explicit_protocol_model':True})
        money=dict(status='ROOT_VERIFIED_CURRENT_SKU_MONEY_NATIVE19_ALL5',head='model-child',tree='model-child-tree',
            actual_Native_cases=19,actual_Auth_HTTP_cases=0,actual_browser_cases=0,complete19_qualified=True,
            native_case_ids=cases,package_all_five=True,prior_runs_aggregated=False,production_go=False,
            independent_acceptance=False,qualified_SKU_cost_money_sources={'explicit_protocol_model':True})
        def controls(candidate):
            pr,mr=a.canonical(parent),a.canonical(candidate)
            values=dict(PARENT_HEAD=parent['head'],PARENT_TREE=parent['tree'],PARENT_ROOT_PIN=a.pin(pr),
                PARENT_SOURCE_PIN=a.pin(a.canonical(parent['qualified_current_Mandor_sources'])),
                PARENT_MODULE_PIN=parent['assembly_source'],SKU_HEAD=money['head'],SKU_TREE=money['tree'],
                SKU_ROOT_PIN=a.pin(mr),SKU_SOURCE_PIN=a.pin(a.canonical(money['qualified_SKU_cost_money_sources'])),
                RUNTIME_ENTRY='explicit protocol model only')
            return pr,mr,values
        mutations=[dict(actual_Native_cases=6),dict(prior_runs_aggregated=True),dict(package_all_five=False),
            dict(synthetic_receipt_not_an_actual_qualification=True),dict(native_case_ids=cases[:-1]),
            dict(qualified_SKU_cost_money_sources={'changed':True})]
        for changed in mutations:
            pr,mr,values=controls(dict(money,**changed))
            with self.subTest(changed=list(changed)),patch.multiple(a,**values),self.assertRaises(ValueError):
                a.admitted(pr,mr,cases)
        self.assertTrue(all(getattr(a,name)is None for name in a.GATES))


if __name__=='__main__':unittest.main()
