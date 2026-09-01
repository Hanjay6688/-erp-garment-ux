#!/usr/bin/env python3
"""Real two-session CP3 concurrency harness for a disposable local Supabase DB."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict

import psycopg

PGURL = os.environ.get("PGURL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
NS = uuid.UUID("26140000-0000-4000-8000-000000000000")


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def connect():
    return psycopg.connect(PGURL, autocommit=False, options="-c application_name=CP3_HPP_CONCURRENCY")


def one(conn, sql: str, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0] if cur.description else None


def setup_base() -> None:
    with connect() as conn:
        one(conn, "insert into erp.product_models(id,model_code,model_name) values (%s,%s,%s)", (uid("model"), "CP3C-MODEL", "CP3 Concurrency Model"))
        one(conn, "insert into erp.sizes(id,size_code,sort_order) values (%s,%s,1)", (uid("size"), "CP3C-SIZE"))
        one(conn, "insert into erp.materials(id,material_sku,material_name,material_type,unit_code) values (%s,%s,%s,'FABRIC','YARD')", (uid("material"), "CP3C-FABRIC", "CP3 Concurrency Fabric"))
        conn.commit()


def setup_period(tag: str, start: str, end: str, event_date: str, amount: int, qty: int) -> dict:
    ids = {k: uid(f"{tag}:{k}") for k in [
        "contractor","worker","employment","rate","attendance_period","attendance_record",
        "payroll","po","group","roll","group_roll","slot","policy_req","sewing_req"
    ]}
    with connect() as conn:
        one(conn, "insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required) values (%s,%s,%s,'MANDOR',true)", (ids["contractor"], f"CP3C-{tag}", f"CP3C {tag}"))
        roster = one(conn, "select erp.save_worker_roster_v1(%s::jsonb,%s::uuid,null)", (json.dumps({
            "contractor_id": ids["contractor"], "worker_code": f"W-{tag}",
            "worker_name": f"Worker {tag}", "job_description": "Sewing",
            "pay_scheme": "DAILY", "joined_at": "2026-01-01", "is_active": True,
            "initial_daily_rate": amount, "rate_effective_from": "2026-01-01",
            "reason": "CP3 authoritative concurrency roster"
        }), uid(f"{tag}:worker-roster")))
        roster = roster if isinstance(roster, dict) else json.loads(roster)
        ids["worker"] = str(roster["worker_id"])
        ids["rate"] = str(one(conn, "select erp.worker_daily_rate_version_id_at(%s::uuid,%s::date)", (ids["worker"], event_date)))
        policy = one(conn, "select erp.save_contractor_hpp_policy_v1(%s::jsonb,%s::uuid,null)", (json.dumps({
            "contractor_id": ids["contractor"], "effective_from": "2026-01-01",
            "attendance_required": True, "is_special": False, "change_reason": "CP3 concurrency policy"
        }), ids["policy_req"]))

        start_day = date.fromisoformat(start)
        end_day = date.fromisoformat(end)
        present_day = date.fromisoformat(event_date)
        attendance = []
        day = start_day
        while day <= end_day:
            present = day == present_day
            attendance.append({
                "worker_id": ids["worker"],
                "attendance_date": day.isoformat(),
                "status": "PRESENT" if present else "OFF",
                "paid_fraction": 1 if present else 0,
                "notes": "CP3 explicit concurrency attendance matrix",
            })
            day += timedelta(days=1)

        attendance_saved = one(conn, "select erp.save_attendance_period_v1(%s::jsonb,%s::uuid,null,false)", (json.dumps({
            "contractor_id": ids["contractor"], "period_number": f"ATT-{tag}",
            "period_start": start, "period_end": end, "pay_date": end,
            "reason": "CP3 authoritative concurrency attendance",
            "attendance": attendance,
        }), uid(f"{tag}:attendance-save")))
        attendance_saved = attendance_saved if isinstance(attendance_saved, dict) else json.loads(attendance_saved)
        ids["attendance_period"] = str(attendance_saved["period_id"])
        one(conn, "select erp.post_attendance_period_v1(%s::uuid,%s,%s::uuid,%s)", (
            ids["attendance_period"], "CP3 authoritative concurrency attendance post",
            uid(f"{tag}:attendance-post"), attendance_saved["row_version"]
        ))
        ids["attendance_record"] = str(one(conn, "select id from erp.attendance_records where attendance_period_id=%s::uuid and worker_id=%s::uuid and attendance_date=%s::date and record_lifecycle='POSTED'", (
            ids["attendance_period"], ids["worker"], event_date
        )))
        one(conn, "insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,payment_date) values (%s,%s,%s,%s,%s,'DRAFT',%s)", (ids["payroll"], f"PAY-{tag}", ids["contractor"], start, end, end))
        one(conn, "insert into erp.payroll_attendance_items(payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot,worker_rate_version_id,attendance_date_snapshot,worker_name_snapshot,job_description_snapshot) values (%s,%s,%s,1,%s,%s,%s,%s,'Sewing')", (ids["payroll"], ids["worker"], ids["attendance_record"], amount, ids["rate"], event_date, f"Worker {tag}"))
        one(conn, "update erp.payroll_settlements set attendance_total=%s,status='PAID',settled_at=%s::date where id=%s", (amount, end, ids["payroll"]))
        one(conn, "select erp.post_journal('PAYROLL_EXTRA_ACCRUAL',%s::uuid,%s::date,%s,jsonb_build_array(jsonb_build_object('mapping_key','LABOR_COST','debit',%s,'credit',0,'contractor_id',%s::uuid),jsonb_build_object('mapping_key','CONTRACTOR_PAYABLE','debit',0,'credit',%s,'contractor_id',%s::uuid)))", (ids["payroll"], end, f"CP3 {tag} payroll accrual", amount, ids["contractor"], amount, ids["contractor"]))
        one(conn, "insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at) values (%s,%s,%s,%s,%s,'SEWING','SEWING',%s::date)", (ids["po"], f"PO-{tag}", uid("model"), ids["contractor"], qty, start))
        one(conn, "insert into erp.cutting_groups(id,po_id,group_number,cut_at,picked_up_at,status) values (%s,%s,%s,%s::date,(%s::date + interval '1 day'),'PICKED_UP')", (ids["group"], ids["po"], f"G-{tag}", start, start))
        one(conn, "insert into erp.material_rolls(id,material_id,roll_number,original_qty,cached_qty,status,received_at) values (%s,%s,%s,%s,%s,'AVAILABLE',%s::date)", (ids["roll"], uid("material"), f"R-{tag}", qty, qty, start))
        one(conn, "insert into erp.cutting_group_rolls(id,cutting_group_id,roll_id,qty_issued,qty_consumed) values (%s,%s,%s,%s,%s)", (ids["group_roll"], ids["group"], ids["roll"], qty, qty))
        one(conn, "insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id) values (%s,%s,1,%s)", (ids["slot"], ids["group"], uid("size")))
        one(conn, "insert into erp.cutting_roll_yields(cutting_group_roll_id,size_slot_id,qty_pcs) values (%s,%s,%s)", (ids["group_roll"], ids["slot"], qty))
        sewing = one(conn, "select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)", (json.dumps({
            "event_number": f"SEW-{tag}", "po_id": ids["po"], "cutting_group_id": ids["group"],
            "qty_pcs": qty, "physical_at": f"{event_date}T08:00:00+07:00", "reason": "CP3 concurrency sewing"
        }), ids["sewing_req"]))
        conn.commit()
    return {**ids, "start": start, "end": end, "amount": amount, "qty": qty, "policy": policy, "sewing": sewing}


@dataclass
class CallResult:
    name: str
    ok: bool
    value: object = None
    error: str | None = None


def concurrent_calls(calls):
    barrier = threading.Barrier(len(calls))
    def worker(name, sql, params):
        with connect() as conn:
            try:
                barrier.wait(timeout=10)
                value = one(conn, sql, params)
                conn.commit()
                return CallResult(name, True, value=value)
            except Exception as exc:
                conn.rollback()
                return CallResult(name, False, error=str(exc).splitlines()[0])
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [pool.submit(worker, *call) for call in calls]
        return [future.result(timeout=30) for future in futures]


def assert_exactly_one(results, label):
    if sum(r.ok for r in results) != 1:
        raise AssertionError(f"{label}: expected exactly one success, got {results}")


def main() -> None:
    report = {"status": "RUNNING", "tests": {}}
    setup_base()

    # Real row-lock race: 60 + 60 cannot both fit in a cutting group with capacity 100.
    race = setup_period("SEW-RACE", "2026-01-01", "2026-01-31", "2026-01-20", 1000, 100)
    with connect() as conn:
        one(conn, "select erp.reverse_sewing_terminal_v1((select id from erp.sewing_terminal_events where event_number='SEW-SEW-RACE'),'reset for race',%s::uuid,(select row_version from erp.sewing_terminal_events where event_number='SEW-SEW-RACE'))", (uid("sew-race-reset"),))
        conn.commit()
    results = concurrent_calls([
        ("sewing-A", "select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)", (json.dumps({"event_number":"SEW-RACE-A","po_id":race["po"],"cutting_group_id":race["group"],"qty_pcs":60,"physical_at":"2026-01-21T08:00:00+07:00","reason":"race A"}), uid("sew-race-a"))),
        ("sewing-B", "select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)", (json.dumps({"event_number":"SEW-RACE-B","po_id":race["po"],"cutting_group_id":race["group"],"qty_pcs":60,"physical_at":"2026-01-21T08:00:00+07:00","reason":"race B"}), uid("sew-race-b"))),
    ])
    assert_exactly_one(results, "sewing capacity race")
    with connect() as conn:
        total = one(conn, "select coalesce(sum(qty_pcs),0) from erp.sewing_terminal_events where cutting_group_id=%s and status='POSTED'", (race["group"],))
        if total != 60: raise AssertionError(f"sewing race total {total}, expected 60")
        conn.commit()
    report["tests"]["sewing_capacity_two_session"] = {"status":"PASS","results":[asdict(r) for r in results],"posted_qty":total}

    # Two differently-keyed overlapping periods: global range lock must allow one only.
    pa = setup_period("RANGE-A", "2026-03-01", "2026-03-31", "2026-03-10", 700, 70)
    pb = setup_period("RANGE-B", "2026-03-15", "2026-04-15", "2026-04-01", 800, 80)
    results = concurrent_calls([
        ("range-A", "select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s::uuid)", (json.dumps({"pool_number":"CP3C-RANGE-A","period_start":pa["start"],"period_end":pa["end"],"reason":"range race A"}), uid("range-pool-a"))),
        ("range-B", "select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s::uuid)", (json.dumps({"pool_number":"CP3C-RANGE-B","period_start":pb["start"],"period_end":pb["end"],"reason":"range race B"}), uid("range-pool-b"))),
    ])
    assert_exactly_one(results, "overlapping range race")
    with connect() as conn:
        active = one(conn, "select count(*) from erp.attendance_hpp_pools where status in ('ACTIVE','POSTED') and period_start<='2026-04-15' and period_end>='2026-03-01'")
        if active != 1: raise AssertionError(f"overlap race left {active} active/posted pools")
        pool_id = one(conn, "select id from erp.attendance_hpp_pools where status='ACTIVE' and pool_number in ('CP3C-RANGE-A','CP3C-RANGE-B')")
        version = one(conn, "select row_version from erp.attendance_hpp_pools where id=%s", (pool_id,))
        conn.commit()
    report["tests"]["overlap_range_two_session"] = {"status":"PASS","results":[asdict(r) for r in results],"active_pool_count":active}

    # Real post-vs-cancel race on the same ACTIVE pool.
    results = concurrent_calls([
        ("post", "select erp.post_attendance_hpp_pool_v1(%s::uuid,'post race',%s::uuid,%s)", (pool_id, uid("post-vs-cancel-post"), version)),
        ("cancel", "select erp.cancel_attendance_hpp_pool_v1(%s::uuid,'cancel race',%s::uuid,%s)", (pool_id, uid("post-vs-cancel-cancel"), version)),
    ])
    assert_exactly_one(results, "post versus cancel race")
    with connect() as conn:
        status = one(conn, "select status from erp.attendance_hpp_pools where id=%s", (pool_id,))
        journals = one(conn, "select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_ALLOCATION' and source_id=%s and status='POSTED'", (pool_id,))
        if status == "POSTED" and journals != 1: raise AssertionError("POSTED race winner lacks exactly one journal")
        if status == "CANCELLED" and journals != 0: raise AssertionError("CANCELLED race winner left a journal")
        conn.commit()
    report["tests"]["post_vs_cancel_two_session"] = {"status":"PASS","results":[asdict(r) for r in results],"terminal_status":status,"posted_journals":journals}

    # Same idempotency key + same payload concurrently must return one effect twice.
    idem = setup_period("IDEM", "2026-05-01", "2026-05-31", "2026-05-20", 900, 90)
    with connect() as conn:
        response = one(conn, "select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s::uuid)", (json.dumps({"pool_number":"CP3C-IDEM","period_start":idem["start"],"period_end":idem["end"],"reason":"idempotency setup"}), uid("idem-create")))
        response = response if isinstance(response, dict) else json.loads(response)
        idem_pool = response["pool_id"]
        idem_version = response["row_version"]
        conn.commit()
    same_key = uid("idem-post-same-key")
    results = concurrent_calls([
        ("idem-A", "select erp.post_attendance_hpp_pool_v1(%s::uuid,'same payload',%s::uuid,%s)", (idem_pool, same_key, idem_version)),
        ("idem-B", "select erp.post_attendance_hpp_pool_v1(%s::uuid,'same payload',%s::uuid,%s)", (idem_pool, same_key, idem_version)),
    ])
    if not all(r.ok for r in results): raise AssertionError(f"same-key same-payload should both succeed: {results}")
    values = [r.value if isinstance(r.value, dict) else json.loads(r.value) for r in results]
    journal_ids = {str(value["journal_entry_id"]) for value in values}
    if len(journal_ids) != 1: raise AssertionError(f"idempotent results returned different journals: {journal_ids}")
    with connect() as conn:
        journals = one(conn, "select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_ALLOCATION' and source_id=%s and status='POSTED'", (idem_pool,))
        issues = one(conn, "select coalesce(sum(issue_count),0) from erp.run_v2614_attendance_hpp_integrity_checks()")
        conn.commit()
    if journals != 1 or issues != 0: raise AssertionError(f"idempotency/integrity mismatch journals={journals} issues={issues}")
    report["tests"]["same_key_same_payload_two_session"] = {"status":"PASS","results":[asdict(r) for r in results],"journal_ids":sorted(journal_ids),"posted_journals":journals}

    report["integrity_issue_count"] = issues
    report["status"] = "PASS"
    print(json.dumps(report, indent=2, default=str))
    with open("cp3-concurrency-report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, default=str)
        handle.write("\n")


if __name__ == "__main__":
    main()
