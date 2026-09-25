"""Independent BB follow-up, frozen before a native run on writer head 4c61aca.

The BB helpers arrange legitimate fixtures. The assertions below inspect the
native ledger and statuses independently of the helpers' own verdicts.
Only disposable clone transactions are used by the auditor runner.
"""
from datetime import timedelta
from decimal import Decimal
import uuid

import cp6_aw_probe as awp
import cp6_az_probe as azp
import cp6_bb_probe as bb


def pooled_cent_ten(cur, today):
    """Ten supplier documents at 10.005 each, mixed in stock before ten cuts."""
    d = today - timedelta(days=4)
    cut_day = d + timedelta(days=1)
    awp.boundary.historical.prior.set_open_period(cur, d - timedelta(days=1))
    first = azp.final_receipt(cur, d, qty=1, price="10.005")
    awp.api.admin(cur)
    first["roll"] = cur.execute(
        "select id from erp.material_rolls where purchase_item_id=%s",
        (first["item"],),
    ).fetchone()[0]
    receipts = [first]
    prod = azp.chain.production
    for _ in range(9):
        prod.zone(cur, "Asia/Jakarta")
        payload = dict(
            purchase_number="G10-PUR-" + uuid.uuid4().hex,
            supplier_id=prod.prior.BASE_SUPPLIER,
            location_id=first["location"],
            supplier_invoice_number="G10-INV-" + uuid.uuid4().hex[:16],
            physical_at=prod.at(d, 10),
            change_reason="Independent ten-document pooling",
            lines=[dict(
                material_id=first["material"], qty=1, unit_price="10.005",
                price_state="FINAL", price_source="SUPPLIER_INVOICE",
                rolls=[dict(roll_number="G10-R-" + uuid.uuid4().hex, qty=1)],
            )],
        )
        draft = prod.rpc(cur, "erp.save_material_purchase_draft_v2", payload)
        purchase = uuid.UUID(draft["purchase_id"])
        cur.execute("select erp.post_material_purchase_v2(%s,%s,%s,%s)",
                    (purchase, uuid.uuid4(), int(draft["row_version"]),
                     "Independent pooled purchase"))
        awp.api.admin(cur)
        item, roll = cur.execute(
            "select i.id,r.id from erp.material_purchase_items i "
            "join erp.material_rolls r on r.purchase_item_id=i.id "
            "where i.purchase_id=%s", (purchase,),
        ).fetchone()
        receipts.append(dict(material=first["material"], location=first["location"],
                             purchase=purchase, item=item, roll=roll))
    before = azp.ledger_days(cur, [d, cut_day, today], [])
    pos = [azp.cut(cur, fx, cut_day, 1, 11 + i) for i, fx in enumerate(receipts)]
    prod.owner(cur)
    cur.execute("select erp.process_cost_recalc_queue(100)")
    awp.api.admin(cur)
    after = azp.ledger_days(cur, [d, cut_day, today], pos)
    per_po = [Decimal(after[str(today)]["WIP_PO"][str(po)]) for po in pos]
    stock_value = Decimal(after[str(today)]["MATERIAL_INVENTORY"]) - Decimal(before[str(today)]["MATERIAL_INVENTORY"])
    qty = Decimal(str(cur.execute(
        "select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s",
        (first["material"],),
    ).fetchone()[0]))
    total = sum(per_po)
    drift = [x - Decimal("10.01") for x in per_po]
    checks = dict(
        ten_distinct_purchase_documents=len({r["purchase"] for r in receipts}) == 10,
        total_equals_document_cents=total == Decimal("100.10"),
        no_remaining_stock_qty_or_value=qty == 0 and stock_value == 0,
    )
    return dict(
        status="PASS" if all(checks.values()) else "COUNTEREXAMPLE",
        checks=checks, per_po=[str(v) for v in per_po],
        deviation_from_own_document_cents=[str(v) for v in drift],
        max_absolute_po_deviation=str(max(abs(v) for v in drift)),
        writer_claim_1_cent_per_po_holds=max(abs(v) for v in drift) <= Decimal("0.01"),
        total_wip=str(total), remaining_material_qty=str(qty), remaining_material_value=str(stock_value),
        purchase_documents=[str(fx["purchase"]) for fx in receipts],
        oracle="Master Pulih M:835, M:3820, M:6632: each purchase document rounds 10.005 to 10.01; "
               "ten docs yield 100.10, all ten one-unit cuts consume stock, inventory is zero. "
               "Per-PO one-cent bound is a separate writer claim, not assumed to be a contract gate.",
    )


