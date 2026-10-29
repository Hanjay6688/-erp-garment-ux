"""Source and import/CLI doubles only. No SQL or Native financial claims."""
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import ast
import contextlib
import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class ExactSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = load('joined_test_source', HERE / 'source_check.py')

    def test_joined_source_closes_and_keeps_no_native_credit(self):
        proof = self.source.check()
        self.assertEqual(proof['retained_qualifier_files'], 20)
        self.assertEqual(proof['changed_runtime_leaves'], ['materialize.sql', 'owning.sql'])
        self.assertEqual(proof['actual_Native_cases'], 0)
        pending = json.loads((HERE / 'CONFIG.json').read_bytes())['native_augmentation']['SOURCE'] is None
        self.assertEqual(proof['augmentation']['status'], 'CLOSED_PENDING_ROOT_SOURCE_BINDING' if pending else 'EXACT_REVIEWED_AUGMENTATION_SOURCE_BOUND')
        self.assertFalse(proof['D902_usable_prerequisite'])

    def test_unknown_file_pin_and_half_binding_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'file').write_bytes(b'original')
            with self.assertRaisesRegex(ValueError, 'EXACT_SOURCE_CHANGED'):
                self.source.pinned(root, 'file', '0' * 64)
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        cfg['native_augmentation'].update(SOURCE=None, required_source=None)
        for field in ('SOURCE', 'required_source'):
            changed = copy.deepcopy(cfg)
            changed['native_augmentation'][field] = {} if field == 'SOURCE' else '0' * 64
            with self.assertRaisesRegex(ValueError, 'BINDING_MUST_BE_COMPLETE'):
                self.source.augmentation(changed)

    def test_pending_binding_refuses_even_when_factory_file_exists(self):
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        cfg['native_augmentation'].update(SOURCE=None, required_source=None)
        # The explicit null gate is authoritative, not file existence.
        with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('must not inspect future factory')):
            with self.assertRaisesRegex(ValueError, self.source.CLOSED):
                self.source.augmentation(cfg)

    def test_bound_source_checks_exact_raw_declaration_and_factory(self):
        from hashlib import sha256
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = cfg['native_augmentation']
            factory = root / a['factory_path']
            factory.parent.mkdir(parents=True)
            factory.write_bytes(b'def business(value): return value\n')
            declaration = {'files': {a['factory_path']: {'bytes': factory.stat().st_size,
                'sha256': sha256(factory.read_bytes()).hexdigest()}}}
            raw = json.dumps(declaration, indent=2).encode()
            (root / a['source_path']).write_bytes(raw)
            a['SOURCE'] = declaration
            a['required_source'] = sha256(raw).hexdigest()
            self.assertEqual(self.source.augmentation(cfg, root)['status'], 'EXACT_REVIEWED_AUGMENTATION_SOURCE_BOUND')
            factory.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'EXACT_SOURCE_CHANGED'):
                self.source.augmentation(cfg, root)

    def test_both_counterparts_pure_scope_guards_refuse_extra_financial_change(self):
        q = load('joined_test_quote', ROOT / 'scripts/current-credit-d1-product-cap-qualification/source_check.py')
        p = load('joined_test_phase', ROOT / 'scripts/current-credit-d1-materialize-phase-successor/check.py')
        before_q = (ROOT / 'scripts/current-credit-d1-product-cap-qualification/retained/owning.before.sql').read_text()
        current_q = (ROOT / self.source.OWNING).read_text()
        with self.assertRaisesRegex(ValueError, 'OTHER_OWNING_BODY_CHANGED'):
            q.quote_scope(before_q, current_q + '\n-- out of scope')
        before_p = (ROOT / 'scripts/current-credit-d1-materialize-phase-successor/evidence/BEFORE_materialize.sql').read_bytes()
        with self.assertRaisesRegex(ValueError, 'ONLY_FOUR_IDENTIFIER'):
            p.derivation(before_p, (ROOT / self.source.MAT).read_bytes() + b'\n')

    def test_new_admission_calls_exact_old_function_with_new_here(self):
        module = load('joined_test_admission', HERE / 'admission.py')
        args = (ROOT, HERE, object(), object())
        old = SimpleNamespace(admitted=mock.Mock(return_value={'status': 'old-proof'}))
        joined = {'augmentation': {'status': 'bound'}}
        closure = SimpleNamespace(check=mock.Mock(return_value=joined))
        def dispatch(name, path):
            self.assertIn(path, (HERE / 'source_check.py', ROOT / 'scripts/current-credit-de-native-qualification/admission.py'))
            return closure if path.name == 'source_check.py' else old
        with mock.patch.object(module, 'load', side_effect=dispatch):
            proof = module.admitted(*args)
        closure.check.assert_called_once_with(ROOT, HERE, require_bound=True)
        old.admitted.assert_called_once_with(*args)
        self.assertEqual(proof['status'], 'old-proof')

    def test_closed_new_admission_never_calls_historical_product(self):
        module = load('joined_test_closed_admission', HERE / 'admission.py')
        closure = SimpleNamespace(check=mock.Mock(side_effect=ValueError(self.source.CLOSED)))
        with mock.patch.object(module, 'load', return_value=closure) as loading:
            with self.assertRaisesRegex(ValueError, self.source.CLOSED):
                module.admitted(ROOT, HERE, object(), object())
        self.assertEqual(loading.call_count, 1)


