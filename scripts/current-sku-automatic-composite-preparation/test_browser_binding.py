"""Closed binding and full source/output controls; no actual Root or ERP."""
from contextlib import chdir
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import CodeType, FunctionType, ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import subprocess
import unittest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


binding = load('current_browser_binding_control', HERE / 'browser_binding.py')


def function(source, name, namespace):
    compiled = compile(source, 'whole_original_fixture_compiler_context', 'exec', dont_inherit=True)
    codes = [code for code in compiled.co_consts if isinstance(code, CodeType) and code.co_name == name]
    if len(codes) != 1:raise AssertionError('One original function required')
    return FunctionType(codes[0], namespace, name)


class BrowserBindingControls(unittest.TestCase):
    def test_browser_and_complete_output_consumer_bind_the_same_exact_current_Afui(self):
        self.assertEqual(binding.AFUI_HEAD, binding.entry.report_io.COMPLETE_ORIGINALS_HEAD)
        actual_tree = subprocess.check_output(['git', '-C', str(HERE.parents[1]), 'rev-parse',
                                              binding.AFUI_HEAD + '^{tree}'], text=True).strip()
        self.assertEqual(binding.AFUI_TREE, actual_tree)

    def test_complete_real_journeys_use_eight_reversible_current_routes(self):
        prepare = load('current_complete_journey_control', HERE / 'browser_prepare.py')
        text, proof = prepare.derive()
        self.assertEqual(text.encode(), (HERE / 'browser.mjs').read_bytes())
        self.assertEqual(proof['exact_reversible_routes'], 8)
        self.assertTrue(proof['complete_original_recovered'])
        self.assertIn('entire_current_source_admission:actual', text)
        self.assertIn("'nilai sumber Rp 68,07'", text)
        self.assertIn('inverseOracle(final,f)', text)
        self.assertIn('session_leaks:final.current_session_leaks', text)
        self.assertIn('current_observations.push({step,state:value})', text)
        with self.assertRaisesRegex(ValueError, 'EXACT_COMPLETE_REAL_APP_JOURNEYS_REQUIRED'):
            prepare.derive(prepare.ORIGINAL.read_bytes() + b'\n')

    def test_real_closed_gates_precede_every_source_or_fixture_entry(self):
        source = load('current_browser_source_control', HERE / 'browser_source.py')
        fixture = load('current_browser_fixture_control', HERE / 'browser_fixture.py')
        with patch.object(Path, 'is_file', side_effect=AssertionError('Frozen input inspected')), \
                patch.object(binding.subprocess, 'check_output', side_effect=AssertionError('Git inspected')):
            for call in (source.check, fixture.main, lambda: binding.fixture(object())):
                with self.subTest(call=call), self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                    call()
            with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                with binding.scope():self.fail('Unadmitted browser context entered')

    def test_actual_constructor_and_two_output_routes_recover_complete_frozen_source(self):
        d = load('current_browser_retained_source_control', HERE.parent / 'current-sku-managed-recovery-native27-qualification/derive.py')
        raw, _ = d.derive('browser_fixture')
        text, proof = binding.derive_fixture(raw.encode())
        self.assertEqual(proof['output_expression_routes'], 2)
        self.assertTrue(proof['complete_original_recovered'])
        self.assertNotIn('blob=', text)
        with self.assertRaisesRegex(ValueError, 'EXACT_COMPLETE_BROWSER_FIXTURE_REQUIRED'):
            binding.derive_fixture(raw.encode() + b'\n')
        actual = load('current_browser_actual_constructor_control', HERE.parent / 'current-sku-combined-fixture-followup/derive.py')
        self.assertEqual(actual.derive('fixture')[0], d.derive('fixture')[0])

    def test_private_current_census_preserves_complete_legacy_bytes_without_old_product(self):
        d = load('current_browser_full_census_source_control', HERE.parent / 'current-sku-managed-recovery-native27-qualification/derive.py')
        raw, _ = d.derive('browser_fixture');text, _ = binding.derive_fixture(raw.encode())
        raw_helper = subprocess.check_output(['git', '-C', str(HERE.parents[1]), 'show',
            binding.entry.report_io.COMPLETE_ORIGINALS_HEAD + ':scripts/cp7_accessory_nonpayable/complete_original_io.py'])
        self.assertEqual((len(raw_helper), sha256(raw_helper).hexdigest()), binding.entry.report_io.COMPLETE_ORIGINALS_PIN)
        with TemporaryDirectory() as source_directory:
            source = Path(source_directory) / 'complete_original_io.py'
            source.write_bytes(raw_helper)
            helper = load('current_browser_exact_streamed_complete_output_control', source)
        catalog = {str(index): {'complete_model_field': ['unicode café', index]} for index in range(22)}
        data = {'erp.explicit_model': [{'unknown_nested_original_field': {'decimal': Decimal('.01')}}],
                'sequence:erp.explicit_model_id_seq': ['7', True]}
        actual_catalog = SimpleNamespace(_catalog_rows=lambda _: catalog, _data=lambda _: data)
        current_product = SimpleNamespace(runtime=lambda: (None, None, None, None, actual_catalog), TABLES=('erp.explicit_model',))
        class WrongProduct:
            TABLES = ()
            def runtime(self):raise AssertionError('Old product catalogue was used')
        common = dict(Path=Path, re=__import__('re'), json=json, sha256=sha256,
                      f=SimpleNamespace(admin=lambda _: None),
                      digest=lambda value: sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest())
        original = ModuleType('explicit_original_browser_fixture_model')
        original.__dict__.update(common, product=WrongProduct(), _COMPLETE_IO=binding.pretty_originals(helper))
        original.census = function(text, 'census', original.__dict__)
        current = binding.entry.money_binding.private_module(original, dict(product=current_product))
        expected_namespace = dict(common, product=current_product)
        old = function(raw, 'census', expected_namespace)
        with TemporaryDirectory() as directory:
            first, second = Path(directory) / 'old', Path(directory) / 'new';first.mkdir();second.mkdir()
            with chdir(first):
                legacy = old(object(), 'SKU29_DESKTOP_MODEL_CENSUS')
                before = Path(legacy['raw_evidence']['path']).read_bytes()
            with chdir(second):
                observed = current.census(object(), 'SKU29_DESKTOP_MODEL_CENSUS')
                after = Path(observed['raw_evidence']['path']).read_bytes()
            self.assertEqual(before, after)
            self.assertEqual(legacy, observed)
            self.assertIs(observed['data_and_sequences'], data)
        self.assertIs(current.census.__code__, original.census.__code__)
        self.assertIs(current.census.__globals__, current.__dict__)
        self.assertIsInstance(original.product, WrongProduct)


if __name__ == '__main__':unittest.main()
