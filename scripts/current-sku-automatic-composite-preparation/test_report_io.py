"""Exact new output routes and source ownership, with no ERP/module imports."""
import ast
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
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


io = load('current_complete_report_output', HERE / 'report_io.py')


class OutputRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        cls.engines = {}
        for name, path in (
            ('mandor17', 'scripts/current-mandor-shop-native-qualification/package_engine.py'),
            ('money19', 'scripts/current-sku-money-composite-preparation/package.py'),
        ):
            cls.engines[name] = load('exact_report_engine_' + name, ROOT / path).derive(original)[0]

    def test_actual_current_Afui_complete_helper_admits_and_old_or_changed_bytes_refuse(self):
        current = '74e7a6bc0754b7b3772f4b47095b518a41b972da'
        old = '92a376091a1d1ea9901648e614f3e5212677a81f'
        source = ':scripts/cp7_accessory_nonpayable/complete_original_io.py'
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', current + source])
        previous = subprocess.check_output(['git', '-C', str(ROOT), 'show', old + source])
        self.assertEqual(io.COMPLETE_ORIGINALS_HEAD, current)
        self.assertNotEqual(raw, previous)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'complete_original_io.py'
            with patch.object(io, 'COMPLETE_ORIGINALS_PATH', path):
                path.write_bytes(raw)
                actual = io.complete_originals()
                self.assertTrue(callable(actual.save_sorted))
                self.assertTrue(callable(actual.copy_exact))
                self.assertTrue(callable(actual.save_gzip_sorted))
                with tempfile.TemporaryDirectory() as output:
                    target = Path(output) / 'whole-current-state.json'
                    value = {'all_values': [None, Decimal('1.23'), 'café', 2**70]}
                    receipt = actual.save_sorted(target, value, 'MODEL_ORIGINAL_CONFLICT')
                    expected = (json.dumps(value, sort_keys=True, default=str) + '\n').encode()
                    self.assertEqual(target.read_bytes(), expected)
                    self.assertEqual(receipt, {'name': target.name, 'bytes': len(expected),
                                              'sha256': sha256(expected).hexdigest()})
                for invalid in (previous, raw + b'\n'):
                    path.write_bytes(invalid)
                    with self.assertRaisesRegex(ValueError, 'EXACT_AFUI_COMPLETE_ORIGINAL_COPY_SOURCE'):
                        io.complete_originals()

    def test_each_complete_engine_has_exactly_one_reversible_output_route(self):
        for name, before in self.engines.items():
            with self.subTest(engine=name):
                after, proof = io.derive_packet(before, name)
                self.assertEqual(after.replace(io.HELPER + '(OUT,report)', io.PACKET_BEFORE, 1), before)
                self.assertEqual(proof['exact_save_expression_routes'], 1)
                # Execute only that exact output expression, not the owning
                # engine's installation or business code.
                tree = ast.parse(after)
                expressions = [node for node in ast.walk(tree) if isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == io.HELPER]
                self.assertEqual(len(expressions), 1)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / 'whole.json'
                    report = dict(status='MODEL_OUTPUT_ONLY', number=2**70,
                                  text='Harga \u2192 \u20ac', amount=Decimal('40.01'))
                    scope = dict(OUT=path, report=report, **{io.HELPER: io.write_complete})
                    exec(compile(ast.Module(body=expressions, type_ignores=[]), 'exact-output-expression-only', 'exec'), scope)
                    self.assertEqual(path.read_bytes(), (json.dumps(report, indent=2, default=str) + '\n').encode())

    def test_unknown_engine_or_altered_complete_source_refuses(self):
        for kind, source in (('other', self.engines['mandor17']),
                             ('mandor17', self.engines['mandor17'] + '\n')):
            with self.assertRaisesRegex(ValueError, 'EXACT_COMPLETE_PREPARED_ENGINE'):
                io.derive_packet(source, kind)

    def test_encoder_is_exact_and_failure_preserves_previous_complete_file(self):
        self.assertEqual(io.primitive_contract()['encoder_source_head'], 'e0cfa98382e977933d63e9f828de17a0faba9ef9')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'group.json'
            value = dict(rows=[dict(body='large immutable SQL ' * 20000)] * 3,
                         when=datetime(2026, 11, 4, tzinfo=timezone.utc),
                         number=Decimal('0.000001'), nan=float('nan'))
            io.write_complete(path, value)
            expected = (json.dumps(value, indent=2, default=str) + '\n').encode()
            self.assertEqual(path.read_bytes(), expected)
            cyclic = []
            cyclic.append(cyclic)
            with self.assertRaisesRegex(ValueError, 'Circular reference'):
                io.write_complete(path, cyclic)
            self.assertEqual(path.read_bytes(), expected)
            self.assertEqual(len(list(Path(directory).glob('*.partial'))), 1)

    def module(self, directory):
        path = Path(directory) / 'writer/scripts/cp6_au_r1_probe.py'
        path.parent.mkdir(parents=True)
        raw = (ROOT / 'scripts/cp6_au_r1_probe.py').read_bytes()
        path.write_bytes(raw)
        module = ModuleType('source_exact_serializer_interface_model')
        module.__file__ = str(path)
        module.OUT = Path(directory) / 'original-output'
        module.json = json
        module.save = FunctionType(io.function_code(raw.decode(), str(path), 'save'), module.__dict__)
        return module

    def test_actual_full_source_compiler_group_scope_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            module = self.module(directory)
            original = module.save
            value = dict(model_only=True, large='x' * 300000, unit=Decimal('35.00'))
            with io.group_scope(module) as proof:
                module.save('CURRENT_GROUP', value)
                self.assertEqual((module.OUT / 'CURRENT_GROUP.json').read_bytes(),
                                 (json.dumps(value, indent=2, default=str) + '\n').encode())
                self.assertTrue(proof['complete_original_group_source_recovered'])
                with self.assertRaisesRegex(ValueError, 'ONE_GROUP_SAVE_SCOPE'):
                    with io.group_scope(module):
                        self.fail('Nested output scope cannot be entered')
            self.assertIs(module.save, original)
            self.assertNotIn(io.HELPER, module.__dict__)

    def test_group_scope_rejects_same_code_with_wrong_globals(self):
        with tempfile.TemporaryDirectory() as directory:
            module = self.module(directory)
            module.save = FunctionType(module.save.__code__, dict(module.__dict__))
            with self.assertRaisesRegex(ValueError, 'ACTUAL_OWNING_R1_COMPILER_CONTEXT'):
                with io.group_scope(module):
                    self.fail('A different globals dictionary is not the owning module')
            self.assertNotIn(io.HELPER, module.__dict__)


if __name__ == '__main__':
    unittest.main()
