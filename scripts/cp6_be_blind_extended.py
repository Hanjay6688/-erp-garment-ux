"""Additional auditor oracles on the same frozen BE disposable runtime.

Existing fixture helpers only create prerequisites and call public commands;
all pass/fail conditions here are explicit auditor assertions.
"""
from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from copy import deepcopy

import psycopg

import cp6_av_probe as avp
import cp6_be_probe as be
import cp6_be_pocket_probe as pocket
import cp6_bd_probe as bd
import cp6_pocket_period_trial as native_pocket

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "be-blind-extended-results.json"


def one(cur, sql, *params):
    return cur.execute(sql, params).fetchone()[0]


def accessory(cur, day):
    f = be.fixture(cur, day)
    bc = bd.bcp
    acc = bc.fixture(cur, f["day"], stock_qty=100, cost="2.00")
    bc.policy(cur, "ACC_DEC04", {"OWN_FG_REPAIR_account_id": bc.account(cur, "5100")})
    bc.policy(cur, "ACC_DEC07", {"approval": "NONE"})
    bd.api.admin(cur)
    original_stock = bc.stock(cur, acc["material"], acc["main"])
    old_income = bd.gl(cur, "OTHER_INCOME")
    old_hpp = bd.lot_value(cur, f["lot"])
    posted = be.be(cur, "POST", dict(f["payload"], expected_returns=[
        {"material_id": acc["material"], "qty": "10", "holder": "Blind actual teardown"}]))
    dest, conv = posted["destination_lot_id"], posted["conversion_id"]
    base_cost = bd.lot_value(cur, dest)
    item = be.be(cur, "POST_USAGE", {
        "conversion_id": conv, "expected_version": one(cur, "select erp.be_conversion_revision_v1(%s)", conv),
        "location_id": acc["main"], "physical_at": f["payload"]["physical_at"],
        "items": [{"material_id": acc["material"], "qty": "6"}],
        "reason": "Blind six new components issued"})
    after_use = bc.stock(cur, acc["material"], acc["main"])
    assert original_stock == 100 and after_use == 94
    assert bd.lot_value(cur, dest) - base_cost == Decimal("12.00")
    assert bd.lot_value(cur, f["lot"]) == old_hpp
    outstanding = one(cur, "select outstanding_id from erp.be_conversion_returns_v1 where conversion_id=%s", conv)
    returned = bc.receive(cur, acc, "TEARDOWN", [(8, outstanding)], f["day"] + timedelta(days=1),
                          reference="Blind actual 8 of 10")
    return_lot = returned["lot_ids"][0]
    bc.inspect(cur, return_lot, bc.local_at(f["day"] + timedelta(days=1), 10),
               "Blind inspector", usable=6, damaged=2)
    state = bc.lot_state(cur, return_lot)
    progress = one(cur, "select erp.be_return_progress_v1(%s)", conv)
    assert len(progress) == 1 and progress[0]["expected"] == "10.000000"
    assert progress[0]["received"] == "8.000000" and progress[0]["unreturned"] == "2.000000"
    assert progress[0]["awaiting_value"] == "8.000000"
    assert state["usable"] == 6 and state["damaged"] == 2 and state["waiting"] == 0
    assert one(cur, "select erp.be_conversion_value_state_v1(%s)", conv) == "PROVISIONAL_RECOVERY"
    assert bd.gl(cur, "OTHER_INCOME") == old_income
    valuation = {"lot_id": return_lot, "condition": "USABLE", "qty": "2", "unit_value": "1.50",
                 "location_id": acc["main"],
                 "physical_at": bc.local_at(f["day"] + timedelta(days=1), 11),
                 "reason": "Blind sourced value for two recovered usable accessories"}
    before_recovery = bd.lot_value(cur, dest)
    try:
        with cur.connection.transaction():
            bc.svc(cur, "VALUE_CUSTODY", valuation)
    except psycopg.Error as error:
        assert "BC_POLICY_PENDING" in error.diag.message_primary, error.diag.message_primary
    else:
        raise AssertionError("Recovery value accepted without owner policy")
    bc.policy(cur, "ACC_DEC03", {"credit_account_id": bc.account(cur, "4100"),
                                 "unit_value_cap": "MOVING_AVERAGE"})
    recovery = bc.svc(cur, "VALUE_CUSTODY", valuation)
    assert bd.lot_value(cur, dest) - before_recovery == Decimal("-3.00")
    assert bd.gl(cur, "OTHER_INCOME") == old_income
    bc.reverse(cur, recovery["document_id"])
    assert bd.lot_value(cur, dest) == before_recovery
    assert bd.gl(cur, "OTHER_INCOME") == old_income
    remainder = one(cur, "select erp.be_return_progress_v1(%s)", conv)
    assert remainder[0]["unreturned"] == "2.000000" and remainder[0]["awaiting_value"] == "8.000000"
    return {"stock_before": original_stock, "stock_after_new_usage": after_use,
            "new_cost": "12.00", "returned": progress[0],
            "classified": {k: str(state[k]) for k in ("usable", "damaged", "waiting")},
            "no_synthetic_income": True, "document": item["cost_document_id"],
            "valuation_refused_until_policy": True,
            "recovery_credit": "3.00", "inverse_recovery_restored": True}


