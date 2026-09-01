#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from cp3_render_reviewed_rollback import render


VALID = b"""-- reviewed candidate\nbegin;\ncreate table erp.demo(id integer);\ninsert into erp.schema_migrations(version, description, installed_at)\nvalues ('v2.6.14a','demo',clock_timestamp());\ncommit;\n"""


class RendererTests(unittest.TestCase):
    def run_render(self, raw: bytes, *, sha: str | None = None, size: int | None = None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sql"
            output = root / "output.sql"
            report = root / "report.json"
            source.write_bytes(raw)
            render(
                source,
                sha or hashlib.sha256(raw).hexdigest(),
                len(raw) if size is None else size,
                output,
                report,
            )
            return output.read_text(), report.read_text()

    def assert_rejected(self, raw: bytes, text: str, **kwargs):
        with self.assertRaisesRegex(ValueError, text):
            self.run_render(raw, **kwargs)

    def test_valid_exact_bytes_render(self):
        output, report = self.run_render(VALID)
        self.assertIn("SOURCE_SHA256", output)
        self.assertTrue(output.rstrip().endswith("rollback;"))
        self.assertNotIn("\ncommit;\n", output.lower())
        self.assertIn('"status": "PASS"', report)

    def test_compact_14c_ledger_marker_render(self):
        raw = VALID.replace(
            b"version, description, installed_at",
            b"version,description,installed_at",
        ).replace(b"'v2.6.14a'", b"'v2.6.14c'")
        output, report = self.run_render(raw)
        self.assertTrue(output.rstrip().endswith("rollback;"))
        self.assertIn('"ledger_version": "v2.6.14c"', report)

    def test_wrong_digest_rejected(self):
        self.assert_rejected(VALID, "sha256 mismatch", sha="0" * 64)

    def test_wrong_size_rejected(self):
        self.assert_rejected(VALID, "byte-length mismatch", size=len(VALID) + 1)

    def test_crlf_rejected(self):
        self.assert_rejected(VALID.replace(b"\n", b"\r\n"), "LF-only")

    def test_missing_commit_rejected(self):
        self.assert_rejected(VALID.replace(b"commit;\n", b""), "one standalone COMMIT")

    def test_duplicate_commit_rejected(self):
        self.assert_rejected(VALID.replace(b"commit;\n", b"commit;\ncommit;\n"), "one standalone COMMIT")

    def test_trailing_sql_after_commit_rejected(self):
        self.assert_rejected(VALID + b"select 1;\n", "not the terminal executable")

    def test_comment_word_commit_does_not_count(self):
        output, _ = self.run_render(VALID.replace(b"-- reviewed candidate", b"-- COMMIT in comment"))
        self.assertTrue(output.rstrip().endswith("rollback;"))

    def test_missing_ledger_marker_rejected(self):
        self.assert_rejected(VALID.replace(b"insert into erp.schema_migrations(version, description, installed_at)\n", b""), "ledger marker")

    def test_wrong_version_rejected(self):
        self.assert_rejected(VALID.replace(b"'v2.6.14a'", b"'v2.6.14x'"), "version is absent")


if __name__ == "__main__":
    unittest.main(verbosity=2)
