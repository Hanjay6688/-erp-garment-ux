#!/usr/bin/env python3
"""Restore AF to the exact 533-function / 220-table AE predecessor."""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import psycopg

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620af_runtime as runtime
from cp6_v2620af_family import actors, expected_refusal, sql_body
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot


ROOT = Path("cp6-proof/writer-af")
REPORT = ROOT / "AF_EXACT_AE_RESTORE.json"
EXPECTED_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"


def normalized(value):
    return json.loads(json.dumps(value, default=str))


def difference(before_catalog, before_boundary, catalog, boundary):
    before_functions = {row[0]: row for row in before_catalog}
    after_functions = {row[0]: row for row in catalog}
    before_tables = {".".join(row[:2]): row for row in before_boundary["tables"]}
    after_tables = {".".join(row[:2]): row for row in boundary["tables"]}
    return {
        "catalog_exact": catalog == before_catalog,
        "boundary_exact": boundary == before_boundary,
        "function_differences": [
            name for name in sorted(before_functions.keys() | after_functions.keys())
            if before_functions.get(name) != after_functions.get(name)
        ],
        "boundary_metadata_exact": {
            key: value for key, value in before_boundary.items() if key != "tables"
        } == {
            key: value for key, value in boundary.items() if key != "tables"
        },
        "table_differences": {
            name: {"before": before_tables.get(name), "after": after_tables.get(name)}
            for name in sorted(before_tables.keys() | after_tables.keys())
            if before_tables.get(name) != after_tables.get(name)
        },
    }


