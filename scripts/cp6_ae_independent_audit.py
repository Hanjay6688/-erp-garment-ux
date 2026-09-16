#!/usr/bin/env python3
"""Independent AE checks on exact original SQL and disposable synthetic data.

Exit 1 means an ordinary authenticated SQL counterexample, 2 means incomplete.
The established fixture grants schema USAGE transactionally when absent. This
is explicitly conditional SQL evidence, never proof of signed HTTP/UI access.
No installed function or posted row is modified by the fixture administrator.
"""
from __future__ import annotations

import hashlib
import json
import os
import traceback
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import psycopg

import cp6_ad_roll_opening_check as rolls
import cp6_aa_invoice_partial_audit as invoices
import cp6_v2620ae_family as ae_cases
import cp6_v2620ae_runtime as runtime
import cp6_v2620e_counterexample_regression as base
import cp6_x_independent_audit as actors
import cp6_z_expanded_integrity_audit as prior
from cp6_v2620n_rollback_guards import function_catalog

HEAD = "ce8e8ea5cdfab4b39ea7095c1b3bd1c8ab1f33d1"
TREE = "738fab9caa9f1d9a66756f169b82f407f929a214"
PGURL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
ROOT = Path("cp6-proof/independent-ae")


def save(name, value):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / (name + ".json")).write_text(json.dumps(value, indent=2, default=str) + "\n")


def attempt(cur, sql, params):
    """Catch database refusals only; assertions cannot masquerade as refusals."""
    actors.owner(cur)
    identity = cur.execute("select current_user,session_user,erp.current_app_role()").fetchone()
    if identity != ("authenticated", "authenticated", "OWNER"):
        raise AssertionError("ORDINARY_OWNER_IDENTITY_REQUIRED")
    cur.execute("savepoint independent_operation")
    error = None
    try:
        cur.execute(sql, params)
        changed = cur.rowcount
    except psycopg.Error as exc:
        if exc.sqlstate not in {"P0001", "42501"}:
            raise
        error = {"sqlstate": exc.sqlstate, "message": str(exc)}
        cur.execute("rollback to savepoint independent_operation")
        changed = 0
    cur.execute("release savepoint independent_operation")
    return {"identity": identity, "refused": error is not None, "error": error, "changed_rows": changed}


def opening_observation(cur, header, item):
    actors.admin(cur)
    return base.one(cur, """select jsonb_build_object(
      'header',to_jsonb(h),'line',(select to_jsonb(i) from erp.opening_balance_items i where id=%s),
      'stock',(select jsonb_agg(to_jsonb(m) order by m.id) from erp.material_stock_movements m
        where m.source_type='OPENING_BALANCE_ITEM' and m.source_id=%s),
      'journal',(select jsonb_agg(to_jsonb(j) order by j.id) from erp.journal_entries j
        where j.source_type='OPENING_BALANCE' and j.source_id=h.id))
      from erp.opening_balance_headers h where h.id=%s""", (item, item, header))


def opening_change(cur, day, action):
    material, location, roll = rolls.create_roll(cur, "ae-independent-" + action)
    origin, items = rolls.create_opening(cur, day, action, material, location, [(roll, Decimal("10"), material)])
    target = uuid.uuid4()
    actors.owner(cur)
    cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status) "
                "values(%s,%s,%s,'DRAFT')", (target, "AE-PEER-" + target.hex, day))
    if action != "DRAFT_MOVE":
        cur.execute("select erp.post_opening_balance(%s)", (origin,))
        ae_cases.assert_ready(cur, day)
    before = opening_observation(cur, origin, items[0])
    if action == "DELETE":
        result = attempt(cur, "delete from erp.opening_balance_items where id=%s", (items[0],))
    elif action == "SAME_PARENT_EDIT":
        result = attempt(cur, "update erp.opening_balance_items set qty=9 where id=%s", (items[0],))
    elif action == "MOVE_AND_EDIT":
        result = attempt(cur, "update erp.opening_balance_items set opening_id=%s,qty=9 where id=%s", (target, items[0]))
    else:
        result = attempt(cur, "update erp.opening_balance_items set opening_id=%s where id=%s", (target, items[0]))
    after = opening_observation(cur, origin, items[0])
    must_refuse = action != "DRAFT_MOVE"
    if result["refused"]:
        status = "CONTROL_PASS" if must_refuse and before == after else "INCOMPLETE"
    else:
        if result["changed_rows"] != 1 or before["line"] == after["line"]:
            raise AssertionError("OPERATION_DID_NOT_CHANGE_ONE_LINE")
        status = "BUG_PROVEN" if must_refuse else "CONTROL_PASS"
    report = ae_cases.report_state(cur, day) if must_refuse else None
    return {**result, "status": status, "action": action, "before": before, "after": after,
            "report": report, "business_requirement": "Posted lines retain their original document and amounts; drafts remain editable",
            "http_ui_reachability_proven": False}


