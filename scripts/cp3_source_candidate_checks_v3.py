#!/usr/bin/env python3
"""Final CP3 source gate extension for authoritative terminal sewing facts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cp3_source_candidate_checks as base
import cp3_source_candidate_checks_v2 as v2

ROOT = Path(__file__).resolve().parents[1]
AUTHORITATIVE = ROOT / "supabase/migrations/20260901023300_erp_v2_6_14d_authoritative_sewing_source.sql"


def function_body(executable: str, function_name: str) -> str:
    match = re.search(
        rf"create\s+or\s+replace\s+function\s+erp\.{re.escape(function_name)}\b([\s\S]*?)\n\$function\$;",
        executable,
        re.IGNORECASE,
    )
    base.require(match is not None, f"function definition missing: {function_name}")
    return match.group(0).lower()


def main() -> int:
    try:
        if v2.main() != 0:
            raise base.CheckFailure("CP3 V2.1 source gate failed")

        base.require(AUTHORITATIVE.is_file(), f"missing authoritative source migration: {AUTHORITATIVE}")
        base.require(AUTHORITATIVE.stat().st_size > 100, "authoritative source migration is suspiciously small")
        tx = base.check_transaction_shape(AUTHORITATIVE, "COMMIT")
        executable = base.strip_sql_comments(AUTHORITATIVE.read_text(encoding="utf-8")).lower()

        for required in (
            "cp3_sewing_source_snapshot_v2",
            "work completion must be terminal",
            "posted","completed","final","closed",
            "source_payload_hash",
            "stale_sewing_source",
            "correct_sewing_terminal_event_v2",
            "replacement terminal work-completion line",
            "correct_sewing_terminal_event_v1 is disabled",
            "asia/jakarta",
            "reversal must exactly negate one authoritative sewing event",
        ):
            base.require(required in executable, f"authoritative sewing contract missing: {required}")

        snapshot = function_body(executable, "cp3_sewing_source_snapshot_v2")
        for forbidden in ("qc", "laundry", "rework", "rewash", "susulan", "return"):
            base.require(forbidden in snapshot, f"downstream rejection token missing from source snapshot: {forbidden}")
        for required in (
            "work_completions",
            "work_completion_lines",
            "work_components",
            "terminal_status",
            "effective_at_epoch_us",
            "source_payload_hash",
        ):
            base.require(required in snapshot, f"source snapshot does not derive {required}")

        record = function_body(executable, "record_sewing_terminal_event_v1")
        for forbidden_input in (
            "'production_order_id'",
            "'contractor_id'",
            "'effective_date'",
            "'effective_at'",
            "'quantity'",
        ):
            # These tokens may appear in derived response/insert expressions, but
            # must not be inside the required/allowed payload contract preceding
            # the first source snapshot call.
            contract_segment = record.split("v_snapshot := erp.cp3_sewing_source_snapshot_v2", 1)[0]
            base.require(
                forbidden_input not in contract_segment,
                f"operator-supplied authoritative field survived record payload contract: {forbidden_input}",
            )
        for required in (
            "expected_source_payload_hash",
            "cp3_sewing_source_snapshot_v2",
            "source_payload_hash",
            "stale_sewing_source",
        ):
            base.require(required in record, f"record source-hash guard missing: {required}")

        correction_v1 = function_body(executable, "correct_sewing_terminal_event_v1")
        base.require("is disabled" in correction_v1, "arbitrary v1 correction remains executable")
        correction_v2 = function_body(executable, "correct_sewing_terminal_event_v2")
        for required in (
            "replacement_source_work_completion_line_id",
            "expected_replacement_source_hash",
            "cp3_sewing_source_snapshot_v2",
            "correction replacement must retain production order and mandor",
        ):
            base.require(required in correction_v2, f"replacement-source correction guard missing: {required}")

        base.require("post_journal(" not in executable, "authoritative source migration must not post GL")
        base.require("create or replace function public." not in executable, "authoritative source migration must remain private")
        base.require(
            "grant execute on function erp.correct_sewing_terminal_event_v1" not in executable,
            "disabled v1 correction was re-granted",
        )

        prior_path = ROOT / "cp3-source-candidate-v2-check-report.json"
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        entry = {
            "label": "migration_authoritative_terminal_sewing_source",
            "path": str(AUTHORITATIVE.relative_to(ROOT)),
            "bytes": AUTHORITATIVE.stat().st_size,
            "sha256": base.sha256(AUTHORITATIVE),
        }
        files = [item for item in prior["files"] if item["path"] != entry["path"]]
        files.append(entry)
        files.sort(key=lambda item: item["path"])

        report = {
            "status": "PASS_SOURCE_SHAPE_ONLY",
            "gate_version": "CP3_SOURCE_CANDIDATE_V2_2",
            "supersedes": "cp3-source-candidate-v2-check-report.json",
            "truth_boundary": prior["truth_boundary"],
            "transaction_shape": {
                **prior["transaction_shape"],
                "migration_authoritative_terminal_sewing_source": tx,
            },
            "rollback_renderer_test_count": prior["rollback_renderer_test_count"],
            "authoritative_source_assertions": {
                "terminal_work_completion_required": True,
                "sewing_component_required": True,
                "downstream_destinations_rejected": True,
                "po_mandor_qty_date_time_derived": True,
                "source_hash_optimistic_guard": True,
                "arbitrary_v1_correction_disabled": True,
                "replacement_source_correction_v2": True,
                "gl_posting_added": False,
                "public_facade_added": False,
            },
            "files": files,
        }
        output = ROOT / "cp3-source-candidate-v3-check-report.json"
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        sums = ROOT / "cp3-source-candidate-v3-SHA256SUMS.txt"
        sums.write_text("".join(f"{item['sha256']}  {item['path']}\n" for item in files), encoding="utf-8")
        print(json.dumps(report, sort_keys=True))
        return 0
    except (base.CheckFailure, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"CP3 V2.2 source candidate check FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
