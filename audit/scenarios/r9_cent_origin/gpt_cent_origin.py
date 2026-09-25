"""Independent CP6 W8 follow-up: isolate each receipt before opening the next.

The Fable three-receipt fixture posts all receipts before the cuts. Here each
one-unit receipt is cut into a separate PO while material stock is empty before
the next receipt. The two tests separate propagation of corrections from the
rounding of a pooled moving-average balance. No product code is changed.
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import uuid

import cp6_aw_probe as awp
import cp6_az_probe as azp

api = awp.api
prod = awp.chain.production
KEYS = ("MATERIAL_INVENTORY", "WIP", "FG_INVENTORY", "COGS")


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def receive(cur, day, material, location, estimate):
    """Ordinary purchase RPC; a unique receipt, purchase document and roll."""
    api.admin(cur)
    prod.zone(cur, "Asia/Jakarta")
    if material is None:
        material = prod.prior.clone_material(cur, "gpt-r9-origin")
        location = uuid.uuid4()
        cur.execute(
            "insert into erp.locations(id,location_code,location_name,location_type,is_active) "
            "values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",
            (location, "G9O-" + location.hex[:20], "GPT W8 isolated origin warehouse"),
        )
    payload = dict(
        purchase_number="G9O-PUR-" + uuid.uuid4().hex,
        supplier_id=prod.prior.BASE_SUPPLIER,
        location_id=location,
        physical_at=prod.at(day, 9),
        change_reason="G9 isolated receipt",
        lines=[dict(
            material_id=material, qty=1, unit_price=estimate,
            price_state="ESTIMATED", price_source="MANUAL_ESTIMATE",
            rolls=[dict(roll_number="G9O-ROLL-" + uuid.uuid4().hex, qty=1)],
        )],
    )
    draft = prod.rpc(cur, "erp.save_material_purchase_draft_v2", payload)
    purchase = uuid.UUID(draft["purchase_id"])
    cur.execute(
        "select erp.post_material_purchase_v2(%s,%s,%s,%s)",
        (purchase, uuid.uuid4(), int(draft["row_version"]), "G9 isolated receipt post"),
    )
    api.admin(cur)
    item, roll = cur.execute(
        "select i.id,r.id from erp.material_purchase_items i "
        "join erp.material_rolls r on r.purchase_item_id=i.id "
        "where i.purchase_id=%s", (purchase,),
    ).fetchone()
    return dict(material=material, location=location, purchase=purchase, item=item, roll=roll)


def late_invoice(cur, source, day, unit_price):
    """One source, one invoice; the other source documents stay unchanged."""
    api.admin(cur)
    version = int(cur.execute(
        "select row_version from erp.material_purchase_headers where id=%s",
        (source["purchase"],),
    ).fetchone()[0])
    payload = dict(
        purchase_id=source["purchase"],
        supplier_invoice_number="G9O-INV-" + uuid.uuid4().hex[:18],
        invoice_date=str(day),
        received_at=prod.at(day, 15),
        reason="Independent isolated receipt recost",
        lines=[dict(purchase_item_id=source["item"], qty_invoiced=1,
                    final_unit_price=unit_price)],
    )
    prod.zone(cur, "Asia/Jakarta")
    answer = prod.rpc(cur, "erp.finalize_material_purchase_invoice_v2",
                      payload, uuid.uuid4(), version)
    api.admin(cur)
    return answer


def one_case(cur, today, scenario, initial, final, order):
    first = today - timedelta(days=8)
    days = [first + timedelta(days=i) for i in range(9)]
    awp.boundary.historical.prior.set_open_period(cur, first - timedelta(days=1))
    baseline = azp.ledger_days(cur, days, [])
    sources, pos, stock_after_each_cut = [], [], []
    for index in range(3):
        day = first + timedelta(days=index)
        previous = sources[0] if sources else {}
        source = receive(cur, day, previous.get("material"),
                         previous.get("location"), initial)
        sources.append(source)
        pos.append(azp.cut(cur, source, day, 1, 12))
        # The physical stock must be exhausted between successive receipts.
        stock_after_each_cut.append(cur.execute(
            "select coalesce(sum(qty_signed),0)::text "
            "from erp.material_stock_movements where material_id=%s",
            (source["material"],),
        ).fetchone()[0])
    before = azp.ledger_days(cur, days, pos)
    invoice_day = first + timedelta(days=5)
    posted = []
    for index in order:
        posted.append(dict(index=index,
                           result=late_invoice(cur, sources[index], invoice_day, final)))
    prod.owner(cur)
    cur.execute("select erp.process_cost_recalc_queue(100)")
    api.admin(cur)
    after = azp.ledger_days(cur, days, pos)

    final_day = str(days[-1])
    observed = [money(after[final_day]["WIP_PO"][str(po)]) for po in pos]
    expected = [money(final if index in order else initial)
                for index in range(3)]
    prior_amounts = [money(before[final_day]["WIP_PO"][str(po)]) for po in pos]
    total_wip = Decimal(after[final_day]["WIP"]) - Decimal(baseline[final_day]["WIP"])
    raw = Decimal(cur.execute(
        "select coalesce(sum(qty_signed),0)::text "
        "from erp.material_stock_movements where material_id=%s",
        (sources[0]["material"],),
    ).fetchone()[0])
    inventory = Decimal(after[final_day]["MATERIAL_INVENTORY"]) - Decimal(
        baseline[final_day]["MATERIAL_INVENTORY"])
    # The first two source pairs are wholly consumed before the later receipt.
    # Validate separately by PO, total, and dated prefixes so no excess cent is
    # silently moved from one source/PO to another to make the total appear right.
    dated = {}
    for day in days:
        k = str(day)
        dated[k] = dict(
            material=str(Decimal(after[k]["MATERIAL_INVENTORY"]) -
                         Decimal(baseline[k]["MATERIAL_INVENTORY"])),
            wip=str(Decimal(after[k]["WIP"]) - Decimal(baseline[k]["WIP"])),
        )
    checks = dict(
        each_interval_exhausted=all(Decimal(v) == 0 for v in stock_after_each_cut),
        prior_po_amounts_match=[v == money(initial) for v in prior_amounts],
        exhausted_material_zero=raw == 0 and inventory == 0,
        total_wip_conserved=total_wip == sum(expected),
        isolated_po_source_cents=[got == want for got, want in zip(observed, expected)],
        no_negative_dated_stock_value=all(Decimal(row["material"]) >= 0 for row in dated.values()),
    )
    return dict(
        status="PASS" if all(all(c) if isinstance(c, list) else c for c in checks.values())
                      else "COUNTEREXAMPLE",
        scenario=scenario, checks=checks, order=order, initial=initial, final=final,
        expected_per_po=list(map(str, expected)), observed_per_po=list(map(str, observed)),
        total_wip=str(total_wip), raw_qty=str(raw), inventory_value=str(inventory),
        stock_between_receipts=stock_after_each_cut, dated=dated,
        documents=[str(row["purchase"]) for row in sources],
        pos=list(map(str, pos)), invoice_results=posted,
        oracle="Master Pulih 3820, 6632: each receipt was fully consumed before the next "
               "entered stock. Corrected source cents must reach its own PO on the "
               "cut date and preserve total, zero exhausted-stock value, and dated prefixes. "
               "M:485 concerns allocation of one pooled pocket-fabric cost, not these "
               "distinct purchase sources.",
    )


def cases(cur, today):
    return [
        ("G9O:THREE_STAGGERED_INVOICE_REVERSE_ORDER_UP",
         lambda: one_case(cur, today, "reverse order +0.005", "10.00", "10.005", [2, 0, 1])),
        ("G9O:THREE_STAGGERED_INVOICE_REVERSE_ORDER_DOWN",
         lambda: one_case(cur, today, "reverse order -0.006", "10.01", "10.004", [2, 0, 1])),
        ("G9O:THREE_STAGGERED_ONLY_MIDDLE_CORRECTED",
         lambda: one_case(cur, today, "middle-only +0.015", "10.00", "10.015", [1])),
    ]
