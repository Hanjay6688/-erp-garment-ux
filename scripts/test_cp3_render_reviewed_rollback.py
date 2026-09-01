from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cp3_render_reviewed_rollback import RenderError, render_reviewed_rollback


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


VALID_SQL = b"""-- reviewed CP3 source\nbegin;\nset local lock_timeout='2s';\ncreate function erp.example() returns void language plpgsql as $fn$\nbegin\n  perform 'COMMIT; inside body';\n  -- COMMIT; inside function comment\nend;\n$fn$;\n/* terminal word COMMIT is harmless here */\ncommit;\n-- trailing comment is allowed\n"""


class RollbackRendererTests(unittest.TestCase):
    def render(self, data: bytes = VALID_SQL) -> tuple[bytes, object]:
        return render_reviewed_rollback(data, digest(data))

    def assert_rejected(self, data: bytes, message: str) -> None:
        with self.assertRaisesRegex(RenderError, message):
            render_reviewed_rollback(data, digest(data))

    def test_valid_exact_bytes_render_one_terminal_rollback(self) -> None:
        rendered, metadata = self.render()
        self.assertIn(b"\nROLLBACK;\n", rendered)
        self.assertNotIn(b"\ncommit;\n", rendered)
        self.assertEqual(metadata.input_sha256, digest(VALID_SQL))
        self.assertEqual(metadata.output_sha256, digest(rendered))
        self.assertEqual(metadata.begin_token_count, 1)
        self.assertEqual(metadata.commit_token_count, 1)
        self.assertEqual(metadata.rollback_token_count, 0)

    def test_non_ascii_before_commit_keeps_valid_output(self) -> None:
        data = VALID_SQL.replace(b"-- reviewed CP3 source", "-- bukti dijahit: aman".encode())
        rendered, metadata = self.render(data)
        self.assertEqual(metadata.output_sha256, digest(rendered))
        self.assertIn("dijahit".encode(), rendered)
        self.assertIn(b"ROLLBACK;", rendered)

    def test_wrong_sha_is_rejected_before_parsing(self) -> None:
        with self.assertRaisesRegex(RenderError, "SHA-256 mismatch"):
            render_reviewed_rollback(VALID_SQL, "0" * 64)

    def test_invalid_expected_sha_format_is_rejected(self) -> None:
        with self.assertRaisesRegex(RenderError, "exactly 64"):
            render_reviewed_rollback(VALID_SQL, "abc")

    def test_bom_is_rejected(self) -> None:
        data = b"\xef\xbb\xbf" + VALID_SQL
        self.assert_rejected(data, "BOM")

    def test_missing_commit_is_rejected(self) -> None:
        self.assert_rejected(b"begin; select 1;", "exactly one top-level COMMIT")

    def test_duplicate_commit_is_rejected(self) -> None:
        self.assert_rejected(b"begin; commit; commit;", "observed 2")

    def test_trailing_sql_after_commit_is_rejected(self) -> None:
        self.assert_rejected(b"begin; select 1; commit; select 2;", "terminal SQL statement")

    def test_commit_in_comments_strings_and_dollar_body_is_ignored(self) -> None:
        data = b"""-- COMMIT;\nbegin;\nselect 'COMMIT;', \"COMMIT\";\ndo $tag$ begin raise notice 'COMMIT'; end $tag$;\n/* a /* nested COMMIT */ comment */\ncommit;\n"""
        rendered, _ = self.render(data)
        self.assertEqual(rendered.count(b"ROLLBACK"), 1)

    def test_unterminated_single_quote_is_rejected(self) -> None:
        self.assert_rejected(b"begin; select 'oops; commit;", "unterminated single")

    def test_unterminated_double_quote_is_rejected(self) -> None:
        self.assert_rejected(b'begin; select "oops; commit;', "unterminated double")

    def test_unterminated_block_comment_is_rejected(self) -> None:
        self.assert_rejected(b"begin; /* oops commit;", "unterminated block")

    def test_unterminated_dollar_quote_is_rejected(self) -> None:
        self.assert_rejected(b"begin; do $tag$ begin null; end; commit;", "unterminated dollar")

    def test_multiple_begin_is_rejected(self) -> None:
        self.assert_rejected(b"begin; begin; commit;", "top-level BEGIN, observed 2")

    def test_existing_rollback_is_rejected(self) -> None:
        self.assert_rejected(b"begin; rollback; commit;", "already contains 1")

    def test_sql_before_begin_is_rejected(self) -> None:
        self.assert_rejected(b"set search_path=erp; begin; commit;", "BEGIN must be the first")

    def test_commit_work_is_rejected_as_unreviewed_terminal_shape(self) -> None:
        self.assert_rejected(b"begin; select 1; commit work;", "exactly COMMIT")

    def test_unterminated_final_statement_is_rejected(self) -> None:
        self.assert_rejected(b"begin; select 1; commit", "semicolon-terminated")

    def test_cli_writes_output_and_metadata(self) -> None:
        script = Path(__file__).with_name("cp3_render_reviewed_rollback.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.sql"
            output = root / "rollback.sql"
            metadata = root / "metadata.json"
            source.write_bytes(VALID_SQL)
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--input",
                    str(source),
                    "--expected-sha256",
                    digest(VALID_SQL),
                    "--output",
                    str(output),
                    "--metadata",
                    str(metadata),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(metadata.read_text())
            self.assertEqual(payload["input_sha256"], digest(VALID_SQL))
            self.assertEqual(payload["output_sha256"], digest(output.read_bytes()))
            self.assertIn(b"ROLLBACK;", output.read_bytes())


if __name__ == "__main__":
    unittest.main()
