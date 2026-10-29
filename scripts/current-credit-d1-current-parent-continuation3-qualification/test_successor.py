"""Source/import/CLI controls only; no SQL, runtime receipts or financial PASS fabricated."""
from pathlib import Path
from hashlib import sha256
from unittest import TestCase, main
from unittest.mock import patch
import ast
import builtins
import importlib.util
import json
import os
import subprocess
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'scripts/current-credit-d1-owner-followup-qualification'
CONT = ROOT / 'scripts/current-credit-d1-continuation-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


class CurrentParentControls(TestCase):
    def test_null_gate_refuses_before_runtime_Git_subprocess_or_GET(self):
        original_import = builtins.__import__
        def guard(name, *args, **kwargs):
            if name.startswith(('psycopg', 'cp7_', 'cp6_')):
                raise AssertionError('CLOSED_IMPORTED_RUNTIME:' + name)
            return original_import(name, *args, **kwargs)
        original_read = Path.read_bytes
        def closed_config(path):
            raw = original_read(path)
            if path == HERE / 'CONFIG.json':
                cfg = json.loads(raw); cfg.update(accepted_native13=None, required_qualified_parent=None)
                return json.dumps(cfg).encode()
            return raw
        with patch.object(Path, 'read_bytes', closed_config), patch.object(builtins, '__import__', guard), patch.object(subprocess, 'check_output', side_effect=AssertionError('CLOSED_CALLED_SUBPROCESS')):
            for name, entry in (('check.py', 'run'), ('probe.py', 'runtime'), ('fetch_prerequisite.py', 'main')):
                with self.assertRaisesRegex(ValueError, 'CLOSED'):
                    getattr(load('continuation_current_closed_' + name, HERE / name), entry)()

    def test_actual_owned_two_piece_fixture_API_and_source_guard_import_without_DB(self):
        result = load('continuation_current_real_API_test', HERE / 'api_check.py').check()
        self.assertEqual(result['actual_SQL_statements'], 0)
        self.assertEqual(result['Native_callbacks'], 3)
        self.assertEqual(result['fixture_functions'], 5)

    def test_old43_manifest_and_exact_callbacks_oracles_are_retained(self):
        origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
        self.assertEqual(len(origin['imported_paths']), 35)
        for path, pin in origin['imported_paths'].items():
            raw = (ROOT / path).read_bytes()
            self.assertEqual((len(raw), sha256(raw).hexdigest()), (pin['bytes'], pin['sha256']))
        helper = load('continuation_current_callback_proof', HERE / 'derive.py')
        _, proof = helper.cases((CONT / 'cases.py').read_bytes())
        self.assertEqual(proof['counted_routing_changes'], 1)
        self.assertEqual(proof['unchanged_Native_callbacks'], 3)
        self.assertGreater(proof['unchanged_functions'], 10)
        self.assertEqual(sha256((CONT / 'oracle.py').read_bytes()).hexdigest(), '5b67898ecd86eb470e1b54f4d69fa47c01352f0e798acbe863ee2629766137dc')

    def test_exact_old_transition_runs_with_only_two_explicit_physical_pins(self):
        result = load('continuation_current_transition_test', HERE / 'transition.py').check()
        self.assertEqual(result['historical']['unchanged_callback_count'], 3)
        self.assertEqual(result['historical']['external_changed_pins'], 4)
        self.assertEqual(result['private_transition_derivation']['counted_routing_changes'], 1)
        original = Path.read_bytes
        def changed(path):
            raw = original(path)
            return raw + b'\n' if path == ROOT / 'scripts/cp7_credit_correction_de/proof.sql' else raw
        with patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(ValueError, 'EXACT_SUCCESSOR_SOURCE_CHANGED'):
                load('continuation_current_untouched_source_negative', HERE / 'transition.py').check()

    def test_routing_missing_duplicate_and_financial_source_mutations_are_refused(self):
        helper = load('continuation_current_anchor_negative', HERE / 'derive.py')
        raw = (CONT / 'cases.py').read_bytes()
        anchor = b"guard = load('d1_cont_exact_source_guard', HERE / 'source_guard.py')"
        for bad in (raw.replace(anchor, b'guard = None', 1), raw + b'\n' + anchor):
            with self.assertRaisesRegex(ValueError, 'ONE_EXACT_ROUTING_ANCHOR'):
                helper.cases(bad)

    def test_engine_preserves_exact_six_changes_and_rejects_missing_install_anchor(self):
        helper = load('continuation_current_six_engine_test', HERE / 'derive.py')
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        _, proof = helper.derive(raw)
        self.assertEqual(proof, json.loads((HERE / 'CONFIG.json').read_bytes())['runner_derivation'])
        with self.assertRaisesRegex(ValueError, 'EXACT_RUNNER_ANCHOR'):
            helper.derive(raw.replace(b"report['actual_Native_cases']=7", b"report['actual_Native_cases']=999", 1))

    def test_original_current_workflow_setup_downloads_client_alignment_cleanup_survive(self):
        helper = load('continuation_current_workflow_test', HERE / 'workflow.py')
        original = yaml.safe_load((ROOT / helper.OLD).read_bytes())
        actual = yaml.safe_load((ROOT / helper.NEW).read_bytes())
        branch = json.loads((HERE / 'CONFIG.json').read_bytes())['root_execution_branch']
        self.assertEqual(actual, helper.derive(original, branch))
        self.assertEqual(actual['jobs']['p21']['steps'][1]['name'], helper.EARLY)
        changed = {'Admit exact vendor parent and declared D1 child before database', 'Run actual D1 Native13 and complete restoration', 'Preserve exact original JSON report bytes in a bounded compressed log receipt'}
        for step in original['jobs']['p21']['steps']:
            if step.get('name') in changed or step.get('uses', '').startswith('actions/upload-artifact@'):
                continue
            self.assertIn(step, actual['jobs']['p21']['steps'])
        for step in actual['jobs']['p21']['steps']:
            if 'run' in step:
                result = subprocess.run(['bash', '-n'], input=step['run'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, (step.get('name'), result.stderr))

    def test_inherited_actual_no_argument_guard_and_BaseException_restore_exact_argv(self):
        scope = load('continuation_current_actual_guard_scope', HERE / 'argv_scope.py')
        path = ROOT / 'scripts/ow04-payment-positive-qualification/native26_probe.py'
        text = path.read_text(); node = next(n for n in ast.parse(text).body if isinstance(n, ast.If) and ast.unparse(n.test) == 'sys.argv[1:]')
        code = compile(ast.get_source_segment(text, node), str(path), 'exec')
        original = ['current-continuation', '--source-only']
        with patch.object(sys, 'argv', original):
            with self.assertRaises(SystemExit):
                exec(code, dict(sys=sys))
            for error in (ValueError('LOCAL_ONLY'), SystemExit('LOCAL_ONLY'), KeyboardInterrupt()):
                with self.assertRaises(type(error)):
                    with scope.inherited_arguments():
                        exec(code, dict(sys=sys)); raise error
                self.assertIs(sys.argv, original); self.assertEqual(sys.argv, ['current-continuation', '--source-only'])

    def test_unknown_outer_flags_still_refuse_before_inherited_arguments_scope(self):
        for name in ('check.py', 'probe.py'):
            result = subprocess.run([sys.executable, '-B', str(HERE / name), '--not-a-wrapper-option'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('CLOSED_EXACT', result.stderr)

    def test_CI_must_not_regenerate_source_or_select_a_parent(self):
        with patch.dict(os.environ, {'CI': 'true'}):
            with self.assertRaisesRegex(ValueError, 'CANNOT_BE_REGENERATED_IN_CI'):
                load('continuation_current_no_CI_reseal', HERE / 'bind.py').bind()


if __name__ == '__main__':
    main(verbosity=2)
