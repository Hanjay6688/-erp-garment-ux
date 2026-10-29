"""Source/API/closed import controls only; no database or fabricated Originals."""
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import ast
import contextlib
import copy
import gzip
import importlib.util
import io
import json
import sys
import unittest
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'scripts/current-credit-e1-native-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SourceControls(unittest.TestCase):
    def test_new_source_closes_every_parent_and_child_file_without_runtime_credit(self):
        source = load('e1_test_current_admission', HERE / 'admission.py').source_only()
        self.assertEqual(len(source['frozen_D1_source']['files']), 174)
        self.assertFalse(source['production_go'])
        self.assertEqual(source['actual_executions'], 0)

    def test_private_old_admission_exactly_two_routes_and_one_historical_endpoint(self):
        module = load('e1_test_current_private', HERE / 'admission.py')
        derive = load('e1_test_current_derivation', HERE / 'derive.py')
        raw = (OLD / 'admission.py').read_bytes()
        current, proof = derive.admission(raw)
        for before, after in reversed(derive.CHANGES):
            self.assertEqual(current.count(after), 1)
            current = current.replace(after, before, 1)
        self.assertEqual(current.encode(), raw)
        legacy, _ = module.legacy()
        parent = '17ac1eeb5833cbf2a786194fe3bfbba6628a1ff8'
        old_raw = (ROOT / 'scripts/current-credit-de-native-qualification/admission.py').read_bytes()
        text, scope = legacy.historical_D1_admission(old_raw, parent)
        self.assertEqual(scope['counted_changes'], 1)
        self.assertEqual(scope['fixed_historical_diff_head'], parent)
        self.assertIn("old.admitted(ROOT, ROOT/'scripts/current-credit-d1-product-phase-native13-qualification'", derive.admission(raw)[0])
        self.assertEqual(proof['counted_source_routing_changes'], 2)
        self.assertIsNotNone(compile(text, '<historical-parent>', 'exec'))

    def test_full_current_child_closure_precedes_any_historical_scope_intake(self):
        module = load('e1_test_outer_scope_first', HERE / 'admission.py')
        gate = SimpleNamespace(selected=lambda cfg: {})
        with mock.patch.object(module, 'load', return_value=gate), mock.patch.object(module, 'source_only', side_effect=ValueError('CURRENT_E_DELTA_REFUSED')), mock.patch.object(module, 'legacy', side_effect=AssertionError('historical intake too early')):
            with self.assertRaisesRegex(ValueError, 'CURRENT_E_DELTA_REFUSED'):
                module.admitted(object(), {})

    def test_API_exact_argument_and_body_reject_drift_without_import(self):
        api = load('e1_test_current_api', HERE / 'api_check.py')
        proof = api.check()
        self.assertGreater(proof['function_bodies'], 10)
        self.assertEqual(proof['actual_Native_cases'], 0)
        declaration = json.loads((HERE / 'API.json').read_bytes())
        path, pin = next(iter(declaration['files'].items()))
        raw = (ROOT / path).read_bytes()
        wrong = copy.deepcopy(pin['functions'])
        next(iter(wrong.values()))['arguments'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'RETAINED_API_CHANGED'):
            api.functions(raw, wrong)

    def test_feba_callback_exact_seventeen_IDs_and_other_sixteen_bodies(self):
        origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
        path = 'scripts/cp7_credit_correction_de/e_cases.py'
        before = (HERE / 'evidence/e_cases.before_feba.py.txt').read_bytes()
        helper = load('e1_test_exact_feba_callback_scope', ROOT / 'scripts/current-credit-e1-late-failure-successor/source_check.py')
        proof = helper.derivation(before, (ROOT / path).read_bytes())
        self.assertFalse(proof['changes_outside_late_failure'])
        self.assertTrue(proof['other_sixteen_callback_bodies_unchanged'])
        self.assertEqual(proof['new_cases_sha256'], origin['feba_case_sha256'])
        self.assertEqual(len(proof['all_seventeen_case_ids']), 17)

    def test_nine_E_leaves_and_lawful_two_PCS_alias_preserve_money_oracles(self):
        from hashlib import sha256
        origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
        self.assertEqual(len(origin['financial_E_runtime_leaves_unchanged']), 9)
        for name, pin in origin['financial_E_runtime_leaves_unchanged'].items():
            self.assertEqual(sha256((ROOT / 'scripts/cp7_credit_correction_de' / name).read_bytes()).hexdigest(), pin)
        e = (ROOT / 'scripts/cp7_credit_correction_de/e_cases.py').read_text()
        de = (ROOT / 'scripts/cp7_credit_correction_de/cases.py').read_text()
        fixture = (ROOT / 'scripts/cp7_credit_correction_de/native_fixture.py').read_text()
        self.assertIn('fixture,basic,native=de.fixture,de.basic,de.native', e)
        self.assertIn("de.post(cur,pair,'250.00')", e)
        self.assertIn('from cp7_credit_correction_de import native_fixture as fixture', de)
        self.assertIn('x["return_payload"]["items"][0]["qty_pcs"] = "2"', fixture)
        transition = json.loads((HERE / 'TRANSITION.json').read_bytes())
        self.assertEqual(transition['upstream_250_path']['initial_credit'], '200.00')
        self.assertEqual(transition['upstream_250_path']['target_net'], '500.00')
        self.assertFalse(transition['parent_Native13_rerun_after_E_install'])

    def test_unchanged_complete_six_change_engine_and_real_carry80_used_witness(self):
        module = load('e1_test_retained_vendor_derive', OLD / 'derive.py')
        anchors = load('e1_test_retained_D1_engine_anchors', ROOT / 'scripts/current-credit-de-native-qualification/derive.py')
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text, proof = module.derive(raw)
        for before, after in reversed(anchors.REPLACEMENTS):
            self.assertEqual(text.count(after), 1)
            text = text.replace(after, before, 1)
        self.assertEqual(text.encode(), raw)
        self.assertEqual(proof['counted_changes'], 6)
        component = (OLD / 'component.py').read_text()
        for exact in ("business.basic.apply(cur, pair, '80.00')", "'550.00', '80.00', '120.00'",
                      'conn.commit()', 'product.rollback_delta_preuse(cur, state)',
                      "str(error) != product.USED_ERROR", 'catalog._data(cur) != before_data'):
            self.assertIn(exact, component)

    def test_workflow_null_gate_precedes_setup_fetch_database_and_cleanup_remains(self):
        module = load('e1_test_current_workflow', HERE / 'workflow.py')
        expected, _ = module.derive(yaml.safe_load((ROOT / module.PARENT).read_text()))
        current = yaml.safe_load((ROOT / module.PATH).read_text())
        self.assertEqual(current, expected)
        job = current['jobs']['p21']; steps = job['steps']
        self.assertIn("p=Path('" + module.NS + "')", steps[1]['run'])
        self.assertIn("p/'gate.py'", steps[1]['run'])
        self.assertEqual(current['on']['push']['branches'], [module.BRANCH])
        self.assertEqual(job['if'], "github.ref == 'refs/heads/" + module.BRANCH + "'")
        start = next(i for i, row in enumerate(steps) if row.get('name') == 'Start disposable database')
        self.assertLess(next(i for i, row in enumerate(steps) if module.NS + '/check.py' in row.get('run', '')), start)
        for name in ('Preserve exact original JSON report bytes in a bounded compressed log receipt', 'Remove disposable database'):
            self.assertEqual(next(row for row in steps if row.get('name') == name)['if'], 'always()')


