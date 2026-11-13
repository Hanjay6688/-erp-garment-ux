"""Disposable runner controls. No ERP cases or database commands are used."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from copy import deepcopy
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import os
import signal
import subprocess
import sys
import unittest

import checkpoint
import component
import context_timezone
import continuation
import cost_source_timezone
import final_gate
import runtime_receipt


class CandidateSourceControls(unittest.TestCase):
    def test_frozen_context_changes_only_function_settings(self):
        directory = Path(context_timezone.__file__).resolve().parent
        source = json.loads((directory / 'SOURCE_REFERENCE.json').read_bytes())
        tree = source['automatic_source']['tree']
        original = subprocess.check_output([
            'git', '-C', str(directory.parents[1]), 'show',
            tree + ':scripts/cp7_sku_automatic_pending/context.sql',
        ]).decode()
        repaired = context_timezone.repair_context(original)
        old = "set search_path=''as $$"
        new = "set search_path='' set \"TimeZone\" to 'UTC' as $$"
        self.assertEqual(repaired.count(new), 2)
        self.assertEqual(repaired.replace(new, old), original)

    def test_cost_capture_timezone_survives_the_money_replacement(self):
        directory = Path(cost_source_timezone.__file__).resolve().parent
        frozen_scripts = directory.parents[2] / 'qualified-sku-money/scripts'
        with patch.object(sys, 'path', [str(frozen_scripts), *sys.path]):
            from cp7_sku_cost_components import money_delta, valuation_delta

        name = cost_source_timezone.SIGNATURE.removesuffix('(uuid)')
        source = (money_delta.HERE / 'source_rebalance.sql').read_text()
        valuation, _ = valuation_delta.derive()
        replacements, _, _ = money_delta.definitions(valuation)
        ddl = source + '\n' + replacements[name]
        profile = json.loads((money_delta.HERE / 'CATALOG_ADDITIONS.json').read_bytes())
        profile['derived_ddl'] = cost_source_timezone.pin(ddl)
        revised, expected = cost_source_timezone.adapt(dict(ddl=ddl, source_files=profile['source_files']), profile)

        before = cost_source_timezone.DDL_BEFORE
        after = cost_source_timezone.DDL_AFTER
        self.assertTrue(revised['ddl'].startswith(source + '\n'))
        self.assertEqual(revised['ddl'], source + '\n' + replacements[name].replace(before, after, 1))
        self.assertIn(cost_source_timezone.MONEY_STATE, revised['ddl'])
        self.assertEqual(expected['groups']['functions'][cost_source_timezone.SIGNATURE][12],
                         ['search_path=""', 'TimeZone=UTC'])

    def test_native_selects_exact_eight_wib_cases_for_historical_and_full_plans(self):
        directory = Path(continuation.__file__).resolve().parent
        scope = continuation.admitted((directory / 'PREPARED_NATIVE25_PLAN.json').read_bytes())
        ids = tuple(scope['planned_case_ids'])
        affected = set(scope['non_po_affected_case_ids'])

        def execute(statement, params=None):
            if statement == "select set_config('TimeZone', %s, true)":
                self.assertEqual(params, ('Asia/Jakarta',))
                cursor.timezone, = params
            else:
                self.assertEqual(statement, "select current_setting('TimeZone')")
            return SimpleNamespace(fetchone=lambda: (cursor.timezone,))

        def run_case(key):
            self.assertEqual(cursor.timezone, 'Asia/Jakarta' if key in affected else 'UTC')
            return dict(case=key, status='PASS')

        cursor = SimpleNamespace(execute=execute, timezone='UTC')
        callbacks = [(case, lambda key=case: run_case(key)) for case in ids]
        original = SimpleNamespace(IDS=ids, cases=lambda _cursor, _today: callbacks)
        for full_plan, expected in ((False, scope['fresh_case_ids']), (True, list(ids))):
            with self.subTest(full_plan=full_plan):
                selected = continuation.select(original, scope, full_plan=full_plan)
                self.assertEqual(selected.IDS, tuple(expected))
                observed = []
                for key, callback in selected.cases(cursor, None):
                    if key not in affected:
                        self.assertIs(callback, dict(callbacks)[key])
                    cursor.timezone = 'UTC'  # The owning snapshot sets UTC before each case.
                    observed.append(callback())
                self.assertEqual([row['case'] for row in observed], expected)
                self.assertEqual({row['case'] for row in observed if row.get('caller_timezone') == 'Asia/Jakarta'}, affected)
        original.cases = lambda _cursor, _today: list(reversed(callbacks))
        with self.assertRaisesRegex(ValueError, 'SKU_E4EA_CONTINUATION_CALLBACK_ORDER_CHANGED'):
            continuation.select(original, scope, full_plan=True).cases(cursor, None)

        def change_timezone():
            cursor.timezone = 'UTC'
            return dict(status='PASS')

        with self.assertRaisesRegex(ValueError, 'SKU_NON_PO_WIB_CALLER_CHANGED_DURING_CASE'):
            continuation.run_in_wib(cursor, change_timezone)

    def test_current_component_adds_only_the_full_plan_wib_binding(self):
        reference = json.loads(component.RETAINED.with_name('SOURCE_REFERENCE.json').read_bytes())
        raw = subprocess.check_output(['git', '-C', str(component.ROOT), 'show',
                                      reference['candidate_tree'] + ':' + component.ORIGINAL])
        original, _ = component.derive(raw)
        current, proof = component.derive(raw, full_plan_wib=True)
        historical, _ = component.derive(raw, focused=True)
        route = '\n    business=_CONTINUATION.select(business,_FULL_PLAN_WIB,full_plan=True)'
        self.assertEqual(current.count(route), 1)
        self.assertEqual(current.replace(route, ''), original)
        self.assertEqual(proof['exact_additional_routes'], 7)
        self.assertIn("qualification_scope='FRESH_SKU13_AND_CURRENT_BROWSER2'", historical)

    def test_full25_gate_accepts_only_the_exact_read_overlay_and_local_seal(self):
        scope = continuation.admitted(continuation.SCOPE.with_name('PREPARED_NATIVE25_PLAN.json').read_bytes())
        pool = final_gate.economic_pool
        typed = final_gate.typed_reader()
        # Small protocol rows let the exact inverse run without a database or historical Original.
        base = {signature: ['\n'.join(before for before, _ in routes), *([None] * 18)]
                for signature, routes in pool.ROUTES.items()}
        preimages = {signature: continuation.catalogue_group_pin(row)['sha256'] for signature, row in base.items()}
        guard = final_gate.CREDIT_GUARD
        base[guard] = [f"begin\n if actual_sha256 is distinct from '{final_gate.CREDIT_SEAL}'then\n end", *([None] * 18)]
        base['example.unchanged()'] = ['unrelated exact definition']
        baseline = continuation.catalogue_group_pin([[signature, row] for signature, row in sorted(base.items())])
        _, _, groups = final_gate.catalogue.exact_readers()
        with patch.object(pool, 'BASELINE_ROWS', preimages), patch.object(final_gate, 'BASELINE_FUNCTIONS', baseline):
            current = deepcopy(base)
            current[pool.FUNCTION] = pool.helper_row()
            current.update({signature: pool.project(signature, base[signature]) for signature in pool.ROUTES})
            current[guard][0] = current[guard][0].replace(final_gate.CREDIT_SEAL, 'b' * 64)

            def check(functions, *, duplicate=False, run_id='425'):
                value = {group: [] for group in groups}
                for group in ('relations', 'roles', 'operators', 'casts', 'languages'):
                    value[group] = [['model.' + group, None]]
                value['functions'] = [[signature, row] for signature, row in sorted(functions.items())]
                if duplicate:
                    value['functions'].append(value['functions'][-1])
                raw = json.dumps(value).encode()
                capture = dict(status='ACTUAL_FULL25_SKU_CATALOGUE_OBSERVED', head='a' * 40, run_id='425', attempt=1,
                    original=dict(name=final_gate.catalogue.ORIGINAL, **continuation.pin(raw)), actual_ERP_case_credit=0,
                    complete_input_review=False, production_go=False,
                    readers={name: dict(bytes=size, sha256=digest)
                             for name, (size, digest) in final_gate.catalogue.SOURCE_PINS.items()},
                    fingerprint=dict(contract='cp7.global-catalogue-fingerprint.v1', groups=25, sha256='c' * 64,
                                     counts={name: len(rows) for name, rows in value.items()}))
                return final_gate.validate_catalogue(typed, raw, capture, 'a' * 40, run_id, scope)

            accepted = check(current)
            self.assertEqual(accepted['economic_pool_functions']['normalized_predecessor'], baseline)
            self.assertEqual(accepted['economic_pool_functions']['database_local_credit_seal'], 'b' * 64)
            self.assertEqual(set(accepted['current_group_pins']), groups)
            self.assertIn('roles', accepted['historical_nonfunction_differences'])
            for signature in (*pool.ROUTES, pool.FUNCTION, guard, 'example.unchanged()'):
                with self.subTest(signature=signature):
                    tampered = deepcopy(current)
                    tampered[signature][0] += '\nunreviewed'
                    with self.assertRaises(ValueError):
                        check(tampered)
            with self.assertRaisesRegex(ValueError, 'SKU_FULL25_REVIEWED_FUNCTIONS_REQUIRED'):
                check({signature: row for signature, row in current.items() if signature != pool.FUNCTION})
            with self.assertRaisesRegex(ValueError, 'SKU_FULL25_ONLY_REVIEWED_ECONOMIC_POOL_FUNCTIONS_MAY_CHANGE'):
                check(dict(current, unreviewed=['extra function']))
            with self.assertRaisesRegex(ValueError, 'SKU_FULL25_ORDERED_UNIQUE_CATALOGUE_KEYS'):
                check(current, duplicate=True)
            with self.assertRaisesRegex(ValueError, 'SKU_FULL25_SAME_ACTUAL_CATALOGUE_OWNER'):
                check(current, run_id='424')


class RuntimeReceiptControls(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=runtime_receipt.REPOSITORY,
                        GITHUB_RUN_ID='425', GITHUB_RUN_ATTEMPT='1', GITHUB_JOB='p21',
                        GITHUB_SHA='a'*40, RUNNER_TEMP=str(self.root))
        self.receipts = runtime_receipt.from_environment(self.env)
        self.report = self.root / 'worker.json'

    def report_with(self, **changes):
        report = dict(status='INCOMPLETE', github_run_id='425', github_run_attempt='1',
                      qualification_commit='a'*40, process_tree_empty=True, process_group_empty=True,
                      worker_exit=-9, supervisor_error='DO_NOT_COPY_THIS')
        report.update(changes)
        self.report.write_text(json.dumps(report))
        return self.report

    def test_missing_prepare_refuses_cleanup(self):
        self.report_with()
        with self.assertRaisesRegex(ValueError, 'MISSING:prepared.json'):
            self.receipts.authorize_stop()
        self.assertFalse(self.receipts.directory.exists())

    def test_stopping_before_launch_prevents_a_future_worker(self):
        self.receipts.prepare()
        self.receipts.authorize_stop()
        self.receipts.authorize_stop()
        with self.assertRaises(FileExistsError):
            self.receipts.claim_worker()
        self.assertEqual(self.receipts.read('decision.json')['phase'], 'STOP_BEFORE_WORKER')

    def test_worker_claim_requires_terminal_proof_and_is_single_use(self):
        self.receipts.prepare()
        self.receipts.claim_worker()
        with self.assertRaises(FileExistsError):
            self.receipts.claim_worker()
        with self.assertRaisesRegex(ValueError, 'MISSING:terminal.json'):
            self.receipts.authorize_stop()

    def test_wrong_run_attempt_and_head_reports_are_refused(self):
        self.receipts.prepare()
        self.receipts.claim_worker()
        for key, value in [('github_run_id', '424'), ('github_run_attempt', '2'), ('qualification_commit', 'b'*40)]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'SUPERVISION_WRONG_RUN_OR_ATTEMPT'):
                self.receipts.finish(self.report_with(**{key: value}))
        with self.assertRaisesRegex(ValueError, 'MISSING:terminal.json'):
            self.receipts.authorize_stop()

    def test_reaped_failed_worker_can_cleanup_without_recovery_credit(self):
        self.receipts.prepare()
        self.receipts.claim_worker()
        self.receipts.finish(self.report_with())
        self.receipts.authorize_stop()
        terminal = self.receipts.read('terminal.json')
        self.assertTrue(terminal['processes_reaped'])
        self.assertFalse(terminal['restoration_verified'])
        self.assertEqual(terminal['actual_case_credit'], 0)
        self.assertNotIn('DO_NOT_COPY_THIS', (self.receipts.directory / 'terminal.json').read_text())
        with self.assertRaises(FileExistsError):
            self.receipts.finish(self.report_with(worker_exit=0))

    def test_nonempty_worker_group_refuses_cleanup(self):
        self.receipts.prepare()
        self.receipts.claim_worker()
        self.receipts.finish(self.report_with(process_group_empty=False))
        with self.assertRaisesRegex(ValueError, 'STOP_REQUIRES_REAPED_WORKER'):
            self.receipts.authorize_stop()

    def test_symlink_and_malformed_receipts_are_refused(self):
        self.receipts.prepare()
        path = self.receipts.directory / 'decision.json'
        path.symlink_to(self.report_with())
        with self.assertRaisesRegex(ValueError, 'RECEIPT_SYMLINK'):
            self.receipts.authorize_stop()
        path.unlink()
        path.write_text('{"identity":')
        with self.assertRaises(json.JSONDecodeError):
            self.receipts.authorize_stop()

    def test_receipts_do_not_cross_job_attempt_or_source(self):
        self.receipts.prepare()
        for key, value, reason in [('GITHUB_RUN_ATTEMPT', '2', 'MISSING:prepared.json'),
                                   ('GITHUB_JOB', 'different', 'MISSING:prepared.json'),
                                   ('GITHUB_SHA', 'b'*40, 'WRONG_RUN_OR_ATTEMPT')]:
            other = runtime_receipt.from_environment(dict(self.env, **{key: value}))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, reason):
                other.authorize_stop()

    def test_simultaneous_worker_and_cleanup_have_one_winner(self):
        self.receipts.prepare()
        start = Barrier(2)

        def attempt(callback):
            start.wait(timeout=3)
            try:
                callback()
            except (ValueError, FileExistsError):
                return False
            return True

        with ThreadPoolExecutor(max_workers=2) as pool:
            worker = pool.submit(attempt, self.receipts.claim_worker)
            cleanup = pool.submit(attempt, self.receipts.authorize_stop)
            self.assertNotEqual(worker.result(timeout=5), cleanup.result(timeout=5))

    def test_sigkill_after_launch_refuses_cleanup_without_terminal(self):
        self.receipts.prepare()
        child = subprocess.run([sys.executable, '-B', '-c',
            'import runtime_receipt, os, signal; runtime_receipt.from_environment().claim_worker();'
            'os.kill(os.getpid(), signal.SIGKILL)'], cwd=Path(runtime_receipt.__file__).parent,
            env=dict(os.environ, **self.env), capture_output=True, timeout=8)
        self.assertEqual(child.returncode, -signal.SIGKILL)
        self.assertEqual(self.receipts.read('decision.json')['phase'], 'WORKER_CLAIMED')
        with self.assertRaisesRegex(ValueError, 'MISSING:terminal.json'):
            self.receipts.authorize_stop()

    def test_real_checkpoint_command_prepares_same_job_receipt(self):
        checkout = self.root / 'checkout'
        checkout.mkdir()

        def git(*args):
            return subprocess.check_output(['git', '-C', str(checkout), *args], stderr=subprocess.PIPE).decode().strip()

        git('init', '--quiet')
        git('config', 'user.name', 'Receipt control')
        git('config', 'user.email', 'test@example.invalid')
        (checkout / 'source').write_text('fixture source\n')
        git('add', 'source')
        git('commit', '-qm', 'source fixture')
        proof = checkout / 'cp6-proof/t3'
        proof.mkdir(parents=True)
        for name in checkpoint.RECEIPTS:
            (proof / name).write_text('{"fixture":true}\n')
        env = dict(self.env, GITHUB_SHA=git('rev-parse', 'HEAD'))
        subprocess.run([sys.executable, '-B', str(Path(checkpoint.__file__)), '--source', str(checkout),
                        '--output', str(self.root / 'checkpoint.json')], check=True, capture_output=True,
                       env=dict(os.environ, **env), timeout=8)
        self.assertEqual(runtime_receipt.from_environment(env).read('prepared.json')['phase'], 'PREPARED_BEFORE_DATABASE')
        self.assertFalse(json.loads((self.root / 'checkpoint.json').read_text())['restoration_verified'])

    def test_owning_execution_reports_failure_without_inventing_a_deadline(self):
        path = Path(checkpoint.__file__).with_name('execution.py')
        spec = importlib.util.spec_from_file_location('receipt_control_owning_execution', path)
        execution = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(execution)
        self.receipts.prepare()
        supervisor = SimpleNamespace(supervise=lambda *args, **kwargs: {})

        def main():
            supervisor._BIND_SUPERVISION(supervisor)
            supervisor.supervise(['model-worker'], work_seconds=3600, recovery_seconds=1200)
            return 124

        supervisor.main = main
        with patch.dict(os.environ, self.env), patch.object(execution, 'ROOT', self.root), \
                patch.object(execution, 'helper', return_value=(supervisor, {})), \
                patch.object(execution.window, 'budget', return_value={'mode': 'STANDARD'}), \
                redirect_stderr(StringIO()) as output:
            self.assertEqual(execution.supervise(False), 1)
            self.assertIn('TERMINAL_RECEIPT_UNAVAILABLE', output.getvalue())
            with self.assertRaisesRegex(ValueError, 'MISSING:terminal.json'):
                execution.supervise(True)

    def test_owning_execution_exit_uses_verified_terminal_evidence(self):
        path = Path(checkpoint.__file__).with_name('execution.py')
        spec = importlib.util.spec_from_file_location('receipt_control_terminal_exit', path)
        execution = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(execution)
        observed_path = self.root / 'cp6-proof/t3' / execution.SUPERVISION_REPORT
        observed_path.parent.mkdir(parents=True)
        controls = (
            ('success', 0, 0, dict(status='WORKER_COMPLETED_AND_REAPED', worker_exit=0)),
            ('clean worker failure', 124, 1, {}),
            ('other clean worker status', 124, 7, dict(worker_exit=7)),
            ('worker 124 without supervisor deadline', 124, 1, dict(worker_exit=124)),
            ('worker zero with incomplete report', 0, 1, dict(worker_exit=0)),
            ('genuine deadline', 124, 124, dict(deadline_reached=True, worker_exit=-2,
                 signals=[dict(signal='SIGINT', reason='RESTORATION_RESERVE_STARTED')])),
            ('external signal', 124, 1, dict(external_signal='SIGTERM', worker_exit=-15)),
            ('orphan stopped', 124, 1, dict(orphaned_child=True, worker_exit=0)),
            ('orphan remains', 124, 1, dict(orphaned_child=True, process_tree_empty=False)),
            ('ambiguous deadline', 124, 1, dict(deadline_reached=None, worker_exit=7)),
            ('deadline without terminal worker status', 124, 1, dict(deadline_reached=True, worker_exit=None)),
        )
        for attempt, (name, retained_code, expected, changes) in enumerate(controls, 1):
            with self.subTest(name=name):
                env = dict(self.env, GITHUB_RUN_ATTEMPT=str(attempt))
                receipt = runtime_receipt.from_environment(env)
                receipt.prepare()
                report = dict(github_run_id='425', github_run_attempt=str(attempt), qualification_commit='a'*40,
                              status='INCOMPLETE', worker_exit=1, deadline_reached=False, external_signal=None,
                              orphaned_child=False, signals=[], process_group_empty=True, process_tree_empty=True)
                report.update(changes)
                supervisor = SimpleNamespace(supervise=lambda *args, **kwargs: {})

                def main():
                    supervisor._BIND_SUPERVISION(supervisor)
                    supervisor.supervise(['model-worker'], work_seconds=3600, recovery_seconds=1200)
                    observed_path.write_text(json.dumps(report))
                    return retained_code

                supervisor.main = main
                with patch.dict(os.environ, env), patch.object(execution, 'ROOT', self.root), \
                        patch.object(execution, 'helper', return_value=(supervisor, {})), \
                        patch.object(execution.window, 'budget', return_value={'mode': 'STANDARD'}):
                    self.assertEqual(execution.supervise(False), expected)
                    terminal = receipt.read('terminal.json')
                    self.assertEqual(terminal['actual_case_credit'], 0)
                    self.assertFalse(terminal['restoration_verified'])
                    if report['process_tree_empty'] and type(report['worker_exit']) is int:
                        self.assertEqual(execution.supervise(True), 0)
                    else:
                        with self.assertRaisesRegex(ValueError, 'STOP_REQUIRES_REAPED_WORKER'):
                            execution.supervise(True)

    def test_diagnostics_output_failure_keeps_nonzero_result(self):
        path = Path(checkpoint.__file__).with_name('execution.py')
        spec = importlib.util.spec_from_file_location('receipt_control_broken_output_execution', path)
        execution = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(execution)
        self.receipts.prepare()
        with patch.dict(os.environ, self.env), patch.object(execution, 'ROOT', self.root), \
                patch.object(execution, 'helper', return_value=(SimpleNamespace(main=lambda: 124), {})), \
                patch('builtins.print', side_effect=BrokenPipeError):
            self.assertEqual(execution.supervise(False), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