def run() -> dict:
    head, tree = runtime.verify_audit_source()
    if os.environ.get("PGURL") != EXPECTED_URL:
        raise AssertionError("AF_EXACT_DISPOSABLE_RESTORE_REQUIRED")
    if (
        os.environ.get("CP6_MAINTENANCE_CONFIRM_DATABASE") != "postgres"
        or os.environ.get("CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE") != "postgres"
    ):
        raise AssertionError("AF_EXPLICIT_DISPOSABLE_SYSTEM_DATABASE_REQUIRED")
    with psycopg.connect(EXPECTED_URL) as connection, connection.cursor() as cur:
        if len(runtime.verified_successor(cur)) != 278:
            raise AssertionError("AF_RESTORE_SOURCE_MISMATCH")

    controls = {
        "FUNCTION_CONFIGURATION": ("alter function erp.guard_child_by_parent_status() set work_mem='64MB'", "AF_TRUSTED_PREDECESSOR_PIN_MISMATCH"),
        "FUNCTION_ACL": ("grant execute on function erp.guard_child_by_parent_status() to anon", "AF_TRUSTED_PREDECESSOR_PIN_MISMATCH"),
        "FUNCTION_OWNER": ("alter function erp.guard_child_by_parent_status() owner to supabase_admin", "AF_TRUSTED_PREDECESSOR_PIN_MISMATCH"),
        "UNEXPECTED_TABLE": ("create table erp.cp6_af_unexpected(id integer)", "AF_BOUNDARY_SNAPSHOT_MISMATCH"),
        "MISSING_TABLE": ("drop table erp.cp6_v2620ab_rollback_capsule", "AF_BOUNDARY_SNAPSHOT_MISMATCH"),
        "POST_USE": ("insert into erp.locations(location_code,location_name,location_type) values('AF-ROLLBACK-PROBE','AF probe','FG_WAREHOUSE')", "AF_POST_USE_ROLLBACK_REFUSED"),
        "CAPSULE_DEFINITION": (f"update {runtime.CAPSULE} set object_definition=object_definition||E'\\n-- altered'", "AF_TRUSTED_PREDECESSOR_PIN_MISMATCH"),
        "PLATFORM_SOURCE": (f"update supabase_migrations.schema_migrations set statements=array['wrong'] where name='{runtime.NAME}'", "AF_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR"),
    }
    atomic = {"status": "INCOMPLETE", "cases": {}, "production_go": False}
    with psycopg.connect(EXPECTED_URL.replace("postgres:postgres@", "supabase_admin:postgres@")) as connection, connection.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        for name, (mutation, error) in controls.items():
            before, catalog = actors.boundary(cur), function_catalog(cur)
            cur.execute("savepoint af_atomic")
            try:
                cur.execute(mutation)
                record = expected_refusal(cur, lambda: cur.execute(sql_body(runtime.ROLLBACK), prepare=False), error)
                record["status"] = "PASS"
            except Exception as exc:
                record = {"status": "FAIL", "error": str(exc), "traceback": traceback.format_exc()}
            finally:
                cur.execute("rollback to savepoint af_atomic;release savepoint af_atomic")
            record["entire_boundary_restored"] = actors.boundary(cur) == before and function_catalog(cur) == catalog
            if not record["entire_boundary_restored"]:
                record["status"] = "FAIL"
            atomic["cases"][name] = record
        connection.rollback()
    if len(atomic["cases"]) == 8 and all(item["status"] == "PASS" for item in atomic["cases"].values()):
        atomic["status"] = "PASS"
    (ROOT / "AF_ROLLBACK_ATOMIC_CONTROLS.json").write_text(json.dumps(atomic, indent=2) + "\n")
    if atomic["status"] != "PASS":
        raise AssertionError("AF_ROLLBACK_ATOMIC_CONTROLS_FAILED:" + json.dumps(atomic))

    result = maintenance.run_maintenance_rollback(
        target_name="AF",
        target_pgurl=EXPECTED_URL,
        maintenance_pgurl=os.environ["CP6_ADMISSION_CONTROL_PGURL"],
        report_path=ROOT / "AF_MAIN_MAINTENANCE_ROLLBACK.json",
        drain_timeout=10,
        natural_grace=0,
        terminate_after_grace=True,
    )
    required = {
        "ENDPOINT_VERIFIED", "CAPSULE_VERIFIED", "ADMISSION_CLOSED", "DRAINED",
        "ROLLBACK_STARTED", "ROLLBACK_COMMITTED", "PREDECESSOR_VERIFIED",
        "ADMISSION_REOPENED",
    }
    if not required.issubset({item["phase"] for item in result["phases"]}):
        raise AssertionError("AF_MAINTENANCE_PHASES_INCOMPLETE")

    before_catalog = json.loads((ROOT / "AE_COMPLETE_CATALOG.json").read_text())
    before_boundary = json.loads((ROOT / "AE_COMPLETE_BOUNDARY.json").read_text())
    admin_url = EXPECTED_URL.replace("postgres:postgres@", "supabase_admin:postgres@")
    with psycopg.connect(admin_url) as connection, connection.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta'")
        runtime.verify_predecessor(cur)
        catalog = normalized(function_catalog(cur))
        boundary = normalized(snapshot(cur))
        users = cur.execute(
            "select (select count(*) from auth.users),(select count(*) from erp.app_users)"
        ).fetchone()
    diagnostics = difference(before_catalog, before_boundary, catalog, boundary)
    (ROOT / "AF_RESTORE_CONTEXT_DIAGNOSTICS.json").write_text(
        json.dumps(diagnostics, indent=2) + "\n"
    )
    exact = catalog == before_catalog and boundary == before_boundary
    final = {
        "status": "PASS" if exact and len(catalog) == 533
        and len(boundary["tables"]) == 220 and users == (0, 0) else "FAIL",
        "head": head, "tree": tree,
        "restored_candidate": runtime.PREDECESSOR_HEAD,
        "functions": len(catalog), "tables": len(boundary["tables"]),
        "full_function_owner_acl_and_data_boundary_exact": exact,
        "auth_users": users[0], "app_users": users[1],
        "baseline_and_restore_context": {
            "user": "supabase_admin", "timezone": "Asia/Jakarta",
        },
        "new_edge": "AF -> AE", "production_go": False,
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(final, indent=2) + "\n")
    return final


if __name__ == "__main__":
    try:
        final = run()
    except Exception as exc:
        final = {
            "status": "FAIL", "error": str(exc),
            "traceback": traceback.format_exc(), "production_go": False,
        }
        ROOT.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(final, indent=2) + "\n")
    print(json.dumps(final))
    raise SystemExit(0 if final["status"] == "PASS" else 1)