def purchase_move(cur, day):
    fixture = invoices.estimated_receipt(cur, day + timedelta(days=3))
    target = invoices.rpc(cur, "erp.save_material_purchase_draft_v2", {
        "purchase_number": "AE-PEER-PUR-" + uuid.uuid4().hex,
        "supplier_id": prior.BASE_SUPPLIER, "location_id": fixture["location"],
        "physical_at": invoices.at(day, 12), "change_reason": "Independent draft control",
        "lines": [{"material_id": fixture["material"], "qty": 1, "unit_price": 10,
                   "price_state": "ESTIMATED", "price_source": "MANUAL_ESTIMATE",
                   "rolls": [{"roll_number": "AE-PEER-ROLL-" + uuid.uuid4().hex, "qty": 1}]}],
    })
    actors.admin(cur)
    before = base.one(cur, "select to_jsonb(i) from erp.material_purchase_items i where id=%s", (fixture["item"],))
    result = attempt(cur, "update erp.material_purchase_items set purchase_id=%s where id=%s",
                     (target["purchase_id"], fixture["item"]))
    actors.admin(cur)
    after = base.one(cur, "select to_jsonb(i) from erp.material_purchase_items i where id=%s", (fixture["item"],))
    if result["refused"]:
        status = "CONTROL_PASS" if before == after else "INCOMPLETE"
    else:
        if result["changed_rows"] != 1 or before == after:
            raise AssertionError("PURCHASE_LINE_NOT_CHANGED")
        status = "BUG_PROVEN"
    return {**result, "status": status, "before": before, "after": after,
            "http_ui_reachability_proven": False}


def independent_roll_value(cur, day, qty):
    material, location, roll = rolls.create_roll(cur, "ae-peer-value")
    header, items = rolls.create_opening(cur, day, "independent-value", material, location, [(roll, qty, material)])
    actors.owner(cur)
    cur.execute("select erp.post_opening_balance(%s)", (header,))
    state = opening_observation(cur, header, items[0])
    actors.admin(cur)
    balances = cur.execute("""select sum(l.debit),sum(l.credit) from erp.journal_lines l
      join erp.journal_entries j on j.id=l.journal_entry_id
      where j.source_type='OPENING_BALANCE' and j.source_id=%s""", (header,)).fetchone()
    expected = (qty * Decimal("1.25")).quantize(Decimal("0.01"))
    if balances != (expected, expected) or len(state["stock"]) != 1:
        raise AssertionError("INDEPENDENT_ROLL_CENTS_MISMATCH")
    movement = state["stock"][0]
    if Decimal(str(movement["qty_signed"])) != qty:
        raise AssertionError("INDEPENDENT_ROLL_QUANTITY_MISMATCH")
    report = ae_cases.assert_ready(cur, day)
    return {"status": "CONTROL_PASS", "expected_qty": qty, "expected_cents": expected,
            "journal_totals": balances, "observation": state, "report": report}