class DerivationTests(unittest.TestCase):
    def test_private_import_is_only_change_all_old_functions_exact(self):
        derive = load('joined_test_derive', HERE / 'derive.py')
        raw = (ROOT / 'scripts/current-credit-de-native-qualification/native_runner.py').read_bytes()
        current, proof = derive.native_runner(raw)
        self.assertEqual(current.replace(derive.AFTER, derive.BEFORE, 1).encode(), raw)
        old_functions = [ast.get_source_segment(raw.decode(), n) for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)]
        new_functions = [ast.get_source_segment(current, n) for n in ast.parse(current).body if isinstance(n, ast.FunctionDef)]
        self.assertEqual(old_functions, new_functions)
        self.assertEqual(proof['counted_changes'], 1)
        for bad in (raw.replace(derive.BEFORE.encode(), b'changed'), raw + b'\n' + derive.BEFORE.encode()):
            with self.assertRaisesRegex(ValueError, 'ONE_EXACT_NATIVE_BUSINESS_BINDING'):
                derive.native_runner(bad)

    def test_workflow_exact_declared_derivation_and_cleanups(self):
        module = load('joined_test_workflow', HERE / 'workflow.py')
        raw = (ROOT / module.OLD_PATH).read_bytes()
        current, proof = module.derive(raw)
        self.assertEqual(current, (ROOT / module.NEW_PATH).read_bytes())
        value = yaml.safe_load(current)
        self.assertEqual(value['on']['push']['branches'], ['astra-a/credit-d1-product-phase-native13-20261030'])
        job = value['jobs']['p21']
        self.assertEqual(job['if'], "github.ref == 'refs/heads/astra-a/credit-d1-product-phase-native13-20261030'")
        steps = job['steps']
        admission = next(i for i, s in enumerate(steps) if module.NEW + '/check.py --runtime' in s.get('run', ''))
        start = next(i for i, s in enumerate(steps) if s.get('name') == 'Start disposable database')
        self.assertLess(admission, start)
        calls = [s for s in steps if module.NEW + '/probe.py' in s.get('run', '')]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['working-directory'], 'writer')
        for name in ('Remove disposable database', 'Preserve exact original JSON report bytes in a bounded compressed log receipt'):
            self.assertEqual(next(s for s in steps if s.get('name') == name)['if'], 'always()')
        self.assertTrue(proof['all_five_package_gates_and_cleanup_unchanged'])


