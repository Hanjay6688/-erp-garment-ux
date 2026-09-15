#!/usr/bin/env python3
"""Assemble and fail-close the exact AC writer evidence manifest."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import traceback
from pathlib import Path
from typing import Any

import cp6_v2620ac_runtime as runtime


PROOF = Path("cp6-proof")
REPORT = PROOF / "CP6_V2620AC_WRITER_MANIFEST.json"


def read(name: str, head: str) -> dict[str, Any]:
    result = json.loads((PROOF / name).read_text(encoding="utf-8"))
    if result.get("head") != head:
        raise AssertionError(f"AC_EVIDENCE_HEAD_MISMATCH:{name}")
    if result.get("production_go") is not False:
        raise AssertionError(f"AC_EVIDENCE_PRODUCTION_FLAG:{name}")
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(
        ["git", "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    if os.environ.get("GITHUB_SHA") != head:
        raise AssertionError("AC_PROOF_EXACT_NATIVE_CHECKOUT_REQUIRED")
    runtime.verify_audit_source()

    static = json.loads(
        (PROOF / "CP6_V2620AC_STATIC_QUALIFICATION.json").read_text()
    )
    if (
        static.get("status") != "PASS"
        or static.get("occurrence_count") != 709
        or static.get("decisions") != {"CHANGE": 422, "EXCLUDE": 2, "KEEP": 285}
        or static.get("function_count") != 115
        or static.get("view_count") != 13
        or static.get("table_default_count") != 144
        or static.get("plpgsql_record_alias_qualification") != {
            "blocks_checked": 124,
            "record_variables_checked": 59,
            "collisions": 0,
        }
        or any(static.get("stale_transaction_clock_tokens", {}).values())
    ):
        raise AssertionError("AC_STATIC_EVIDENCE_MISMATCH")

    install = read("CP6_V2620AC_INSTALL_QUALIFICATION.json", head)
    installed = read("V2620AC_INSTALLED_RUNTIME.json", head)
    invoice = read(
        "writer-ac/AC_INVOICE_PARTIAL_REGRESSION.json", head
    )
    linked = read(
        "writer-ac/AC_LINKED_LIFECYCLE_REGRESSION.json", head
    )
    operational = read(
        "writer-ac/AC_OPERATIONAL_CLOCK_REGRESSION.json", head
    )
    revocation = read(
        "writer-ac/revocation/AC_REVOCATION_REGRESSION.json", head
    )
    schedules = read("AC_MAINTENANCE_ROLLBACK/manifest.json", head)
    guards = read("CP6_V2620AC_ROLLBACK_GUARDS.json", head)
    restore = read("V2620AC_COMPLETE_AB_RESTORE.json", head)
    carry = read("CP6_AB189_MATRIX_CARRY_FORWARD.json", head)

    if (
        install.get("status") != "PASS"
        or install.get("expected_cases") != len(install.get("cases", {}))
        or install.get("expected_cases") != 16
        or not install.get("entire_runtime_restored")
        or not all(
            case.get("status") == "CONTROL_PASS"
            and case.get("full_case_boundary_restored")
            for case in install.get("cases", {}).values()
        )
    ):
        raise AssertionError("AC_INSTALL_EVIDENCE_MISMATCH")
    if (
        installed.get("status") != "PASS"
        or installed.get("object_count") != 272
        or installed.get("object_counts")
        != {"COLUMN_DEFAULT": 144, "FUNCTION": 115, "VIEW": 13}
    ):
        raise AssertionError("AC_RUNTIME_EVIDENCE_MISMATCH")

    bounded = (
        (invoice, 16, "PASS_BOUNDED_REGRESSION"),
        (linked, 63, "PASS_BOUNDED_REGRESSION"),
        (operational, 10, "PASS_BOUNDED_AUDIT"),
        (revocation, 3, "PASS_BOUNDED_AUDIT"),
    )
    for report, count, status in bounded:
        if (
            report.get("status") != status
            or report.get("expected_cases") != count
            or len(report.get("cases", {})) != count
            or report.get("controls") != count
            or report.get("counterexamples") != 0
            or report.get("incomplete") != 0
        ):
            raise AssertionError("AC_BOUNDED_REGRESSION_MISMATCH")
    if (
        not operational.get("physical_harness_complete")
        or operational.get("application_function_modifications") != 0
        or not operational.get("source_boundary_unchanged")
        or not operational.get("source_clock_still_real")
        or operational.get("cleanup_errors")
    ):
        raise AssertionError("AC_OPERATIONAL_CLOCK_HARNESS_MISMATCH")
    if not revocation.get("source_boundary_unchanged"):
        raise AssertionError("AC_REVOCATION_SOURCE_CHANGED")
    if (
        schedules.get("status") != "PASS"
        or schedules.get("expected_case_count") != 20
        or schedules.get("completed_case_count") != 20
        or len(schedules.get("cases", [])) != 20
        or any(case.get("status") != "PASS" for case in schedules["cases"])
    ):
        raise AssertionError("AC_MAINTENANCE_SCHEDULE_MISMATCH")
    if (
        guards.get("status") != "PASS"
        or guards.get("boundary_refusal_control_count") != 2
        or len(guards.get("boundary_refusal_cases", {})) != 2
        or any(
            case.get("status") != "CONTROL_PASS"
            or not case.get("full_runtime_restored")
            for case in guards.get("boundary_refusal_cases", {}).values()
        )
        or guards.get("restored_ab_function_count") != 5
        or guards.get("ac_residue_zero") is not True
        or restore.get("status") != "PASS"
        or restore.get("complete_function_count") != 533
        or restore.get("restored_table_count") != 215
        or not restore.get("definitions_owners_acls_exact")
        or not restore.get("full_table_boundary_exact")
    ):
        raise AssertionError("AC_ROLLBACK_RESTORE_MISMATCH")
    if (
        carry.get("status") != "QUALIFIED_PREDECESSOR_EVIDENCE_CARRIED_FORWARD"
        or carry.get("predecessor_head") != runtime.AB_HEAD
        or carry.get("predecessor_tree") != runtime.AB_TREE
        or carry.get("case_count") != 460
        or carry.get("failed_case_count") != 0
    ):
        raise AssertionError("AC_PREDECESSOR_MATRIX_EVIDENCE_MISMATCH")

    source_paths = [
        runtime.MIGRATION, runtime.ROLLBACK, runtime.PINS, runtime.DISPOSITION,
        Path("scripts/cp6_v2620ac_temporal_spec.py"),
        Path("scripts/cp6_v2620ac_build_sql.py"),
        Path("scripts/cp6_v2620ac_runtime.py"),
        Path("scripts/cp6_v2620ac_static_qualification.py"),
        Path("scripts/cp6_v2620ac_install_qualification.py"),
        Path("scripts/cp6_v2620ac_invoice_partial_regression.py"),
        Path("scripts/cp6_v2620ac_linked_lifecycle_regression.py"),
        Path("scripts/cp6_v2620ac_operational_clock_regression.py"),
        Path("scripts/cp6_v2620ac_revocation_regression.py"),
        Path("scripts/cp6_v2620ac_maintenance_schedules.py"),
        Path("scripts/cp6_v2620ac_rollback_guards.py"),
        Path("scripts/cp6_v2620ac_proof.py"),
        Path("scripts/cp6_v2620ab_runtime.py"),
        Path("scripts/cp6_x_independent_audit.py"),
        Path("scripts/cp6_y_independent_audit.py"),
        Path("scripts/cp6_z_expanded_integrity_audit.py"),
        Path("scripts/cp6_aa_midnight_audit.py"),
        Path("scripts/cp6_aa_revocation_audit.py"),
        Path("scripts/cp6_preuse_rollback_maintenance.py"),
        Path("scripts/cp6_v2620h_maintenance_rollback_matrix.py"),
        Path("scripts/cp6_v2620ab_rollback_guards.py"),
        Path("scripts/cp6_v2620ab_proof.py"),
        Path(".github/workflows/cp6-full-schema-validation.yml"),
    ]
    source_pins = {
        str(path): {"bytes": len(path.read_bytes()), "sha256": sha256(path)}
        for path in source_paths
    }
    result = {
        "format": "CP6_V2620AC_WRITER_MANIFEST_V1",
        "status": "WRITER_PASS_PENDING_INDEPENDENT_AUDIT",
        "head": head, "tree": tree,
        "predecessor_head": runtime.AB_HEAD,
        "predecessor_tree": runtime.AB_TREE,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "temporal_inventory": {
            "reviewed_occurrences": 709, "changed": 422,
            "retained": 285, "excluded": 2, "unresolved": 0,
        },
        "runtime_objects": installed["object_counts"],
        "new_runtime_cases": {
            "atomic_admission": 16,
            "invoice_partial": 16,
            "linked_lifecycle": 63,
            "operational_clock": 10,
            "authorization_revocation": 3,
            "maintenance_schedules": 20,
            "rollback_boundary_refusals": 2,
            "total": 130,
        },
        "predecessor_matrix": {
            "cases": 460, "execution": "CARRIED_FROM_EXACT_AB_NATIVE_189",
            "native_run_id": carry["native_run_id"],
            "manifest_sha256": carry["manifest_sha256"],
        },
        "source_pins": source_pins,
        "rollback_restored_exact_ab": True,
        "hosted_database_used": False,
        "independent_acceptance_complete": False,
        "production_go": False,
    }
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    try:
        outcome = run()
    except Exception as exc:
        outcome = {
            "format": "CP6_V2620AC_WRITER_MANIFEST_V1",
            "status": "FAIL", "error": str(exc),
            "traceback": traceback.format_exc(), "production_go": False,
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(outcome, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in outcome.items() if k != "source_pins"}))
    raise SystemExit(
        0 if outcome.get("status") == "WRITER_PASS_PENDING_INDEPENDENT_AUDIT"
        else 1
    )
