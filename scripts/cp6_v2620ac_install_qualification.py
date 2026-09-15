#!/usr/bin/env python3
"""AC atomic admission qualification on the disposable Native database."""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot
import cp6_v2620ab_runtime as predecessor
import cp6_v2620ac_runtime as runtime


REPORT = Path("cp6-proof/CP6_V2620AC_INSTALL_QUALIFICATION.json")


def boundary(cur) -> dict:
    return {
        "functions": function_catalog(cur),
        "relations": snapshot(cur),
    }


def run() -> dict:
    params = conninfo_to_dict(os.environ.get("PGURL", ""))
    expected_endpoint = {
        "user": "postgres", "password": "postgres", "host": "127.0.0.1",
        "port": "54322", "dbname": "postgres",
    }
    if (
        params != expected_endpoint
        or os.environ.get("CP6_AC_DISPOSABLE_CONFIRM") != "postgres"
    ):
        raise AssertionError("AC_INSTALL_EXACT_DISPOSABLE_ENDPOINT_REQUIRED")
    source = runtime.MIGRATION.read_text(encoding="utf-8")
    if source.count("\nbegin;\n") != 1 or not source.endswith("commit;\n"):
        raise AssertionError("AC_INSTALL_TRANSACTION_SHAPE")
    body = source.replace("\nbegin;\n", "\n", 1).removesuffix("commit;\n")
    pin_payload = runtime.pins()
    function = pin_payload["functions"][0]["identity"]
    view = pin_payload["views"][0]["identity"]
    default = pin_payload["table_defaults"][0]
    table = "erp." + default["table"]
    cases = [
        (
            "FUNCTION_DEFINITION",
            f"alter function {function} cost 999",
            "AC_FUNCTION_PREDECESSOR_MISMATCH",
        ),
        (
            "FUNCTION_ACL",
            f"grant execute on function {function} to anon",
            "AC_FUNCTION_PREDECESSOR_MISMATCH",
        ),
        (
            "FUNCTION_OWNER",
            f"alter function {function} owner to service_role",
            "AC_FUNCTION_PREDECESSOR_MISMATCH",
        ),
        (
            "VIEW_DEFINITION",
            """create or replace view erp.v_accessory_category_current_cost
with (security_invoker=true) as
select id as category_id,category_code,category_name,base_uom_code,
  erp.accessory_category_weighted_avg_cost_at(id,now())
    as weighted_avg_cost_per_base_uom
from erp.accessory_categories
where false""",
            "AC_VIEW_PREDECESSOR_MISMATCH",
        ),
        (
            "VIEW_OPTIONS",
            f"alter view {view} set (security_invoker=false)",
            "AC_VIEW_PREDECESSOR_MISMATCH",
        ),
        (
            "VIEW_ACL",
            f"grant select on {view} to anon",
            "AC_VIEW_PREDECESSOR_MISMATCH",
        ),
        (
            "VIEW_OWNER",
            f"alter view {view} owner to service_role",
            "AC_VIEW_PREDECESSOR_MISMATCH",
        ),
        (
            "TABLE_DEFAULT",
            f"alter table {table} alter column {default['column']} "
            "set default clock_timestamp()",
            "AC_DEFAULT_PREDECESSOR_MISMATCH",
        ),
        (
            "TABLE_ACL",
            f"grant select on {table} to anon",
            "AC_DEFAULT_PREDECESSOR_MISMATCH",
        ),
        (
            "TABLE_OWNER",
            f"alter table {table} owner to service_role",
            "AC_DEFAULT_PREDECESSOR_MISMATCH",
        ),
        (
            "MISSING_AB_MARKER",
            "delete from erp.schema_migrations where version='v2.6.20ab'",
            "AC_REQUIRES_EXACT_AB_WITHOUT_SUCCESSOR_RESIDUE",
        ),
        (
            "MISSING_AB_CAPSULE_ROW",
            "delete from erp.cp6_v2620ab_rollback_capsule where "
            "object_regidentity=(select min(object_regidentity) "
            "from erp.cp6_v2620ab_rollback_capsule)",
            "AC_REQUIRES_EXACT_AB_WITHOUT_SUCCESSOR_RESIDUE",
        ),
        (
            "AB_PLATFORM_BYTES",
            "update supabase_migrations.schema_migrations "
            "set statements=array['AC corrupt AB control'] "
            "where name='erp_v2_6_20ab_cp6_operational_business_clock'",
            "AC_REQUIRES_EXACT_AB_WITHOUT_SUCCESSOR_RESIDUE",
        ),
        (
            "UNEXPECTED_SUCCESSOR",
            "insert into supabase_migrations.schema_migrations(version,name,statements) "
            "values('99999999999999','ac_admission_successor_probe',array['probe'])",
            "AC_REQUIRES_EXACT_AB_WITHOUT_SUCCESSOR_RESIDUE",
        ),
        (
            "EXTRA_TABLE_BOUNDARY",
            "create table erp.ac_admission_boundary_probe(id integer)",
            "AC_FULL_ERP_BOUNDARY_CARDINALITY",
        ),
        ("LAWFUL_EXACT_AB", None, None),
    ]
    result = {
        "format": "CP6_V2620AC_INSTALL_QUALIFICATION_V1",
        "status": "FAIL",
        "head": os.environ.get("GITHUB_SHA"),
        "expected_cases": len(cases),
        "cases": {},
        "production_go": False,
    }
    with psycopg.connect(**dict(params, user="supabase_admin")) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='360s';set local lock_timeout='10s'")
        if runtime.verified_successor(cur) or len(predecessor.verified_successor(cur)) != 5:
            raise AssertionError("AC_INSTALL_EXACT_AB_REQUIRED")
        untouched = boundary(cur)
        for name, mutation, expected_error in cases:
            cur.execute("savepoint ac_admission_case")
            before = boundary(cur)
            evidence = {
                "status": "FAIL",
                "expected_error": expected_error,
                "refusal_expected": expected_error is not None,
            }
            try:
                if mutation:
                    cur.execute(mutation, prepare=False)
                    if mutation.startswith(("delete ", "update ")) and cur.rowcount != 1:
                        raise AssertionError("AC_ADMISSION_MUTATION_NOT_QUALIFIED")
                before_attempt = boundary(cur)
                cur.execute("savepoint ac_admission_attempt")
                error = None
                observations = None
                try:
                    cur.execute(body, prepare=False)
                    if expected_error is None:
                        cur.execute(
                            "insert into supabase_migrations.schema_migrations"
                            "(version,name,statements) values(%s,%s,%s)",
                            (runtime.STAMP, runtime.NAME, [source]),
                        )
                        observations = runtime.verified_successor(cur)
                except psycopg.Error as exc:
                    error = str(exc)
                    evidence["sqlstate"] = exc.sqlstate
                finally:
                    cur.execute("rollback to savepoint ac_admission_attempt")
                    cur.execute("release savepoint ac_admission_attempt")
                correct = (
                    error is None and len(observations or {}) == 272
                    if expected_error is None
                    else error is not None and expected_error in error
                )
                if not correct:
                    raise AssertionError("AC_ADMISSION_WRONG_RESULT:" + str(error))
                if boundary(cur) != before_attempt:
                    raise AssertionError("AC_ADMISSION_ATTEMPT_CHANGED_STATE")
                if (
                    cur.execute(
                        "select to_regclass(%s),to_regclass(%s)",
                        (runtime.MAIN_CAPSULE, runtime.RELATION_CAPSULE),
                    ).fetchone() != (None, None)
                ):
                    raise AssertionError("AC_ADMISSION_CAPSULE_RESIDUE")
                evidence.update(
                    status="CONTROL_PASS",
                    actual_error=error,
                    attempt_boundary_exact=True,
                    installed_observation_count=len(observations or {}),
                    capsule_residue_zero=True,
                )
            except Exception as exc:
                evidence.update(
                    status="FAIL", error=str(exc), traceback=traceback.format_exc()
                )
            finally:
                cur.execute("rollback to savepoint ac_admission_case")
                cur.execute("release savepoint ac_admission_case")
            evidence["full_case_boundary_restored"] = boundary(cur) == before
            result["cases"][name] = evidence
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(result, indent=2, default=str) + "\n")
            print(
                "AC_INSTALL_CASE "
                + json.dumps({"name": name, **evidence}, default=str),
                flush=True,
            )
        result["entire_runtime_restored"] = boundary(cur) == untouched
        conn.rollback()
    if (
        len(result["cases"]) == result["expected_cases"] == 16
        and all(
            item["status"] == "CONTROL_PASS"
            and item["full_case_boundary_restored"]
            for item in result["cases"].values()
        )
        and result["entire_runtime_restored"]
    ):
        result["status"] = "PASS"
    return result


if __name__ == "__main__":
    try:
        outcome = run()
    except Exception as exc:
        outcome = {
            "status": "FAIL", "error": str(exc),
            "traceback": traceback.format_exc(), "production_go": False,
        }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(outcome, indent=2, default=str) + "\n")
    print(json.dumps({key: value for key, value in outcome.items() if key != "cases"}))
    raise SystemExit(0 if outcome.get("status") == "PASS" else 1)
