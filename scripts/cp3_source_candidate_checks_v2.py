#!/usr/bin/env python3
"""Superseding CP3 V2.1 source gate including the hardening delta."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cp3_source_candidate_checks as base

ROOT = Path(__file__).resolve().parents[1]
HARDENING = ROOT / "supabase/migrations/20260901023200_erp_v2_6_14c_attendance_hpp_candidate_hardening.sql"


def main() -> int:
    try:
        if base.main() != 0:
            raise base.CheckFailure("base CP3 source gate failed")

        base.require(HARDENING.is_file(), f"missing hardening migration: {HARDENING}")
        base.require(HARDENING.stat().st_size > 100, "hardening migration is suspiciously small")
        hardening_tx = base.check_transaction_shape(HARDENING, "COMMIT")
        text = base.strip_sql_comments(HARDENING.read_text(encoding="utf-8")).lower()

        for required in (
            "guard_attendance_hpp_sewing_event_v1",
            "cp3_validate_sewing_source_v1",
            "reversal must exactly negate",
            "correction must retain source production",
            "sewing_contractor_without_payroll_source",
            "invalid_policy_manifest",
            "destination_count_mismatch",
            "o(pool_sources + pool_destinations + allocations)",
        ):
            base.require(required in text, f"hardening contract missing: {required}")

        base.require("post_journal(" not in text, "hardening migration must not post GL")
        base.require("create or replace function public." not in text, "hardening migration must remain private")

        report_path = ROOT / "cp3-source-candidate-check-report.json"
        base_report = json.loads(report_path.read_text(encoding="utf-8"))
        hardening_entry = {
            "label": "migration_candidate_hardening",
            "path": str(HARDENING.relative_to(ROOT)),
            "bytes": HARDENING.stat().st_size,
            "sha256": base.sha256(HARDENING),
        }
        files = [entry for entry in base_report["files"] if entry["path"] != hardening_entry["path"]]
        files.append(hardening_entry)
        files.sort(key=lambda item: item["path"])

        report = {
            "status": "PASS_SOURCE_SHAPE_ONLY",
            "gate_version": "CP3_SOURCE_CANDIDATE_V2_1",
            "supersedes": "cp3-source-candidate-check-report.json",
            "truth_boundary": base_report["truth_boundary"],
            "transaction_shape": {
                **base_report["transaction_shape"],
                "migration_candidate_hardening": hardening_tx,
            },
            "rollback_renderer_test_count": base_report["rollback_renderer_test_count"],
            "hardening_assertions": {
                "trigger_rechecks_authoritative_sewing_source": True,
                "exact_reversal_lineage": True,
                "correction_lineage": True,
                "sewing_contractor_requires_pool_payroll_source": True,
                "policy_manifest_required": True,
                "destination_count_reconciled": True,
                "deferred_validator_added": False,
                "gl_posting_added": False,
                "public_facade_added": False,
            },
            "files": files,
        }
        output = ROOT / "cp3-source-candidate-v2-check-report.json"
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        sums = ROOT / "cp3-source-candidate-v2-SHA256SUMS.txt"
        sums.write_text("".join(f"{item['sha256']}  {item['path']}\n" for item in files), encoding="utf-8")
        print(json.dumps(report, sort_keys=True))
        return 0
    except (base.CheckFailure, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"CP3 V2.1 source candidate check FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
