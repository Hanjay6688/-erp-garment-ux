#!/usr/bin/env python3
"""Twenty AJ schedules using the unchanged established concurrency oracle."""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import psycopg
import importlib.util
import sys
sys.path.insert(0,str(Path.cwd()/"scripts"))

import cp6_v2620aj_runtime as runtime
import cp6_v2620h_maintenance_rollback_matrix as matrix

# Bind only the controller dependency to the AJ target addition. The matrix
# schedule, business sentinel, drain and refusal assertions stay byte-identical.
spec = importlib.util.spec_from_file_location('aj_matrix_controller', runtime.ROOT / 'scripts/cp6_preuse_rollback_maintenance.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
matrix.maintenance = controller


ROOT = Path("cp6-proof/AJ_MAINTENANCE_ROLLBACK")
REPORT = ROOT / "manifest.json"


def prepare(target, operation, folder, *, source_generation):
    """Bind the old oracle's fixture setup to AJ -> AI, with exact verification."""
    if target != "AJ" or source_generation != "AJ":
        raise AssertionError("AJ_SCHEDULE_REQUIRES_EXACT_EDGE")
    matrix.command(
        ["bash", "scripts/clone-cp6-disposable-database.sh", matrix.SOURCE,
         matrix.MAINTENANCE, matrix.CLONE, "cp6_rollback", matrix.CONTAINER,
         str(folder / "PHYSICAL_BOUNDARY")],
        folder / "clone.log",
    )
    with matrix.legacy.connect("aj-clone-source") as conn, conn.cursor() as cur:
        if len(runtime.verified_successor(cur)) != 690:
            raise AssertionError("AJ_CLONE_RUNTIME_MISMATCH")
    matrix.maintenance_strip("AJ", folder)
    with matrix.legacy.connect("aj-predecessor-fixture") as conn, conn.cursor() as cur:
        runtime.verify_predecessor(cur)
        fixture = matrix.legacy.seed(cur, operation)
        conn.commit()
    matrix.command(
        ["psql", matrix.CLONE, "-X", "-v", "ON_ERROR_STOP=1", "-f", str(runtime.MIGRATION)],
        folder / "install.log",
    )
    with matrix.legacy.connect("aj-exact-platform-ledger") as conn, conn.cursor() as cur:
        cur.execute(
            "insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)",
            (runtime.STAMP, runtime.NAME, [runtime.MIGRATION.read_text()]),
        )
        if len(runtime.verified_successor(cur)) != 690:
            raise AssertionError("AJ_SEEDED_RUNTIME_MISMATCH")
        conn.commit()
    capsule = matrix.legacy.capture_capsule("AJ")
    if len(capsule) != 6:
        raise AssertionError("AJ_SCHEDULE_CAPSULE_CARDINALITY")
    matrix.legacy.verify_functions(capsule, True)
    return fixture, capsule


def run():
    head, tree = runtime.verify_audit_source()
    controller.TARGETS['AJ']['rollback'] = runtime.reviewed_local_rollback()
    expected = (matrix.SOURCE, matrix.MAINTENANCE, matrix.CLONE, matrix.CONTAINER, "cp6_rollback")
    actual = (
        os.environ.get("PGURL"), os.environ.get("CP6_MAINTENANCE_PGURL"),
        os.environ.get("CP6_ROLLBACK_RACE_PGURL"), os.environ.get("CP6_DATABASE_CONTAINER"),
        os.environ.get("CP6_MAINTENANCE_CONFIRM_DATABASE"),
    )
    if actual != expected or os.environ.get("CP6_AJ_MAINTENANCE_CONFIRM") != "cp6_rollback":
        raise AssertionError("AJ_MAINTENANCE_EXACT_DISPOSABLE_ENVIRONMENT_REQUIRED")
    with psycopg.connect(matrix.SOURCE) as conn, conn.cursor() as cur:
        if len(runtime.verified_successor(cur)) != 690:
            raise AssertionError("AJ_MAINTENANCE_SOURCE_MISMATCH")
    matrix.TARGETS["AJ"] = (runtime.STAMP, runtime.NAME, runtime.VERSION, "v2.6.20ai", 6)
    original_prepare = matrix.prepare
    matrix.prepare = prepare
    result = {
        "format": "CP6_AJ_MAINTENANCE_SCHEDULES_V1", "status": "INCOMPLETE",
        "head": head, "tree": tree, "expected_case_count": 20, "cases": [],
        "unchanged_schedule_oracle": "scripts/cp6_v2620h_maintenance_rollback_matrix.py",
        "production_go": False,
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    try:
        for operation in matrix.OPERATIONS:
            for mode in matrix.MODES:
                name = f"AJ-{operation}-{mode}"
                folder = ROOT / name
                folder.mkdir(parents=True, exist_ok=True)
                try:
                    evidence = matrix.run_case("AJ", operation, mode, folder, source_generation="AJ")
                except Exception as exc:
                    evidence = {
                        "status": "FAIL", "target": "AJ", "operation": operation,
                        "mode": mode, "error": str(exc), "traceback": traceback.format_exc(),
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
                print(json.dumps({"case": name, "status": evidence["status"], "error": evidence.get("error")}), flush=True)
    finally:
        matrix.prepare = original_prepare
    result["completed_case_count"] = sum(item["status"] == "PASS" for item in result["cases"])
    if len(result["cases"]) == result["completed_case_count"] == result["expected_case_count"]:
        result["status"] = "PASS"
    REPORT.write_text(json.dumps(result, indent=2, default=str) + "\n")
    return result


if __name__ == "__main__":
    try:
        outcome = run()
    except Exception as exc:
        outcome = {"status": "FAIL", "error": str(exc), "traceback": traceback.format_exc(), "production_go": False}
        ROOT.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(outcome, indent=2) + "\n")
    print(json.dumps({key: value for key, value in outcome.items() if key != "cases"}))
    raise SystemExit(0 if outcome["status"] == "PASS" else 1)