class ArgvControls(unittest.TestCase):
    def setUp(self):
        self.boundary = load('joined_test_argv', HERE / 'argv_boundary.py')
        self.probe = load('joined_test_probe', HERE / 'probe.py')
        self.cli = load('joined_test_check', HERE / 'check.py')
        original = (ROOT / 'scripts/ow04-payment-used-restore-qualification/probe.py').read_text()
        tree = ast.parse(original)
        guard = next(n for n in tree.body if isinstance(n, ast.If)
                     and 'Current used-state restore accepts no arguments' in ast.get_source_segment(original, n))
        self.guard = 'import sys\n' + ast.get_source_segment(original, guard) + '\n'

    def test_exact_old_guard_denies_flags_and_all_baseexceptions_restore_caller(self):
        caller, contents = sys.argv, sys.argv[:]
        try:
            for error in (None, RuntimeError('expected'), SystemExit('expected'), KeyboardInterrupt()):
                sys.argv = ['caller', '--runtime']
                saved = sys.argv
                with self.assertRaisesRegex(SystemExit, 'accepts no arguments'):
                    exec(self.guard, {})
                try:
                    with self.boundary.inherited_imports():
                        exec(self.guard, {})
                        saved.append('mutated old alias')
                        sys.argv = ['replaced', 'inner']
                        if error is not None:
                            raise error
                except BaseException as observed:
                    self.assertIs(observed, error)
                self.assertIs(sys.argv, saved)
                self.assertEqual(saved, ['caller', '--runtime'])
        finally:
            caller[:] = contents
            sys.argv = caller

    def test_actual_cli_parsers_unknown_flags_refuse_before_import(self):
        for module in (self.cli, self.probe):
            with mock.patch.object(module, 'load', side_effect=AssertionError('should not load')), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as got:
                    module.main(['--unknown'])
                self.assertEqual(got.exception.code, 2)

    def test_actual_pending_runtime_and_check_stop_before_erp_import(self):
        source = load('joined_test_pending_source_gate', HERE / 'source_check.py')
        pending = json.loads((HERE / 'CONFIG.json').read_bytes())
        pending['native_augmentation'].update(SOURCE=None, required_source=None)
        gate = SimpleNamespace(check=lambda **kwargs: source.augmentation(pending, required=True))
        with mock.patch.object(self.probe, 'load', return_value=gate), mock.patch.object(self.probe.importlib, 'import_module', side_effect=AssertionError('ERP imported')):
            for entry in (self.probe.check, lambda: self.probe.main(['--check'])):
                with self.assertRaisesRegex(ValueError, 'CLOSED_REVIEWED_NATIVE_AUGMENTATION_REQUIRED'):
                    entry()
            with mock.patch.object(self.cli, 'load', return_value=self.probe):
                with self.assertRaisesRegex(ValueError, 'CLOSED_REVIEWED_NATIVE_AUGMENTATION_REQUIRED'):
                    self.cli.main(['--runtime'])

    def test_runtime_and_lazy_admission_actual_parsers_with_faithful_guard_doubles(self):
        # Execute actual new runtime/parser code. Only inherited ERP imports are
        # replaced by import guards/doubles; this is not a Native execution.
        events = []
        engine_body = self.guard + '\nfrom types import SimpleNamespace\npackage=SimpleNamespace(run=lambda mode: None)\n'
        component_body = self.guard + '\nexercise=lambda *args: None\n'
        def admitted(*args):
            exec(self.guard, {})  # deferred source()/admission import guard
            events.append('lazy-admission')
            return {'status': 'TEST_IMPORT_ONLY', 'qualified_parent': {}}
        def dispatch(name, path):
            if path.name == 'source_check.py':
                return SimpleNamespace(check=lambda **kw: events.append('source-before-runtime'))
            if path.name == 'argv_boundary.py':
                return self.boundary
            if path == ROOT / 'scripts/current-credit-de-native-qualification/derive.py':
                return SimpleNamespace(derive=lambda raw: (engine_body, {}))
            if path == HERE / 'derive.py':
                return SimpleNamespace(native_runner=lambda raw: (component_body, {}))
            if path.name == 'factory.py':
                return SimpleNamespace(business=lambda value: value)
            if path.name == 'native_runner.py':
                exec(self.guard, {})
                return SimpleNamespace(scheduler_quiet=object())
            if path.name == 'admission.py':
                return SimpleNamespace(admitted=admitted)
            self.fail('undeclared local double ' + str(path))
        caller, contents = sys.argv, sys.argv[:]
        try:
            with mock.patch.object(self.probe, 'load', side_effect=dispatch), mock.patch.object(self.probe.importlib, 'import_module', return_value=object()):
                for flag in ('--runtime', '--check'):
                    sys.argv = ['caller', flag]
                    saved = sys.argv
                    with contextlib.redirect_stdout(io.StringIO()):
                        if flag == '--runtime':
                            with mock.patch.object(self.cli, 'load', return_value=self.probe):
                                self.cli.main([flag])
                        else:
                            self.probe.main([flag])
                    self.assertIs(sys.argv, saved)
                    self.assertEqual(saved, ['caller', flag])
            self.assertEqual(events.count('source-before-runtime'), 2)
            self.assertEqual(events.count('lazy-admission'), 2)
        finally:
            caller[:] = contents
            sys.argv = caller


if __name__ == '__main__':
    unittest.main()
