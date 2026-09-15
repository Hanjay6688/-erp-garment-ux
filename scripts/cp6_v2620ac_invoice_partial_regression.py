#!/usr/bin/env python3
"""Sixteen focused AC late-invoice and partial-allocation regressions."""
from __future__ import annotations

import hashlib
import json
import os
import traceback
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_aa_invoice_partial_audit as audit
import cp6_v2620ac_runtime as runtime


REPORT = Path("cp6-proof/writer-ac/AC_INVOICE_PARTIAL_REGRESSION.json")


def persist(result: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, default=str, sort_keys=True) + "\n")


def run() -> dict:
    params = conninfo_to_dict(os.environ.get("PGURL", ""))
    expected = {
        "user": "postgres", "password": "postgres", "host": "127.0.0.1",
        "port": "54322", "dbname": "postgres",
    }
    if (
        params != expected
        or os.environ.get("CP6_AC_INVOICE_REGRESSION_CONFIRM") != "postgres"
    ):
        raise AssertionError("AC_INVOICE_EXACT_DISPOSABLE_ENDPOINT_REQUIRED")
    head, tree = runtime.verify_audit_source()
    result = {
        "format": "CP6_V2620AC_INVOICE_PARTIAL_REGRESSION_V1",
        "status": "INCOMPLETE", "head": head, "tree": tree,
        "phase": "AC_REGRESSION", "runtime_generation": "AC",
        "business_predecessor_head": runtime.AB_HEAD,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "synthetic_fixture_only": True, "hosted_database_used": False,
        "production_go": False, "independent_acceptance_complete": False,
        "expected_cases": 16, "cases": {},
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    persist(result)
    with psycopg.connect(**dict(params, user="supabase_admin")) as conn, conn.cursor() as cur:
        cur.execute(
            "set local timezone='UTC';set local statement_timeout='180s';"
            "set local lock_timeout='8s'"
        )
        baseline = audit.boundary(cur)
        result["engine"] = audit.one(cur, "select version()")
        if not str(audit.one(cur, "select current_setting('server_version')")).startswith("17.6"):
            raise AssertionError("AC_INVOICE_PINNED_POSTGRES_REQUIRED")
        installed = runtime.verified_successor(cur)
        predecessor_edges = runtime.verify_ab_predecessor_edge(cur, installed)
        if len(predecessor_edges) != 5 or len(installed) != 272:
            raise AssertionError("AC_INVOICE_EXACT_INSTALLED_AC_REQUIRED")
        result["verified_ab_function_edge_count"] = len(predecessor_edges)
        result["verified_ab_functions_transitioned_by_ac"] = sum(
            item["transitioned_by_ac"] for item in predecessor_edges.values()
        )
        result["verified_ac_object_count"] = len(installed)
        usage = audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:
            cur.execute("grant usage on schema erp to authenticated")
        audit.prior.actors.claims(
            cur, {"sub": audit.base.OPERATOR_AUTH, "role": "authenticated"}
        )
        audit.base.load_fixture_foundation(cur)
        today = audit.one(
            cur, "select (clock_timestamp() at time zone 'Asia/Jakarta')::date"
        )
        specs = [
            (partial, caller_zone, final_cost)
            for partial in (False, True)
            for caller_zone in audit.prior.ZONES
            for final_cost in ("20", "20.003")
        ]
        for partial, caller_zone, final_cost in specs:
            name = (
                ("PARTIAL_CHAIN:" if partial else "ESTIMATED_RECEIPT:")
                + caller_zone + ":" + final_cost
            )
            audit.admin(cur)
            cur.execute("savepoint ac_invoice_case")
            before_case = audit.boundary(cur)
            try:
                evidence = audit.invoice_case(
                    cur, caller_zone, today, partial, final_cost
                )
            except Exception as exc:
                evidence = {
                    "status": "INCOMPLETE", "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            finally:
                cur.execute("rollback to savepoint ac_invoice_case")
                audit.admin(cur)
                cur.execute("release savepoint ac_invoice_case")
            evidence["full_boundary_restored"] = audit.boundary(cur) == before_case
            if not evidence["full_boundary_restored"]:
                evidence["status"] = "INCOMPLETE"
            result["cases"][name] = evidence
            persist(result)
            print(json.dumps({"case": name, "status": evidence["status"]}), flush=True)
        conn.rollback()
        result["entire_unseeded_runtime_restored"] = audit.boundary(cur) == baseline
        result["schema_usage_restored"] = (
            audit.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
            == usage
        )
        conn.rollback()
    result["controls"] = sum(
        case["status"] == "CONTROL_PASS" for case in result["cases"].values()
    )
    result["counterexamples"] = sum(
        case["status"] == "COUNTEREXAMPLE" for case in result["cases"].values()
    )
    result["incomplete"] = sum(
        case["status"] == "INCOMPLETE" for case in result["cases"].values()
    )
    restored = (
        result["entire_unseeded_runtime_restored"]
        and result["schema_usage_restored"]
    )
    if restored and len(result["cases"]) == result["expected_cases"]:
        result["status"] = (
            "FAIL_NEW_COUNTEREXAMPLE" if result["counterexamples"]
            else "PASS_BOUNDED_REGRESSION" if result["controls"] == 16
            else "INCOMPLETE"
        )
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
    raise SystemExit(
        0 if outcome.get("status") == "PASS_BOUNDED_REGRESSION"
        else 1 if outcome.get("status") == "FAIL_NEW_COUNTEREXAMPLE"
        else 2
    )
