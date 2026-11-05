"""Source/interface controls only; no Native callback or database is executed."""
import ast
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assembly = load('automatic_bridge_control_assembly', HERE / 'assembly.py')
native = load('automatic_native_callback_declarations', HERE / 'native_cases.py')


class NoInspection:
    def __getattribute__(self, name):
        raise AssertionError('Closed admission must precede caller inspection')


class SourceAndInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ref = json.loads((HERE / 'SOURCE_REFERENCE.json').read_bytes())
        cls.raw = subprocess.check_output(['git', '-C', str(ROOT), 'show',
            ref['automatic_source']['tree'] + ':scripts/cp7_sku_automatic_pending/composition.py'])
        cls.text, cls.proof = assembly.derivation.derive(cls.raw)

    def test_exact_five_reversible_routes(self):
        restored = self.text
        for before, after in reversed(assembly.derivation.REPLACEMENTS):
            self.assertEqual(restored.count(after), 1)
            restored = restored.replace(after, before, 1)
        self.assertEqual(restored.encode(), self.raw)
        self.assertEqual(self.proof['exact_routes'], 5)

    def test_six_unmodified_verification_and_inverse_functions(self):
        def functions(source):
            return {node.name: ast.dump(node, include_attributes=False)
                    for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
        original, derived = functions(self.raw), functions(self.text)
        expected = ('runtime', 'prepared', 'verify', 'install', 'rollback_delta_preuse', 'rollback_preuse')
        for name in expected:
            with self.subTest(function=name):
                self.assertEqual(original[name], derived[name])
        self.assertIn("USED_ERROR = 'SKU_AUTOMATIC_PENDING_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'", self.text)

    def test_whole_current_parent_state_and_verifier_proof_are_bound(self):
        node = next(node for node in ast.parse(self.text).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'binding')
        ns = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'actual-derived-binding', 'exec'), ns)
        catalog = SimpleNamespace(digest=lambda value: sha256(json.dumps(value, sort_keys=True).encode()).hexdigest())
        state = dict(sources={'money': 1}, before={'all22': 1}, after={'all22': 2},
                     original_current_parent={'Afui': {'native_history': [1, 2]}},
                     before_data={'all_tables': {'opaque_parent_receipt': 'kept'}})
        proof = dict(status='MODEL_PARENT_VERIFIER_ONLY')
        first = ns['binding'](catalog, state, proof)
        for key in ('original_current_parent', 'before_data'):
            changed = deepcopy(state)
            changed[key] = dict(different_current_parent_fact=True)
            self.assertNotEqual(ns['binding'](catalog, changed, proof), first)
        self.assertNotEqual(ns['binding'](catalog, state, dict(status='DIFFERENT_PROOF')), first)

    def test_unknown_installer_source_refuses(self):
        for raw in (self.raw + b'\n', self.raw.replace(b'return money_parent', b'return other_parent', 1)):
            with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_INSTALLER'):
                assembly.derivation.derive(raw)

    def test_all_and_partial_closed_gates_precede_any_caller_access(self):
        gate = assembly.admission
        original = {name: getattr(gate, name) for name in gate.GATES}
        try:
            for selected in (None, *gate.GATES):
                for name in gate.GATES:
                    setattr(gate, name, dict(model_gate=True) if name == selected else None)
                with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                    assembly.load_prepared(*[NoInspection() for _ in range(7)])
        finally:
            for name, value in original.items():
                setattr(gate, name, value)

    def test_original_money44_and_automatic20_are_exact(self):
        ref, _, proof = assembly.prepared_sources()
        self.assertEqual(len(ref['unchanged_money_product']['files']), 44)
        self.assertEqual(len(ref['automatic_files']), 20)
        self.assertTrue(proof['original_recovered_exactly'])
        self.assertEqual(proof['actual_ERP_cases'], 0)

    def test_native_factory_declares_four_cases_without_caller_or_ERP_access(self):
        cases = native.cases(*[NoInspection() for _ in range(5)])
        self.assertEqual(tuple(key for key, _ in cases), native.IDS)
        self.assertEqual(len(set(native.IDS)), 4)
        self.assertTrue(all(callable(operation) for _, operation in cases))

    def test_helper_declarations_bind_all_six_new_caller_shapes(self):
        def declaration(path, name):
            node = next(node for node in ast.parse(path.read_bytes()).body
                        if isinstance(node, ast.FunctionDef) and node.name == name)
            scope = {}
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(path) + '::signature-only', 'exec'), scope)
            return scope[name]
        fixture_path = ROOT / 'scripts/cp7_accessory_nonpayable/native_fixture.py'
        fixture = SimpleNamespace(**{name: declaration(fixture_path, name)
                                    for name in ('prepare', 'post_good', 'actual_time')})
        chain_path = ROOT / 'scripts/cp6_v2620al_review.py'
        modules = SimpleNamespace(bd=SimpleNamespace(
            sized_product=declaration(ROOT / 'scripts/cp6_bd_probe.py', 'sized_product'),
            chain=SimpleNamespace(**{name: declaration(chain_path, name) for name in ('bs_action', 'version')})))
        proof = native.source_contract(fixture, modules)
        self.assertEqual(proof['calls'], 6)
        self.assertEqual(proof['actual_ERP_cases'], 0)
        fixture.prepare = lambda cur, today, modules: None
        with self.assertRaises(TypeError):
            native.source_contract(fixture, modules)


if __name__ == '__main__':
    unittest.main()
