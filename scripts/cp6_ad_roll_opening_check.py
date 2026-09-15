#!/usr/bin/env python3
"""Small CP6 AD roll-opening check on a disposable database."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import os
import subprocess
import traceback
import uuid

import psycopg

import cp6_v2620ad_runtime as runtime
import cp6_v2620e_counterexample_regression as base
import cp6_x_independent_audit as actors
import cp6_z_expanded_integrity_audit as prior


AD_HEAD = "8a23373e8ac6ebf2a1880949f46e0f9e00b15f8a"
AD_TREE = "e9535daf943959f29fd668f362ff48312f815036"
CHECK_NAME = "V2620AD_OPENING_MATERIAL_TIMELINE_MISMATCH"
OUTPUT = Path("cp6-proof/ad-roll-opening/RESULT.json")
ALLOWED_ROUND_FILES = {
    ".github/workflows/cp6-ad-roll-opening-check.yml",
    ".github/workflows/cp6-full-schema-validation.yml",
    "scripts/cp6_ad_roll_opening_check.py",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def save(result: dict) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, default=str) + "\n")


def verify_round_source() -> tuple[str, str]:
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    if os.environ.get("GITHUB_SHA") != head:
        raise AssertionError("ROUND_HEAD_MISMATCH")
    if git("rev-parse", AD_HEAD + "^{tree}") != AD_TREE:
        raise AssertionError("AD_TREE_MISMATCH")
    if git("merge-base", AD_HEAD, head) != AD_HEAD:
        raise AssertionError("ROUND_MUST_DESCEND_FROM_AD")
    if git("rev-list", "--merges", AD_HEAD + ".." + head):
        raise AssertionError("ROUND_MUST_STAY_LINEAR")
    changed = set(git("diff", "--name-only", AD_HEAD, head).splitlines())
    if changed != ALLOWED_ROUND_FILES:
        raise AssertionError("ROUND_FILE_BOUNDARY_MISMATCH:" + repr(sorted(changed)))
    runtime.verify_source_files()
    return head, tree


def create_roll(cur, label: str, original_qty: Decimal = Decimal("10"), material=None):
    actors.admin(cur)
    material = material or prior.clone_material(cur, "roll-opening-" + label)
    location = uuid.uuid4()
    roll = uuid.uuid4()
    cur.execute(
        "insert into erp.locations(id,location_code,location_name,location_type,is_active) "
        "values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",
        (location, "ROLL-CHK-" + location.hex[:16], "Roll opening check " + label),
    )
    cur.execute(
        "insert into erp.material_rolls"
        "(id,material_id,roll_number,original_qty,cached_qty,status) "
        "values(%s,%s,%s,%s,0,'AVAILABLE')",
        (roll, material, "ROLL-CHK-" + roll.hex, original_qty),
    )
    return material, location, roll


def create_opening(cur, day, label: str, material, location, items):
    actors.owner(cur)
    actors.zone(cur, "Asia/Jakarta")
    header = uuid.uuid4()
    cur.execute(
        "insert into erp.opening_balance_headers"
        "(id,opening_number,opening_date,status) values(%s,%s,%s,'DRAFT')",
        (header, "ROLL-CHK-" + header.hex[:20], day),
    )
    item_ids = []
    for index, (roll, qty, item_material) in enumerate(items, start=1):
        item = uuid.uuid4()
        item_ids.append(item)
        cur.execute(
            "insert into erp.opening_balance_items"
            "(id,opening_id,balance_type,material_id,roll_id,location_id,qty,unit_cost_snapshot,notes) "
            "values(%s,%s,'MATERIAL',%s,%s,%s,%s,1.25,%s)",
            (item, header, item_material or material, roll, location, qty, label + " line " + str(index)),
        )
    return header, item_ids


def owner_post(cur, header, day):
    actors.owner(cur)
    actors.zone(cur, "Asia/Jakarta")
    cur.execute("select erp.post_opening_balance(%s)", (header,))
    identity = cur.execute(
        "select current_user,session_user,erp.current_app_role()"
    ).fetchone()
    snapshot = base.one(
        cur,
        "select erp.get_owner_financial_snapshot_v2(%s,%s,%s)",
        (day, day, day),
    )
    check = cur.execute(
        "select severity,issue_count,details from erp.run_v268_financial_report_checks() "
        "where check_name=%s",
        (CHECK_NAME,),
    ).fetchone()
    if identity != ("authenticated", "authenticated", "OWNER"):
        raise AssertionError("ORDINARY_OWNER_SESSION_REQUIRED")
    return snapshot, check, identity


def observe_roll(cur, roll, snapshot, check, identity):
    actors.admin(cur)
    original_qty, cached_qty, roll_status = cur.execute(
        "select original_qty,cached_qty,status from erp.material_rolls where id=%s",
        (roll,),
    ).fetchone()
    movement_count, opening_qty = cur.execute(
        "select count(*),coalesce(sum(qty_signed),0) "
        "from erp.material_stock_movements "
        "where roll_id=%s and movement_type='OPENING' and reversal_of_id is null",
        (roll,),
    ).fetchone()
    item_count = base.one(
        cur,
        "select count(*) from erp.opening_balance_items i "
        "join erp.opening_balance_headers h on h.id=i.opening_id "
        "where i.roll_id=%s and h.status='POSTED'",
        (roll,),
    )
    one_opening_source = item_count == 1 and movement_count == 1
    quantity_within_roll = opening_qty > 0 and opening_qty <= original_qty
    cache_matches = cached_qty == opening_qty
    report_ready = (
        snapshot["data_confidence"]["status"] == "READY"
        and check is not None
        and check[1] == 0
    )
    return {
        "identity": identity,
        "original_qty": original_qty,
        "cached_qty": cached_qty,
        "roll_status": roll_status,
        "opening_movement_count": movement_count,
        "posted_opening_item_count": item_count,
        "opening_qty": opening_qty,
        "one_opening_source": one_opening_source,
        "quantity_within_roll": quantity_within_roll,
        "cache_matches": cache_matches,
        "report_status": snapshot["data_confidence"]["status"],
        "ad_check": check,
        "report_ready": report_ready,
        "roll_opening_valid": one_opening_source and quantity_within_roll and cache_matches,
    }


def valid_single(cur, day):
    material, location, roll = create_roll(cur, "valid")
    header, _ = create_opening(
        cur, day, "valid", material, location, [(roll, Decimal("10"), material)]
    )
    snapshot, check, identity = owner_post(cur, header, day)
    return observe_roll(cur, roll, snapshot, check, identity)


def oversized_single(cur, day):
    material, location, roll = create_roll(cur, "oversized")
    header, _ = create_opening(
        cur, day, "oversized", material, location, [(roll, Decimal("11"), material)]
    )
    snapshot, check, identity = owner_post(cur, header, day)
    return observe_roll(cur, roll, snapshot, check, identity)


def duplicate_same_document(cur, day):
    material, location, roll = create_roll(cur, "duplicate-one-document")
    header, _ = create_opening(
        cur,
        day,
        "duplicate-one-document",
        material,
        location,
        [(roll, Decimal("5"), material), (roll, Decimal("5"), material)],
    )
    snapshot, check, identity = owner_post(cur, header, day)
    return observe_roll(cur, roll, snapshot, check, identity)


def reused_next_document(cur, day):
    material, location, roll = create_roll(cur, "reused-next-document")
    first, _ = create_opening(
        cur,
        day,
        "reused-next-document-first",
        material,
        location,
        [(roll, Decimal("6"), material)],
    )
    owner_post(cur, first, day)
    second, _ = create_opening(
        cur,
        day,
        "reused-next-document-second",
        material,
        location,
        [(roll, Decimal("4"), material)],
    )
    snapshot, check, identity = owner_post(cur, second, day)
    return observe_roll(cur, roll, snapshot, check, identity)


def mismatched_material(cur, day):
    material, location, roll = create_roll(cur, "mismatched-material")
    other_material = prior.clone_material(cur, "roll-opening-other-material")
    header, _ = create_opening(
        cur,
        day,
        "mismatched-material",
        other_material,
        location,
        [(roll, Decimal("1"), other_material)],
    )
    owner_post(cur, header, day)
    return {"unexpected_acceptance": True, "roll": roll, "material": material}


def run_case(cur, name: str, function, day, expected: str):
    actors.admin(cur)
    before = actors.boundary(cur)
    cur.execute("savepoint cp6_ad_roll_case")
    error = None
    error_trace = None
    try:
        observation = function(cur, day)
    except psycopg.Error as exc:
        observation = None
        error = {"sqlstate": exc.sqlstate, "message": str(exc)}
    except Exception as exc:
        observation = None
        error = {"sqlstate": None, "message": str(exc)}
        error_trace = traceback.format_exc()
    finally:
        cur.execute("rollback to savepoint cp6_ad_roll_case")
        actors.admin(cur)
        cur.execute("release savepoint cp6_ad_roll_case")
    restored = actors.boundary(cur) == before

    result = {
        "name": name,
        "expected": expected,
        "error": error,
        "observation": observation,
        "full_boundary_restored": restored,
    }
    if error_trace:
        result["traceback"] = error_trace
    if not restored:
        result["status"] = "INCOMPLETE"
    elif expected == "VALID_SINGLE":
        result["status"] = (
            "CONTROL_OK"
            if error is None
            and observation["roll_opening_valid"]
            and observation["report_ready"]
            else "INCOMPLETE"
        )
    elif expected == "MATERIAL_MISMATCH_REFUSAL":
        result["status"] = (
            "CONTROL_OK"
            if error is not None
            and "roll does not belong to the selected material" in error["message"].lower()
            else "INCOMPLETE"
        )
    elif error is not None:
        result["status"] = "INCOMPLETE"
    elif not observation["roll_opening_valid"] and observation["report_ready"]:
        result["status"] = "BUG_PROVEN"
    else:
        result["status"] = "INCOMPLETE"
    return result


def run() -> dict:
    head, tree = verify_round_source()
    expected_url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    if os.environ.get("PGURL") != expected_url:
        raise AssertionError("DISPOSABLE_DATABASE_URL_REQUIRED")
    if os.environ.get("CP6_AD_ROLL_CHECK_CONFIRM") != "postgres":
        raise AssertionError("DISPOSABLE_DATABASE_CONFIRMATION_REQUIRED")

    result = {
        "format": "CP6_AD_ROLL_OPENING_CHECK_V1",
        "status": "INCOMPLETE",
        "candidate_head": AD_HEAD,
        "candidate_tree": AD_TREE,
        "round_head": head,
        "round_tree": tree,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "hosted_database_used": False,
        "production_go": False,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cases": {},
    }
    save(result)

    admin_url = expected_url.replace("postgres:postgres@", "supabase_admin:postgres@")
    with psycopg.connect(admin_url) as connection, connection.cursor() as cur:
        cur.execute(
            "set local statement_timeout='180s';set local lock_timeout='8s';"
            "set local timezone='Asia/Jakarta'"
        )
        untouched = actors.boundary(cur)
        if len(runtime.verified_successor(cur)) != 274:
            raise AssertionError("AD_RUNTIME_NOT_EXACT")
        usage_before = base.one(
            cur, "select has_schema_privilege('authenticated','erp','USAGE')"
        )
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

        cases = (
            ("VALID_SINGLE", valid_single, "VALID_SINGLE"),
            ("OVERSIZED_SINGLE", oversized_single, "REFUSAL"),
            ("DUPLICATE_SAME_DOCUMENT", duplicate_same_document, "REFUSAL"),
            ("REUSED_NEXT_DOCUMENT", reused_next_document, "REFUSAL"),
            ("MISMATCHED_MATERIAL", mismatched_material, "MATERIAL_MISMATCH_REFUSAL"),
        )
        for name, function, expected in cases:
            result["cases"][name] = run_case(cur, name, function, day, expected)
            save(result)
            print(json.dumps({"case": name, "status": result["cases"][name]["status"]}), flush=True)

        connection.rollback()
        result["entire_unseeded_boundary_restored"] = actors.boundary(cur) == untouched
        result["schema_usage_restored"] = (
            base.one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
            == usage_before
        )
        connection.rollback()

    statuses = [case["status"] for case in result["cases"].values()]
    result["bugs_proven"] = statuses.count("BUG_PROVEN")
    result["controls_ok"] = statuses.count("CONTROL_OK")
    result["incomplete"] = statuses.count("INCOMPLETE")
    if (
        len(statuses) == 5
        and result["bugs_proven"] > 0
        and result["controls_ok"] == 2
        and result["incomplete"] == 0
        and result["entire_unseeded_boundary_restored"]
        and result["schema_usage_restored"]
    ):
        result["status"] = "BUG_PROVEN"
    elif (
        len(statuses) == 5
        and result["bugs_proven"] == 0
        and result["incomplete"] == 0
        and result["entire_unseeded_boundary_restored"]
        and result["schema_usage_restored"]
    ):
        result["status"] = "NO_BUG_IN_THIS_ROUND"
    save(result)
    return result


if __name__ == "__main__":
    try:
        final = run()
    except Exception as exc:
        final = {
            "status": "INCOMPLETE",
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "production_go": False,
        }
        save(final)
    print(json.dumps({key: value for key, value in final.items() if key != "cases"}, default=str))
    raise SystemExit(
        1 if final["status"] == "BUG_PROVEN" else 0 if final["status"] == "NO_BUG_IN_THIS_ROUND" else 2
    )