class ClosedControls(unittest.TestCase):
    def setUp(self):
        self.gate = load('e1_test_current_gate', HERE / 'gate.py')
        self.pending = json.loads((HERE / 'CONFIG.json').read_bytes())
        self.pending.update(accepted_D1=None, accepted_raw_parent=None, required_qualified_parent=None)

    def test_every_missing_or_half_pin_refuses_before_original_gate(self):
        for provided in ({}, {'accepted_D1': {}}, {'accepted_D1': {}, 'required_qualified_parent': {}},
                         {'accepted_raw_parent': {}, 'required_qualified_parent': {}}):
            cfg = dict(self.pending, **provided)
            with mock.patch.object(self.gate, 'original', side_effect=AssertionError('too early')):
                with self.assertRaisesRegex(ValueError, 'CLOSED_ROOT_TERMINAL'):
                    self.gate.selected(cfg)

    def test_actual_default_and_fetch_runtime_closed_without_product_or_GET(self):
        probe = load('e1_test_current_probe', HERE / 'probe.py')
        fetch = load('e1_test_current_fetch', HERE / 'fetch_prerequisite.py')
        read_bytes = Path.read_bytes
        pending = json.dumps(self.pending).encode()
        def read(path):
            return pending if path == HERE / 'CONFIG.json' else read_bytes(path)
        with mock.patch.object(Path, 'read_bytes', read), mock.patch('subprocess.check_output', side_effect=AssertionError('GET before gate')), mock.patch('importlib.import_module', side_effect=AssertionError('product before gate')):
            for entry in (probe.runtime, fetch.main):
                with self.assertRaisesRegex(ValueError, 'CLOSED_ROOT_TERMINAL'):
                    entry()

    def test_unknown_flags_refuse_before_any_import_boundary(self):
        for name in ('probe.py', 'check.py'):
            module = load('e1_test_unknown_' + name, HERE / name)
            with mock.patch.object(module, 'load', side_effect=AssertionError('before parser')), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    module.main(['--unknown'])
                self.assertEqual(caught.exception.code, 2)

    def test_retained_actual_failed_a994_never_becomes_current_qualified_parent(self):
        raw = gzip.decompress((OLD / 'retained_a994/CP7_CREDIT_DE_NATIVE13_CASES.json.gz').read_bytes())
        proof = self.gate.retained_failure(self.pending, raw)
        self.assertFalse(proof['usable_prerequisite'])
        self.assertEqual(proof['fresh_E_cases_credited'], 0)
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_BYTES_CHANGED'):
            self.gate.retained_failure(self.pending, raw + b' ')

    def test_all_BaseException_paths_restore_caller_argv_identity_and_contents(self):
        boundary = load('e1_test_current_argv', HERE / 'argv_boundary.py')
        caller, contents = sys.argv, sys.argv[:]
        try:
            for error in (RuntimeError('test'), SystemExit('test'), KeyboardInterrupt()):
                sys.argv = ['caller', '--runtime']; original = sys.argv
                try:
                    with boundary.inherited_imports():
                        self.assertEqual(sys.argv, ['caller'])
                        original.append('mutated alias')
                        sys.argv = ['replaced']
                        raise error
                except BaseException as got:
                    self.assertIs(got, error)
                self.assertIs(sys.argv, original)
                self.assertEqual(original, ['caller', '--runtime'])
        finally:
            caller[:] = contents; sys.argv = caller


if __name__ == '__main__':
    unittest.main()
