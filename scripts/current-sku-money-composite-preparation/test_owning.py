"""Exact source and closed-entry controls; no native callback is executed."""
from pathlib import Path
from unittest.mock import patch
import ast
import importlib.util
import unittest

HERE=Path(__file__).resolve().parent


def load(name):
    spec=importlib.util.spec_from_file_location('money_owning_control_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class OwningMoneyPreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge=load('assembly');cls.component=load('component');cls.package=load('package')
        cls.ref,_,_,_=cls.bridge.prepared_sources()

    def raw(self,name):return self.bridge.git(self.bridge.ROOT,'show',self.ref['candidate_tree']+':'+name)

    def test_exact_nineteen_component_routes_preserve_every_assertion(self):
        raw=self.raw(self.component.ORIGINAL);source,proof=self.component.derive(raw)
        recovered=source
        for before,after in reversed(self.component.REPLACEMENTS):recovered=recovered.replace(after,before,1)
        self.assertEqual(recovered.encode(),raw)
        self.assertEqual(proof['exact_routes'],5)
        before={n.name:n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        after={n.name:n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(set(before),set(after))
        for name in before:
            self.assertEqual(ast.dump(before[name].args),ast.dump(after[name].args),name)
            if name!='exercise':self.assertEqual(ast.dump(before[name]),ast.dump(after[name]),name)
        self.assertEqual([ast.dump(n)for n in ast.walk(before['exercise'])if isinstance(n,ast.Assert)],
            [ast.dump(n)for n in ast.walk(after['exercise'])if isinstance(n,ast.Assert)])
        with self.assertRaisesRegex(ValueError,'EXACT_NINETEEN_COMPONENT_REQUIRED'):
            self.component.derive(raw+b'\n')

    def test_complete_package_restoration_and_fresh_count_routes(self):
        raw=self.raw(self.package.ORIGINAL);source,proof=self.package.derive(raw)
        self.assertTrue(proof['complete_retained_package_recovered'])
        self.assertTrue(proof['original']['complete_original_recovered'])
        self.assertEqual(proof['original']['exact_routes'],3)
        self.assertEqual(proof['additional_label_routes'],2)
        self.assertIn("product.parent().install,cur)",source)
        self.assertIn("'CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY'",source)
        self.assertIn("report['actual_Auth_HTTP_cases']=0",source)
        self.assertIn("report['actual_two_session_races']=0",source)
        before={n.name:n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        after={n.name:n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(set(before),set(after))
        changed=set()
        for name in before:
            self.assertEqual(ast.dump(before[name].args),ast.dump(after[name].args),name)
            if ast.dump(before[name])!=ast.dump(after[name]):changed.add(name)
        self.assertEqual(changed,{'run_inner'})

    def test_component_all_closed_and_each_partial_admission_refuses_first(self):
        class Forbidden:
            def __getattribute__(self,name):raise AssertionError('closed owning entry inspected '+name)
        a=self.bridge.admission
        self.assertTrue(all(getattr(a,name)is None for name in a.GATES))
        candidates=[{name:None for name in a.GATES}]+[
            {name:None if name==missing else 'EXPLICIT_GATE_CONTROL_ONLY'for name in a.GATES}
            for missing in a.GATES]
        for values in candidates:
            with self.subTest(values=values),patch.multiple(a,**values):
                with self.assertRaisesRegex(ValueError,'ACTUAL_MANDOR17_CANDIDATE_SOURCE_AND_OWNING_ENTRY_PENDING'):
                    self.component.load_prepared(self.bridge,Forbidden(),Forbidden(),Forbidden(),Forbidden())


if __name__=='__main__':unittest.main()
