"""Independent commit/abort race oracles on the frozen disposable BE database.

The AW scheduler supplies separate PostgreSQL sessions. Assertions and fixtures
below are owned by this auditor. All rows stay inside the disposable runtime.
"""
from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import psycopg

import cp6_aw_probe as aw
import cp6_be_probe as be
import cp6_bd_probe as bd
import cp6_be_pocket_probe as pocket

OUT = Path(__file__).resolve().parents[1] / "be-blind-race-results.json"
DB = os.environ["PGURL"].replace("//postgres:", "//supabase_admin:", 1)


def one(cur, sql, *args):
    return cur.execute(sql, args).fetchone()[0]


def conversion(day, commit, same_key=False):
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        f = be.fixture(cur, day)
    first_id = str(uuid.uuid4())
    second_id = first_id if same_key else str(uuid.uuid4())
    first, lock, second = aw.two_sessions(DB,
        lambda cur: be.be(cur, "POST", f["payload"], first_id),
        lambda cur: be.be(cur, "POST", f["payload"], second_id), commit)
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        remaining = be.qty(cur, f["lot"])
        count = one(cur, """select count(*) from erp.be_conversion_sources_v1 s
            join erp.product_conversions c on c.id=s.conversion_id
            where s.source_lot_id=%s and c.status='POSTED'""", f["lot"])
    assert lock == {"kind": "BLOCKED", "holder_blocks_worker": True}, lock
    assert (remaining, count) == (4, 1), (remaining, count)
    if commit and not same_key:
        assert not second["ok"] and "STALE_VERSION" in second["message"], second
    else:
        assert second["ok"] and (not same_key or
            second["result"]["conversion_id"] == first["conversion_id"]), second
    return {"first_committed": commit, "same_uuid": same_key,
            "lock_blocked": True, "second_ok": second["ok"], "remaining_qty": remaining, "posted": count}


def price(day, commit):
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        f = be.redye_fixture(cur, day, known=False)
    action = lambda rate: lambda cur: be.be(cur, "SET_REDYE_PRICE", {
        "service_id": f["redye"], "rate": rate, "reason": "Blind two-session price"})
    _, lock, second = aw.two_sessions(DB, action("50.00"), action("60.00"), commit)
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        count = one(cur, "select count(*) from erp.be_redye_price_events_v1 where service_id=%s", f["redye"])
        cost = one(cur, "select erp.be_redye_cost_v1(%s)", f["redye"])
    assert lock == {"kind": "BLOCKED", "holder_blocks_worker": True}, lock
    assert count == 1 and cost == Decimal("200.00" if commit else "240.00"), (count, cost)
    if commit:
        assert not second["ok"] and "BE_PRICE_ALREADY_KNOWN" in second["message"], second
    else:
        assert second["ok"], second
    return {"first_committed": commit, "events": count, "cost": str(cost),
            "second_ok": second["ok"], "lock_blocked": True}


def invoice(day, commit):
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        f = be.redye_fixture(cur, day, known=True)
        bd.invoice_policies(cur)
        row = {"vendor_id": f["vendor"], "invoice_date": str(f["day"]),
            "header_total": "240.00", "lines": [{"line_kind": "BILL",
            "rework_service_id": f["redye"], "category": "GOOD", "qty": 4,
            "amount": "240.00"}]}
        a = bd.bd(cur, "SAVE_INVOICE_DRAFT", dict(row, invoice_number="BLIND-A-" + uuid.uuid4().hex))
        b = bd.bd(cur, "SAVE_INVOICE_DRAFT", dict(row, invoice_number="BLIND-B-" + uuid.uuid4().hex))
    _, lock, second = aw.two_sessions(DB,
        lambda cur: bd.post_draft(cur, a), lambda cur: bd.post_draft(cur, b), commit)
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        cost = one(cur, "select erp.be_redye_cost_v1(%s)", f["redye"])
        posted = one(cur, """select count(*) from erp.bd_laundry_invoices_v1 i
            join erp.bd_laundry_invoice_lines_v1 l on l.invoice_id=i.id
            where l.rework_service_id=%s and i.status='POSTED'""", f["redye"])
    assert lock == {"kind": "BLOCKED", "holder_blocks_worker": True}, lock
    assert cost == Decimal("240.00") and posted == 1, (cost, posted)
    if commit:
        assert not second["ok"] and "BD_INVOICE_CAPACITY" in second["message"], second
    else:
        assert second["ok"], second
    return {"first_committed": commit, "posted_bills": posted, "cost": str(cost),
            "second_ok": second["ok"], "lock_blocked": True}