def run():
    head, tree = runtime.verify_audit_source()
    if (head, tree) != (HEAD, TREE) or os.environ.get("PGURL") != PGURL:
        raise AssertionError("EXACT_AE_AND_DISPOSABLE_TARGET_REQUIRED")
    if os.environ.get("CP6_AE_INDEPENDENT_CONFIRM") != "postgres":
        raise AssertionError("DISPOSABLE_TARGET_CONFIRMATION_REQUIRED")
    result = {"format": "CP6_AE_INDEPENDENT_V1", "status": "INCOMPLETE",
              "candidate_head": head, "candidate_tree": tree,
              "harness_head": os.environ["CP6_AUDIT_HARNESS_HEAD"],
              "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "run_id": os.environ.get("GITHUB_RUN_ID"), "cases": {},
              "synthetic_jwt": True, "http_ui_reachability_proven": False,
              "hosted_database_used": False, "production_go": False}
    save("RESULT", result)
    with psycopg.connect(PGURL.replace("postgres:postgres@", "supabase_admin:postgres@")) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
        if len(runtime.verified_successor(cur)) != 276:
            raise AssertionError("EXACT_AE_RUNTIME_REQUIRED")
        untouched = actors.boundary(cur)
        catalog = function_catalog(cur)
        save("ORIGINAL_FUNCTION_CATALOG", catalog)
        triggers = cur.execute("""select n.nspname,c.relname,t.tgname,pg_get_triggerdef(t.oid)
          from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace
          where not t.tgisinternal and t.tgfoid='erp.guard_child_by_parent_status()'::regprocedure
          order by n.nspname,c.relname,t.tgname""").fetchall()
        save("SHARED_GUARD_CONSUMERS", triggers)
        usage = base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        result["schema_usage_original"] = usage
        result["schema_usage_fixture_grant"] = not usage
        if not usage:
            cur.execute("grant usage on schema erp to authenticated")
        cur.execute("select set_config('request.jwt.claims',%s,true)",
                    (json.dumps({"sub": base.OPERATOR_AUTH, "role": "authenticated"}),))
        base.load_fixture_foundation(cur)
        actors.admin(cur)
        day = base.one(cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date") - timedelta(days=3)
        prior.set_open_period(cur, day - timedelta(days=2))
        cases = [("ROLL_FULL_VALUE", lambda c,d: independent_roll_value(c,d,Decimal("10"))),
                 ("ROLL_PARTIAL_VALUE", lambda c,d: independent_roll_value(c,d,Decimal("6"))),
                 ("PURCHASE_POSTED_LINE_MOVE", purchase_move)]
        cases += [("OPENING_" + name, lambda c,d,a=name: opening_change(c,d,a))
                  for name in ("SAME_PARENT_EDIT", "DELETE", "MOVE", "MOVE_AND_EDIT", "DRAFT_MOVE")]
        cases += [("AE_" + name, fn) for name, fn in ae_cases.phase_cases("successor")
                  if name in {"OVERSIZED", "DUPLICATE_SAME_DOCUMENT", "REUSED_NEXT_DOCUMENT", "VALID_ROLL_IMPORT"}]
        for name, fn in cases:
            actors.admin(cur)
            before = actors.boundary(cur)
            cur.execute("savepoint independent_case")
            try:
                record = fn(cur, day)
                if record["status"] == "PASS":
                    record["status"] = "CONTROL_PASS"
            except Exception as exc:
                record = {"status": "INCOMPLETE", "error": str(exc), "traceback": traceback.format_exc()}
            finally:
                cur.execute("rollback to savepoint independent_case")
                actors.admin(cur)
                cur.execute("release savepoint independent_case")
            record["entire_data_boundary_restored"] = actors.boundary(cur) == before
            if not record["entire_data_boundary_restored"]:
                record["status"] = "INCOMPLETE"
            result["cases"][name] = record
            save("RESULT", result)
            print(json.dumps({"case": name, "status": record["status"], "error": record.get("error")}), flush=True)
        actors.admin(cur)
        result["installed_functions_unchanged"] = function_catalog(cur) == catalog
        conn.rollback()
        cur.execute("set local timezone='Asia/Jakarta'")
        result["entire_unseeded_boundary_restored"] = actors.boundary(cur) == untouched
        result["schema_usage_restored"] = base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')") == usage
        conn.rollback()
    result["bugs_proven"] = sum(r["status"] == "BUG_PROVEN" for r in result["cases"].values())
    result["controls_passed"] = sum(r["status"] == "CONTROL_PASS" for r in result["cases"].values())
    result["incomplete"] = sum(r["status"] == "INCOMPLETE" for r in result["cases"].values())
    if all(result[k] for k in ("installed_functions_unchanged", "entire_unseeded_boundary_restored", "schema_usage_restored")) and result["incomplete"] == 0:
        result["status"] = "BUG_PROVEN" if result["bugs_proven"] else "PASS_WITHIN_SCOPE"
    save("RESULT", result)
    return result


if __name__ == "__main__":
    try:
        outcome = run()
    except Exception as exc:
        outcome = {"status": "INCOMPLETE", "error": str(exc), "traceback": traceback.format_exc(), "production_go": False}
        save("RUNNER_FAILURE", outcome)
    print(json.dumps({k: v for k, v in outcome.items() if k != "cases"}, default=str), flush=True)
    raise SystemExit(0 if outcome["status"] == "PASS_WITHIN_SCOPE" else 1 if outcome["status"] == "BUG_PROVEN" else 2)
