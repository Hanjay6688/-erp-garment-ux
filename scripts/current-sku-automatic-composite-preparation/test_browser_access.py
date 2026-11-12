"""Owning entry, decoder scope and explicit browser-copy admission controls."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
import gzip
import importlib
import importlib.util
import json
import os
import sys
import unittest

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


entry = load('current_browser_owner_control', 'qualification.py')
access = load('current_browser_copy_control', 'browser_access.py')


class BrowserAccessControls(unittest.TestCase):
    def test_real_closed_inputs_precede_copy_product_or_mode_inspection(self):
        gates = dict.fromkeys(entry.admission.GATES)
        with patch.multiple(entry.admission, **gates), \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('File inspected')), \
                patch.object(entry, 'load', side_effect=AssertionError('Copy mode inspected')):
            with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                access.run(entry, object(), object(), object(), {})
            with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                with access.copy_scope(entry, object(), object(), object()):
                    self.fail('Unadmitted copy entered')

    def test_native_only_plan_cannot_silently_activate_browser_copies(self):
        current = json.loads(entry.PLAN_FILE.read_bytes())
        current.pop('required_browser_case_ids')
        current.pop('fresh_real_Auth_browser_required')
        originals = (b'CONTROL_ONLY_NO_ROOT', b'CONTROL_ONLY_NO_SOURCE', json.dumps(current).encode(), {})
        gates = {key: getattr(entry.admission, key) for key in entry.admission.GATES}
        with patch.object(entry, 'actual_inputs', return_value=originals):
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_COMPLETE_PLAN_ADOPTION_REQUIRED'):
                access.actual_inputs(entry)
        current.update(required_browser_case_ids=list(access.IDS), fresh_real_Auth_browser_required=True)
        values = (*originals[:2], json.dumps(current).encode(), {})
        with patch.object(entry, 'actual_inputs', return_value=values):
            with patch.dict(os.environ, GITHUB_REF='refs/heads/control-wrong-owner'):
                with self.assertRaisesRegex(ValueError, 'SINGLE_OWNING_BRANCH_REQUIRED'):
                    access.actual_inputs(entry)
            with patch.dict(os.environ, GITHUB_REF=entry.BRANCH):
                self.assertEqual(access.actual_inputs(entry), values)
        self.assertEqual({key: getattr(entry.admission, key) for key in gates}, gates)

    def bound_runner(self):
        """Evaluate the owning runtime's exact binding without running its I/O."""
        tree = ast.parse(Path(entry.__file__).read_bytes())
        runtime = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'runtime')
        binding = [node for node in ast.walk(runtime) if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id in ('browser_access', 'browser_entry')
                           for target in node.targets)]
        self.assertEqual(len(binding), 2)
        browser_run, = [keyword.value for node in ast.walk(runtime) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute) and node.func.attr == 'load_prepared'
                        for keyword in node.keywords if keyword.arg == 'browser_run']
        scope = dict(vars(entry))
        exec(compile(ast.Module(body=sorted(binding, key=lambda node: node.lineno), type_ignores=[]),
                     str(HERE / 'qualification.py'), 'exec'), scope)
        return eval(compile(ast.Expression(browser_run), str(HERE / 'qualification.py'), 'eval'), scope)

    def test_copy_binding_reuses_active_owning_decoder_and_restores_on_exit(self):
        other = load('current_browser_duplicate_owner_control', 'qualification.py')
        plan = entry.PLAN_FILE.read_bytes()
        originals = (b'CONTROL_ONLY_NO_ROOT', b'CONTROL_ONLY_NO_SOURCE', plan, {})
        original_path = list(sys.path)
        original_meta = list(sys.meta_path)
        original_argv = sys.argv
        p00 = entry.ROOT.parent / 'qualified-sku090b'
        source = entry.FROZEN_AFUI / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py'
        fence = entry.load('current_browser_unchanged_source_control_fence', source)
        state = {'after': object()}
        catalogue = object()
        original_copy = object()
        modes = SimpleNamespace(copy_db=original_copy)
        product = SimpleNamespace(
            __file__=str(entry.assembly.FROZEN_AUTO / 'scripts/cp7_sku_automatic_pending/composition.py'),
            runtime=lambda: (catalogue,), verify=lambda *_: self.fail('Database verifier invoked'))

        with patch.object(entry, 'actual_inputs', return_value=originals), \
                patch.object(other, 'actual_inputs', return_value=originals), \
                patch.dict(os.environ, GITHUB_REF=entry.BRANCH), \
                patch.dict(sys.modules), fence.fenced_source_read() as guard:
            runner = self.bound_runner()
            browser_entry, = runner.args
            self.assertIs(browser_entry.inherited_scope, entry.inherited_scope)
            self.assertIs(browser_entry.actual_inputs, entry.actual_inputs)
            self.assertIs(browser_entry.load, entry.load)
            self.assertIsNot(other.catalogue_decode, entry.catalogue_decode)
            self.assertEqual(runner.func.__code__, access.run.__code__)
            for name in entry.catalogue_decode.PINS:
                self.assertNotIn(name, sys.modules)
            sys.path.insert(0, str(p00 / 'scripts'))
            try:
                with entry.inherited_scope():
                    name = 'cp7_supplier_credit_guard'
                    consumer = importlib.import_module(name)
                    decoder = entry.catalogue_decode._active[-1][1]
                    original_binding = consumer.gzip, consumer.json
                    self.assertIs(consumer.gzip.decompress.__self__, decoder)
                    self.assertIs(consumer.json.loads.__self__, decoder)
                    signature = consumer.SIGNATURES[0]
                    definition = consumer.accepted(signature)
                    self.assertIn(signature.split('(')[0], definition)
                    with self.assertRaisesRegex(ValueError, 'SKU_CATALOGUE_UNCHANGED_DECODER_BINDINGS_REQUIRED'):
                        with access.copy_scope(other, modes, product, state):
                            self.fail('Duplicate owner entered Mandor copy authority')
                    self.assertIs(modes.copy_db, original_copy)
                    self.assertEqual(other.catalogue_decode._active, [])

                    class IntentionalCopyExit(Exception):
                        pass

                    with self.assertRaises(IntentionalCopyExit):
                        with access.copy_scope(browser_entry, modes, product, state) as copies:
                            self.assertEqual(copies['actual_copy_admissions'], [])
                            self.assertTrue(copies['source']['all_raw22_authority_checks_unchanged'])
                            self.assertIs(modes.copy_db.__globals__['STATE']['installed_catalog'], state['after'])
                            self.assertIs(modes.copy_db.__globals__['PRODUCT'].catalog, catalogue)
                            self.assertIs(entry.catalogue_decode._active[-1][1], decoder)
                            self.assertEqual(len(entry.catalogue_decode._active), 1)
                            self.assertEqual((consumer.gzip, consumer.json), original_binding)
                            self.assertEqual(consumer.accepted(signature), definition)
                            raise IntentionalCopyExit()
                    self.assertIs(modes.copy_db, original_copy)
                    self.assertEqual((consumer.gzip, consumer.json), original_binding)
                self.assertIs(consumer.gzip, gzip)
                self.assertIs(consumer.json, json)
                self.assertEqual(entry.catalogue_decode._active, [])
                self.assertIsNone(decoder.parsed)
            finally:
                sys.path[:] = original_path
            self.assertEqual(guard['attempts'], [])
            self.assertEqual(guard['network_nonGit_attempts'], [])
        self.assertEqual(sys.meta_path, original_meta)
        self.assertIs(sys.argv, original_argv)


if __name__ == '__main__':
    unittest.main()
