#!/usr/bin/env python3
"""Trusted AC capsule preflight and admission-closed exact AC-to-AB restore."""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620ab_runtime as predecessor
import cp6_v2620ac_runtime as runtime


REPORT = Path("cp6-proof/CP6_V2620AC_ROLLBACK_GUARDS.json")
MAINTENANCE_REPORT = Path("cp6-proof/V2620AC_MAIN_MAINTENANCE_ROLLBACK.json")


def qualify_boundary_refusals() -> dict[str, dict]:
    """Prove AC rollback refuses both missing and unexpected boundary tables."""
    source = runtime.ROLLBACK.read_text(encoding="utf-8")
    if source.count("\nbegin;\n") != 1 or not source.endswith("commit;\n"):
        raise AssertionError("AC_ROLLBACK_TRANSACTION_SHAPE")
    body = source.replace("\nbegin;\n", "\n", 1).removesuffix("commit;\n")
    cases = {
        "MISSING_BOUNDARY_TABLE": (
            "drop table erp.cp6_v2620ab_rollback_capsule",
            "AC_ROLLBACK_BOUNDARY_CAPSULE_MISMATCH",
        ),
        "UNEXPECTED_BOUNDARY_TABLE": (
            "create table erp.cp6_v2620ac_boundary_probe(id integer)",
            "AC_ROLLBACK_BOUNDARY_CAPSULE_MISMATCH",
        ),
    }
    results: dict[str, dict] = {}
    with psycopg.connect(os.environ["PGURL"]) as conn, conn.cursor() as cur:
        for name, (mutation, expected_error) in cases.items():
            cur.execute("savepoint ac_rollback_boundary_case")
            error = None
            sqlstate = None
            try:
                cur.execute(mutation)
                try:
                    cur.execute(body, prepare=False)
                except psycopg.Error as exc:
                    error = str(exc)
                    sqlstate = exc.sqlstate
                if error is None or expected_error not in error:
                    raise AssertionError(
                        f"AC_ROLLBACK_BOUNDARY_WRONG_RESULT:{name}:{error}"
                    )
            finally:
                cur.execute("rollback to savepoint ac_rollback_boundary_case")
                cur.execute("release savepoint ac_rollback_boundary_case")
            restored = (
                len(runtime.verified_successor(cur)) == 272
                and cur.execute(
                    "select count(*) from erp.cp6_v2620ab_rollback_capsule"
                ).fetchone()[0] == 5
                and cur.execute(
                    "select to_regclass('erp.cp6_v2620ac_boundary_probe') is null"
                ).fetchone()[0]
            )
            results[name] = {
                "status": "CONTROL_PASS" if restored else "FAIL",
                "expected_error": expected_error,
                "actual_error": error,
                "sqlstate": sqlstate,
                "full_runtime_restored": restored,
            }
        conn.rollback()
    if any(item["status"] != "CONTROL_PASS" for item in results.values()):
        raise AssertionError("AC_ROLLBACK_BOUNDARY_REFUSAL_NOT_RESTORED")
    return results


