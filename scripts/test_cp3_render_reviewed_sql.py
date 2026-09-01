#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from cp3_render_reviewed_sql import RenderError, analyze_source, render


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sql_for(domain="ATTENDANCE_HPP", operation_type="ATTENDANCE_HPP_FOUNDATION", body="select 1;"):
    return f"-- CP3_OPERATION: DOMAIN={domain} TYPE={operation_type}\nbegin; {body} commit;\n"


def write_case(
    root: Path,
    sql: str,
    *,
    operation=None,
    overrides=None,
):
    source = root / "supabase/migrations/candidate.sql"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(sql, encoding="utf-8")
    analysis = analyze_source(source.read_bytes())
    renderer = Path(__file__).with_name("cp3_render_reviewed_sql.py")
    operation = operation or {
        "domain": "ATTENDANCE_HPP",
        "operation_type": "ATTENDANCE_HPP_FOUNDATION",
        "source_path": "supabase/migrations/candidate.sql",
    }
    payload = {
        "manifest_version": "CP3_REVIEWED_SQL_V1",
        "candidate": "test",
        "source_path": "supabase/migrations/candidate.sql",
        "source_sha256": analysis["source_sha256"],
        "source_bytes": analysis["source_bytes"],
        "renderer_sha256": digest(renderer.read_bytes()),
        "expected_top_level_statement_count": analysis["top_level_statement_count"],
        "expected_terminal_commit_start": analysis["terminal_commit_start"],
        "expected_rendered_sha256": analysis["rendered_sha256"],
        "expected_rendered_bytes": analysis["rendered_bytes"],
        "operations": [operation],
    }
    if overrides:
        payload.update(overrides)
    manifest_dir = root / "ops/cp3"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = manifest_dir / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return manifest


def expect_pass(name: str, sql: str, *, operation=None) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        manifest = write_case(root, sql, operation=operation)
        metadata = render(manifest, root / "out.sql", root / "out.json")
        assert metadata["status"] == "PASS", name


def expect_fail(name: str, sql: str, *, operation=None, overrides=None) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        try:
            manifest = write_case(root, sql, operation=operation, overrides=overrides)
            render(manifest, root / "out.sql", root / "out.json")
        except (RenderError, ValueError):
            return
        raise AssertionError(f"{name}: expected fail-closed RenderError")


def main() -> None:
    attendance = sql_for()
    expect_pass("normal_attendance", attendance)
    expect_pass("comment_commit_ignored", sql_for(body="-- COMMIT;\nselect 1;"))
    expect_pass("dollar_commit_ignored", sql_for(body="do $$ begin raise notice 'COMMIT;'; end $$;"))
    expect_fail("missing_commit", "-- CP3_OPERATION: DOMAIN=ATTENDANCE_HPP TYPE=ATTENDANCE_HPP_FOUNDATION\nbegin; select 1;\n")
    expect_fail("duplicate_commit", sql_for(body="select 1; commit;"))
    expect_fail("trailing_sql", attendance + "select 2;\n")
    expect_fail("wrong_source_digest", attendance, overrides={"source_sha256": "0" * 64})
    expect_fail("wrong_renderer_digest", attendance, overrides={"renderer_sha256": "0" * 64})
    expect_fail("wrong_rendered_digest", attendance, overrides={"expected_rendered_sha256": "0" * 64})
    expect_fail("wrong_statement_count", attendance, overrides={"expected_top_level_statement_count": 999})
    expect_fail("marker_manifest_mismatch", attendance, operation={
        "domain": "LAUNDRY_CLAIM", "operation_type": "LAUNDRY_CLAIM_SETTLEMENT",
        "source_path": "supabase/migrations/candidate.sql",
    })
    expect_fail("operation_source_path_mismatch", attendance, operation={
        "domain": "ATTENDANCE_HPP", "operation_type": "ATTENDANCE_HPP_FOUNDATION",
        "source_path": "supabase/migrations/other.sql",
    })

    claim_settlement = {
        "domain": "LAUNDRY_CLAIM", "operation_type": "LAUNDRY_CLAIM_SETTLEMENT",
        "source_path": "supabase/migrations/candidate.sql",
    }
    claim_reversal = {
        "domain": "LAUNDRY_CLAIM", "operation_type": "LAUNDRY_CLAIM_REVERSAL",
        "source_path": "supabase/migrations/candidate.sql",
    }
    expect_pass("claim_settlement_only", sql_for("LAUNDRY_CLAIM", "LAUNDRY_CLAIM_SETTLEMENT"), operation=claim_settlement)
    expect_pass("claim_reversal_only", sql_for("LAUNDRY_CLAIM", "LAUNDRY_CLAIM_REVERSAL"), operation=claim_reversal)
    expect_fail("claim_transfer_injection", sql_for("LAUNDRY_CLAIM", "LAUNDRY_CLAIM_SETTLEMENT", "select transfer_payload from x;"), operation=claim_settlement)
    expect_fail("claim_carry_injection", sql_for("LAUNDRY_CLAIM", "LAUNDRY_CLAIM_SETTLEMENT", "select carry_forward from x;"), operation=claim_settlement)
    expect_fail("claim_movement_injection", sql_for("LAUNDRY_CLAIM", "LAUNDRY_CLAIM_REVERSAL", "select stock_movement from x;"), operation=claim_reversal)
    print("CP3 renderer tests: PASS (17/17)")


if __name__ == "__main__":
    main()
