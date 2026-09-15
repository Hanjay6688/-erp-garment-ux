#!/usr/bin/env python3
"""Restore AE to the exact 533-function / 219-table AD predecessor."""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import psycopg

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620ae_runtime as runtime
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot


ROOT = Path("cp6-proof/writer-ae")
REPORT = ROOT / "AE_EXACT_AD_RESTORE.json"
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
        raise AssertionError("AE_EXACT_DISPOSABLE_RESTORE_REQUIRED")
    if (
        os.environ.get("CP6_MAINTENANCE_CONFIRM_DATABASE") != "postgres"
        or os.environ.get("CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE") != "postgres"
    ):
        raise AssertionError("AE_EXPLICIT_DISPOSABLE_SYSTEM_DATABASE_REQUIRED")
    with psycopg.connect(EXPECTED_URL) as connection, connection.cursor() as cur:
        if len(runtime.verified_successor(cur)) != 276:
            raise AssertionError("AE_RESTORE_SOURCE_MISMATCH")

    result = maintenance.run_maintenance_rollback(
        target_name="AE",
        target_pgurl=EXPECTED_URL,
        maintenance_pgurl=os.environ["CP6_ADMISSION_CONTROL_PGURL"],
        report_path=ROOT / "AE_MAIN_MAINTENANCE_ROLLBACK.json",
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
        raise AssertionError("AE_MAINTENANCE_PHASES_INCOMPLETE")

    before_catalog = json.loads((ROOT / "AD_COMPLETE_CATALOG.json").read_text())
    before_boundary = json.loads((ROOT / "AD_COMPLETE_BOUNDARY.json").read_text())
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
    (ROOT / "AE_RESTORE_CONTEXT_DIAGNOSTICS.json").write_text(
        json.dumps(diagnostics, indent=2) + "\n"
    )
    exact = catalog == before_catalog and boundary == before_boundary
    final = {
        "status": "PASS" if exact and len(catalog) == 533
        and len(boundary["tables"]) == 219 and users == (0, 0) else "FAIL",
        "head": head, "tree": tree,
        "restored_candidate": runtime.PREDECESSOR_HEAD,
        "functions": len(catalog), "tables": len(boundary["tables"]),
        "full_function_owner_acl_and_data_boundary_exact": exact,
        "auth_users": users[0], "app_users": users[1],
        "baseline_and_restore_context": {
            "user": "supabase_admin", "timezone": "Asia/Jakarta",
        },
        "new_edge": "AE -> AD", "production_go": False,
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
