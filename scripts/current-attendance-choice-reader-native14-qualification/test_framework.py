"""Closed source/derivation controls. No ERP/DB/remote proof is generated."""
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
OLD = ROOT / 'scripts/current-attendance-period-choice-native11-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


class Framework(TestCase):
    def test_null_source_API_parent_gate_refuses_before_ERP_or_subprocess(self):
        original = builtins.__import__
        def guard(name, *args, **kwargs):
            if name.startswith(('psycopg', 'cp7_', 'cp6_')):
                raise AssertionError('CLOSED_IMPORTED_ERP:' + name)
            return original(name, *args, **kwargs)
        read = Path.read_bytes
        def closed(path):
            raw = read(path)
            if path == HERE / 'CONFIG.json':
                cfg = json.loads(raw); cfg.update(backend_binding=None, required_backend_source=None, required_qualified_parent=None)
                return json.dumps(cfg).encode()
            return raw
        with patch.object(Path, 'read_bytes', closed), patch.object(builtins, '__import__', guard), patch.object(subprocess, 'check_output', side_effect=AssertionError('CLOSED_CALLED_PROCESS_OR_GET')):
            for name in ('probe.py', 'native_runner.py'):
                with self.assertRaisesRegex(ValueError, 'S03_NATIVE14_CLOSED'):
                    load('s03_reader14_closed_' + name, HERE / name).runtime()

    def test_plan_is_exact_original11_plus_three_readerIDs_not_capture15(self):
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        plan = load('s03_reader14_pure_ID_plan', HERE / 'case_plan.py')
        self.assertEqual(list(plan.IDS), cfg['Native_case_ids'])
        self.assertEqual(tuple(plan.IDS), (*plan.ORIGINAL11_IDS, *plan.READER3_IDS))
        self.assertEqual((len(plan.ORIGINAL11_IDS), len(plan.READER3_IDS), len(set(plan.IDS))), (11, 3, 14))
        historical = json.loads((HERE / 'retained_9a0/native11/CONFIG.json').read_bytes())
        self.assertEqual(list(plan.ORIGINAL11_IDS), historical['Native_case_ids'])
        self.assertEqual(cfg['expected_captured_originals'], 15)

    def test_original80_and_old251_and_full_native11_namespace_stay_exact_history(self):
        origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
        prior = load('s03_reader14_exact_history_check', HERE / 'source_check.py').historical(ROOT, HERE, origin)
        self.assertEqual(len(prior['files']), 251)
        self.assertEqual(len(origin['historical_old80_files']), 80)
        case = ROOT / 'scripts/current-attendance-period-choice-qualification/cases.py'
        self.assertEqual(sha256(case.read_bytes()).hexdigest(), '15fe990cccb82ff4c1dcd9ca40dc17fe93ac26a3a359a37361e6d8780b1f16e2')

    def test_complete_vendor_engine_is_exact_six_reversible_selections(self):
        helper = load('s03_reader14_six_derivation', HERE / 'derive.py')
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        code, proof = helper.derive(raw)
        self.assertEqual(proof, json.loads((HERE / 'CONFIG.json').read_bytes())['runner_derivation'])
        self.assertEqual(proof['counted_changes'], 6)
        for before, after in reversed(helper.REPLACEMENTS):
            self.assertEqual(code.count(after), 1); code = code.replace(after, before, 1)
        self.assertEqual(code.encode(), raw)

    def test_private_runner_reconstructs_original_and_inserts_reader_after_fresh11_before_witness(self):
        helper = load('s03_reader14_actual_private_runner_deriver', HERE / 'derive.py')
        raw = (OLD / 'native_runner.py').read_bytes(); code, proof = helper.native_runner(raw)
        self.assertEqual(proof['counted_changes'], 5)
        self.assertIn("actual.get('counts') != {'PASS': 11}", code)
        self.assertIn('or len(planned) != 11:', code)
        self.assertIn('business.cases(cursor, today, state=state, evidence=report)', code)
        self.assertLess(code.index("raise ValueError('S03_NATIVE11_COMPLETE_ELEVEN_PASS_REQUIRED')"), code.index('run_actual_reader3('))
        self.assertLess(code.index('run_actual_reader3('), code.index('business.allocate(cursor, fixture, output)'))
        self.assertIn('actual_Native_cases=14', code)
        for before, after in reversed(helper.NATIVE_PAIRS):
            self.assertEqual(code.count(after), 1); code = code.replace(after, before, 1)
        self.assertEqual(code.encode(), raw)
        before = helper.NATIVE_PAIRS[0][0].encode()
        for bad in (raw.replace(before, b'', 1), raw + b'\n' + before):
            with self.assertRaisesRegex(ValueError, 'ONE_EXACT_PRIVATE_ANCHOR'):
                helper.native_runner(bad)

    def test_private_source_intake_changes_only_history_read_and_plan_capture_metadata(self):
        helper = load('s03_reader14_metadata_intake_derivation', HERE / 'derive.py')
        raw = (OLD / 'source_check.py').read_bytes(); code, proof = helper.source_checker(raw)
        self.assertEqual(proof['counted_changes'], 4)
        self.assertTrue(proof['actual_current_product_and_all_authored_files_checked_by_outer_first'])
        self.assertIn("raw = (here / 'retained_9a0/source80' / name).read_bytes()", code)
        self.assertIn('len(stage.NATIVE_SIGNATURES) != 12', code)
        self.assertIn('len(stage.SIGNATURES) != 15', code)
        self.assertIn('len(set(ids[0])) != 14', code)
        compile(code, 'private-source-intake-no-exec', 'exec')

    def test_frozen_P0_and_later_validators_and_producer_deltas_are_bounded(self):
        for name, digest in (('generated_receipts.py', 'a569138a5b6d4c0d1ce542ab45af98ee156f47e6d772766c214bbae3366ffc7e'),
                             ('generated_later.py', '7bf35d85d9f7ec19da34c5626f24af908f3691a4e3ed7251dbc4958e59b4bea3')):
            self.assertEqual(sha256((HERE / name).read_bytes()).hexdigest(), digest)
        old_path = '.github/workflows/cp7-s03-attendance-native11.yml'; new_path = '.github/workflows/cp7-s03-choice-reader-native14.yml'
        for name in ('GENERATED_RECEIPTS.json', 'LATER_GENERATED_RECEIPTS.json'):
            old = json.loads((OLD / name).read_bytes()); new = json.loads((HERE / name).read_bytes())
            expected_producers = dict(old['producer_files']); expected_producers.pop(old_path)
            raw = (ROOT / new_path).read_bytes(); expected_producers[new_path] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
            self.assertEqual(new['producer_files'], expected_producers)
            for key in old:
                if key not in ('producer_files', 'package_workflow_name', 'S03_contract_derivation'):
                    self.assertEqual(new[key], old[key])

    def test_workflow_keeps_all_unrelated_producers_clone_restore_cleanup_and_has_first_gate(self):
        helper = load('s03_reader14_exact_workflow_derivation', HERE / 'workflow.py')
        before = yaml.safe_load((ROOT / helper.OLD).read_bytes()); after = yaml.safe_load((ROOT / helper.NEW).read_bytes())
        branch = json.loads((HERE / 'CONFIG.json').read_bytes())['root_execution_branch']
        self.assertEqual(after, helper.derive(before, branch))
        self.assertEqual(after['jobs']['p21']['steps'][1]['name'], helper.EARLY)
        changed = {'Check frozen S03 qualification and workflow controls before database',
            'Admit exact vendor41c parent and frozen S03 source before database', 'Run actual S03 Native11 and complete restoration',
            'Require exact Native11 used guard outer restore and five package gates',
            'Preserve exact original JSON report bytes in a bounded compressed log receipt'}
        for step in before['jobs']['p21']['steps']:
            if step.get('name') in changed or step.get('uses', '').startswith('actions/upload-artifact@'):
                continue
            self.assertIn(step, after['jobs']['p21']['steps'])
        for step in after['jobs']['p21']['steps']:
            if 'run' in step:
                result = subprocess.run(['bash', '-n'], input=step['run'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, (step.get('name'), result.stderr))

    def test_inherited_no_argument_scope_restores_same_object_even_BaseException(self):
        helper = load('s03_reader14_actual_argv_boundary', HERE / 'argv_boundary.py')
        original = ['new-native14', '--runtime']
        with patch.object(sys, 'argv', original):
            for error in (ValueError('LOCAL'), SystemExit('LOCAL'), KeyboardInterrupt()):
                with self.assertRaises(type(error)):
                    with helper.inherited_imports():
                        self.assertEqual(sys.argv, ['new-native14']); raise error
                self.assertIs(sys.argv, original)
                self.assertEqual(sys.argv, ['new-native14', '--runtime'])

    def test_unknown_cli_flags_reject_before_gate_and_CI_cannot_reseal(self):
        for name in ('check.py', 'probe.py'):
            result = subprocess.run([sys.executable, '-B', str(HERE / name), '--unknown-flag'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0); self.assertNotIn('S03_NATIVE14_CLOSED', result.stderr)
        with patch.dict(os.environ, {'CI': 'true'}):
            with self.assertRaisesRegex(ValueError, 'REGENERATION_IN_CI_FORBIDDEN'):
                load('s03_reader14_no_CI_binding', HERE / 'bind.py').bind()


if __name__ == '__main__':
    main(verbosity=2)