def two_drafts_one_stock(cur, today):
    """Two original drafts compete for one stock; edit, cancel, post through native RPCs."""
    cutover = today - timedelta(days=10)
    rows = bb.s02_rows(cutover, drafts=(("SD-{C}", "3"), ("SE-{C}", "2")))
    batch, code, _ = bb.post_batch(cur, today, rows)
    awp.api.admin(cur)
    sale1 = bb.s02_sale(cur, code, "SD-" + code)
    sale2 = bb.s02_sale(cur, code, "SE-" + code)
    original = dict(free=bb.s02_free(cur, code),
                    reserve1=bb.s02_reserves(cur, sale1[0]),
                    reserve2=bb.s02_reserves(cur, sale2[0]))
    before = bb.gl(cur)
    bb.s02_save(cur, sale1[0], code, 4, bb.now(cur).isoformat())
    edited = dict(free=bb.s02_free(cur, code),
                  reserve1=bb.s02_reserves(cur, sale1[0]))
    h2 = bb.s02_sale(cur, code, "SE-" + code)
    azp.chain.production.owner(cur)
    cur.execute("select erp.cancel_sale_draft_v2(%s,%s,%s,%s)",
                (sale2[0], "Second imported draft cancelled", uuid.uuid4(), h2[2]))
    awp.api.admin(cur)
    cancelled = dict(free=bb.s02_free(cur, code),
                     reserve2=bb.s02_reserves(cur, sale2[0]),
                     status=bb.s02_sale(cur, code, "SE-" + code)[1],
                     journals=bb.moved(before, bb.gl(cur)))
    h1 = bb.s02_sale(cur, code, "SD-" + code)
    azp.chain.production.owner(cur)
    cur.execute("select erp.post_sale_v2(%s,%s,%s)",
                (sale1[0], uuid.uuid4(), h1[2]))
    awp.api.admin(cur)
    final = dict(free=bb.s02_free(cur, code),
                 reserve1=bb.s02_reserves(cur, sale1[0]),
                 status1=bb.s02_sale(cur, code, "SD-" + code)[1],
                 status2=bb.s02_sale(cur, code, "SE-" + code)[1])
    delta = bb.moved(before, bb.gl(cur))
    expected = {bb.account(cur, k): v for k, v in (
        ("AR_CUSTOMER", "40.00"), ("SALES_REVENUE", "-40.00"),
        ("COGS", "24.00"), ("FG_INVENTORY", "-24.00"))}
    checks = dict(
        two_imported_reservations_once=original == dict(free=5, reserve1=(1, 3), reserve2=(1, 2)),
        editing_reconciles_availability=edited == dict(free=4, reserve1=(1, 4)),
        cancelling_releases_only_own_reservation=(cancelled["free"] == 6
            and cancelled["reserve2"] == (0, 0) and cancelled["status"] == "CANCELLED"
            and cancelled["journals"] == {}),
        post_does_not_deduct_again=final == dict(free=6, reserve1=(0, 0),
            status1="POSTED", status2="CANCELLED"),
        journal_once=all(delta.get(k) == v for k, v in expected.items()),
    )
    return dict(status="PASS" if all(checks.values()) else "COUNTEREXAMPLE",
                checks=checks, original=original, edited=edited, cancelled=cancelled,
                final=final, journal_delta=delta, expected_journal=expected,
                batch=str(batch), oracle="Master Pulih M:3821, M:6631: two imported sales DRAFTs "
                "reserve once against ten physical PCS; edit and cancel each reconcile availability; "
                "POST removes only fulfilled quantity once and books the single native sale.")


def cases(cur, today):
    return [
        ("G10:BA_TEN_DOCUMENT_CENT_POOL", lambda: pooled_cent_ten(cur, today)),
        ("G10:BB_TWO_DRAFT_SHARED_RESERVE", lambda: two_drafts_one_stock(cur, today)),
    ]
