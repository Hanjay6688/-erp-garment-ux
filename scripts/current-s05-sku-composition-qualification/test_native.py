"""Focused private-binding controls; no real ERP/runtime or PASS evidence."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import ast
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('s05_sku_native_under_test', HERE/'native.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
RAW = (ROOT/native.ORIGINAL).read_bytes()
CASE_RAW = (ROOT/'scripts/cp7_accessory_standard_report/cases.py').read_bytes()
IDS = next(ast.literal_eval(n.value) for n in ast.parse(CASE_RAW).body
           if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))


def retained():
    module = ModuleType('retained_S05_controls_only')
    module.IDS = IDS
    for name in ('stage', 'physical', 'issues', 'master', 'qc_source', 'sessions', 'b', 'prod'):
        setattr(module, name, object())
    return module


def copy_factory(original, state):
    module = ModuleType('private_S05_controls_only')
    module.__dict__.update(original.__dict__)
    exec('def callback():\n    return stage\n', module.__dict__)
    return module


class ComponentSource(unittest.TestCase):
    def test_complete_component_reverses_and_compiles_without_ERP_imports(self):
        text, proof = native.derive_component(RAW)
        self.assertEqual(proof['counted_change_groups'], 5)
        self.assertEqual(proof['changed_occurrences'], 6)
        reverse = text
        for before, after, count in reversed(native.CHANGES):
            self.assertEqual(reverse.count(after), count)
            reverse = reverse.replace(after, before)
        self.assertEqual(reverse.encode(), RAW)
        before_functions = {n.name: ast.dump(n) for n in ast.parse(RAW).body if isinstance(n, ast.FunctionDef)}
        after_functions = {n.name: ast.dump(n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
        self.assertEqual(set(before_functions), set(after_functions))
        for name in set(before_functions)-{'scheduler_quiet', 'exercise'}:
            self.assertEqual(before_functions[name], after_functions[name])
        module = ModuleType('source_only_no_component_execution')
        module.__file__ = str(ROOT/native.ORIGINAL)
        exec(compile(text, module.__file__, 'exec'), module.__dict__)
        self.assertEqual(module.CASE, 'S05_ON_SKU_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE')
        self.assertEqual(module.LABEL, 'CP7_S05_ON_SKU_NATIVE10_CASES')

    def test_changed_or_duplicate_parent_and_factory_anchors_refuse(self):
        for before, after, _ in native.CHANGES:
            with self.subTest(before=before):
                with self.assertRaises(ValueError):
                    native.derive_component(RAW.replace(before.encode(), b'CHANGED', 1))
                with self.assertRaises(ValueError):
                    native.derive_component(RAW+b'\n'+before.encode())
                with self.assertRaises(ValueError):
                    native.derive_component(RAW+b'\n'+after.encode())


class PrivateBinding(unittest.TestCase):
    def test_retained_stage_untouched_and_private_callback_reads_SKU_reader(self):
        original, reader = retained(), object()
        before = dict(original.__dict__)
        private = native.bind_private_business(original, {}, SimpleNamespace(business=copy_factory), reader)
        self.assertIs(private.stage, reader)
        self.assertIs(private.callback(), reader)
        self.assertEqual(original.__dict__, before)
        self.assertEqual(private.IDS, IDS)
        self.assertEqual(private.sku_parent_binding['actual_new_Native_credit'], 0)

    def test_alias_of_retained_module_refuses_before_stage_mutation(self):
        original = retained(); before = original.stage
        with self.assertRaisesRegex(ValueError, 'PRIVATE_CASE_MODULE_REQUIRED'):
            native.bind_private_business(original, {}, SimpleNamespace(business=lambda r, s: r), object())
        self.assertIs(original.stage, before)

    def test_wrong_callback_set_or_native_dependency_refuses(self):
        for changed in ('IDS', 'stage', 'physical', 'issues', 'master', 'qc_source', 'sessions', 'b', 'prod'):
            original = retained(); before = original.stage
            def wrong(r, s):
                private = copy_factory(r, s)
                setattr(private, changed, IDS[:-1] if changed == 'IDS' else object())
                return private
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                native.bind_private_business(original, {}, SimpleNamespace(business=wrong), object())
            self.assertIs(original.stage, before)

    def test_wrong_factory_cannot_change_original_stage_unnoticed(self):
        original = retained()
        def wrong(r, s):
            private = copy_factory(r, s); r.stage = object(); return private
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_STAGE_IDENTITY_REQUIRED'):
            native.bind_private_business(original, {}, SimpleNamespace(business=wrong), object())


if __name__ == '__main__':
    unittest.main()
