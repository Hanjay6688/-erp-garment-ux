from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

import checkpoint as c


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = dict(GITHUB_REPOSITORY='Hanjay6688/-erp-garment-ux', GITHUB_SHA='a'*40,
                        GITHUB_RUN_ID='1', GITHUB_RUN_ATTEMPT='1', GH_TOKEN='NEVER_EXPORT_THIS')

    def tearDown(self):
        self.tmp.cleanup()

    def test_secret_environment_not_serialized(self):
        out = StringIO()
        with redirect_stdout(out), c.phase(self.root, 'INSTALL', self.env):
            pass
        combined = out.getvalue() + ''.join(p.read_text() for p in self.root.glob('*.json'))
        self.assertNotIn('NEVER_EXPORT_THIS', combined)
        self.assertNotIn('GH_TOKEN', combined)
        for p in self.root.glob('*.json'):
            d = json.loads(p.read_text())
            self.assertEqual(d['actual_case_credit'], 0)
            self.assertFalse(d['restoration_verified'])

    def test_original_failure_preserved_without_message_leak(self):
        error = ValueError('NEVER_EXPORT_THIS')
        with self.assertRaises(ValueError) as caught, redirect_stdout(StringIO()):
            with c.phase(self.root, 'INSTALL', self.env):
                raise error
        self.assertIs(caught.exception, error)
        self.assertFalse((self.root / 'INSTALL_COMPLETED.json').exists())
        text = (self.root / 'INSTALL_FAILED.json').read_text()
        self.assertNotIn('NEVER_EXPORT_THIS', text)
        first = (self.root / 'INSTALL_FAILED.json').read_bytes()
        with self.assertRaises(FileExistsError), redirect_stdout(StringIO()):
            with c.phase(self.root, 'INSTALL', self.env):
                pass
        self.assertEqual((self.root / 'INSTALL_FAILED.json').read_bytes(), first)

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
        code = ('import checkpoint as c, os, signal, json; '
                'from pathlib import Path\n'
                'with c.phase(Path(os.environ["TEST_OUTPUT"]), "INSTALL", os.environ):\n'
                ' os.kill(os.getpid(), signal.SIGKILL)\n')
        env = dict(os.environ, **self.env, TEST_OUTPUT=str(self.root))
        run = subprocess.run([sys.executable, '-c', code], cwd=Path(c.__file__).parent,
                             env=env, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, -signal.SIGKILL)
        self.assertEqual([p.name for p in self.root.glob('*.json')], ['INSTALL_STARTED.json'])
        self.assertEqual(json.loads((self.root/'INSTALL_STARTED.json').read_text())['state'], 'STARTED')

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