def accessory_scale(cur, day):
    physical_day = day - timedelta(days=4)
    bd.api.admin(cur)
    source_product = bd.sized_product(cur, bd.chain.base.SIZE, "BLIND-100-SOURCE-" + uuid.uuid4().hex[:8])
    target_product = bd.sized_product(cur, bd.chain.base.SIZE, "BLIND-100-TARGET-" + uuid.uuid4().hex[:8])
    opening = str(uuid.uuid4())
    cur.execute("""insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by)
        values(%s,%s,%s,'DRAFT',%s)""", (opening, "BLIND-100-" + opening, physical_day,
                                           bd.chain.base.OPERATOR_APP))
    cur.execute("""insert into erp.opening_balance_items(opening_id,balance_type,product_id,location_id,
        qty,unit_cost_snapshot,quality_grade,hpp_input_method)
        values(%s,'FINISHED_GOODS',%s,%s,100,1.00,'GRADE_A','MANUAL')""",
        (opening, source_product, bd.chain.base.LOCATION))
    bd.internal(cur, "post_opening_balance", opening)
    lot = one(cur, "select id from erp.fg_lots where product_id=%s and lot_origin='OPENING'", source_product)
    bc = bd.bcp
    acc = bc.fixture(cur, physical_day, stock_qty=200, cost="2.00")
    bc.policy(cur, "ACC_DEC04", {"OWN_FG_REPAIR_account_id": bc.account(cur, "5100")})
    bc.policy(cur, "ACC_DEC07", {"approval": "NONE"})
    bd.api.admin(cur)
    before_stock = bc.stock(cur, acc["material"], acc["main"])
    posting = be.be(cur, "POST", {"source_lot_id": str(lot),
        "target_product_id": target_product, "location_id": bd.chain.base.LOCATION,
        "qty_pcs": 100, "physical_at": bd.iso(bd.chain.production.at(physical_day + timedelta(days=1), 9)),
        "reason": "Blind actual hundred-piece relabel",
        "expected_version": one(cur, "select erp.be_source_revision_v1(%s,%s)", lot, bd.chain.base.LOCATION),
        "expected_returns": [{"material_id": acc["material"], "qty": "100",
                              "holder": "Blind teardown of hundred old tags"}]})
    conv, dest = posting["conversion_id"], posting["destination_lot_id"]
    before_value = bd.lot_value(cur, dest)
    be.be(cur, "POST_USAGE", {"conversion_id": conv,
        "expected_version": one(cur, "select erp.be_conversion_revision_v1(%s)", conv),
        "location_id": acc["main"],
        "physical_at": bd.iso(bd.chain.production.at(physical_day + timedelta(days=1), 10)),
        "items": [{"material_id": acc["material"], "qty": "100"}],
        "reason": "Blind actual replacement of hundred tags"})
    assert bc.stock(cur, acc["material"], acc["main"]) == before_stock - 100
    assert bd.lot_value(cur, dest) - before_value == Decimal("200.00")
    outstanding = one(cur, "select outstanding_id from erp.be_conversion_returns_v1 where conversion_id=%s", conv)
    old_income = bd.gl(cur, "OTHER_INCOME")
    returned = bc.receive(cur, acc, "TEARDOWN", [(80, outstanding)],
                          physical_day + timedelta(days=2), reference="Blind actual eighty returned")
    return_lot = returned["lot_ids"][0]
    bc.inspect(cur, return_lot, bc.local_at(physical_day + timedelta(days=2), 10),
               "Blind scale inspection", usable=60, damaged=20)
    state = bc.lot_state(cur, return_lot)
    progress = one(cur, "select erp.be_return_progress_v1(%s)", conv)
    assert progress[0]["expected"] == "100.000000"
    assert progress[0]["received"] == "80.000000"
    assert progress[0]["unreturned"] == "20.000000"
    assert progress[0]["awaiting_value"] == "80.000000"
    assert state["usable"] == 60 and state["damaged"] == 20
    assert bd.gl(cur, "OTHER_INCOME") == old_income
    return {"source_pcs": 100, "new_accessory_stock_delta": -100,
            "new_cost_once": "200.00", "old_received": 80, "usable": 60,
            "damaged": 20, "unreturned": 20, "awaiting_value": 80,
            "no_synthetic_income": True}


