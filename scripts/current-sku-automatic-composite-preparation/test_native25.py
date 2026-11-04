"""Source, plan and closed-entry checks; no ERP callback is executed."""
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import subprocess
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path=None):
    spec = importlib.util.spec_from_file_location('automatic25_control_' + name, path or HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoInspection:
    def __getattribute__(self, name):
        raise AssertionError('Closed admission or callback construction inspected a caller')


class Native25Preparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.component = load('component')
        cls.suite = load('native_suite')
        cls.assembly = load('assembly')
        cls.money = load('money_component', ROOT / 'scripts/current-sku-money-composite-preparation/component.py')
        cls.reference = json.loads((ROOT / 'scripts/current-sku-money-composite-preparation/SOURCE_REFERENCE.json').read_bytes())
        cls.plan = json.loads((HERE / 'PREPARED_NATIVE25_PLAN.json').read_bytes())

    def test_exact_component_routes_preserve_all_retained_money_assertions_and_recovery(self):
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                      self.reference['candidate_tree'] + ':' + self.component.ORIGINAL])
        before, _ = self.money.derive(raw)
        after, proof = self.component.derive(raw)
        self.assertEqual(proof['exact_additional_routes'], 5)
        self.assertTrue(proof['complete_money_component_recovered'])
        def functions(source):
            return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
        original, derived = functions(before), functions(after)
        self.assertEqual(set(original), set(derived))
        for name in original:
            if name != 'exercise':
                self.assertEqual(ast.dump(original[name]), ast.dump(derived[name]), name)
        self.assertEqual([ast.dump(node) for node in ast.walk(original['exercise']) if isinstance(node, ast.Assert)],
                         [ast.dump(node) for node in ast.walk(derived['exercise']) if isinstance(node, ast.Assert)])
        self.assertIn("with _REPORT_IO.group_scope(native.r1),_CASE_OUTPUT.scope(native,'native'),exact_public_catalog", after)
        self.assertIn('_COMPLETE_ORIGINALS.copy_exact(original,destination/name,', after)
        self.assertIn("report['status']='INCOMPLETE'\n    _BROWSER_ACCESS.run(product,state,verify,report)", after)
        self.assertNotIn('raw=original.read_bytes();(destination/name).write_bytes(raw)', after)
        with self.assertRaisesRegex(ValueError, 'EXACT_NINETEEN_COMPONENT'):
            self.component.derive(raw + b'\n')

    def test_original_nineteen_callback_objects_and_order_remain_exact(self):
        ids = tuple(self.reference['native_case_ids'])
        callbacks = [(key, object()) for key in ids]
        business = SimpleNamespace(IDS=ids, cases=lambda *_: callbacks,
                                   n=NoInspection(), f=NoInspection(), canonical=object(), legacy_post=object())
        combined, _ = self.suite.bind(business, NoInspection(), NoInspection(), NoInspection())
        operations = combined.cases(NoInspection(), NoInspection())
        self.assertEqual(tuple(key for key, _ in operations), tuple(self.plan['case_ids']))
        self.assertEqual(operations[:19], callbacks)
        self.assertTrue(all(callable(operation) for _, operation in operations[19:]))
        self.assertIs(combined.n, business.n)
        self.assertIs(combined.canonical, business.canonical)
        business.IDS = tuple('duplicate' for _ in range(19))
        with self.assertRaisesRegex(ValueError, 'EXACT_RETAINED_NINETEEN'):
            self.suite.bind(business, NoInspection(), NoInspection(), NoInspection())

    def test_closed_component_and_each_partial_gate_refuse_before_caller_access(self):
        gate = self.assembly.admission
        for missing in (None, *gate.GATES):
            values = {name: None if missing is None or name == missing else 'CONTROL_ONLY' for name in gate.GATES}
            with self.subTest(missing=missing), patch.multiple(gate, **values):
                with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                    self.component.load_prepared(self.assembly, *[NoInspection() for _ in range(5)])

    def test_invoice_helper_shapes_come_from_original_native_declarations(self):
        def declaration(path, name):
            node = next(node for node in ast.parse(path.read_bytes()).body if isinstance(node, ast.FunctionDef) and node.name == name)
            scope = {}
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(path) + '::shape-only', 'exec'), scope)
            return scope[name]
        invoices = ROOT / 'scripts/cp7_invoice_cases.py'
        modules = SimpleNamespace(invoice=SimpleNamespace(**{name: declaration(invoices, name) for name in ('payload', 'finalize', 'reverse')}),
                                  bc=SimpleNamespace(internal=declaration(ROOT / 'scripts/cp6_bc_probe.py', 'internal')))
        proof = self.suite.invoices.source_contract(modules)
        self.assertEqual(proof['original_invoice_helper_shapes'], 4)
        modules.invoice.finalize = lambda cursor: None
        with self.assertRaises(TypeError):
            self.suite.invoices.source_contract(modules)

    def test_all_new_function_and_permission_constants_have_retained_native_sources(self):
        source = json.loads((HERE / 'PREREQUISITE_SOURCE.json').read_bytes())
        prerequisites = self.suite.prerequisites
        self.assertEqual(set(prerequisites.FUNCTIONS), set(source['functions']))
        literal_keys = set().union(*(set(item['literal_permission_keys']) for item in source['permission_sources'].values()))
        needed = set().union(*(set(keys) for keys in prerequisites.ACTOR_PERMISSIONS.values()))
        self.assertLessEqual(needed, literal_keys)
        self.assertEqual(set(prerequisites.ACTOR_PERMISSIONS['supplier_invoice_owner']),
                         set(source['permission_sources']['cp7_invoice.access_now()']['literal_permission_keys']))
        self.assertEqual(self.plan['native_cases_planned'], len(self.plan['case_ids']))
        self.assertEqual(self.plan['actual_ERP_cases'], 0)
        self.assertTrue(self.plan['current_Auth_HTTP_races_browser_and_full_owning_runtime_pending'])

    def test_complete_package_retains_dynamic_counts_and_every_recovery_function(self):
        package = load('package')
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        before, _ = load('money_package', package.RETAINED).derive(raw)
        after, proof = package.derive(raw)
        self.assertTrue(proof['complete_money_engine_recovered'])
        original = {node.name: node for node in ast.parse(before).body if isinstance(node, ast.FunctionDef)}
        derived = {node.name: node for node in ast.parse(after).body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(set(original), set(derived))
        changed = {name for name in original if ast.dump(original[name]) != ast.dump(derived[name])}
        self.assertEqual(changed, {'run_inner'})
        self.assertIn("report['actual_Native_cases']=cases[runner.CASE]['actual_Native_cases']", after)
        self.assertIn("report['actual_Auth_HTTP_cases']=0", after)
        self.assertIn("report['actual_two_session_races']=0", after)
        self.assertIn("report['actual_browser_cases']=cases[runner.CASE]['actual_browser_cases']", after)
        self.assertIn("report['real_Auth_browser_claim']=cases[runner.CASE]['real_Auth_browser_claim']", after)


if __name__ == '__main__':
    unittest.main()
