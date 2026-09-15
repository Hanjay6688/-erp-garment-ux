#!/usr/bin/env python3
"""Focused whole-family qualification for the AE roll-opening repair."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import traceback
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

import psycopg

import cp6_aa_invoice_partial_audit as purchase_fixture
import cp6_ac_independent_audit as import_fixture
import cp6_ad_roll_opening_check as roll_fixture
import cp6_v2620ad_runtime as ad_runtime
import cp6_v2620ae_runtime as runtime
import cp6_v2620e_counterexample_regression as base
import cp6_x_independent_audit as actors
import cp6_z_expanded_integrity_audit as prior
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot


ROOT = Path("cp6-proof/writer-ae")
CHECK = "V2620AE_OPENING_MATERIAL_ROLL_INTEGRITY"
EXPECTED_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
Case = Callable[[psycopg.Cursor, object], dict]


def persist(name: str, result: dict) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / (name + ".json")).write_text(
        json.dumps(result, indent=2, default=str, sort_keys=True) + "\n"
    )


def sql_body(path: Path) -> str:
    source = path.read_text()
    if source.count("\nbegin;\n") != 1 or not source.endswith("commit;\n"):
        raise AssertionError("AE_REVIEWED_SQL_TRANSACTION_SHAPE")
    return source.replace("\nbegin;\n", "\n", 1).removesuffix("commit;\n")


def expected_refusal(cur, operation: Callable[[], None], message: str) -> dict:
    actors.admin(cur)
    cur.execute("savepoint ae_expected_refusal")
    observed = None
    try:
        operation()
    except psycopg.Error as exc:
        observed = {"sqlstate": exc.sqlstate, "message": str(exc)}
    finally:
        cur.execute("rollback to savepoint ae_expected_refusal")
        actors.admin(cur)
        cur.execute("release savepoint ae_expected_refusal")
    if observed is None or message not in observed["message"]:
        raise AssertionError(f"AE_EXPECTED_REFUSAL_MISMATCH:{message}:{observed}")
    return observed


def owner_post(cur, opening_id) -> tuple[str, str, str]:
    actors.owner(cur)
    actors.zone(cur, "Asia/Jakarta")
    cur.execute("select erp.post_opening_balance(%s)", (opening_id,))
    identity = cur.execute(
        "select current_user,session_user,erp.current_app_role()"
    ).fetchone()
    if identity != ("authenticated", "authenticated", "OWNER"):
        raise AssertionError("AE_ORDINARY_OWNER_SESSION_REQUIRED")
    return identity


def report_state(cur, day) -> dict:
    actors.owner(cur)
    actors.zone(cur, "Asia/Jakarta")
    identity = cur.execute(
        "select current_user,session_user,erp.current_app_role()"
    ).fetchone()
    owner_snapshot = base.one(
        cur, "select erp.get_owner_financial_snapshot_v2(%s,%s,%s)",
        (day, day, day),
    )
    check = cur.execute(
        "select severity,issue_count,details "
        "from erp.run_v268_financial_report_checks() where check_name=%s",
        (CHECK,),
    ).fetchone()
    actors.admin(cur)
    return {"identity": identity, "owner_snapshot": owner_snapshot, "check": check}


def assert_ready(cur, day) -> dict:
    state = report_state(cur, day)
    if (
        state["identity"] != ("authenticated", "authenticated", "OWNER")
        or state["owner_snapshot"]["data_confidence"]["status"] != "READY"
        or state["check"] is None
        or state["check"][0] != "CRITICAL"
        or state["check"][1] != 0
    ):
        raise AssertionError("AE_NORMAL_STATE_NOT_READY:" + json.dumps(state, default=str))
    return state


def observe_roll(cur, roll, expected_qty: Decimal) -> dict:
    actors.admin(cur)
    row = cur.execute(
        "select original_qty,cached_qty,status,purchase_item_id "
        "from erp.material_rolls where id=%s", (roll,),
    ).fetchone()
    movements = cur.execute(
        "select count(*),coalesce(sum(qty_signed),0) "
        "from erp.material_stock_movements where roll_id=%s "
        "and movement_type='OPENING' and reversal_of_id is null", (roll,),
    ).fetchone()
    items = base.one(
        cur,
        "select count(*) from erp.opening_balance_items i "
        "join erp.opening_balance_headers h on h.id=i.opening_id "
        "where h.status='POSTED' and i.roll_id=%s", (roll,),
    )
    if row is None or row[1] != expected_qty or movements != (1, expected_qty) or items != 1:
        raise AssertionError(f"AE_VALID_ROLL_OBSERVATION_MISMATCH:{row}:{movements}:{items}")
    return {
        "original_qty": row[0], "cached_qty": row[1], "roll_status": row[2],
        "purchase_item_id": row[3], "opening_movements": movements[0],
        "opening_qty": movements[1], "posted_items": items,
    }


def set_accessory(cur, material) -> None:
    actors.admin(cur)
    category = base.one(cur, "select id from erp.accessory_categories order by id limit 1")
    if category is None:
        category = uuid.uuid4()
        cur.execute(
            "insert into erp.accessory_categories"
            "(id,category_code,category_name,base_uom_code) values(%s,%s,%s,'PCS')",
            (category, "AE-CAT-" + category.hex[:16], "AE accessory category"),
        )
    cur.execute(
        "update erp.materials set material_type='ACCESSORY',unit_code='PCS',"
        "accessory_category_id=%s where id=%s", (category, material),
    )


def make_accessory(cur, label: str):
    actors.admin(cur)
    material = prior.clone_material(cur, label)
    set_accessory(cur, material)
    return material


def make_location(cur, kind: str = "RAW_MATERIAL_WAREHOUSE"):
    actors.admin(cur)
    location = uuid.uuid4()
    cur.execute(
        "insert into erp.locations(id,location_code,location_name,location_type,is_active) "
        "values(%s,%s,%s,%s,true)",
        (location, "AE-LOC-" + location.hex[:16], "AE focused location", kind),
    )
    return location


def direct_opening(cur, day, material, location, roll, qty=Decimal("1"), balance_type="MATERIAL", product=None):
    actors.owner(cur)
    actors.zone(cur, "Asia/Jakarta")
    opening_id = uuid.uuid4()
    item_id = uuid.uuid4()
    cur.execute(
        "insert into erp.opening_balance_headers"
        "(id,opening_number,opening_date,status) values(%s,%s,%s,'DRAFT')",
        (opening_id, "AE-OPEN-" + opening_id.hex[:20], day),
    )
    cur.execute(
        "insert into erp.opening_balance_items"
        "(id,opening_id,balance_type,material_id,roll_id,product_id,location_id,qty,"
        "unit_cost_snapshot,hpp_input_method) "
        "values(%s,%s,%s,%s,%s,%s,%s,%s,1.25,'MANUAL')",
        (item_id, opening_id, balance_type, material, roll, product, location, qty),
    )
    return opening_id, item_id


def valid_roll(cur, day, qty: Decimal, label: str) -> dict:
    material, location, roll = roll_fixture.create_roll(cur, label)
    opening, _ = roll_fixture.create_opening(
        cur, day, label, material, location, [(roll, qty, material)]
    )
    identity = owner_post(cur, opening)
    observation = observe_roll(cur, roll, qty)
    ready = assert_ready(cur, day)
    return {"status": "PASS", "identity": identity, "roll": observation, "report": ready}


def valid_full(cur, day) -> dict:
    return valid_roll(cur, day, Decimal("10"), "ae-valid-full")


def valid_partial(cur, day) -> dict:
    result = valid_roll(cur, day, Decimal("6"), "ae-valid-partial")
    if result["roll"]["roll_status"] != "HALF_USED":
        raise AssertionError("AE_VALID_PARTIAL_STATUS_MISMATCH")
    return result


def valid_accessory_without_roll(cur, day) -> dict:
    material = make_accessory(cur, "ae-accessory")
    location = make_location(cur)
    opening, item = direct_opening(cur, day, material, location, None, Decimal("3"))
    identity = owner_post(cur, opening)
    actors.admin(cur)
    movement = cur.execute(
        "select qty_signed,roll_id from erp.material_stock_movements "
        "where source_type='OPENING_BALANCE_ITEM' and source_id=%s", (item,),
    ).fetchone()
    if movement != (Decimal("3"), None):
        raise AssertionError("AE_ACCESSORY_OPENING_CHANGED")
    return {"status": "PASS", "identity": identity, "movement": movement, "report": assert_ready(cur, day)}


def valid_roll_import(cur, day) -> dict:
    result = import_fixture.opening_case(cur, "FABRIC_ROLL", "Asia/Jakarta", day, "IMPORT")
    if result["status"] != "CONTROL_PASS" or result["route"] != "IMPORT":
        raise AssertionError("AE_VALID_ROLL_IMPORT_CHANGED:" + json.dumps(result, default=str))
    return {"status": "PASS", "import": result, "report": assert_ready(cur, day)}


def oversized(cur, day) -> dict:
    material, location, roll = roll_fixture.create_roll(cur, "ae-oversized")
    opening, _ = roll_fixture.create_opening(
        cur, day, "ae-oversized", material, location,
        [(roll, Decimal("11"), material)],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_OPENING_QTY_EXCEEDS_ROLL_ORIGINAL"
    )
    return {"status": "PASS", "error": error}


def duplicate_same_document(cur, day) -> dict:
    material, location, roll = roll_fixture.create_roll(cur, "ae-duplicate")
    opening, _ = roll_fixture.create_opening(
        cur, day, "ae-duplicate", material, location,
        [(roll, Decimal("5"), material), (roll, Decimal("5"), material)],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_OPENING_ROLL_DUPLICATE_IN_DOCUMENT"
    )
    return {"status": "PASS", "error": error}


def reused_next_document(cur, day) -> dict:
    material, location, roll = roll_fixture.create_roll(cur, "ae-reuse")
    first, _ = roll_fixture.create_opening(
        cur, day, "ae-reuse-first", material, location,
        [(roll, Decimal("10"), material)],
    )
    owner_post(cur, first)
    second, _ = roll_fixture.create_opening(
        cur, day, "ae-reuse-second", material, location,
        [(roll, Decimal("1"), material)],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, second), "AE_OPENING_ROLL_ALREADY_POSTED"
    )
    observation = observe_roll(cur, roll, Decimal("10"))
    return {"status": "PASS", "error": error, "first_document": observation, "report": assert_ready(cur, day)}


def mismatched_material(cur, day) -> dict:
    material, location, roll = roll_fixture.create_roll(cur, "ae-mismatch")
    other = prior.clone_material(cur, "ae-other")
    opening, _ = roll_fixture.create_opening(
        cur, day, "ae-mismatch", other, location,
        [(roll, Decimal("1"), other)],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_OPENING_ROLL_MATERIAL_MISMATCH"
    )
    return {"status": "PASS", "error": error, "roll_material": material, "line_material": other}


def fabric_without_roll(cur, day) -> dict:
    material, location, _ = roll_fixture.create_roll(cur, "ae-no-roll")
    opening, _ = roll_fixture.create_opening(
        cur, day, "ae-no-roll", material, location,
        [(None, Decimal("1"), material)],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_FABRIC_OPENING_REQUIRES_ROLL"
    )
    return {"status": "PASS", "error": error}


def accessory_with_roll(cur, day) -> dict:
    material, location, roll = roll_fixture.create_roll(cur, "ae-accessory-roll")
    set_accessory(cur, material)
    opening, _ = roll_fixture.create_opening(
        cur, day, "ae-accessory-roll", material, location,
        [(roll, Decimal("1"), material)],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_OPENING_ROLL_REQUIRES_FABRIC"
    )
    return {"status": "PASS", "error": error}


def nonmaterial_with_roll(cur, day) -> dict:
    _, _, roll = roll_fixture.create_roll(cur, "ae-fg-roll")
    product = base.create_product(cur, uuid.uuid4().hex[:16])
    location = make_location(cur, "FG_WAREHOUSE")
    opening, _ = direct_opening(
        cur, day, None, location, roll, Decimal("1"), "FINISHED_GOODS", product
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_OPENING_ROLL_ONLY_ALLOWED_FOR_MATERIAL"
    )
    return {"status": "PASS", "error": error}


def unavailable_roll(cur, day) -> dict:
    material, location, roll = roll_fixture.create_roll(cur, "ae-unavailable")
    actors.admin(cur)
    cur.execute("update erp.material_rolls set status='EXHAUSTED' where id=%s", (roll,))
    opening, _ = roll_fixture.create_opening(
        cur, day, "ae-unavailable", material, location,
        [(roll, Decimal("1"), material)],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_OPENING_ROLL_NOT_AVAILABLE"
    )
    return {"status": "PASS", "error": error}


def cached_history_roll(cur, day) -> dict:
    material, location, roll = roll_fixture.create_roll(cur, "ae-cached")
    actors.admin(cur)
    cur.execute("update erp.material_rolls set cached_qty=1 where id=%s", (roll,))
    opening, _ = roll_fixture.create_opening(
        cur, day, "ae-cached", material, location,
        [(roll, Decimal("1"), material)],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_OPENING_ROLL_HAS_EXISTING_STOCK_HISTORY"
    )
    return {"status": "PASS", "error": error}


def purchased_roll(cur, day) -> dict:
    fixture = purchase_fixture.estimated_receipt(cur, day + timedelta(days=3))
    opening, _ = roll_fixture.create_opening(
        cur, day, "ae-purchased", fixture["material"], fixture["location"],
        [(fixture["roll"], Decimal("1"), fixture["material"])],
    )
    error = expected_refusal(
        cur, lambda: owner_post(cur, opening), "AE_PURCHASE_ROLL_CANNOT_BE_OPENING_BALANCE"
    )
    return {"status": "PASS", "error": error, "ordinary_purchase": True}


def ad_post_dirty(cur, day, kind: str) -> dict:
    """Create one state accepted by AD so AE admission must stop for review."""
    if kind == "OVERSIZED":
        material, location, roll = roll_fixture.create_roll(cur, "ad-dirty-large")
        opening, _ = roll_fixture.create_opening(
            cur, day, kind, material, location, [(roll, Decimal("11"), material)]
        )
        owner_post(cur, opening)
    elif kind == "DUPLICATE":
        material, location, roll = roll_fixture.create_roll(cur, "ad-dirty-dup")
        opening, _ = roll_fixture.create_opening(
            cur, day, kind, material, location,
            [(roll, Decimal("5"), material), (roll, Decimal("5"), material)],
        )
        owner_post(cur, opening)
    elif kind == "REUSED":
        material, location, roll = roll_fixture.create_roll(cur, "ad-dirty-reuse")
        first, _ = roll_fixture.create_opening(
            cur, day, kind + "-1", material, location, [(roll, Decimal("6"), material)]
        )
        owner_post(cur, first)
        second, _ = roll_fixture.create_opening(
            cur, day, kind + "-2", material, location, [(roll, Decimal("4"), material)]
        )
        owner_post(cur, second)
    elif kind == "FABRIC_WITHOUT_ROLL":
        material, location, _ = roll_fixture.create_roll(cur, "ad-dirty-none")
        opening, _ = roll_fixture.create_opening(
            cur, day, kind, material, location, [(None, Decimal("1"), material)]
        )
        owner_post(cur, opening)
    elif kind == "ACCESSORY_WITH_ROLL":
        material, location, roll = roll_fixture.create_roll(cur, "ad-dirty-acc")
        set_accessory(cur, material)
        opening, _ = roll_fixture.create_opening(
            cur, day, kind, material, location, [(roll, Decimal("1"), material)]
        )
        owner_post(cur, opening)
    elif kind == "NONMATERIAL_WITH_ROLL":
        _, _, roll = roll_fixture.create_roll(cur, "ad-dirty-fg")
        product = base.create_product(cur, uuid.uuid4().hex[:16])
        location = make_location(cur, "FG_WAREHOUSE")
        opening, _ = direct_opening(
            cur, day, None, location, roll, Decimal("1"), "FINISHED_GOODS", product
        )
        owner_post(cur, opening)
    elif kind == "PURCHASED_ROLL":
        fixture = purchase_fixture.estimated_receipt(cur, day + timedelta(days=3))
        opening, _ = roll_fixture.create_opening(
            cur, day, kind, fixture["material"], fixture["location"],
            [(fixture["roll"], Decimal("1"), fixture["material"])],
        )
        owner_post(cur, opening)
    else:
        raise AssertionError("AE_UNKNOWN_DIRTY_CASE:" + kind)
    return {"kind": kind, "ordinary_ad_posting": True}


def admission_case(kind: str) -> Case:
    def run(cur, day) -> dict:
        dirty = ad_post_dirty(cur, day, kind)
        error = expected_refusal(
            cur,
            lambda: cur.execute(sql_body(runtime.MIGRATION), prepare=False),
            "AE_PREEXISTING_OPENING_ROLL_REVIEW_REQUIRED",
        )
        return {"status": "PASS", "dirty": dirty, "error": error}
    return run


def detector_case(kind: str) -> Case:
    def run(cur, day) -> dict:
        actors.admin(cur)
        live_definition = base.one(
            cur, "select pg_get_functiondef('erp.post_opening_balance(uuid)'::regprocedure)"
        )
        predecessor_definition = base.one(
            cur, f"select object_definition from {runtime.CAPSULE} "
            "where object_regidentity='erp.post_opening_balance(uuid)'"
        )
        cur.execute(predecessor_definition, prepare=False)
        dirty = ad_post_dirty(cur, day, kind)
        actors.admin(cur)
        cur.execute(live_definition, prepare=False)
        state = report_state(cur, day)
        if (
            state["owner_snapshot"]["data_confidence"]["status"] != "BLOCKED"
            or state["check"] is None
            or state["check"][0] != "CRITICAL"
            or state["check"][1] <= 0
        ):
            raise AssertionError("AE_DETECTOR_DID_NOT_BLOCK:" + json.dumps(state, default=str))
        return {
            "status": "PASS", "detector_control_only": True,
            "ordinary_ad_posting_reintroduced_transactionally": True,
            "dirty": dirty, "report": state,
        }
    return run


def phase_cases(phase: str) -> tuple[tuple[str, Case], ...]:
    if phase == "admission":
        names = (
            "OVERSIZED", "DUPLICATE", "REUSED", "FABRIC_WITHOUT_ROLL",
            "ACCESSORY_WITH_ROLL", "NONMATERIAL_WITH_ROLL", "PURCHASED_ROLL",
        )
        return tuple((name, admission_case(name)) for name in names)
    if phase == "successor":
        return (
            ("VALID_FULL", valid_full),
            ("VALID_PARTIAL", valid_partial),
            ("VALID_ACCESSORY_WITHOUT_ROLL", valid_accessory_without_roll),
            ("VALID_ROLL_IMPORT", valid_roll_import),
            ("OVERSIZED", oversized),
            ("DUPLICATE_SAME_DOCUMENT", duplicate_same_document),
            ("REUSED_NEXT_DOCUMENT", reused_next_document),
            ("MISMATCHED_MATERIAL", mismatched_material),
            ("FABRIC_WITHOUT_ROLL", fabric_without_roll),
            ("ACCESSORY_WITH_ROLL", accessory_with_roll),
            ("NONMATERIAL_WITH_ROLL", nonmaterial_with_roll),
            ("UNAVAILABLE_ROLL", unavailable_roll),
            ("CACHED_HISTORY_ROLL", cached_history_roll),
            ("PURCHASED_ROLL", purchased_roll),
        )
    if phase == "detector":
        names = (
            "OVERSIZED", "DUPLICATE", "FABRIC_WITHOUT_ROLL",
            "ACCESSORY_WITH_ROLL", "NONMATERIAL_WITH_ROLL", "PURCHASED_ROLL",
        )
        return tuple((name, detector_case(name)) for name in names)
    raise AssertionError("AE_UNKNOWN_PHASE:" + phase)


def run_phase(phase: str) -> dict:
    head, tree = runtime.verify_audit_source()
    if os.environ.get("PGURL") != EXPECTED_URL:
        raise AssertionError("AE_EXACT_DISPOSABLE_TARGET_REQUIRED")
    if os.environ.get("CP6_AE_FAMILY_CONFIRM") != "postgres":
        raise AssertionError("AE_DISPOSABLE_TARGET_CONFIRMATION_REQUIRED")
    result = {
        "format": "CP6_AE_ROLL_OPENING_FAMILY_V1", "phase": phase,
        "status": "INCOMPLETE", "head": head, "tree": tree,
        "predecessor_head": runtime.PREDECESSOR_HEAD,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "hosted_database_used": False, "production_go": False, "cases": {},
    }
    persist(phase, result)
    admin_url = EXPECTED_URL.replace("postgres:postgres@", "supabase_admin:postgres@")
    with psycopg.connect(admin_url) as connection, connection.cursor() as cur:
        cur.execute(
            "set local statement_timeout='240s';set local lock_timeout='8s';"
            "set local timezone='Asia/Jakarta'"
        )
        untouched = actors.boundary(cur)
        if phase == "admission":
            if len(ad_runtime.verified_successor(cur)) != 274:
                raise AssertionError("AE_ADMISSION_REQUIRES_AD_274")
            catalog = function_catalog(cur)
            boundary = snapshot(cur)
            if len(catalog) != 533 or len(boundary["tables"]) != 219:
                raise AssertionError("AE_AD_BASELINE_CARDINALITY_MISMATCH")
            persist("AD_COMPLETE_CATALOG", catalog)
            persist("AD_COMPLETE_BOUNDARY", boundary)
        elif len(runtime.verified_successor(cur)) != 276:
            raise AssertionError("AE_SUCCESSOR_RUNTIME_NOT_276")
        usage_before = base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage_before:
            cur.execute("grant usage on schema erp to authenticated")
        cur.execute(
            "select set_config('request.jwt.claims',%s,true)",
            (json.dumps({"sub": base.OPERATOR_AUTH, "role": "authenticated"}),),
        )
        base.load_fixture_foundation(cur)
        actors.admin(cur)
        day = base.one(
            cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date"
        ) - timedelta(days=3)
        prior.set_open_period(cur, day - timedelta(days=2))

        for name, function in phase_cases(phase):
            actors.admin(cur)
            before = actors.boundary(cur)
            cur.execute("savepoint ae_family_case")
            try:
                record = function(cur, day)
            except Exception as exc:
                record = {
                    "status": "FAIL", "error": str(exc),
                    "sqlstate": getattr(exc, "sqlstate", None),
                    "traceback": traceback.format_exc(),
                }
            finally:
                cur.execute("rollback to savepoint ae_family_case")
                actors.admin(cur)
                cur.execute("release savepoint ae_family_case")
            record["full_boundary_restored"] = actors.boundary(cur) == before
            if not record["full_boundary_restored"]:
                record["status"] = "FAIL"
            result["cases"][name] = record
            persist(phase, result)
            print(json.dumps({"phase": phase, "case": name, "status": record["status"]}), flush=True)

        connection.rollback()
        result["entire_unseeded_boundary_restored"] = actors.boundary(cur) == untouched
        result["schema_usage_restored"] = (
            base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
            == usage_before
        )
        connection.rollback()

    result["passed"] = sum(item["status"] == "PASS" for item in result["cases"].values())
    result["failed"] = sum(item["status"] != "PASS" for item in result["cases"].values())
    if (
        result["failed"] == 0
        and result["passed"] == len(phase_cases(phase))
        and result["entire_unseeded_boundary_restored"]
        and result["schema_usage_restored"]
    ):
        result["status"] = "PASS"
    persist(phase, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("admission", "successor", "detector"), required=True)
    args = parser.parse_args()
    try:
        final = run_phase(args.phase)
    except Exception as exc:
        final = {
            "status": "INCOMPLETE", "phase": args.phase, "error": str(exc),
            "traceback": traceback.format_exc(), "production_go": False,
        }
        persist(args.phase, final)
    print(json.dumps({key: value for key, value in final.items() if key != "cases"}, default=str))
    raise SystemExit(0 if final["status"] == "PASS" else 1)