def nonpo_conversion(cur, day):
    economic = day - timedelta(days=3)
    bd.api.admin(cur)
    bd.boundary.historical.prior.set_open_period(cur, economic - timedelta(days=1))
    source_product = bd.sized_product(cur, bd.chain.base.SIZE, "BLIND-OPEN-" + uuid.uuid4().hex[:8])
    target_product = bd.sized_product(cur, bd.chain.base.SIZE, "BLIND-DEST-" + uuid.uuid4().hex[:8])
    opening = str(uuid.uuid4())
    cur.execute("""insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by)
        values(%s,%s,%s,'DRAFT',%s)""",
        (opening, "BLIND-OPEN-" + opening, economic, bd.chain.base.OPERATOR_APP))
    cur.execute("""insert into erp.opening_balance_items(opening_id,balance_type,product_id,location_id,
        qty,unit_cost_snapshot,quality_grade,hpp_input_method)
        values(%s,'FINISHED_GOODS',%s,%s,10,10.01,'GRADE_A','MANUAL')""",
        (opening, source_product, bd.chain.base.LOCATION))
    bd.internal(cur, "post_opening_balance", opening)
    lot = one(cur, "select id from erp.fg_lots where product_id=%s and lot_origin='OPENING'", source_product)
    source_initial = be.qty(cur, lot)
    payload = {"source_lot_id": str(lot), "target_product_id": target_product,
               "location_id": bd.chain.base.LOCATION, "qty_pcs": 6,
               "physical_at": bd.iso(bd.chain.production.at(economic + timedelta(days=1), 9)),
               "reason": "Blind non-PO opening lot relabel",
               "expected_version": one(cur, "select erp.be_source_revision_v1(%s,%s)", lot, bd.chain.base.LOCATION)}
    posted = be.be(cur, "POST", payload)
    dest = posted["destination_lot_id"]
    assert source_initial == 10 and (be.qty(cur, lot), be.qty(cur, dest)) == (4, 6)
    source_book = cur.execute("select * from erp.compute_non_po_product_hpp_book_v2620f(%s)",
                              (source_product,)).fetchone()
    target_book = cur.execute("select * from erp.compute_non_po_product_hpp_book_v2620f(%s)",
                              (target_product,)).fetchone()
    assert source_book[0] == Decimal("40.04") and target_book[0] == Decimal("60.06")
    assert bd.lot_value(cur, dest) == Decimal("60.06")
    be.be(cur, "REVERSE", {"conversion_id": posted["conversion_id"],
                           "reason": "Blind inverse non-PO source"})
    assert (be.qty(cur, lot), be.qty(cur, dest)) == (10, 0)
    return {"source_opening": "100.10", "remaining_qty": 4, "target_qty": 6,
            "source_book": str(source_book[0]), "target_book": str(target_book[0]),
            "inverse_restored": True}


def sold_child_recost(cur, day):
    f, bc = be.fixture(cur, day), bd.bcp
    acc = bc.fixture(cur, f["day"], stock_qty=100, cost="2.00")
    bc.policy(cur, "ACC_DEC04", {"OWN_FG_REPAIR_account_id": bc.account(cur, "5100")})
    bc.policy(cur, "ACC_DEC07", {"approval": "NONE"})
    bd.api.admin(cur)
    posted = be.be(cur, "POST", dict(f["payload"], expected_returns=[
        {"material_id": acc["material"], "qty": "3", "holder": "Blind recost holder"}]))
    parent, conv = posted["destination_lot_id"], posted["conversion_id"]
    be.be(cur, "POST_USAGE", {"conversion_id": conv,
        "expected_version": one(cur, "select erp.be_conversion_revision_v1(%s)", conv),
        "location_id": acc["main"], "physical_at": f["payload"]["physical_at"],
        "items": [{"material_id": acc["material"], "qty": "6"}],
        "reason": "Blind actual six new components"})
    target2 = bd.sized_product(cur, bd.chain.base.SIZE, "BLIND-CHILD-" + uuid.uuid4().hex[:8])
    child = be.be(cur, "POST", {"source_lot_id": parent, "target_product_id": target2,
        "location_id": f["location"], "qty_pcs": 2,
        "physical_at": bd.iso(bd.chain.production.at(f["day"], 16)),
        "reason": "Blind actual child conversion",
        "expected_version": one(cur, "select erp.be_source_revision_v1(%s,%s)", parent, f["location"])})["destination_lot_id"]
    bd.api.admin(cur)
    # The legacy sale fixture switches to authenticated and calls an internal
    # role introspection helper; this test-only grant rolls back with the case.
    if not one(cur, "select has_schema_privilege('authenticated','erp','USAGE')"):
        cur.execute("grant usage on schema erp to authenticated")
    sale1 = bd.sell(cur, f, f["target"], 1, 17)
    sale2 = bd.sell(cur, f, target2, 1, 18)
    snapshots = cur.execute("""select id,total_hpp from erp.sale_stock_allocations
        where sale_item_id in(select id from erp.sales_items where sale_id in(%s,%s)) order by id""",
        (sale1, sale2)).fetchall()
    gl = lambda: {k: bd.gl(cur, k) for k in ("FG_INVENTORY", "COGS", "OTHER_INCOME")}
    before, parent_value, child_value = gl(), bd.lot_value(cur, parent), bd.lot_value(cur, child)
    trial = bd.bbp.receipt_trial
    invoice = trial.post_invoice(bd.api, cur, trial.invoice(bd.api, cur, day,
        {"supplier_id": acc["supplier"], "purchase_item_id": acc["item"]},
        "100", "3.00", date=f["day"] + timedelta(days=1)))
    bd.api.admin(cur)
    after_invoice = gl()
    assert {k: after_invoice[k] - before[k] for k in ("FG_INVENTORY", "COGS")} == {
        "FG_INVENTORY": Decimal("4.00"), "COGS": Decimal("2.00")}
    assert bd.lot_value(cur, parent) - parent_value == Decimal("6.00")
    assert bd.lot_value(cur, child) - child_value == Decimal("2.00")
    outstanding = one(cur, "select outstanding_id from erp.be_conversion_returns_v1 where conversion_id=%s", conv)
    returned = bc.receive(cur, acc, "TEARDOWN", [(2, outstanding)],
                          f["day"] + timedelta(days=1), reference="Blind recovered two")
    lot = returned["lot_ids"][0]
    bc.inspect(cur, lot, bc.local_at(f["day"] + timedelta(days=1), 10), "Blind inspect", usable=2)
    bc.policy(cur, "ACC_DEC03", {"credit_account_id": bc.account(cur, "4100"),
                                  "unit_value_cap": "MOVING_AVERAGE"})
    recovered = bc.svc(cur, "VALUE_CUSTODY", {"lot_id": lot, "condition": "USABLE",
        "qty": "2", "unit_value": "1.50", "location_id": acc["main"],
        "physical_at": bc.local_at(f["day"] + timedelta(days=1), 11),
        "reason": "Blind sourced two old accessories"})
    after_recovery = gl()
    assert {k: after_recovery[k] - after_invoice[k] for k in ("FG_INVENTORY", "COGS")} == {
        "FG_INVENTORY": Decimal("-2.00"), "COGS": Decimal("-1.00")}
    assert after_recovery["OTHER_INCOME"] == before["OTHER_INCOME"]
    assert snapshots == cur.execute("""select id,total_hpp from erp.sale_stock_allocations
        where sale_item_id in(select id from erp.sales_items where sale_id in(%s,%s)) order by id""",
        (sale1, sale2)).fetchall()
    bc.reverse(cur, recovered["document_id"])
    assert gl() == after_invoice
    trial.rpc(bd.api, cur, "reverse_material_supplier_invoice_v2",
              invoice["supplier_invoice_id"], "Blind invoice inverse", uuid.uuid4(), invoice["row_version"])
    bd.api.admin(cur)
    assert gl() == before and (bd.lot_value(cur, parent), bd.lot_value(cur, child)) == (parent_value, child_value)
    return {"invoice_fg": "4.00", "invoice_cogs": "2.00", "parent_recost": "6.00",
            "child_recost": "2.00", "recovery_fg": "-2.00", "recovery_cogs": "-1.00",
            "snapshots_immutable": True, "both_inverses_restored": True}