def run() -> dict:
    target = conninfo_to_dict(os.environ.get("PGURL", ""))
    controller = conninfo_to_dict(
        os.environ.get("CP6_ADMISSION_CONTROL_PGURL", "")
    )
    if target != {
        "user": "postgres", "password": "postgres", "host": "127.0.0.1",
        "port": "54322", "dbname": "postgres",
    }:
        raise AssertionError("AC_ROLLBACK_EXACT_TARGET_REQUIRED")
    expected_controller = {
        "user": "cp6_maintenance_admission", "host": "127.0.0.1",
        "port": "54322", "dbname": "template1",
    }
    if (
        set(controller) != {*expected_controller, "password"}
        or any(controller.get(key) != value for key, value in expected_controller.items())
        or not controller.get("password")
    ):
        raise AssertionError("AC_ROLLBACK_EXACT_MAINTENANCE_ENDPOINT_REQUIRED")
    if (
        os.environ.get("CP6_MAINTENANCE_CONFIRM_DATABASE") != "postgres"
        or os.environ.get("CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE") != "postgres"
    ):
        raise AssertionError("AC_ROLLBACK_EXPLICIT_SYSTEM_DATABASE_CONFIRMATION_REQUIRED")

    with psycopg.connect(os.environ["PGURL"]) as conn, conn.cursor() as cur:
        installed = runtime.verified_successor(cur)
    if len(installed) != 272:
        raise AssertionError("AC_ROLLBACK_EXACT_AC_RUNTIME_REQUIRED")
    kinds = {
        kind: sum(item["kind"] == kind for item in installed.values())
        for kind in ("FUNCTION", "VIEW", "COLUMN_DEFAULT")
    }
    if kinds != {"FUNCTION": 115, "VIEW": 13, "COLUMN_DEFAULT": 144}:
        raise AssertionError("AC_ROLLBACK_OBJECT_CARDINALITY")

    result = {
        "format": "CP6_V2620AC_ROLLBACK_GUARDS_V1",
        "status": "FAIL",
        "head": os.environ.get("GITHUB_SHA"),
        "preflight_object_counts": kinds,
        "production_go": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n")
    result["boundary_refusal_cases"] = qualify_boundary_refusals()
    result["boundary_refusal_control_count"] = sum(
        item["status"] == "CONTROL_PASS"
        for item in result["boundary_refusal_cases"].values()
    )
    REPORT.write_text(json.dumps(result, indent=2) + "\n")
    maintenance_result = maintenance.run_maintenance_rollback(
        target_name="AC",
        target_pgurl=os.environ["PGURL"],
        maintenance_pgurl=os.environ["CP6_ADMISSION_CONTROL_PGURL"],
        report_path=MAINTENANCE_REPORT,
        drain_timeout=10,
        natural_grace=0,
        terminate_after_grace=True,
    )
    required = {
        "ENDPOINT_VERIFIED", "CAPSULE_VERIFIED", "ADMISSION_CLOSED", "DRAINED",
        "ROLLBACK_STARTED", "ROLLBACK_COMMITTED", "PREDECESSOR_VERIFIED",
        "ADMISSION_REOPENED",
    }
    phases = [item["phase"] for item in maintenance_result.get("phases", [])]
    if not required.issubset(phases):
        raise AssertionError("AC_ROLLBACK_MAINTENANCE_PHASES_INCOMPLETE")
    with psycopg.connect(os.environ["PGURL"]) as conn, conn.cursor() as cur:
        restored = predecessor.verified_successor(cur)
        residue = cur.execute(
            "select to_regclass(%s),to_regclass(%s),"
            "(select count(*) from erp.schema_migrations where version=%s),"
            "(select count(*) from supabase_migrations.schema_migrations where name=%s)",
            (
                runtime.MAIN_CAPSULE, runtime.RELATION_CAPSULE,
                runtime.VERSION, runtime.NAME,
            ),
        ).fetchone()
    if len(restored) != 5 or residue != (None, None, 0, 0):
        raise AssertionError("AC_ROLLBACK_EXACT_AB_POSTCONDITION")
    result.update(
        status="PASS",
        maintenance=maintenance_result,
        restored_ab_function_count=len(restored),
        ac_residue_zero=True,
    )
    REPORT.write_text(json.dumps(result, indent=2, default=str) + "\n")
    return result


if __name__ == "__main__":
    try:
        outcome = run()
    except Exception as exc:
        outcome = {
            "format": "CP6_V2620AC_ROLLBACK_GUARDS_V1",
            "status": "FAIL", "error": str(exc),
            "traceback": traceback.format_exc(), "production_go": False,
        }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(outcome, indent=2, default=str) + "\n")
    print(json.dumps({key: value for key, value in outcome.items() if key != "maintenance"}))
    raise SystemExit(0 if outcome.get("status") == "PASS" else 1)
