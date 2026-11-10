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
    def test_actual_shared_helpers_keep_exact_qualified_ancestor_and_money_bytes(self):
        legacy = binding.ROOT.parent / 'qualified-sku090b'
        with patch.dict('os.environ', JOIN_QUALIFIED_SKU_ROOT=str(legacy)):
            for name in ('be', 'bf'):
                module = SimpleNamespace(__file__=str(legacy / 'scripts' / ('cp6_' + name + '_probe.py')))
                proof = binding.native_helper_origin(module, name)
                self.assertTrue(proof['identical_current_money_helper'])
                self.assertEqual(proof['actual_qualified_ancestor']['head'], '090b85d3fcb738d3e694d4329d306f199a686eb8')

    def test_foreign_helper_is_refused_even_if_its_filename_matches(self):
        with TemporaryDirectory() as directory:
            module = SimpleNamespace(__file__=str(Path(directory) / 'cp6_be_probe.py'))
            with self.assertRaisesRegex(ValueError, 'REAL_FROZEN_NATIVE_HELPER'):
                binding.native_helper_origin(module, 'be')

    def test_shared_helper_source_change_is_refused(self):
        path = binding.entry.FROZEN_AFUI / 'scripts/cp6_be_probe.py'
        original = Path.read_bytes
        def changed(p): return b'changed shared helper' if p == path else original(p)
        with patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(ValueError, 'NATIVE_HELPER_SOURCE_CHANGED'):
                binding.native_helper_origin(SimpleNamespace(__file__=str(path)), 'be')

    def test_actual_browser_donor_keeps_pinned_constructor_separate_from_money_constructor(self):
        root, deriver, browser_text, native_text = binding.fixture_sources()
        self.assertEqual(root, binding.entry.FROZEN_PARENT)
        self.assertEqual(binding.entry.admission.pin(native_text.encode()), binding.preflight.PINS['fixture'])
        self.assertEqual(binding.entry.admission.pin(browser_text.encode()), binding.preflight.PINS['browser_fixture'])
        relative, expected = deriver.SOURCES['fixture']
        actual = (root / relative).read_bytes()
        money = (binding.entry.FROZEN_SKU / relative).read_bytes()
        self.assertEqual(sha256(actual).hexdigest(), expected)
        self.assertNotEqual(actual, money)
        self.assertIn(b'def opening(cur,product,qty,unit,day,location=None):', money)

    def test_wrong_money_donor_is_refused_instead_of_repinning_the_browser_fixture(self):
        with patch.object(binding.entry, 'FROZEN_PARENT', binding.entry.FROZEN_SKU):
            with self.assertRaisesRegex(ValueError, 'SKU23_FROZEN_SOURCE_CHANGED'):
                binding.fixture_sources()

    def test_browser_graph_and_complete_output_bind_the_same_exact_current_Afui(self):
        graph = load('current_graph_intake_afui_source_control', HERE / 'source_intake.py')
        source = binding.entry.report_io
        actual_tree = subprocess.check_output(['git', '-C', str(HERE.parents[1]), 'rev-parse',
                                              source.COMPLETE_ORIGINALS_HEAD + '^{tree}'], text=True).strip()
        self.assertEqual(source.COMPLETE_ORIGINALS_TREE, actual_tree)
        for entry in (binding.entry, graph.entry):
            with patch.object(entry, 'frozen') as frozen:
                entry.frozen_afui()
                frozen.assert_called_once_with(entry.FROZEN_AFUI, source.COMPLETE_ORIGINALS_HEAD, actual_tree)

    def test_complete_real_journeys_use_exact_current_writer_routes(self):
        prepare = load('current_complete_journey_control', HERE / 'browser_prepare.py')
        text, proof = prepare.derive()
        self.assertEqual(text.encode(), (HERE / 'browser.mjs').read_bytes())
        self.assertEqual(proof['exact_reversible_routes'], 11)
        self.assertEqual(text.count('cwd:WRITER'), 2)
        self.assertIn("const WRITER=resolve(ROOT,'../writer')", text)
        self.assertIn("['--check-browser-source']", text)
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
        expected_namespace = dict(common, product=current_product)
        old = function(raw, 'census', expected_namespace)
        with TemporaryDirectory() as directory:
            workspace = Path(directory).resolve()
            reference, writer, auditor = (workspace / name for name in ('reference', 'writer', 'auditor'))
            for checkout in (reference, writer, auditor):
                checkout.mkdir()
            current = binding.entry.money_binding.private_module(
                original, dict(product=current_product, _BROWSER_PROOF_ROOT=auditor))
            with chdir(reference):
                legacy = old(object(), 'SKU29_DESKTOP_MODEL_CENSUS')
                before = Path(legacy['raw_evidence']['path']).read_bytes()
            with chdir(writer):
                observed = current.census(object(), 'SKU29_DESKTOP_MODEL_CENSUS')
            relative = Path(observed['raw_evidence']['path'])
            self.assertFalse((writer / relative).exists())
            gate = load('current_browser_exact_asset_consumer_control', HERE / 'browser_gate.py')
            after = gate.asset(auditor / 'cp6-proof/t3', relative.name)
            self.assertEqual(before, after)
            self.assertEqual(legacy, observed)
            self.assertIs(observed['data_and_sequences'], data)
        self.assertIs(current.census.__code__, original.census.__code__)
        self.assertIs(current.census.__globals__, current.__dict__)
        self.assertIsInstance(original.product, WrongProduct)


if __name__ == '__main__':unittest.main()
