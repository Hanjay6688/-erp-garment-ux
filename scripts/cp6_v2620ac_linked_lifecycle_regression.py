#!/usr/bin/env python3
"""Focused AC linked-payment, opening, return, and report-state regression."""
from __future__ import annotations

import hashlib
import json
import os
import traceback
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620m_subledger_regression as m_oracle
import cp6_v2620n_supplier_cent_regression as n_oracle
import cp6_v2620o_supplier_return_regression as o_oracle
import cp6_v2620y_cash_business_date_regression as y_oracle
import cp6_x_independent_audit as cash_audit
import cp6_v2620ab_runtime as predecessor
import cp6_v2620ac_runtime as runtime


REPORT = Path("cp6-proof/writer-ac/AC_LINKED_LIFECYCLE_REGRESSION.json")
SQL_SOURCES = (
    Path("supabase/tests/cp6_subledger_exact_cent.sql"),
    Path("supabase/tests/cp6_supplier_cent_lifecycle.sql"),
    Path("supabase/tests/cp6_supplier_return_document_allocation.sql"),
)


def persist(result: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, default=str) + "\n")


def run() -> dict:
    params = conninfo_to_dict(os.environ.get("PGURL", ""))
    expected = {
        "user": "postgres", "password": "postgres", "host": "127.0.0.1",
        "port": "54322", "dbname": "postgres",
    }
    if (
        params != expected
        or os.environ.get("CP6_AC_LINKED_REGRESSION_CONFIRM") != "postgres"
    ):
        raise AssertionError("AC_LINKED_EXACT_DISPOSABLE_ENDPOINT_REQUIRED")
    head, tree = runtime.verify_audit_source()
    expected_cases = (
        len(m_oracle.CASES) + len(n_oracle.CASES) + len(o_oracle.CASES) + 10
    )
    result = {
        "format": "CP6_V2620AC_LINKED_LIFECYCLE_REGRESSION_V1",
        "status": "INCOMPLETE", "head": head, "tree": tree,
        "phase": "AC_REGRESSION", "runtime_generation": "AC",
        "business_predecessor_head": runtime.AB_HEAD,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "expected_cases": expected_cases, "cases": {},
        "oracle_sources": {
            str(path): {
                "bytes": len(path.read_bytes()),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in SQL_SOURCES
        },
        "synthetic_fixture_only": True, "hosted_database_used": False,
        "independent_acceptance_complete": False, "production_go": False,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    persist(result)
    with psycopg.connect(**dict(params, user="supabase_admin")) as conn, conn.cursor() as cur:
        cur.execute(
            "set local timezone='UTC';set local statement_timeout='180s';"
            "set local lock_timeout='8s'"
        )
        untouched = cash_audit.boundary(cur)
        inherited = predecessor.verified_successor(cur)
        installed = runtime.verified_successor(cur)
        if len(inherited) != 5 or len(installed) != 272:
            raise AssertionError("AC_LINKED_EXACT_INSTALLED_AC_REQUIRED")
        result["verified_ab_function_count"] = len(inherited)
        result["verified_ac_object_count"] = len(installed)
        usage = base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:
            cur.execute("grant usage on schema erp to authenticated")
        cur.execute(
            "select set_config('request.jwt.claims',%s,true)",
            (json.dumps({"sub": base.OPERATOR_AUTH, "role": "authenticated"}),),
        )
        cur.execute(
            "select set_config('app.change_reason',%s,true)",
            ("CP6 AC focused linked lifecycle regression",),
        )
        base.load_fixture_foundation(cur)
        for source in SQL_SOURCES:
            cur.execute(source.read_text(), prepare=False)

        groups = (
            ("OPENING_SUBLEDGER", "m_case", m_oracle.CASES),
            ("SUPPLIER_CENT", "n_case", n_oracle.CASES),
            ("SUPPLIER_RETURN", "o_case", o_oracle.CASES),
        )
        for group, function, cases in groups:
            for case_name in cases:
                name = f"{group}:{case_name}"
                cur.execute("savepoint ac_linked_case")
                before = cash_audit.boundary(cur)
                try:
                    evidence = base.one(
                        cur, f"select pg_temp.{function}(%s,true)", (case_name,)
                    )
                    if evidence.get("status") != "PASS":
                        raise AssertionError(
                            f"AC_LINKED_ORACLE_STATUS_MISMATCH:{name}:{evidence}"
                        )
                    evidence["status"] = "CONTROL_PASS"
                except Exception as exc:
                    evidence = {
                        "status": "INCOMPLETE", "error": str(exc),
                        "sqlstate": getattr(exc, "sqlstate", None),
                        "traceback": traceback.format_exc(),
                    }
                finally:
                    cur.execute("rollback to savepoint ac_linked_case")
                    cash_audit.admin(cur)
                    cur.execute("release savepoint ac_linked_case")
                evidence["full_boundary_restored"] = cash_audit.boundary(cur) == before
                evidence["report_ready_after_restore"] = (
                    base.one(cur, "select pg_temp.m_report()") == "READY"
                )
                if (
                    not evidence["full_boundary_restored"]
                    or not evidence["report_ready_after_restore"]
                ):
                    evidence["status"] = "INCOMPLETE"
                result["cases"][name] = evidence
                persist(result)

        cash = base.one(
            cur, "select id from erp.cash_accounts where is_active order by id limit 1"
        )
        for case_name, operation in y_oracle.extensions(cur, cash):
            name = "CASH_LINKED:" + case_name
            cur.execute("savepoint ac_cash_case")
            before = cash_audit.boundary(cur)
            try:
                evidence = operation()
                if evidence.get("status") != "CONTROL_PASS":
                    raise AssertionError(
                        f"AC_CASH_ORACLE_STATUS_MISMATCH:{name}:{evidence}"
                    )
            except Exception as exc:
                evidence = {
                    "status": "INCOMPLETE", "error": str(exc),
                    "sqlstate": getattr(exc, "sqlstate", None),
                    "traceback": traceback.format_exc(),
                }
            finally:
                cur.execute("rollback to savepoint ac_cash_case")
                cash_audit.admin(cur)
                cur.execute("release savepoint ac_cash_case")
            evidence["full_boundary_restored"] = cash_audit.boundary(cur) == before
            evidence["report_ready_after_restore"] = (
                base.one(cur, "select pg_temp.m_report()") == "READY"
            )
            if (
                not evidence["full_boundary_restored"]
                or not evidence["report_ready_after_restore"]
            ):
                evidence["status"] = "INCOMPLETE"
            result["cases"][name] = evidence
            persist(result)

        conn.rollback()
        result["entire_unseeded_runtime_restored"] = (
            cash_audit.boundary(cur) == untouched
        )
        result["schema_usage_restored"] = (
            base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
            == usage
        )
        conn.rollback()
    result["controls"] = sum(
        item["status"] == "CONTROL_PASS" for item in result["cases"].values()
    )
    result["counterexamples"] = sum(
        item["status"] == "COUNTEREXAMPLE" for item in result["cases"].values()
    )
    result["incomplete"] = sum(
        item["status"] == "INCOMPLETE" for item in result["cases"].values()
    )
    if (
        len(result["cases"]) == result["expected_cases"]
        and result["controls"] == result["expected_cases"]
        and result["counterexamples"] == result["incomplete"] == 0
        and result["entire_unseeded_runtime_restored"]
        and result["schema_usage_restored"]
    ):
        result["status"] = "PASS_BOUNDED_REGRESSION"
    persist(result)
    return result


if __name__ == "__main__":
    try:
        outcome = run()
    except Exception as exc:
        outcome = {
            "status": "INCOMPLETE", "error": str(exc),
            "traceback": traceback.format_exc(), "production_go": False,
        }
        persist(outcome)
    print(json.dumps({k: v for k, v in outcome.items() if k != "cases"}, default=str))
    raise SystemExit(0 if outcome.get("status") == "PASS_BOUNDED_REGRESSION" else 2)
