"""Independent BE facts on a full disposable T1 schema.

The writer's old fixture helpers create physical prerequisites only. Assertions,
boundary cases, and the invoice threshold come from the auditor's frozen oracle.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import psycopg

import cp6_be_probe as setup
import cp6_bd_probe as bdp
import cp6_be_pocket_probe as pocket

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "be-blind-native-results.json"
HTTP_FIXTURE = ROOT / "be-blind-http-fixture.json"


def one(cur, sql: str, *args):
    return cur.execute(sql, args).fetchone()[0]


def business_date(cur):
    return one(cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date")


def post_draft(cur, invoice: dict):
    return bdp.bd(cur, "POST_INVOICE", {"invoice_id": invoice["invoice_id"],
                                       "expected_version": invoice["row_version"]})


def main() -> None:
    result = {"status": "INCOMPLETE", "candidate": "2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b",
              "production_go": False}
    with psycopg.connect(os.environ["PGURL"].replace("//postgres:", "//supabase_admin:", 1)) as conn, conn.cursor() as cur:
        day = business_date(cur)
        assert one(cur, "select count(*) from erp.schema_migrations where version='v2.6.20be'") == 1
        if not one(cur, "select has_schema_privilege('authenticated','erp','USAGE')"):
            cur.execute("grant usage on schema erp to authenticated")
        bdp.api.seed(cur)
        bdp.boundary.historical.prior.set_open_period(cur, day - timedelta(days=30))

        # B01: selected source, real movements, replay, and inverse. A separate
        # fixture lot provides a negative control for accidental FIFO selection.
        chosen = setup.fixture(cur, day)
        unrelated = setup.fixture(cur, day)
        chosen_initial = setup.qty(cur, chosen["lot"])
        unrelated_initial = setup.qty(cur, unrelated["lot"])
        source_value = bdp.lot_value(cur, chosen["lot"])
        key = str(uuid.uuid4())
        posted = setup.be(cur, "POST", chosen["payload"], key)
        replay = setup.be(cur, "POST", chosen["payload"], key)
        target_lot = posted["destination_lot_id"]
        after_source, after_target = setup.qty(cur, chosen["lot"]), setup.qty(cur, target_lot)
        unrelated_after = setup.qty(cur, unrelated["lot"])
        target_value = bdp.lot_value(cur, target_lot)
        assert chosen_initial == unrelated_initial == 10
        assert (after_source, after_target, unrelated_after) == (4, 6, 10)
        assert target_value == source_value * Decimal("0.6")
        assert replay["conversion_id"] == posted["conversion_id"]
        assert one(cur, "select count(*) from erp.product_conversions where id=%s", key) == 1
        setup.be(cur, "REVERSE", {"conversion_id": posted["conversion_id"],
                                   "reason": "Independent inverse after selected-lot transfer"})
        assert (setup.qty(cur, chosen["lot"]), setup.qty(cur, target_lot),
                setup.qty(cur, unrelated["lot"])) == (10, 0, 10)
        http_source = setup.fixture(cur, day)
        http_payload = dict(http_source["payload"])
        http_payload["expected_version"] = one(cur, "select erp.be_source_revision_v1(%s,%s)",
                                               http_source["lot"], http_source["location"])
        race_payload = dict(unrelated["payload"])
        race_payload["expected_version"] = one(cur, "select erp.be_source_revision_v1(%s,%s)",
                                               unrelated["lot"], unrelated["location"])
        HTTP_FIXTURE.write_text(json.dumps({"payload": http_payload, "source_lot_id": http_source["lot"],
                                            "race_payload": race_payload, "race_lot_id": unrelated["lot"]}) + "\n")
        result["selected_lot"] = {"source_before": chosen_initial, "source_after_post": after_source,
                                  "target_after_post": after_target, "unrelated": unrelated_after,
                                  "replay_same": True, "inverse_restored": True,
                                  "source_value": str(source_value), "target_value": str(target_value)}

        # B05: the BE third invoice source must not inherit BD's integer-cent
        # overflow. A small invoice on the same source is the positive control.
        service = setup.redye_fixture(cur, day, known=True)
        bdp.invoice_policies(cur, after="CORRECTION_DOCUMENT")
        bdp.api.admin(cur)
        sold = bdp.sell(cur, service, service["target"], 1, 17)
        sale_snapshot = one(cur, "select sum(total_hpp) from erp.sale_stock_allocations "
                                 "where sale_item_id in(select id from erp.sales_items where sale_id=%s)", sold)
        ap_before = Decimal(str(bdp.ap(cur, service["vendor"])))
        huge = bdp.bd(cur, "SAVE_INVOICE_DRAFT", {
            "vendor_id": service["vendor"], "invoice_number": "BE-AUD-HUGE-" + uuid.uuid4().hex[:9],
            "invoice_date": str(service["day"]), "header_total": "22000000.00",
            "lines": [{"line_kind": "BILL", "rework_service_id": service["redye"],
                       "category": "GOOD", "qty": 4, "amount": "22000000.00"}]})
        try:
            with conn.transaction():
                post_draft(cur, huge)
        except psycopg.Error as error:
            huge_state, huge_error = error.sqlstate, error.diag.message_primary
        else:
            huge_state, huge_error = "POSTED", "unexpected success"
        huge_status = one(cur, "select status from erp.bd_laundry_invoices_v1 where id=%s", huge["invoice_id"])
        assert huge_state == "22003" and huge_status == "DRAFT", (huge_state, huge_error, huge_status)
        assert Decimal(str(bdp.ap(cur, service["vendor"]))) == ap_before
        small = bdp.bd(cur, "SAVE_INVOICE_DRAFT", {
            "vendor_id": service["vendor"], "invoice_number": "BE-AUD-SMALL-" + uuid.uuid4().hex[:9],
            "invoice_date": str(service["day"]), "header_total": "240.00",
            "lines": [{"line_kind": "BILL", "rework_service_id": service["redye"],
                       "category": "GOOD", "qty": 4, "amount": "240.00"}]})
        small_posted = post_draft(cur, small)
        assert small_posted["status"] == "POSTED"
        cost = one(cur, "select erp.be_redye_cost_v1(%s)", service["redye"])
        accrued = one(cur, "select erp.be_redye_accrual_v1(%s)", service["po"])
        sale_after = one(cur, "select sum(total_hpp) from erp.sale_stock_allocations "
                                   "where sale_item_id in(select id from erp.sales_items where sale_id=%s)", sold)
        assert cost == 240 and accrued == 0 and sale_after == sale_snapshot
        assert Decimal(str(bdp.ap(cur, service["vendor"]))) - ap_before == 240
        result["redye_invoice_boundary"] = {"huge_amount": "22000000.00", "sqlstate": huge_state,
                                            "draft_after_failure": huge_status,
                                            "small_posted": small_posted["status"], "small_cost": str(cost),
                                            "accrual_after_small": str(accrued),
                                            "sale_snapshot_immutable": sale_after == sale_snapshot}

        # B06: the new BE adapter makes a previously unreachable BD button
        # actionable; unknown remains null until owner records a first price.
        pending = setup.redye_fixture(cur, day, known=False)
        initial_rate = one(cur, "select erp.be_redye_rate_v1(%s)", pending["redye"])
        action = bdp.bd(cur, "SET_REDYE_PRICE", {"service_id": pending["redye"],
                          "rate": "50.00", "reason": "Independent exact first price"})
        resolved = one(cur, "select erp.be_redye_rate_v1(%s)", pending["redye"])
        assert initial_rate is None and resolved == 50 and action["rate"] == "50.00"
        result["redye_unknown_resolution"] = {"initial_rate": None, "resolved_rate": str(resolved),
                                              "bd_facade_reachable": True}

        # B08: real pre-cutover source and three destinations. The imported
        # physical history is fixture data; expected postings are oracle facts.
        cutover = day - timedelta(days=10)
        pocket_source = bdp.bbp.production_post(cur, day, pocket.active_unit(cur, pocket.rows(cutover)))
        start = cutover - timedelta(days=1)
        before_physical = (one(cur, "select count(*) from erp.material_stock_movements"),
                           one(cur, "select count(*) from erp.sewing_terminal_events"))
        accounts = ("WIP", "FG_INVENTORY", "COGS", "OTHER_EXPENSE")
        before_books = {account: bdp.gl(cur, account) for account in accounts}
        preview = pocket.preview(cur, start, cutover)
        assert preview["quantity"] == "10" and preview["amount"] == "11.25", preview
        payload = {"period_start": str(start), "period_end": str(cutover),
                   "expected_revision": preview["revision"], "reason": "Blind historical pocket allocation"}
        period_key = str(uuid.uuid4())
        allocation = pocket.call(cur, "POST_PERIOD", payload, period_key)
        replay_allocation = pocket.call(cur, "POST_PERIOD", payload, period_key)
        delta = {account: bdp.gl(cur, account) - before_books[account] for account in accounts}
        expected = {"WIP": Decimal("5.62"), "FG_INVENTORY": Decimal("3.38"),
                    "COGS": Decimal("2.25"), "OTHER_EXPENSE": Decimal("-11.25")}
        assert delta == expected and allocation["id"] == replay_allocation["id"], (delta, replay_allocation)
        revision = one(cur, "select erp.pocket_period_state_v1(%s)", allocation["id"])["revision"]
        pocket.call(cur, "CANCEL_PERIOD", {"id": allocation["id"], "expected_revision": revision,
                                              "reason": "Blind pocket inverse"})
        inverse = {account: bdp.gl(cur, account) - before_books[account] for account in accounts}
        after_physical = (one(cur, "select count(*) from erp.material_stock_movements"),
                          one(cur, "select count(*) from erp.sewing_terminal_events"))
        assert all(value == 0 for value in inverse.values()) and before_physical == after_physical
        result["historical_pocket"] = {"batch": pocket_source["batch"],
                                        "preview": {"qty": preview["quantity"], "amount": preview["amount"]},
                                        "posted_delta": {k: str(v) for k, v in delta.items()},
                                        "replay_same": True, "inverse_zero": True,
                                        "no_synthetic_physical_events": True}

        result["status"] = "FULL_SCHEMA_PROBES_COMPLETE"
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(OUT.read_text(), flush=True)


if __name__ == "__main__":
    main()
