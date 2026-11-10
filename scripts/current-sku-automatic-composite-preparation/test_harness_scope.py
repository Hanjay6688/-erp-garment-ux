"""Cold nested imports must use the exact harness without changing writer cwd."""
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
import importlib
import importlib.util
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('automatic_harness_import_controls', HERE / 'module_scope.py')
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


@contextmanager
def sources():
    saved = {n: sys.modules[n] for n in scope.HARNESS_NAMES if n in sys.modules}
    before_path, before_meta, cwd = list(sys.path), list(sys.meta_path), Path.cwd()
    for name in saved: sys.modules.pop(name)
    try:
        with tempfile.TemporaryDirectory() as directory:
            root, wrong = Path(directory) / 'accepted', Path(directory) / 'wrong'
            (root / 'scripts/current-final-s03-sku-s05-preparation').mkdir(parents=True)
            wrong.mkdir()
            contract = root / 'scripts/current-final-s03-sku-s05-preparation/parent_import.py'
            contract.write_text('def owning_harness():\n    names=' + repr(scope.HARNESS_NAMES) + '\n')
            for name in scope.HARNESS_NAMES:
                (root / 'scripts' / (name + '.py')).write_text("marker='accepted'\n")
                (wrong / (name + '.py')).write_text("marker='wrong'\n")
            (root / 'scripts/cp6_t3_package_run.py').write_text(
                'import sys\nfrom pathlib import Path\n'
                + 'sys.path.insert(0,' + repr(str(wrong)) + ')\n'
                + 'import cp6_aw_probe\nmarker=cp6_aw_probe.marker\nobserved_cwd=Path.cwd()\n')
            sys.path.insert(0, str(wrong))
            yield root, wrong, contract
    finally:
        for name in scope.HARNESS_NAMES: sys.modules.pop(name, None)
        sys.modules.update(saved)
        sys.path[:] = before_path
        assert sys.meta_path == before_meta
        assert Path.cwd() == cwd


class FrozenHarnessImports(unittest.TestCase):
    def test_real_nested_plain_import_beats_cwd_path_side_effect(self):
        with sources() as (root, wrong, _):
            cwd = Path.cwd()
            with scope.harness_scope(root):
                with scope.harness_scope(root):
                    package = importlib.import_module('cp6_t3_package_run')
                    self.assertEqual(package.marker, 'accepted')
                    self.assertEqual(package.observed_cwd, cwd)
                    self.assertEqual(Path(sys.modules['cp6_aw_probe'].__file__), root / 'scripts/cp6_aw_probe.py')
                self.assertIs(importlib.import_module('cp6_aw_probe'), sys.modules['cp6_aw_probe'])
            self.assertEqual(sys.path[0], str(wrong))

    def test_foreign_loaded_harness_is_refused_and_not_replaced(self):
        with sources() as (root, wrong, _):
            for name in scope.HARNESS_NAMES:
                foreign = ModuleType(name);foreign.__file__ = str(wrong / (name + '.py'))
                sys.modules[name] = foreign
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'FROZEN_HARNESS_COLLISION:' + name):
                    with scope.harness_scope(root): self.fail('foreign source admitted')
                self.assertIs(sys.modules.pop(name), foreign)

    def test_import_failure_removes_resolver_without_changing_cwd(self):
        with sources() as (root, _, _):
            (root / 'scripts/cp6_aw_probe.py').write_text("raise RuntimeError('original failure')\n")
            with self.assertRaisesRegex(RuntimeError, 'original failure'):
                with scope.harness_scope(root): importlib.import_module('cp6_t3_package_run')

    def test_incomplete_contract_missing_file_and_symlink_are_refused(self):
        with sources() as (root, wrong, contract):
            original = contract.read_bytes()
            contract.write_text('def owning_harness():\n    names=()\n')
            with self.assertRaisesRegex(ValueError, 'COMPLETE_HARNESS_IMPORT_CONTRACT'):
                with scope.harness_scope(root): self.fail('incomplete contract')
            contract.write_bytes(original)
            target = root / 'scripts/cp6_aw_probe.py';target.unlink()
            with self.assertRaisesRegex(ValueError, 'REGULAR_HARNESS_SOURCE_REQUIRED'):
                with scope.harness_scope(root): self.fail('missing source')
            target.symlink_to(wrong / 'cp6_aw_probe.py')
            with self.assertRaisesRegex(ValueError, 'REGULAR_HARNESS_SOURCE_REQUIRED'):
                with scope.harness_scope(root): self.fail('symlink source')


if __name__ == '__main__': unittest.main()
