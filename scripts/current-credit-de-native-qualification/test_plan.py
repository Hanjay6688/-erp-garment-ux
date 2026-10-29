"""Prepared scope and failure-evidence controls; no database runtime credit."""
from pathlib import Path
import ast
import json
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


class PlanTests(unittest.TestCase):
    def test_thirteen_unique_cases_and_no_fresh_auth_or_race_claim(self):
        tree = ast.parse((ROOT / 'scripts/cp7_credit_correction_de/cases.py').read_text())
        ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
        self.assertEqual(len(ids), 13)
        self.assertEqual(len(set(ids)), 13)
        self.assertIn('E_UNIMPLEMENTED_INCOMING_CORRECTION_STAYS_GUARDED', ids)
        self.assertIn('D_ATOMIC_POST_FAILURE_RESTORE', ids)
        runner = (HERE / 'native_runner.py').read_text()
        self.assertIn("actual.get('complete_boundary_restored') is True", runner)
        self.assertIn('business.post(cursor, pair)', runner)
        self.assertIn('product.USED_ERROR', runner)

    def test_partial_original_is_retained_exactly_without_synthesizing_pass(self):
        # Isolate the actual copy function without loading any product/runtime.
        tree = ast.parse((HERE / 'native_runner.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'retain_originals')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'strict-originals'
            original.mkdir()
            raw = b'{"status":"INCOMPLETE","cases":{"FIRST":{"status":"INCOMPLETE"}}}\n'
            (original / 'TEST.json').write_bytes(raw)
            from hashlib import sha256
            env = dict(ROOT=root, LABEL='TEST', sha256=sha256)
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<retained-originals>', 'exec'), env)
            report = {}
            env['retain_originals'](SimpleNamespace(r1=SimpleNamespace(OUT=original)), report)
            self.assertEqual((root / 'cp6-proof/t3/TEST.json').read_bytes(), raw)
            self.assertEqual(report['strict_group_originals'], [dict(name='TEST.json', bytes=len(raw), sha256=sha256(raw).hexdigest())])
            self.assertNotIn('status', report)


if __name__ == '__main__':
    unittest.main()
