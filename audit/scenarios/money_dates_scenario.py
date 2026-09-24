"""Independent CP6 money/date cases. NOT_RUN until executed on the pinned candidate.

Oracle: Master 1022, 1664, 3816, 3818, 3820, 3825; receipt and all physical
consumption both contain one unit. Monetary results are rounded endpoints.
Writer modules are used only for ordinary fixture/actor setup, never assertions.
Every unexpected error (including a product refusal) is INCOMPLETE.
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import traceback
import uuid

import cp6_az_probe as azp

D = Decimal
KEYS = ("MATERIAL_INVENTORY", "WIP", "FG_INVENTORY", "COGS", "AP_SUPPLIER", "GRNI_MATERIAL")


def cents(value):
    return D(str(value)).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def ledger(cur, days):
    azp.api.admin(cur)
    result = {}
    for day in days:
        row = {}
        for key in KEYS:
            value = cur.execute(
                "select coalesce(sum(a.debit_total-a.credit_total),0) "
                "from erp.account_daily_balances a "
                "where a.account_id=erp.account_id(%s) and a.balance_date<=%s",
                (key, day),
            ).fetchone()[0]
            row[key] = D(str(value))
        result[str(day)] = row
    return result


def delta(after, before):
    return {day: {key: after[day][key]-before[day][key] for key in KEYS} for day in after}


def strings(value):
    if isinstance(value, dict):
        return {str(k): strings(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [strings(v) for v in value]
    if isinstance(value, (D, uuid.UUID)):
        return str(value)
    return value


def estimated_receipt(cur, day, price):
    # An independent parameterized data builder using the canonical draft/post RPCs.
    prod = azp.chain.production
    prior = prod.prior
    azp.api.admin(cur)
    prod.zone(cur, "Asia/Jakarta")
    material = prior.clone_material(cur, "blind-money-cent")
    location = uuid.uuid4()
    cur.execute(
        "insert into erp.locations(id,location_code,location_name,location_type,is_active) "
        "values(%s,%s,'Blind money cent raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",
        (location, "BM-LOC-" + location.hex[:20]),
    )
    draft = prod.rpc(cur, "erp.save_material_purchase_draft_v2", dict(
        purchase_number="BM-PUR-" + str(uuid.uuid4()), supplier_id=prior.BASE_SUPPLIER,
        location_id=location, physical_at=prod.at(day, 10),
        change_reason="Independent money cent receipt",
        lines=[dict(material_id=material, qty=1, unit_price=price,
                    price_state="ESTIMATED", price_source="MANUAL_ESTIMATE",
                    rolls=[dict(roll_number="BM-ROLL-" + str(uuid.uuid4()), qty=1)])],
    ))
    purchase = uuid.UUID(draft["purchase_id"])
    cur.execute("select erp.post_material_purchase_v2(%s,%s,%s,%s)",
                (purchase, uuid.uuid4(), int(draft["row_version"]), "Independent receipt post"))
    azp.api.admin(cur)
    item, roll = cur.execute(
        "select i.id,r.id from erp.material_purchase_items i "
        "join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=%s",
        (purchase,),
    ).fetchone()
    return dict(material=material, purchase=purchase, item=item, roll=roll, location=location)


def correction(cur, fx, day, price):
    azp.api.admin(cur)
    correction_id = uuid.uuid4()
    cur.execute(
        "insert into erp.material_purchase_cost_corrections "
        "(id,correction_number,purchase_id,supplier_invoice_number,invoice_date,reason,status) "
        "values(%s,%s,%s,%s,%s,'Independent cent conservation correction','DRAFT')",
        (correction_id, "BM-CC-" + correction_id.hex, fx["purchase"],
         "BM-INV-" + correction_id.hex, day),
    )
    cur.execute(
        "insert into erp.material_purchase_cost_correction_items "
        "(correction_id,purchase_item_id,new_unit_price) values(%s,%s,%s)",
        (correction_id, fx["item"], price),
    )
    azp.chain.production.owner(cur)
    cur.execute("select erp.post_material_purchase_cost_correction(%s)", (correction_id,))
    azp.api.admin(cur)
    return correction_id


def invoice(cur, fx, today, day, price):
    azp.api.admin(cur)
    version = cur.execute("select row_version from erp.material_purchase_headers where id=%s",
                          (fx["purchase"],)).fetchone()[0]
    response = azp.chain.production.rpc(cur, "erp.finalize_material_purchase_invoice_v2", dict(
        purchase_id=fx["purchase"], supplier_invoice_number="BM-INV-" + uuid.uuid4().hex,
        invoice_date=day, received_at=azp.chain.production.at(today, 0),
        reason="Independent cent conservation invoice",
        lines=[dict(purchase_item_id=fx["item"], qty_invoiced=1, final_unit_price=price)],
    ), uuid.uuid4(), int(version))
    azp.api.admin(cur)
    return response


def money_rounding(cur, today, old_price, new_price, kind):
    prod = azp.chain.production
    receipt_day, cutting_day, invoice_day = [today-timedelta(days=n) for n in (4, 3, 2)]
    days = [receipt_day, cutting_day, invoice_day, today]
    azp.api.admin(cur)
    prod.prior.set_open_period(cur, receipt_day-timedelta(days=1))
    before = ledger(cur, days)
    if kind == "DIRECT":
        fx = azp.final_receipt(cur, receipt_day, qty=1, price=old_price)
        fx["roll"] = cur.execute("select id from erp.material_rolls where purchase_item_id=%s",
                                 (fx["item"],)).fetchone()[0]
    else:
        fx = estimated_receipt(cur, receipt_day, old_price)
    po = azp.cut(cur, fx, cutting_day, 1)
    initial = delta(ledger(cur, days), before)
    # Certify the fixture without using the implementation's cost calculator.
    original_total, corrected_total = cents(old_price), cents(new_price)
    if initial[str(cutting_day)]["MATERIAL_INVENTORY"] != 0 or initial[str(cutting_day)]["WIP"] != original_total:
        return dict(status="INCOMPLETE", reason="Independent baseline receipt/issue did not reconcile",
                    fixture=strings(fx), initial=strings(initial))
    result = correction(cur, fx, invoice_day, new_price) if kind == "DIRECT" else invoice(cur, fx, today, invoice_day, new_price)
    observed = delta(ledger(cur, days), before)
    expected = {}
    for day in days:
        amount = corrected_total if day >= invoice_day else original_total
        expected[str(day)] = dict.fromkeys(KEYS, D("0.00"))
        expected[str(day)]["MATERIAL_INVENTORY"] = amount if day < cutting_day else D("0.00")
        expected[str(day)]["WIP"] = amount if day >= cutting_day else D("0.00")
        liability = "AP_SUPPLIER" if kind == "DIRECT" or day >= invoice_day else "GRNI_MATERIAL"
        expected[str(day)][liability] = -amount
    qty = D(str(cur.execute("select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s",
                           (fx["material"],)).fetchone()[0]))
    movements = cur.execute(
        "select movement_type,qty_signed,original_unit_cost_snapshot,unit_cost_snapshot "
        "from erp.material_stock_movements where material_id=%s order by physical_at,system_created_at,id",
        (fx["material"],),
    ).fetchall()
    events = cur.execute(
        "select e.effective_date,e.delta_amount,e.counterpart_mapping_key,j.economic_date,j.transaction_date "
        "from erp.material_cost_revaluation_events e join erp.journal_entries j on j.id=e.journal_entry_id "
        "where e.material_id=%s order by j.transaction_date,e.id", (fx["material"],)
    ).fetchall()
    # Readiness is evidence only. This case does not assume that unrelated seed policy blockers are absent.
    azp.api.ordinary(cur)
    snapshot = cur.execute("select erp.get_owner_financial_snapshot_v2(%s,%s,%s)",
                           (receipt_day, today, today)).fetchone()[0]
    azp.api.admin(cur)
    mismatch = {day: {k: dict(expected=str(expected[day][k]), actual=str(observed[day][k]))
                     for k in KEYS if expected[day][k] != observed[day][k]}
                for day in observed}
    mismatch = {day: row for day, row in mismatch.items() if row}
    return dict(status="COUNTEREXAMPLE" if mismatch or qty != 0 else "PASS",
                oracle="Receipt and full issue each one unit: endpoint-rounded cost; raw stock and its value zero after full consumption.",
                kind=kind, price_before=old_price, price_after=new_price,
                fixture=strings(fx), po_id=str(po), command_result=strings(result),
                observed=strings(observed), expected=strings(expected), mismatches=mismatch,
                raw_quantity=str(qty), movements=strings(movements), events=strings(events),
                confidence=snapshot.get("data_confidence"))


def guarded(cur, function):
    cur.execute("savepoint blind_money_case")
    try:
        result = function()
        cur.execute("release savepoint blind_money_case")
        return result
    except Exception as exc:
        # No expected refusal is defined for these valid-data money cases.
        # Refusals and any fixture/runtime problem therefore remain INCOMPLETE.
        cur.execute("rollback to savepoint blind_money_case")
        cur.execute("release savepoint blind_money_case")
        return dict(status="INCOMPLETE", error=str(exc),
                    primary_message=getattr(getattr(exc, "diag", None), "message_primary", None),
                    error_type=type(exc).__name__, traceback=traceback.format_exc())


def cases(cur, today):
    return [("BLIND-MONEY-CENT-"+kind+"-"+direction,
             lambda old=old, new=new, kind=kind: guarded(cur, lambda: money_rounding(cur,today,old,new,kind)))
            for kind in ("DIRECT", "INVOICE")
            for direction, old, new in (("UP", "10.005", "10.014"), ("DOWN", "10.014", "10.005"))]
