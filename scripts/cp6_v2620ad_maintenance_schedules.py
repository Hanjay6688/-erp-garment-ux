#!/usr/bin/env python3
"""Twenty focused AD admission/drain/rollback schedules on fresh clones."""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import psycopg

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620ad_runtime as runtime
import cp6_v2620h_maintenance_rollback_matrix as matrix


ROOT = Path("cp6-proof/AD_MAINTENANCE_ROLLBACK")
REPORT = ROOT / "manifest.json"


def run() -> dict:
    expected_environment = (
        matrix.SOURCE, matrix.MAINTENANCE, matrix.CLONE, matrix.CONTAINER,
        "cp6_rollback",
    )
    actual_environment = (
        os.environ.get("PGURL"), os.environ.get("CP6_MAINTENANCE_PGURL"),
        os.environ.get("CP6_ROLLBACK_RACE_PGURL"),
        os.environ.get("CP6_DATABASE_CONTAINER"),
        os.environ.get("CP6_MAINTENANCE_CONFIRM_DATABASE"),
    )
    if actual_environment != expected_environment:
        raise AssertionError("AD_MAINTENANCE_EXACT_DISPOSABLE_ENVIRONMENT_REQUIRED")
    if os.environ.get("CP6_AD_MAINTENANCE_CONFIRM") != "cp6_rollback":
        raise AssertionError("AD_MAINTENANCE_EXPLICIT_CONFIRMATION_REQUIRED")

    matrix.TARGETS["AC"] = ("20260915031500", "erp_v2_6_20ac_cp6_temporal_surface_closure", "v2.6.20ac", "v2.6.20ab", 115)
    matrix.TARGETS["AD"] = (
        runtime.STAMP, runtime.NAME, runtime.VERSION, "v2.6.20ac", 2,
    )
    with psycopg.connect(matrix.SOURCE) as conn, conn.cursor() as cur:
        source_objects = runtime.verified_successor(cur)
    if len(source_objects) != 274:
        raise AssertionError("AD_MAINTENANCE_EXACT_AD_SOURCE_REQUIRED")

    result = {
        "format": "CP6_V2620AD_MAINTENANCE_SCHEDULES_V1",
        "status": "FAIL",
        "head": os.environ.get("GITHUB_SHA"),
        "source_object_count": len(source_objects),
        "expected_case_count": 20,
        "cases": [],
        "production_go": False,
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    for operation in matrix.OPERATIONS:
        for mode in matrix.MODES:
            name = f"AD-{operation}-{mode}"
            folder = ROOT / name
            folder.mkdir(parents=True, exist_ok=True)
            try:
                evidence = matrix.run_case(
                    "AD", operation, mode, folder, source_generation="AD"
                )
            except Exception as exc:
                evidence = {
                    "status": "FAIL", "target": "AD", "operation": operation,
                    "mode": mode, "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            finally:
                matrix.legacy.drop_clone()
            with psycopg.connect(matrix.MAINTENANCE) as conn:
                remaining = conn.execute(
                    "select count(*) from pg_database where datname='cp6_rollback'"
                ).fetchone()[0]
            evidence["remaining_clone_databases"] = remaining
            if remaining:
                evidence["status"] = "FAIL"
            result["cases"].append(evidence)
            REPORT.write_text(json.dumps(result, indent=2, default=str) + "\n")
            print(json.dumps({
                "case": name, "status": evidence["status"],
                "remaining_clone_databases": remaining,
            }), flush=True)
    result["completed_case_count"] = sum(
        item["status"] == "PASS" for item in result["cases"]
    )
    if (
        len(result["cases"]) == result["expected_case_count"] == 20
        and result["completed_case_count"] == 20
    ):
        result["status"] = "PASS"
    REPORT.write_text(json.dumps(result, indent=2, default=str) + "\n")
    return result


if __name__ == "__main__":
    try:
        outcome = run()
    except Exception as exc:
        outcome = {
            "format": "CP6_V2620AD_MAINTENANCE_SCHEDULES_V1",
            "status": "FAIL", "error": str(exc),
            "traceback": traceback.format_exc(), "production_go": False,
        }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(outcome, indent=2, default=str) + "\n")
    print(json.dumps({key: value for key, value in outcome.items() if key != "cases"}))
    raise SystemExit(0 if outcome.get("status") == "PASS" else 1)
