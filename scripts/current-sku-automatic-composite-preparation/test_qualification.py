"""Owning-entry and real import/provenance controls; no ERP execution."""
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('automatic_owning_control_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def temporary_modules(names):
    previous = {key: value for key, value in sys.modules.items() if any(key == n or key.startswith(n + '.') for n in names)}
    for key in previous:
        sys.modules.pop(key)
    try:
        yield
    finally:
        for key in list(sys.modules):
            if any(key == n or key.startswith(n + '.') for n in names):
                sys.modules.pop(key)
        sys.modules.update(previous)


class OwningNative25(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = load('qualification')
        cls.binding = cls.entry.money_binding
        cls.modules = cls.entry.modules

    def test_all_reachable_parent_bare_imports_are_scoped_and_foreign_case_helpers_refuse(self):
        qualifier = HERE.parent / 'current-mandor-shop-native-qualification'
        proof = self.modules.require_import_closure(qualifier)
        self.assertEqual(set(proof['scoped_bare_modules']), set(self.modules.NAMES))
        self.assertEqual(len(self.modules.NAMES), 15)
        with tempfile.TemporaryDirectory() as directory, temporary_modules(self.modules.NAMES):
            correct, wrong = Path(directory) / 'correct', Path(directory) / 'wrong'
            correct.mkdir();wrong.mkdir()
            before = list(sys.path)
            for name in ('cases', 'oracle', 'native_fixture', 'access_runtime'):
                foreign = ModuleType(name);foreign.__file__ = str(wrong / (name + '.py'));sys.modules[name] = foreign
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'INHERITED_MODULE_COLLISION:' + name):
                    with self.modules.scope(correct):self.fail('Foreign parent helper entered')
                self.assertIs(sys.modules.pop(name), foreign)
                self.assertEqual(sys.path, before)

    def test_closed_and_every_partial_entry_refuses_before_any_receipt_read(self):
        gate = self.entry.admission
        for missing in (None, *gate.GATES):
            values = {key: None if missing is None or missing == key else 'CONTROL_ONLY' for key in gate.GATES}
            with self.subTest(missing=missing), patch.multiple(gate, **values), patch.object(Path, 'read_bytes', side_effect=AssertionError('receipt read')):
                for call in (self.entry.actual_inputs, self.entry.runtime):
                    with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                        call()
        with patch.multiple(gate, **{key: 'FORGED' for key in gate.GATES}), patch.object(Path, 'read_bytes', side_effect=AssertionError('receipt read')):
            with self.assertRaisesRegex(ValueError, 'EXACT_OWNING_RUNTIME_ENTRY'):
                self.entry.actual_inputs()

    def test_money_binding_closed_gate_never_inspects_receipts_or_loads_retained_modules(self):
        admission = self.binding.admission
        with patch.multiple(admission, **dict.fromkeys(admission.GATES)), \
                patch.object(self.binding, 'load', side_effect=AssertionError('retained module inspected')):
            with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                self.binding.bind(object(), object(), object())

    def test_private_function_code_and_original_admission_are_unchanged(self):
        original = self.binding.load('automatic_exact_money_bridge_control', self.binding.PRIOR)
        original_globals = dict(original.__dict__)
        original_gates = dict(original.admission.__dict__)
        replacement = object()
        private = self.binding.private_module(original, dict(admission=replacement))
        self.assertIs(private.admission, replacement)
        for name in ('load_prepared', 'prepared_sources', 'source_manifest', 'git', 'require'):
            old, new = getattr(original, name), getattr(private, name)
            self.assertIs(new.__code__, old.__code__)
            self.assertIs(new.__globals__, private.__dict__)
            self.assertIs(old.__globals__, original.__dict__)
            self.assertEqual(new.__defaults__, old.__defaults__)
            self.assertEqual(new.__kwdefaults__, old.__kwdefaults__)
        self.assertTrue(all(original.__dict__[name] is value for name, value in original_globals.items()))
        self.assertEqual(original_gates, original.admission.__dict__)
        self.assertTrue(all(getattr(original.admission, name) is None for name in original.admission.GATES))

    def test_retained_admission_still_refuses_an_explicit_synthetic_root(self):
        parent = dict(status='ROOT_VERIFIED_CURRENT_MANDOR17_ALL5', head='a' * 40, tree='b' * 40,
                      actual_Native_cases=9, actual_Native_session_cases=4, actual_Auth_HTTP_cases=2, actual_browser_cases=2,
                      actual_business_cases=17, complete17_qualified=True, package_all_five=True, prior_runs_aggregated=False,
                      assembly_source=dict(bytes=1, sha256='0' * 64), qualified_current_Mandor_sources={},
                      production_go=False, independent_acceptance=False, synthetic_receipt_not_an_actual_qualification=True)
        raw = json.dumps(parent).encode()
        money = self.entry.MONEY_FILE.read_bytes()
        plan = self.entry.PLAN_FILE.read_bytes()
        gates = self.binding.admission
        values = dict(MANDOR_ROOT_PIN=gates.pin(raw), MONEY_SOURCE_PREFLIGHT_PIN=gates.pin(money),
                      CURRENT_MONEY_GRAPH_PIN={'control_only': True}, COMBINED_NATIVE_PLAN_PIN=gates.pin(plan),
                      OWNING_RUNTIME_ENTRY=self.entry.ENTRY)
        with patch.multiple(gates, **values), self.assertRaisesRegex(ValueError, 'SYNTHETIC_RECEIPT_REFUSED'):
            self.binding.bind(raw, money, plan)

    def test_actual_plain_import_uses_frozen_qualifier_first_and_nested_scope_keeps_it_alive(self):
        with tempfile.TemporaryDirectory() as directory, temporary_modules(self.modules.NAMES):
            root = Path(directory)
            correct, wrong = root / 'correct', root / 'wrong'
            correct.mkdir();wrong.mkdir()
            (correct / 'admission.py').write_text("marker='correct'\n")
            (wrong / 'admission.py').write_text("marker='wrong'\n")
            prior_path = list(sys.path)
            sys.path.insert(0, str(wrong))
            try:
                with self.modules.scope(correct):
                    with self.modules.scope(correct):
                        admitted = importlib.import_module('admission')
                        self.assertEqual(admitted.marker, 'correct')
                    self.assertIs(sys.modules['admission'], admitted)
                    self.assertEqual(sys.path[0], str(correct))
                self.assertNotIn('admission', sys.modules)
                self.assertEqual(sys.path[0], str(wrong))
            finally:
                sys.path[:] = prior_path

    def test_other_qualifier_or_existing_foreign_module_is_refused_and_failure_restores_state(self):
        with tempfile.TemporaryDirectory() as directory, temporary_modules(self.modules.NAMES):
            correct, wrong = Path(directory) / 'correct', Path(directory) / 'wrong'
            correct.mkdir();wrong.mkdir()
            foreign = ModuleType('admission');foreign.__file__ = str(wrong / 'admission.py')
            sys.modules['admission'] = foreign
            before = list(sys.path)
            with self.assertRaisesRegex(ValueError, 'INHERITED_MODULE_COLLISION'):
                with self.modules.scope(correct):
                    self.fail('foreign admission entered')
            self.assertIs(sys.modules.pop('admission'), foreign)
            self.assertEqual(sys.path, before)
            with self.assertRaisesRegex(RuntimeError, 'control failure'):
                with self.modules.scope(correct):
                    with self.assertRaisesRegex(ValueError, 'ANOTHER_INHERITED_SCOPE'):
                        with self.modules.scope(wrong):
                            self.fail('another qualifier entered')
                    module = ModuleType('admission');module.__file__ = str(correct / 'admission.py')
                    sys.modules['admission'] = module
                    raise RuntimeError('control failure')
            self.assertEqual(sys.path, before)
            self.assertNotIn('admission', sys.modules)

    def test_namespace_and_regular_packages_keep_real_source_paths_and_refuse_foreign_children(self):
        name = 'automatic_frozen_namespace_control'
        with tempfile.TemporaryDirectory() as directory, temporary_modules((name,)):
            root = Path(directory)
            correct, wrong = root / 'correct', root / 'wrong'
            correct.mkdir();wrong.mkdir()
            (correct / 'composition.py').write_text("marker='exact source'\n")
            (wrong / 'composition.py').write_text("marker='wrong source'\n")
            package = self.modules.select_package(name, correct)
            self.assertIsNone(package.__file__)
            self.assertEqual(package.__path__, [str(correct)])
            composed = importlib.import_module(name + '.composition')
            self.assertEqual(composed.marker, 'exact source')
            self.assertEqual(Path(composed.__file__), correct / 'composition.py')
            with self.assertRaisesRegex(ValueError, 'FROZEN_PACKAGE_COLLISION'):
                self.modules.select_package(name, wrong)
            alien = ModuleType(name + '.alien');alien.__file__ = str(wrong / 'alien.py')
            sys.modules[alien.__name__] = alien
            with self.assertRaisesRegex(ValueError, 'FROZEN_SUBMODULE_COLLISION'):
                self.modules.select_package(name, correct)
        with tempfile.TemporaryDirectory() as directory, temporary_modules((name,)):
            root = Path(directory)
            (root / '__init__.py').write_text("marker='real initializer'\n")
            package = self.modules.select_package(name, root)
            self.assertEqual(package.marker, 'real initializer')
            self.assertEqual(Path(package.__file__), root / '__init__.py')

    def test_copy_binding_uses_exact_current_Afui_source_without_whole_file_reads(self):
        io = self.entry.report_io
        raw = self.entry.assembly.git('show', io.COMPLETE_ORIGINALS_HEAD +
                                      ':scripts/cp7_accessory_nonpayable/complete_original_io.py')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'complete_original_io.py'
            original.write_bytes(raw)
            with patch.object(io, 'COMPLETE_ORIGINALS_PATH', original):
                helper = io.complete_originals()
                before = root / 'before.json'
                after = root / 'after.json'
                payload = b'{"complete_original":true}\n' * 1024
                before.write_bytes(payload)
                with patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded original read')):
                    receipt = helper.copy_exact(before, after, 'CONTROL_COPY_CONFLICT')
                self.assertEqual(before.read_bytes(), after.read_bytes())
                self.assertEqual(receipt, dict(name=after.name, bytes=len(payload), sha256=io.sha256(payload).hexdigest()))
                original.write_bytes(raw + b'\n')
                with self.assertRaisesRegex(ValueError, 'EXACT_AFUI_COMPLETE_ORIGINAL_COPY_SOURCE'):
                    io.complete_originals()

    def test_complete_case_output_keeps_exact_bytes_in_the_owning_checkout(self):
        raw = self.entry.assembly.git('show', self.entry.report_io.COMPLETE_ORIGINALS_HEAD + ':' + self.entry.CASE_OUTPUT_PATH)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frozen = root / 'frozen'
            path = frozen / self.entry.CASE_OUTPUT_PATH
            path.parent.mkdir(parents=True)
            path.write_bytes(raw)
            with patch.object(self.entry, 'FROZEN_AFUI', frozen), patch.object(self.entry, 'ROOT', root / 'owner'):
                output = self.entry.complete_case_output()
                row = dict(status='PASS', complete_model_only={'values': [0, False, None, 'actual bytes retained']})
                text = io.StringIO()
                with redirect_stdout(text):
                    receipt = output.retain('EXPLICIT_MODEL', 'CONTROL', row)
                expected = (json.dumps(dict(group='EXPLICIT_MODEL', case='CONTROL', **row), default=str) + '\n').encode()
                self.assertEqual((output.OUT / receipt['complete_original_file']).read_bytes(), expected)
                self.assertTrue(receipt['console_is_only_a_receipt'])
                self.assertLess(len(text.getvalue().encode()), 2048)
                self.assertTrue(output.OUT.is_relative_to(root / 'owner'))
                native_path = frozen / 'scripts/cp6_auditor_runner.py'
                native_raw = self.entry.assembly.git('show', self.entry.report_io.COMPLETE_ORIGINALS_HEAD + ':scripts/cp6_auditor_runner.py')
                native_path.write_bytes(native_raw)
                native = ModuleType('automatic_actual_case_output_scope_fixture')
                native.__file__ = str(native_path)
                original = FunctionType(self.entry.report_io.function_code(native_raw, str(native_path), '_strict_group_once'), native.__dict__)
                native._strict_group_once = original
                with output.scope(native, 'native'):
                    self.assertIsNot(native._strict_group_once, original)
                    with redirect_stdout(io.StringIO()):
                        scoped = native.__dict__['_afui_retain_complete_case_stdout']('EXPLICIT_SCOPE_MODEL', 'CONTROL', row)
                    self.assertEqual((output.OUT / scoped['complete_original_file']).read_bytes(),
                                     (json.dumps(dict(group='EXPLICIT_SCOPE_MODEL', case='CONTROL', **row), default=str) + '\n').encode())
                self.assertIs(native._strict_group_once, original)
                self.assertNotIn('_afui_retain_complete_case_stdout', native.__dict__)
                path.write_bytes(raw + b'\n')
                with self.assertRaisesRegex(ValueError, 'EXACT_COMPLETE_CASE_OUTPUT_SOURCE'):
                    self.entry.complete_case_output()


class InstallAuthorityControls(unittest.TestCase):
    def test_parent_and_top_level_operations_use_their_qualified_identities(self):
        package = load('package')
        cursor = SimpleNamespace(identity='maintenance')
        events = []
        phases = []

        @contextmanager
        def observe(name):
            phases.append((name, cursor.identity))
            yield

        def operation(name, expected, result):
            def call(cur, *args):
                self.assertIs(cur, cursor)
                self.assertEqual(cur.identity, expected)
                events.append((name, args))
                return result
            return call

        def as_admin(cur, callback):
            self.assertEqual(cur.identity, 'maintenance')
            cur.identity = 'admin'
            try:
                return callback(cur)
            finally:
                cur.identity = 'maintenance'

        mandor = SimpleNamespace(install_delta=operation('Mandor', 'maintenance', 'mandor'))
        moving = SimpleNamespace(parent=lambda: mandor, install_delta=operation('Moving', 'admin', 'moving'))
        money = SimpleNamespace(parent=lambda: moving, install_delta=operation('Money', 'admin', 'money'))
        product = SimpleNamespace(parent=lambda: money,
                                  install_delta=operation('Automatic', 'admin', 'automatic'),
                                  rollback_delta_preuse=operation('Inverse', 'admin', 'inverse'),
                                  verify=operation('Verify', 'admin', 'verified'))
        bindings = package.bind_install_authority(product, operation('Afui', 'maintenance', 'afui'),
                                                  as_admin, observe=observe)
        prior = bindings['_sku_install_parent'](cursor)
        state = bindings['_sku_install_delta'](cursor, prior)
        self.assertEqual(bindings['_sku_rollback_delta_preuse'](cursor, state), 'inverse')
        state = bindings['_sku_install_delta'](cursor, prior)
        self.assertEqual(bindings['_sku_verify_installed'](cursor, state), 'verified')
        self.assertEqual(cursor.identity, 'maintenance')
        self.assertEqual(phases, [('AFUI_PARENT_INSTALL', 'maintenance'),
                                  ('MANDOR_PARENT_DELTA', 'maintenance'),
                                  ('SKU_MOVING_PARENT_DELTA', 'admin'),
                                  ('SKU_MONEY_PARENT_DELTA', 'admin')])
        self.assertEqual(events, [('Afui', ()), ('Mandor', ('afui',)), ('Moving', ('mandor',)),
                                  ('Money', ('moving',)), ('Automatic', ('money',)),
                                  ('Inverse', ('automatic',)), ('Automatic', ('money',)),
                                  ('Verify', ('automatic',))])

    def test_changed_mandor_authority_source_is_rejected_before_import(self):
        package = load('package')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / package.MANDOR_AUTHORITY
            path.parent.mkdir(parents=True)
            path.write_text("raise AssertionError('must never load')\n")
            with patch.object(package, 'load') as imported:
                with self.assertRaisesRegex(ValueError, 'EXACT_MANDOR_INSTALL_AUTHORITY_BYTES_REQUIRED'):
                    package.installer_authority(root)
                imported.assert_not_called()


class CompleteStateBindingControls(unittest.TestCase):
    @staticmethod
    def products(package):
        # Exact three retained derived functions, including their full payloads.
        bodies = (
            "return catalog.digest(dict(complete_current_parent=prior,verified_parent_proof=proof,contract='cp7.current-mandor-complete-state-binding.v1'))",
            "return catalog.digest(dict(complete_current_moving_parent=prior,verified_parent_proof=proof,contract='cp7.current-mandor-moving-money-complete-state-binding.v1'))",
            "return catalog.digest(dict(complete_current_money_parent=prior,verified_parent_proof=proof,contract='cp7.current-automatic-complete-parent-state.v1'))",
        )
        modules = []
        for (name, folder, _, _), body in zip(package.STATE_BINDINGS, bodies):
            module = ModuleType(name)
            frozen = 'qualified-sku-automatic' if folder == 'cp7_sku_automatic_pending' else 'qualified-sku-money'
            module.__file__ = str(package.ROOT.parent / frozen / 'scripts' / folder / 'composition.py')
            exec(compile('def binding(catalog, prior, proof):\n    ' + body + '\n', module.__file__, 'exec'), module.__dict__)
            modules.append(module)
        modules[2].parent = lambda: modules[1]
        modules[1].parent = lambda: modules[0]
        return modules

    def test_all_three_complete_bindings_accept_typed_state_and_detect_changes(self):
        from copy import deepcopy
        from datetime import datetime, timezone
        from decimal import Decimal
        from uuid import UUID
        package = load('package')
        modules = self.products(package)
        original = tuple(module.binding for module in modules)
        catalog = SimpleNamespace(digest=lambda value: json.dumps(value, sort_keys=True))
        untouched = catalog.digest
        prior = dict(sources={'SQL': 'exact body'}, before={'owner': 'postgres'},
                     after={'grant': ['SELECT'], 'sequence': [11, True]},
                     parent={'at': datetime(2026, 11, 11, 1, 2, 3, 456789, timezone.utc),
                             'amount': Decimal('9007199254740993.00100'),
                             'id': UUID('06f4266d-305a-45ce-bd0a-0d53ac2a9917'), 'raw': b'\x00\xff'})
        proof = {'all22': True}
        snapshot = deepcopy(prior)
        for binding in original:
            with self.assertRaisesRegex(TypeError, 'datetime'):
                binding(catalog, {'at': prior['parent']['at']}, proof)
            with self.assertRaisesRegex(TypeError, 'not JSON serializable'):
                binding(catalog, prior, proof)
        receipt = package.bind_parent_state(modules[2])
        self.assertEqual(receipt['complete_binding_payloads'], 3)
        self.assertIs(catalog.digest, untouched)
        for module in modules:
            digest = module.binding(catalog, prior, proof)
            self.assertEqual(digest, module.binding(catalog, deepcopy(prior), dict(proof)))
            changes = (
                ('sources', 'SQL', 'changed body'), ('before', 'owner', 'authenticated'),
                ('after', 'grant', []), ('after', 'sequence', [12, True]),
                ('parent', 'amount', Decimal('9007199254740993.00101')),
                ('parent', 'at', prior['parent']['at'].replace(microsecond=456788)),
                ('parent', 'id', UUID(int=0)), ('parent', 'raw', b'\x00\xfe'),
            )
            for section, key, value in changes:
                changed = deepcopy(prior); changed[section][key] = value
                self.assertNotEqual(digest, module.binding(catalog, changed, proof))
            self.assertNotEqual(digest, module.binding(catalog, prior, {'all22': False}))
        self.assertEqual(prior, snapshot)
        self.assertIs(catalog.digest, untouched)

    def test_type_tags_prevent_string_and_numeric_collisions(self):
        from datetime import date, datetime, time, timedelta, timezone
        from decimal import Decimal
        from uuid import UUID
        package = load('package')
        values = [None, False, 0, 0.0, -0.0, Decimal('0'), Decimal('0.00'), '0',
                  date(2026, 11, 11), '2026-11-11', datetime(2026, 11, 11, tzinfo=timezone.utc),
                  time(1, 2, 3), timedelta(seconds=1), b'abc', bytearray(b'abc'),
                  UUID(int=0), str(UUID(int=0)), [], (), set(), frozenset(), {}]
        hashes = [package.state_digest(value) for value in values]
        self.assertEqual(len(set(hashes)), len(values))
        self.assertEqual(package.state_digest({'a': 1, 'b': 2}), package.state_digest({'b': 2, 'a': 1}))
        for bad in (object(), float('nan'), float('inf'), Decimal('NaN'), Decimal('Infinity')):
            with self.subTest(value=type(bad).__name__), self.assertRaisesRegex(TypeError, 'UNSUPPORTED_VALUE'):
                package.state_digest({'nested': [bad]})
        self.assertNotEqual(package.state_digest({1: 'value'}), package.state_digest({'1': 'value'}))
        self.assertEqual(package.state_digest({1: 'a', '1': 'b'}), package.state_digest({'1': 'b', 1: 'a'}))
        with self.assertRaisesRegex(TypeError, 'UNSUPPORTED_VALUE'):
            package.state_digest({object(): 'unsupported key must never be stringified'})

    def test_changed_or_frozen_module_refuses_before_any_private_binding_changes(self):
        package = load('package')
        for violation in ('payload', 'origin', 'closure'):
            modules = self.products(package)
            originals = [module.binding for module in modules]
            if violation == 'payload':
                exec('def binding(catalog, prior, proof):\n    return catalog.digest(prior)\n', modules[2].__dict__)
            elif violation == 'origin':
                modules[2].__file__ = '/different-frozen-root/composition.py'
            else:
                modules[2].binding = lambda catalog, prior, proof: 'forged'
            with self.assertRaisesRegex(ValueError, 'EXACT_DERIVED_MODULE|UNCHANGED_COMPLETE_BINDING'):
                package.bind_parent_state(modules[2])
            self.assertIs(modules[0].binding, originals[0])
            self.assertIs(modules[1].binding, originals[1])


if __name__ == '__main__':
    unittest.main()