def period(day, commit, offset):
    cut = day - timedelta(days=offset)
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        f = bd.bbp.production_post(cur, day, pocket.active_unit(cur, pocket.rows(cut)))
        preview = pocket.preview(cur, cut - timedelta(days=1), cut)
    payload = {"period_start": preview["period_start"], "period_end": preview["period_end"],
        "expected_revision": preview["revision"], "reason": "Blind two-session historical pool"}
    with psycopg.connect(DB) as first, psycopg.connect(DB) as second:
        with first.cursor() as a, second.cursor() as z:
            assert one(a, "select pg_backend_pid()") != one(z, "select pg_backend_pid()")
            posted = pocket.call(a, "POST_PERIOD", payload)
            try:
                with second.transaction():
                    pocket.call(z, "POST_PERIOD", payload)
            except psycopg.Error as error:
                assert "POCKET_PERIOD_BUSY" in error.diag.message_primary, error.diag.message_primary
            else:
                raise AssertionError("Second period command did not see in-flight lock")
            if commit:
                first.commit()
                try:
                    with second.transaction():
                        pocket.call(z, "POST_PERIOD", payload)
                except psycopg.Error as error:
                    assert "tumpang tindih" in error.diag.message_primary, error.diag.message_primary
                else:
                    raise AssertionError("Overlapping period accepted after first commit")
            else:
                first.rollback()
                accepted = pocket.call(z, "POST_PERIOD", payload)
                assert accepted["status"] == "ACTIVE"
                second.commit()
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        count = one(cur, """select count(*) from erp.pocket_period_sources
            where historical_usage_id in(select id from erp.be_pocket_usage_v1 where batch_id=%s)""", f["batch"])
    assert count == 1, count
    return {"first_committed": commit, "first_pool_id": posted["id"] if commit else None,
            "in_flight_refused": True, "once": count}


def main():
    report = {"candidate": "2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b",
              "status": "INCOMPLETE", "production_go": False, "cases": {}}
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        day = one(cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date")
        bd.boundary.historical.prior.set_open_period(cur, day - timedelta(days=30))
    cases = [("CONVERSION_COMMIT", lambda: conversion(day, True)),
        ("CONVERSION_ABORT", lambda: conversion(day, False)),
        ("CONVERSION_SAME_UUID", lambda: conversion(day, True, True)),
        ("PRICE_COMMIT", lambda: price(day, True)),
        ("PRICE_ABORT", lambda: price(day, False)),
        ("INVOICE_COMMIT", lambda: invoice(day, True)),
        ("INVOICE_ABORT", lambda: invoice(day, False)),
        ("POCKET_COMMIT", lambda: period(day, True, 10)),
        ("POCKET_ABORT", lambda: period(day, False, 12))]
    for name, case in cases:
        try:
            report["cases"][name] = {"status": "PASS", **case()}
        except Exception as error:
            report["cases"][name] = {"status": "INCOMPLETE", "error": str(error),
                                     "traceback": traceback.format_exc()[-4000:]}
        OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({"case": name, **report["cases"][name]}, default=str), flush=True)
    report["status"] = "PASS" if all(r["status"] == "PASS" for r in report["cases"].values()) else "INCOMPLETE"
    OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
    assert report["status"] == "PASS", report


if __name__ == "__main__":
    main()
