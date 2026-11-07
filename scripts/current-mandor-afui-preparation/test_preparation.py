"""Current parent/caller source controls, without running a business case."""
import ast
from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import FunctionType, ModuleType
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


routes = load('mandor_current_preparation_routes_control', HERE / 'routes.py')
io = load('mandor_current_preparation_output_control', HERE / 'report_io.py')


class NoInspection:
    def __getattribute__(self, name):
        raise AssertionError('Unaccepted parent was inspected')


class CurrentMandorPreparation(unittest.TestCase):
    def original(self, name):
        return subprocess.check_output(['git', '-C', str(ROOT), 'show', routes.BASE + ':' + routes.NS + name])

    def test_all_reviewed_callers_are_exact_bounded_source_routes(self):
        for name in routes.PINS:
            raw = self.original(name)
            after, proof = routes.derive(raw, name)
            self.assertEqual((ROOT / routes.NS / name).read_bytes(), after)
            restored = after.decode()
            for before, changed in reversed(routes.replacements(name)):
                restored = restored.replace(changed, before, 1)
            self.assertEqual(restored.encode(), raw)
            self.assertTrue(proof['whole_original_caller_recovered'])
            self.assertEqual([ast.dump(n) for n in ast.walk(ast.parse(raw)) if isinstance(n, ast.Assert)],
                             [ast.dump(n) for n in ast.walk(ast.parse(after)) if isinstance(n, ast.Assert)])
            with self.assertRaisesRegex(ValueError, 'EXACT_PREPARED_CALLER_SOURCE'):
                routes.derive(raw + b'\n', name)

    def test_package_announcement_preserves_frozen_harness_origin(self):
        identity = load('mandor_identity_regression', ROOT / routes.NS / 'package_identity.py')
        frozen_root = identity.FROZEN
        frozen = load('mandor_frozen_recorder_regression', frozen_root / identity.PATH)
        guard = load('mandor_actual_frozen_guard_regression', frozen_root / 'scripts/current-final-s03-sku-s05-preparation/parent_import.py')
        # Exercise the actual failing origin guard and both real identity
        # recorders without importing unrelated DB-dependent harness modules.
        names = ('cp6_t3_package_run', 'cp6_aw_probe', 'cp6_ax_probe',
                 'cp6_g01_fingerprint', 'cp6_t3_backup_restore_drill',
                 'cp6_t3_release_package', 'cp6_t3_browser', 'cp6_t3_aligned_install')
        modules = {name: ModuleType(name) for name in names}
        for name, module in modules.items():
            module.__file__ = str(frozen_root / 'scripts' / (name + '.py'))
        modules['cp6_t3_package_run'].AUDITOR = frozen_root
        modules['cp6_t3_package_run'].OUT = frozen_root / 'cp6-proof/t3'
        modules['cp6_run_identity'] = frozen
        package = ast.parse((frozen_root / 'scripts/cp6_t3_package_run.py').read_bytes())
        run = next(node for node in package.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
        start = next(i for i, node in enumerate(run.body) if isinstance(node, ast.Import))
        announcement = compile(ast.Module(body=run.body[start:start+2], type_ignores=[]), '<exact-package-announcement>', 'exec')
        path = sys.path[:]
        try:
            with patch.dict(sys.modules, modules), redirect_stdout(StringIO()):
                with identity.scope():
                    exec(announcement, dict(report={}, mode='install'))
                    with self.assertRaisesRegex(ValueError, 'JOIN_OWNING_CP6_HARNESS_ORIGIN_CHANGED:cp6_run_identity:'):
                        guard.owning_harness()
                report = {}
                with io.package_identity_scope(identity):
                    exec(announcement, dict(report=report, mode='install'))
                    self.assertIs(sys.modules['cp6_run_identity'], frozen)
                    self.assertEqual(guard.owning_harness()['cp6_run_identity'], str(frozen_root / identity.PATH))
                self.assertEqual(report['run_identity'], self.owning_identity(identity))
        finally:
            sys.path[:] = path

    def owning_identity(self, identity):
        with identity.scope():
            return sys.modules['cp6_run_identity'].identity('T3_PREP', mode='install')

    def test_pending_current_parent_refuses_before_raw_or_ERP_import(self):
        qualifier = ROOT / routes.NS
        sys.path.insert(0, str(qualifier))
        try:
            admission = load('mandor_current_closed_actual_parent', qualifier / 'admission.py')
            self.assertEqual(admission.PARENT_HEAD, routes.AFUI)
            self.assertIsNone(admission.PARENT_ROOT_PIN)
            self.assertIsNone(admission.RUNTIME_ENTRY)
            with self.assertRaisesRegex(ValueError, 'ACTUAL_AFUI15_ROOT_ACCEPTANCE'):
                admission.parent(NoInspection())
            entry = load('mandor_current_closed_owning_entry', qualifier / 'qualification.py')
            before = set(sys.modules)
            with self.assertRaisesRegex(ValueError, 'ACTUAL_AFUI15_ROOT_ACCEPTANCE'):
                entry.runtime()
            self.assertEqual(set(sys.modules), before)
        finally:
            sys.path.pop(0)

    def test_streaming_adopts_only_the_exact_unchanged_complete_mandor_engine(self):
        package = load('mandor_current_original_whole_package', ROOT / routes.NS / 'package_engine.py')
        raw = (ROOT / package.ORIGINAL).read_bytes()
        original, _ = package.derive(raw)
        changed, proof = io.derive_packet(original, 'mandor17')
        self.assertEqual(changed.replace(io.HELPER + '(OUT,report)', io.PACKET_BEFORE, 1), original)
        authorized = io.derive_parent_install(changed)
        self.assertEqual(authorized.replace(io.PARENT_INSTALL_AFTER, io.PARENT_INSTALL_BEFORE, 1), changed)
        self.assertEqual(authorized.count(io.PARENT_INSTALL_AFTER), 1)
        with self.assertRaisesRegex(ValueError, 'MANDOR_ONE_EXACT_AFUI_INSTALL_AUTHORITY_ROUTE_REQUIRED'):
            io.derive_parent_install(authorized)
        self.assertTrue(proof['financial_cases_and_full_recovery_unchanged'])
        self.assertEqual(proof['actual_ERP_cases'], 0)
        with self.assertRaisesRegex(ValueError, 'EXACT_COMPLETE_PREPARED_ENGINE'):
            io.derive_packet(original + '\n', 'mandor17')

    def test_exact_owning_R1_group_save_restores_code_and_globals_after_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'writer/scripts/cp6_au_r1_probe.py'
            path.parent.mkdir(parents=True)
            path.write_bytes((ROOT / 'scripts/cp6_au_r1_probe.py').read_bytes())
            module = ModuleType('mandor_original_source_save_interface_control')
            module.__file__ = str(path)
            module.OUT = Path(temporary) / 'groups'
            module.json = json
            module.save = FunctionType(io.function_code(path.read_text(), str(path), 'save'), module.__dict__)
            original = module.save
            value = dict(whole='Native catalogue ' * 30000, amount=9)
            with self.assertRaisesRegex(RuntimeError, 'ORIGINAL_FAILURE'):
                with io.group_scope(module):
                    module.save('MANDOR_WHOLE_ORIGINAL', value)
                    raise RuntimeError('ORIGINAL_FAILURE')
            self.assertIs(module.save, original)
            self.assertNotIn(io.HELPER, module.__dict__)
            self.assertEqual((module.OUT / 'MANDOR_WHOLE_ORIGINAL.json').read_bytes(),
                             (json.dumps(value, indent=2, default=str) + '\n').encode())


if __name__ == '__main__':
    unittest.main()
