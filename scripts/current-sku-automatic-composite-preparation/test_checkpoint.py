from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import checkpoint as c


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY='Hanjay6688/-erp-garment-ux', GITHUB_SHA='a'*40,
                        GITHUB_RUN_ID='1', GITHUB_RUN_ATTEMPT='1', GH_TOKEN='NEVER_EXPORT_THIS')

    def tearDown(self):
        self.tmp.cleanup()

    def test_secret_environment_not_serialized(self):
        out = StringIO()
        with patch.dict(os.environ, self.env), redirect_stdout(out), c.observe_parent_phase('INSTALL'):
            pass
        self.assertNotIn('NEVER_EXPORT_THIS', out.getvalue())
        self.assertNotIn('GH_TOKEN', out.getvalue())
        rows = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual([row['state'] for row in rows], ['STARTED', 'COMPLETED'])
        for d in rows:
            self.assertEqual(d['actual_case_credit'], 0)
            self.assertFalse(d['restoration_verified'])

    def test_original_failure_preserved_without_message_leak(self):
        error = ValueError('NEVER_EXPORT_THIS')
        out = StringIO()
        with patch.dict(os.environ, self.env), self.assertRaises(ValueError) as caught, redirect_stdout(out):
            with c.observe_parent_phase('INSTALL'):
                raise error
        self.assertIs(caught.exception, error)
        self.assertNotIn('NEVER_EXPORT_THIS', out.getvalue())
        self.assertEqual([json.loads(line)['state'] for line in out.getvalue().splitlines()],
                         ['STARTED', 'FAILED'])

    def test_log_stream_failure_cannot_interrupt_operation(self):
        with patch.dict(os.environ, self.env), patch('builtins.print', side_effect=BrokenPipeError):
            with c.observe_parent_phase('INSTALL'):
                result = 'underlying operation completed'
        self.assertEqual(result, 'underlying operation completed')

    def test_output_symlink_and_existing_receipt_refused(self):
        real = self.root / 'real'; real.mkdir()
        link = self.root / 'link'; link.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'SYMLINK'):
            c.immutable_json(link / 'out.json', {})
        path = real / 'out.json'; c.immutable_json(path, {'first':True})
        with self.assertRaises(FileExistsError):
            c.immutable_json(path, {'first':False})
        self.assertTrue(json.loads(path.read_text())['first'])

    def test_wrong_run_identity_refused_before_writes(self):
        for key, value in [('GITHUB_SHA', 'short'), ('GITHUB_RUN_ID', '0'),
                           ('GITHUB_RUN_ATTEMPT', '1\nsecret'), ('GITHUB_REPOSITORY', 'other/repo')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.identity(dict(self.env, **{key:value}))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_sigkill_keeps_started_without_false_completion(self):
        code = ('import checkpoint as c, os, signal\n'
                'with c.observe_parent_phase("INSTALL"):\n'
                ' os.kill(os.getpid(), signal.SIGKILL)\n')
        env = dict(os.environ, **self.env)
        run = subprocess.run([sys.executable, '-c', code], cwd=Path(c.__file__).parent,
                             env=env, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, -signal.SIGKILL)
        rows = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual([row['state'] for row in rows], ['STARTED'])
        self.assertEqual(rows[0]['actual_case_credit'], 0)
        self.assertFalse(rows[0]['restoration_verified'])

    def test_dirty_or_wrong_checkout_refused(self):
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE).decode().strip()
        git('init'); git('config', 'user.name', 'Local checkpoint test')
        git('config', 'user.email', 'test@example.invalid')
        (self.root/'source.txt').write_text('source one\n')
        git('add','source.txt');git('commit','-m','Local synthetic source')
        env = dict(self.env, GITHUB_SHA=git('rev-parse', 'HEAD'))
        proofs = self.root/'cp6-proof'/'t3'; proofs.mkdir(parents=True)
        for name in c.RECEIPTS:
            (proofs/name).write_text('{"fixture": "SYNTHETIC_CONTROL_ONLY"}\n')
        snapshot = c.source_checkpoint(self.root, env)
        self.assertEqual(snapshot['source_tree'], git('rev-parse', 'HEAD^{tree}'))
        with self.assertRaisesRegex(ValueError, 'HEAD_MISMATCH'):
            c.source_checkpoint(self.root, self.env)
        (self.root/'source.txt').write_text('stale/edited source\n')
        with self.assertRaisesRegex(ValueError, 'SOURCE_DIRTY'):
            c.source_checkpoint(self.root, env)

    def test_admission_receipts_recover_exact_bytes_and_refuse_secret(self):
        proofs = self.root/'cp6-proof'/'t3'; proofs.mkdir(parents=True)
        raw = b'{ "synthetic_control": true, "n": 3 }\n'
        for name in c.RECEIPTS:
            (proofs/name).write_bytes(raw)
        observed = c.admission_receipts(self.root)
        for receipt in observed.values():
            self.assertEqual(receipt['original_utf8'].encode(), raw)
            self.assertEqual(receipt['sha256'], c.sha256(raw).hexdigest())
        (proofs/c.RECEIPTS[0]).write_text('{"password":"NEVER_EXPORT_THIS"}')
        with self.assertRaisesRegex(ValueError, 'SENSITIVE'):
            c.admission_receipts(self.root)
        (proofs/c.RECEIPTS[0]).write_text('{"url":"postgresql://user:secret@host/db"}')
        with self.assertRaisesRegex(ValueError, 'CREDENTIAL'):
            c.admission_receipts(self.root)
        (proofs/c.RECEIPTS[0]).unlink()
        with self.assertRaisesRegex(ValueError, 'BOUNDED_ADMISSION'):
            c.admission_receipts(self.root)

    def test_terminal_observation_pins_same_attempt_without_serializing_report_bodies(self):
        worker = dict(qualification_commit='a'*40, github_run_id='1', github_run_attempt='1',
                      worker_exit=1, process_group_empty=True, process_tree_empty=True,
                      error='NEVER_EXPORT_THIS')
        package = dict(run_identity=dict(tool_head='a'*40, github_sha='a'*40, run_id='1', run_attempt='1'),
                       gate=dict.fromkeys(c.PACKAGE_CHECKS, True) | {'writer_runtime': False})
        backup = dict(status='RESTORED_IDENTICAL', checks=dict.fromkeys(c.BACKUP_CHECKS, True),
                      data=dict(tables=407, differ={}))
        for name, report in zip(c.TERMINAL_REPORTS, (worker, package, backup)):
            (self.root/name).write_text(json.dumps(report))
        observed = c.terminal_observation(self.root, self.env)
        self.assertEqual(observed['worker']['worker_exit'], 1)
        self.assertTrue(observed['worker']['process_tree_empty'])
        self.assertFalse(observed['package_checks']['writer_runtime'])
        self.assertTrue(observed['backup']['zero_row_differences'])
        self.assertFalse(observed['restoration_verified'])
        self.assertFalse(observed['canonical_archive_verified'])
        self.assertEqual(observed['actual_case_credit'], 0)
        self.assertNotIn('NEVER_EXPORT_THIS', json.dumps(observed))
        for name in c.TERMINAL_REPORTS:
            raw = (self.root/name).read_bytes()
            self.assertEqual(observed['originals'][name], dict(bytes=len(raw), sha256=c.sha256(raw).hexdigest()))
        with self.assertRaisesRegex(ValueError, 'TERMINAL_WORKER_WRONG_RUN_OR_ATTEMPT'):
            c.terminal_observation(self.root, dict(self.env, GITHUB_RUN_ATTEMPT='2'))
        (self.root/c.SUPERVISION_REPORT).unlink()
        self.assertNotIn('worker', c.terminal_observation(self.root, self.env))


if __name__ == '__main__':
    unittest.main(verbosity=2)