def rework(cur, day):
    f = avp.rework_ready(cur, day - timedelta(days=1))
    bd.api.admin(cur)
    old = cur.execute("select vendor_id,physical_sent_at,return_fg_location_id from erp.rework_orders where id=%s",
                      (f["order"],)).fetchone()
    bd.chain.bs_action(cur, "SAVE_REWORK", {"id": f["order"], "action": "CANCEL",
                          "change_reason": "Blind replace draft"}, bd.chain.version(cur, "rework_orders", f["order"]))
    bd.api.admin(cur)
    target = bd.sized_product(cur, bd.chain.base.SIZE, "BLIND-REWORK-" + uuid.uuid4().hex[:8])
    bom = one(cur, "select id from erp.accessory_bom_versions where product_id=%s and is_active", f["product"])
    order = {"rework_number": "BE-BLIND-" + uuid.uuid4().hex[:15], "bs_case_id": str(f["bs"]),
             "destination_type": "LAUNDRY", "contractor_id": None, "vendor_id": str(old[0]),
             "qty_sent": 4, "physical_sent_at": old[1].isoformat(), "status": "IN_PROGRESS",
             "return_fg_location_id": str(old[2]), "accessory_bom_version_id": str(bom),
             "accessory_bom_item_ids": [], "components": []}
    wrong_size = str(uuid.uuid4())
    cur.execute("insert into erp.sizes(id,size_code,sort_order,is_active) values(%s,%s,99,true)",
                (wrong_size, "BLIND-" + wrong_size[:8]))
    incompatible = bd.sized_product(cur, wrong_size, "BLIND-WRONG-" + uuid.uuid4().hex[:8])
    try:
        with cur.connection.transaction():
            be.be(cur, "SAVE_REWORK", {"order": order, "target_product_id": incompatible,
                                        "reason": "Blind wrong-size target must fail"})
    except psycopg.Error as error:
        assert "BE_DIMENSION_MISMATCH" in error.diag.message_primary, error.diag.message_primary
    else:
        raise AssertionError("Wrong-size rework target was accepted")
    assert one(cur, "select count(*) from erp.rework_orders where rework_number=%s",
               order["rework_number"]) == 0
    wrong_model = str(uuid.uuid4())
    cur.execute("insert into erp.product_models(id,model_code,model_name) values(%s,%s,%s)",
                (wrong_model, "BLIND-" + wrong_model[:8], "Blind incompatible construction"))
    incompatible_model = str(uuid.uuid4())
    cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,
        product_name,identity_root_id,effective_from,is_active,is_portal_visible)
        select %s,%s,%s,brand_id,%s,size_id,%s,%s,effective_from,true,true
        from erp.products where id=%s""", (incompatible_model,
        "BLIND-MODEL-" + incompatible_model[:8], wrong_model,
        "Blind construction", "Blind incompatible construction", incompatible_model, f["product"]))
    try:
        with cur.connection.transaction():
            be.be(cur, "SAVE_REWORK", {"order": order, "target_product_id": incompatible_model,
                                        "reason": "Blind wrong-model target must fail"})
    except psycopg.Error as error:
        assert "BE_DIMENSION_MISMATCH" in error.diag.message_primary, error.diag.message_primary
    else:
        raise AssertionError("Wrong-model rework target was accepted")
    assert one(cur, "select count(*) from erp.rework_orders where rework_number=%s",
               order["rework_number"]) == 0
    made = be.be(cur, "SAVE_REWORK", {"order": order, "target_product_id": target,
                                        "reason": "Blind same-construction target"})
    rid = made["rework_id"]
    bd.chain.bs_action(cur, "SAVE_REWORK", {"id": rid, "action": "SAVE",
         "qty_good_returned": 1, "qty_bs_returned": 0,
         "return_fg_location_id": str(old[2]), "change_reason": "Blind partial physical return"},
         bd.chain.version(cur, "rework_orders", rid))
    bd.api.admin(cur)
    partial = cur.execute("select status,good_fg_lot_id from erp.rework_orders where id=%s", (rid,)).fetchone()
    assert partial[0] == "PARTIAL" and partial[1] is None
    assert one(cur, "select count(*) from erp.be_conversion_sources_v1 where rework_id=%s", rid) == 0
    payload = {"rework_order_id": rid, "qty_good": 2, "qty_bs": 2,
               "completed_at": bd.iso(bd.chain.production.at(f["day"], 16)),
               "return_fg_location_id": str(old[2]), "change_reason": "Blind final 2 GOOD and 2 BS"}
    version, key = bd.chain.version(cur, "rework_orders", rid), str(uuid.uuid4())
    first = bd.chain.bs_action(cur, "COMPLETE_REWORK", payload, version, key=key)
    second = bd.chain.bs_action(cur, "COMPLETE_REWORK", payload, version, key=key)
    assert first.get("result") == second.get("result"), (first, second)
    bd.api.admin(cur)
    source = one(cur, "select good_fg_lot_id from erp.rework_orders where id=%s", rid)
    destinations = cur.execute("""select a.destination_lot_id from erp.be_conversion_sources_v1 s
        join erp.product_conversion_allocations a on a.conversion_id=s.conversion_id
        where s.rework_id=%s""", (rid,)).fetchall()
    assert len(destinations) == 1
    dest = destinations[0][0]
    assert be.qty(cur, source) == 0 and be.qty(cur, dest) == 2
    assert str(one(cur, "select product_id from erp.fg_lots where id=%s", dest)) == target
    bd.chain.bs_action(cur, "REVERSE_REWORK_COMPLETION", {
        "rework_order_id": rid, "change_reason": "Blind inverse real rework"},
        bd.chain.version(cur, "rework_orders", rid))
    bd.api.admin(cur)
    assert be.qty(cur, source) == 0 and be.qty(cur, dest) == 0
    return {"partial": partial[0], "partial_fg": 0, "good_target": 2, "bs": 2,
            "source_shadow_good": 0, "replay_same": True, "inverse_zero": True,
            "wrong_size_refused_without_order": True,
            "wrong_model_refused_without_order": True}


def zero_redye(cur, day):
    f = be.redye_fixture(cur, day, known=False)
    pending = one(cur, "select erp.be_redye_rate_v1(%s)", f["redye"])
    blocker = one(cur, "select count(*) from erp.period_blockers_v1(%s,%s) where code='BE_REDYE_PRICE_UNKNOWN'",
                  f["day"], f["day"])
    assert pending is None and blocker == 1
    payload = {"service_id": f["redye"], "rate": "0.00", "reason": "Blind owner explicitly approves zero"}
    key = str(uuid.uuid4())
    first = bd.bd(cur, "SET_REDYE_PRICE", payload, key)
    again = bd.bd(cur, "SET_REDYE_PRICE", payload, key)
    assert (again.get("replayed") is True and
            {k: v for k, v in again.items() if k != "replayed"} == first), (first, again)
    rate = one(cur, "select erp.be_redye_rate_v1(%s)", f["redye"])
    remaining = one(cur, "select count(*) from erp.period_blockers_v1(%s,%s) where code='BE_REDYE_PRICE_UNKNOWN'",
                    f["day"], f["day"])
    assert rate == 0 and one(cur, "select erp.be_redye_cost_v1(%s)", f["redye"]) == 0 and remaining == 0
    assert one(cur, "select count(*) from erp.be_redye_price_events_v1 where service_id=%s", f["redye"]) == 1
    return {"unknown": None, "blocked_before": blocker, "explicit_zero_event": True,
            "cost": "0.00", "blockers_after": remaining, "replay_same": True}


def later_rate_redye(cur, day):
    f = be.redye_fixture(cur, day, known=True)
    original = cur.execute("""select rate_version_id,initial_rate,wash_process_id,sent_at
        from erp.be_redye_services_v1 where id=%s""", (f["redye"],)).fetchone()
    assert original[0] is not None and original[1] == Decimal("50.00")
    before = (one(cur, "select erp.be_redye_rate_v1(%s)", f["redye"]),
              one(cur, "select erp.be_redye_cost_v1(%s)", f["redye"]),
              bd.lot_value(cur, f["dest"]))
    assert before[:2] == (Decimal("50.00"), Decimal("200.00"))
    later = bd.chain.production.at(f["day"] + timedelta(days=1), 13)
    assert later > original[3]
    bd.process_rate(cur, {"vendor": f["vendor"], "process": str(original[2]), "start": later},
                    "75.00")
    frozen = cur.execute("""select rate_version_id,initial_rate from erp.be_redye_services_v1
        where id=%s""", (f["redye"],)).fetchone()
    after = (one(cur, "select erp.be_redye_rate_v1(%s)", f["redye"]),
             one(cur, "select erp.be_redye_cost_v1(%s)", f["redye"]),
             bd.lot_value(cur, f["dest"]))
    assert frozen == original[:2] and after == before, (original, frozen, before, after)
    return {"sent_rate": str(before[0]), "later_rate": "75.00",
            "cost_and_lot_unchanged": True, "rate_version_unchanged": True}


def paid_redye(cur, day):
    f = be.redye_fixture(cur, day, known=True)
    bd.invoice_policies(cur, after="CORRECTION_DOCUMENT")
    bd.api.admin(cur)
    sale = bd.sell(cur, f, f["target"], 1, 17)
    sale_snapshot = one(cur, """select sum(total_hpp) from erp.sale_stock_allocations
        where sale_item_id in(select id from erp.sales_items where sale_id=%s)""", sale)
    before = {k: bd.gl(cur, k) for k in ("FG_INVENTORY", "COGS")}
    payable = Decimal(str(bd.ap(cur, f["vendor"])))
    draft = bd.bd(cur, "SAVE_INVOICE_DRAFT", {
        "vendor_id": f["vendor"], "invoice_number": "BLIND-REDYE-" + uuid.uuid4().hex[:10],
        "invoice_date": str(f["day"]), "header_total": "240.00",
        "lines": [{"line_kind": "BILL", "rework_service_id": f["redye"],
                   "category": "GOOD", "qty": 4, "amount": "240.00"}]})
    posted = bd.post_draft(cur, draft)
    assert posted["status"] == "POSTED"
    delta = {k: bd.gl(cur, k) - v for k, v in before.items()}
    assert delta == {"FG_INVENTORY": Decimal("30.00"), "COGS": Decimal("10.00")}, delta
    assert Decimal(str(bd.ap(cur, f["vendor"]))) - payable == 240
    assert one(cur, "select erp.be_redye_cost_v1(%s)", f["redye"]) == 240
    assert one(cur, "select erp.be_redye_accrual_v1(%s)", f["po"]) == 0
    assert one(cur, """select sum(total_hpp) from erp.sale_stock_allocations
        where sale_item_id in(select id from erp.sales_items where sale_id=%s)""", sale) == sale_snapshot
    repeat = bd.bd(cur, "SAVE_INVOICE_DRAFT", {
        "vendor_id": f["vendor"], "invoice_number": "BLIND-OVER-" + uuid.uuid4().hex[:10],
        "invoice_date": str(f["day"]), "header_total": "240.00",
        "lines": [{"line_kind": "BILL", "rework_service_id": f["redye"],
                   "category": "GOOD", "qty": 4, "amount": "240.00"}]})
    try:
        with cur.connection.transaction():
            bd.post_draft(cur, repeat)
    except psycopg.Error as error:
        refusal = error.diag.message_primary
    else:
        refusal = "accepted"
    assert "BD_INVOICE_CAPACITY" in refusal, refusal
    return {"invoice": "240.00", "ap_delta": "240.00",
            "fg_delta": str(delta["FG_INVENTORY"]), "cogs_delta": str(delta["COGS"]),
            "accrual_left": "0.00", "sale_snapshot_immutable": True,
            "second_invoice_refused": refusal}


def afui_mix(cur, day):
    cut = day - timedelta(days=10)
    historical = bd.bbp.production_post(cur, day, pocket.active_unit(cur, pocket.rows(cut)))
    fresh = native_pocket.fixture(bd.api, cur, day, special=True)
    bd.api.admin(cur)
    start, end = cut - timedelta(days=1), fresh["end"]
    bd.boundary.historical.prior.set_open_period(cur, start)
    before = {k: bd.gl(cur, k) for k in ("WIP", "FG_INVENTORY", "COGS", "OTHER_EXPENSE")}
    physical = (one(cur, "select count(*) from erp.material_stock_movements"),
                one(cur, "select count(*) from erp.sewing_terminal_events"))
    preview = pocket.preview(cur, start, end)
    assert (preview["quantity"], preview["amount"], preview["per_piece"]) == ("20", "22.50", "1.125000"), preview
    made = pocket.call(cur, "POST_PERIOD", {"period_start": str(start), "period_end": str(end),
             "expected_revision": preview["revision"], "reason": "Blind mixed native and historical including Afui"})
    pool = made["id"]
    kinds = cur.execute("""select adjustment_id is not null,historical_usage_id is not null,count(*)
        from erp.pocket_period_sources where pool_id=%s group by 1,2 order by 1,2""", (pool,)).fetchall()
    assert kinds == [(False, True, 1), (True, False, 1)]
    special = one(cur, """select count(*) from erp.pocket_period_destinations d
        join erp.contractor_hpp_policy_versions h on h.contractor_id=d.contractor_id
        join erp.contractors c on c.id=h.contractor_id where d.pool_id=%s and d.event_id is not null
        and h.is_special and not c.attendance_required and h.effective_from<=%s
        and (h.effective_to is null or h.effective_to>=%s)""", pool, end, end)
    assert special >= 1
    actual = {k: bd.gl(cur, k) - v for k, v in before.items()}
    assert actual == {"WIP": Decimal("11.24"), "FG_INVENTORY": Decimal("6.76"),
                      "COGS": Decimal("4.50"), "OTHER_EXPENSE": Decimal("-22.50")}
    revision = one(cur, "select erp.pocket_period_state_v1(%s)", pool)["revision"]
    pocket.call(cur, "CANCEL_PERIOD", {"id": pool, "expected_revision": revision,
                                        "reason": "Blind mixed period inverse"})
    assert {k: bd.gl(cur, k) for k in before} == before
    assert physical == (one(cur, "select count(*) from erp.material_stock_movements"),
                        one(cur, "select count(*) from erp.sewing_terminal_events"))
    return {"historical_batch": historical["batch"], "source_kinds": [list(x) for x in kinds],
            "afui_destinations": special, "allocation": {k: str(v) for k, v in actual.items()},
            "inverse_exact": True, "no_second_physical_events": True}


def pocket_import(cur, day):
    cut = day - timedelta(days=20)
    rows = pocket.active_unit(cur, pocket.rows(cut))
    pending = {kind: rows.pop(kind) for kind in ("OPENING_POCKET_USAGE", "OPENING_POCKET_SEWING")}
    before = (one(cur, "select count(*) from erp.journal_entries"),
              one(cur, "select count(*) from erp.material_stock_movements"),
              one(cur, "select count(*) from erp.sewing_terminal_events"))
    draft = bd.bbp.production_post(cur, day, rows, cutover_days=20, expect=True)
    assert not draft["errors"]
    batch, code = draft["batch"], draft["code"]
    fill = lambda value: value.replace("{C}", code) if isinstance(value, str) else value
    for kind, records in pending.items():
        bd.api.upload(cur, batch, kind, [{k: fill(v) for k, v in row.items()} for row in records])
    checked = bd.api.invoke(cur, "VALIDATE", batch)
    after_validate = (one(cur, "select count(*) from erp.journal_entries"),
                      one(cur, "select count(*) from erp.material_stock_movements"),
                      one(cur, "select count(*) from erp.sewing_terminal_events"))
    assert checked["error_rows"] == 0 and before == after_validate, (checked, before, after_validate)
    revision = bd.api.read(cur, batch)["batch"]["revision"]
    payload = {"batch_id": batch, "expected_revision": revision}
    key = str(uuid.uuid4())
    posted = bd.api.call(cur, "FINALIZE", payload, key)
    replay = bd.api.call(cur, "FINALIZE", payload, key)
    assert posted == replay and posted["status"] == "POSTED"
    bd.api.admin(cur)
    usage = one(cur, "select count(*) from erp.be_pocket_usage_v1 where batch_id=%s", batch)
    sewing = one(cur, "select count(*) from erp.be_pocket_sewing_v1 where batch_id=%s", batch)
    source_amount = one(cur, "select sum(original_amount) from erp.be_pocket_usage_v1 where batch_id=%s", batch)
    denominator = one(cur, "select sum(qty) from erp.be_pocket_sewing_v1 where batch_id=%s", batch)
    after = (one(cur, "select count(*) from erp.material_stock_movements"),
             one(cur, "select count(*) from erp.sewing_terminal_events"))
    assert (usage, sewing, source_amount, denominator) == (1, 3, Decimal("11.25"), 10)
    assert after == before[1:], (before, after)
    return {"draft_and_validate_without_facts": True, "usage_rows": usage,
            "sewing_rows": sewing, "source_amount": str(source_amount),
            "denominator": denominator, "finalize_replay_same": True,
            "no_fake_material_or_sewing_events": True}


def closed_pocket_correction(cur, day):
    cut = day - timedelta(days=10)
    f = bd.bbp.production_post(cur, day, pocket.active_unit(cur, pocket.rows(cut)))
    preview = pocket.preview(cur, cut - timedelta(days=1), cut)
    pool = pocket.call(cur, "POST_PERIOD", {"period_start": preview["period_start"],
        "period_end": preview["period_end"], "expected_revision": preview["revision"],
        "reason": "Blind period before business close"})["id"]
    usage = one(cur, "select id from erp.be_pocket_usage_v1 where batch_id=%s", f["batch"])
    old = pocket.amounts(cur)
    prior = cur.execute("""select l.account_id,sum(l.debit-l.credit) from erp.journal_lines l
        join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and j.transaction_date<=%s
        group by l.account_id order by l.account_id""", (day - timedelta(days=1),)).fetchall()
    historical = cur.execute("select id,to_jsonb(j) from erp.journal_entries j order by id").fetchall()
    bd.boundary.historical.prior.set_open_period(cur, day - timedelta(days=1))
    key = str(uuid.uuid4())
    payload = {"usage_id": str(usage), "amount": "15.00", "expected_amount": "11.25",
        "economic_date": str(cut + timedelta(days=1)),
        "reason": "Blind late correction from closed source"}
    first = pocket.call(cur, "CORRECT_OPENING_USAGE", payload, key)
    again = pocket.call(cur, "CORRECT_OPENING_USAGE", payload, key)
    assert first == again
    now = pocket.amounts(cur)
    delta = {k: now[k] - v for k, v in old.items()}
    assert delta == {"WIP": Decimal("1.88"), "FG_INVENTORY": Decimal("1.12"),
        "COGS": Decimal("0.75"), "OTHER_EXPENSE": Decimal("0.00"),
        "OPENING_EQUITY": Decimal("-3.75")}, delta
    dates = cur.execute("""select j.economic_date,j.transaction_date from erp.journal_entries j
        where j.id in(select journal_id from erp.be_pocket_source_events_v1 where id=%s
            union select journal_entry_id from erp.pocket_period_events
            where pool_id=%s and kind='RECOST') order by j.id""", (key, pool)).fetchall()
    assert len(dates) == 2 and all(x == (cut + timedelta(days=1), day) for x in dates), dates
    old_asof = cur.execute("""select l.account_id,sum(l.debit-l.credit) from erp.journal_lines l
        join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and j.transaction_date<=%s
        group by l.account_id order by l.account_id""", (day - timedelta(days=1),)).fetchall()
    assert prior == old_asof
    immutable = cur.execute("select id,to_jsonb(j) from erp.journal_entries j where id=any(%s::uuid[]) order by id",
                            ([str(x[0]) for x in historical],)).fetchall()
    assert historical == immutable
    pocket.call(cur, "CORRECT_OPENING_USAGE", dict(payload, amount="11.25", expected_amount="15.00",
        economic_date=str(cut + timedelta(days=2)), reason="Blind linked inverse after close"))
    assert pocket.amounts(cur) == old
    return {"replay_same": True, "economic_date": str(cut + timedelta(days=1)),
            "journal_date": str(day), "old_asof_immutable": True, "old_journals_immutable": True,
            "delta": {k: str(v) for k, v in delta.items()}, "inverse_restored": True}


def pocket_import_refusals(cur, day):
    cut = day - timedelta(days=10)
    template = pocket.active_unit(cur, pocket.rows(cut))
    checks = (
        ("missing_document", lambda r: r["OPENING_POCKET_USAGE"][0].update(document_number=""), "BE_POCKET_PROVENANCE"),
        ("missing_prior_reference", lambda r: r["OPENING_POCKET_USAGE"][0].update(allocation_status="ALLOCATED"), "BE_POCKET_PRIOR_ALLOCATION"),
        ("future_history", lambda r: r["OPENING_POCKET_USAGE"][0].update(physical_date=str(cut)), "BE_POCKET_DATE"),
        ("incomplete_numerator", lambda r: r["OPENING_POCKET_USAGE"][0].update(control_amount="12.00"), "BE_POCKET_CONTROL"),
        ("incomplete_denominator", lambda r: r["OPENING_POCKET_SEWING"].pop(), "BE_POCKET_DENOMINATOR_INCOMPLETE"),
        ("fractional_piece", lambda r: r["OPENING_POCKET_SEWING"][0].update(qty="4.5"), "BE_POCKET_SEWING_PCS"),
        ("missing_target", lambda r: r["OPENING_POCKET_SEWING"][0].update(target_source_key="ABSENT"), "BE_POCKET_TARGET_SOURCE_REQUIRED"),
    )
    observed = {}
    for label, edit, expected in checks:
        rows = deepcopy(template)
        edit(rows)
        before = one(cur, "select count(*) from erp.journal_entries")
        bd.api.admin(cur)
        cur.execute("savepoint blind_import_bad_file")
        try:
            result = bd.bbp.production_post(cur, day, rows, expect=True)
            assert expected in str(result["errors"]), (label, expected, result["errors"])
            assert one(cur, "select count(*) from erp.journal_entries") == before, label
            observed[label] = expected
        finally:
            bd.api.admin(cur)
            cur.execute("rollback to savepoint blind_import_bad_file")
            cur.execute("release savepoint blind_import_bad_file")
    return {"refused": observed, "draft_failures_no_ledger": True}


def main():
    report = {"candidate": "2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b",
              "status": "INCOMPLETE", "production_go": False, "cases": {}}
    with psycopg.connect(os.environ["PGURL"].replace("//postgres:", "//supabase_admin:", 1)) as conn, conn.cursor() as cur:
        day = one(cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date")
        if one(cur, "select count(*) from erp.app_users") == 0:
            if not one(cur, "select has_schema_privilege('authenticated','erp','USAGE')"):
                cur.execute("grant usage on schema erp to authenticated")
            bd.api.seed(cur)
        bd.boundary.historical.prior.set_open_period(cur, day - timedelta(days=30))
        for name, case in (("B02_B03_ACCESSORY", accessory), ("B02_SCALE_100", accessory_scale),
                           ("B03_NONPO_OPENING", nonpo_conversion),
                           ("B03_SOLD_CHILD_RECOST", sold_child_recost),
                           ("B04_REWORK", rework),
                           ("B05_SMALL_REDYE", paid_redye), ("B06_EXPLICIT_ZERO", zero_redye),
                           ("B06_LATER_RATE", later_rate_redye),
                           ("B08_AFUI_MIX", afui_mix), ("B08_CLOSED_CORRECTION", closed_pocket_correction),
                           ("B09_POCKET_IMPORT", pocket_import),
                           ("B09_IMPORT_NEGATIVES", pocket_import_refusals)):
            bd.api.admin(cur)
            cur.execute("savepoint blind_extended_case")
            try:
                value = case(cur, day)
                report["cases"][name] = {"status": "PASS", **value}
            except Exception as error:
                report["cases"][name] = {"status": "INCOMPLETE", "error": str(error),
                                          "kind": type(error).__name__, "traceback": traceback.format_exc()[-3000:]}
            finally:
                cur.execute("rollback to savepoint blind_extended_case")
                cur.execute("release savepoint blind_extended_case")
                OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
                print(json.dumps({"case": name, **report["cases"][name]}, default=str), flush=True)
    report["status"] = "PASS" if all(c["status"] == "PASS" for c in report["cases"].values()) else "INCOMPLETE"
    OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
    assert report["status"] == "PASS", report


if __name__ == "__main__":
    main()
