"""Disposable runner controls. No ERP cases or database commands are used."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
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
import runtime_receipt


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

    def test_owning_execution_keeps_original_failure_and_checks_cleanup(self):
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
            self.assertEqual(execution.supervise(False), 124)
            self.assertIn('TERMINAL_RECEIPT_UNAVAILABLE', output.getvalue())
            with self.assertRaisesRegex(ValueError, 'MISSING:terminal.json'):
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
            self.assertEqual(execution.supervise(False), 124)


if __name__ == '__main__':
    unittest.main(verbosity=2)
