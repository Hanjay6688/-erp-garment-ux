"""A changed oracle or extra source edit is never hidden by the adapter."""
from pathlib import Path
import ast
import unittest
from derive import derive, REPLACEMENTS

ROOT = Path(__file__).resolve().parents[2]


class DerivedRunnerTests(unittest.TestCase):
    def test_all_other_bytes_and_existing_restore_oracles_are_identical(self):
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        current, proof = derive(raw)
        ast.parse(current)
        for before, after in reversed(REPLACEMENTS):
            self.assertEqual(current.count(after), 1)
            current = current.replace(after, before, 1)
        self.assertEqual(current.encode(), raw)
        self.assertEqual(proof['counted_changes'], 6)

    def test_missing_or_duplicate_anchor_refuses_before_runtime(self):
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        old = REPLACEMENTS[0][0].encode()
        for changed in (raw.replace(old, b'CHANGED', 1), raw + b'\n' + old):
            with self.assertRaises(ValueError):
                derive(changed)


if __name__ == '__main__':
    unittest.main()
