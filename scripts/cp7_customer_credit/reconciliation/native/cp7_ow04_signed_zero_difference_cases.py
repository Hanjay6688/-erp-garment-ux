"""UNEXECUTED fifth Native source case, separate from the frozen four cases.

No import/registration connects, installs, commits, or executes SQL. The closed
Native harness owns the supplied cursor, transaction and rollback boundary.
All business documents use existing public APIs. Disposable master/period setup
is inherited from the already inspected Native helpers and remains labelled.
"""
from datetime import datetime, timedelta
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import copy
import json
import uuid

import cp7_ow04_signed_source_cases as signed

initial, native = signed.initial, signed.native
b, cmd = native.b, native.cmd
EXPECTED_SHA = "0eaa6829643dc5675c4d854a75ea855486bc78db6d8aa54c2d09d803945c2a7a"
CASE_ID = "OW04_SIGNED_ZERO_DIFF_EARLIER_ZERO_RETURN_REVERSE"
FINANCIAL_TABLES = (
    "recognition_plans", "recognition_components", "component_parts", "component_journals",
    "consumption_events", "financial_materializations", "financial_materialization_objects",
)


def expected():
    raw = Path(__file__).with_name("ZERO_DIFF_EXPECTED.json").read_bytes()
    assert sha256(raw).hexdigest() == EXPECTED_SHA, "OW04_SIGNED_ZERO_DIFF_FROZEN_EXPECTED_CHANGED"
    result = json.loads(raw)
    assert result["id"] == CASE_ID and result["case_count"] == 1
    assert result["native_executed"] is False and result["production_go"] is False
    assert result["preserved_four_case_expected_sha256"] == signed.EXPECTED_SHA
    return result


def _rows(cur, table, predicate="true", args=()):
    return native._array(cur, "cp7_credit." + table, predicate, args)


def _ordinary_zero_return(cur, x):
    """Real ordinary RETURN; no fake funding, return, journal or family rows."""
    f = x["f"]
    payload, version = native.returns.payload(cur, f, qty="1", refund="0.00", destination=f["destination"])
    # Explicit physical input on D1 after the actual D1 payment, not a journal
    # clock override. Native retains its own business/book date rules.
    payload["physical_at"] = (datetime.fromisoformat(x["physical"]["payment"]) + timedelta(hours=1)).isoformat()
    payload["notes"] = "Earlier genuine one-piece physical return with explicit refund zero"
    assert datetime.fromisoformat(payload["physical_at"]).date().isoformat() == x["dates"]["D1"]
    request = uuid.uuid4()
    before_accounts = cmd.accounts(cur)
    result = cmd.command(cur, "RETURN", payload, version, request)
    signed._assert_request(cur, "RETURN", payload, version, request, result)
    returned = result["return_id"]
    assert result["return_status"] == "POSTED"
    family = _rows(cur, "return_families", "first_return_id=%s", (returned,))["document"]
    assert len(family) == 1 and str(family[0]["family_ordinal"]) == "1"
    assert _rows(cur, "cohorts", "family_id=%s", (family[0]["id"],))["document"] == []
    assert cur.execute("select coalesce(sum(ri.refund_amount),0)from erp.sales_return_items ri where ri.return_id=%s",
                       (returned,)).fetchone() == (D("0.00"),)
    journals = cur.execute("select id::text from erp.journal_entries where source_type='SALES_RETURN'"
                           "and source_id=%s and reversal_of_id is null", (returned,)).fetchall()
    assert len(journals) == 1
    journal = initial._journal_matches(cur, journals[0][0], "SALES_RETURN", returned,
        (x["dates"]["D1"], x["dates"]["D1"]),
        ((cmd.mapping(cur, "FG_INVENTORY"), D("10.00")), (cmd.mapping(cur, "COGS"), D("-10.00"))), f["customer"])
    assert len(journal["document"]["lines"]) == 2
    assert cmd.delta(before_accounts, cmd.accounts(cur)) == {
        cmd.mapping(cur, "FG_INVENTORY"): D("10.00"), cmd.mapping(cur, "COGS"): D("-10.00")}
    assert cur.execute("select sum(qty_signed),sum(qty_signed*unit_hpp_snapshot)from erp.fg_stock_movements where lot_id=%s",
                       (f["lot"],)).fetchone() == (6, D("60.00"))
    items = native._array(cur, "erp.sales_return_items", "return_id=%s", (returned,))
    assert len(items["document"]) == 1
    movements = native._array(cur, "erp.fg_stock_movements", "source_type='SALES_RETURN_ITEM'and source_id=%s",
                              (items["document"][0]["id"],))
    assert len(movements["document"]) == 1
    move = movements["document"][0]
    assert (D(str(move["qty_signed"])), D(str(move["unit_hpp_snapshot"])), move["reversal_of_id"]) == (D("1"), D("10.00"), None)
    cur.execute("set constraints all immediate")
    cur.execute("set constraints all deferred")
    return dict(result=result, request_id=str(request), payload=payload, version=version,
                family=family[0], journal=journal, items=items, movement=move)


def _setup(cur, today, gold):
    initial._require_installed(cur)
    x = native.prepared(cur, today, "1000.00", "OPEN")
    earlier = _ordinary_zero_return(cur, x)
    # The earlier return changed the real review token/version. Read the
    # existing public ordinary intent again before the public quote/settle path.
    x["return_payload"], x["return_version"] = native.return_intent(cur, x)
    credit = initial._credit_master(cur)
    initial_gold = next(row for row in initial.expected()["cases"] if row["id"] == "OW04_INITIAL_1000_OPEN_CREDIT")
    query = initial._input(x, initial_gold, credit)
    before_quote = signed._observe(cur, x)
    quote = native.call_quote(cur, query)
    assert signed._observe(cur, x) == before_quote, "OW04_SIGNED_ZERO_DIFF_QUOTE_WROTE"
    # Its financial/public quote expectation is unchanged: prior refund0 does
    # not change gross/net/P/I; source-derived prior floor remains SALE D0.
    initial._assert_quote(cur, quote, query, x, initial_gold, credit)
    envelope = initial._envelope(query, quote)
    request = uuid.uuid4()
    before_accounts = cmd.accounts(cur)
    result = initial._settle(cur, envelope, request)
    # The original initial helper hardcodes ordinal1 and stock6. Keep it intact;
    # this fixture asserts its independently frozen ordinal2/stock7 contract.
    assert (result["contract_version"], result["kind"], result["action"], result["request_id"],
            result["sale_id"], result["return_status"], result["family_ordinal"], result["production_go"]) == (
        "cp7.sales-return-settlement-outcome.v1", "COMMITTED_OUTCOME", "RETURN_SETTLEMENT", str(request),
        x["f"]["sale"], "POSTED", "2", False)
    initial._uuid(result["return_id"])
    initial._uuid(result["credit_id"])
    assert result["refund_event_id"] is None
    assert result["quote_sha256"] == quote["binding"]["quote_sha256"] == envelope["document"]["quote_sha256"]
    assert result["projection_sha256"] == quote["binding"]["projection_sha256"]
    for key in ("quote_sha256", "projection_sha256", "actual_manifest_sha256", "projection_actual_proof_sha256"):
        initial._sha(result[key])
    families = _rows(cur, "return_families", "family_root_sale_id=%s", (x["f"]["sale"],))["document"]
    assert sorted((str(row["family_ordinal"]), row["first_return_id"]) for row in families) == [
        ("1", earlier["result"]["return_id"]), ("2", result["return_id"])]
    later_family = next(row for row in families if row["first_return_id"] == result["return_id"])
    cohorts = _rows(cur, "cohorts", "family_id=%s", (later_family["id"],))["document"]
    assert len(cohorts) == 1
    cohort = cohorts[0]
    assert (cohort["id"], cohort["source_return_id"], cohort["initial_mode"], D(str(cohort["initial_net_amount"]))) == (
        result["credit_id"], result["return_id"], "CREDIT", D("200.00"))
    plans = _rows(cur, "recognition_plans", "cohort_id=%s", (cohort["id"],))["document"]
    assert len(plans) == 1
    plan = plans[0]
    assert (plan["id"], plan["plan_kind"], D(str(plan["net_amount"])), plan["expected_component_count"], plan["expected_part_count"]) == (
        cohort["initial_plan_id"], "INITIAL", D("200.00"), 1, 1)
    # This is genuine old support, not a fabricated empty-family prefix.
    assert any(event["id"] == "journal:" + earlier["journal"]["document"]["header"]["id"]
               and D(str(event["amount"])) == D("0.00") for event in plan["before_events"])
    component = _rows(cur, "recognition_components", "plan_id=%s", (plan["id"],))["document"]
    assert len(component) == 1 and D(str(component[0]["amount"])) == D("200.00")
    parts = _rows(cur, "component_parts", "component_id=%s", (component[0]["id"],))["document"]
    assert len(parts) == 1 and D(str(parts[0]["amount"])) == D("200.00")
    links = _rows(cur, "component_journals", "part_id=%s", (parts[0]["id"],))["document"]
    assert len(links) == 1
    recognition = initial._journal_matches(cur, links[0]["journal_id"], "CP7_CUSTOMER_CREDIT_RECOGNITION", parts[0]["id"],
        (x["dates"]["D2"], x["dates"]["D2"]),
        ((cohort["ar_account_id"], D("200.00")), (credit["id"], D("-200.00"))), x["f"]["customer"])
    assert cmd.delta(before_accounts, cmd.accounts(cur)) == {
        cmd.mapping(cur, "SALES_REVENUE"): D("200.00"), cmd.mapping(cur, "FG_INVENTORY"): D("10.00"),
        cmd.mapping(cur, "COGS"): D("-10.00"), credit["id"]: D("-200.00")}
    assert signed._profile(cur, x, credit, cohort["id"]) == gold["before"]
    native.assert_payment_unchanged(cur, x)
    cur.execute("set constraints all immediate")
    cur.execute("set constraints all deferred")
    return x, credit, earlier, result, cohort, recognition


def _zero_difference(cur, today, gold):
    with native.isolated(cur):
        x, credit, earlier, later, cohort, recognition = _setup(cur, today, gold)
        f = x["f"]
        later_family = _rows(cur, "return_families", "first_return_id=%s", (later["return_id"],))
        later_items = native._array(cur, "erp.sales_return_items", "return_id=%s", (later["return_id"],))
        preserved = signed._preserved(cur, x, dict(family=later_family, return_items=later_items))
        finance_before = {table: _rows(cur, table) for table in FINANCIAL_TABLES}
        earlier_header = native._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s", (earlier["result"]["return_id"],))
        operation_before = _rows(cur, "source_operation_materializations_v1", "sale_id=%s", (f["sale"],))
        assert operation_before["document"] == []
        payload, version = cmd.review(cur, f)
        payload["return_id"] = earlier["result"]["return_id"]
        payload["change_reason"] = "Reverse actual earlier zero-money physical return; retain later actual credit"
        frozen = copy.deepcopy(payload)
        request = uuid.uuid4()
        began = signed._business_day(cur)
        result = cmd.command(cur, "RETURN_REVERSE", payload, version, request)
        signed._assert_same_business_day(cur, began)
        signed._assert_request(cur, "RETURN_REVERSE", payload, version, request, result)
        assert (result["contract_version"], result["kind"], result["action"], result["request_id"], result["sale_id"],
                result["status"], result["return_id"], result["return_status"]) == (
            "cp7.sales-outcome.v1", "COMMITTED_OUTCOME", "RETURN_REVERSE", str(request), f["sale"],
            "PAID", earlier["result"]["return_id"], "REVERSED")
        assert signed._profile(cur, x, credit, cohort["id"]) == gold["after"]
        inverse = signed._assert_actual_inverse(cur, earlier["journal"])
        inverse_id = inverse["document"]["header"]["id"]
        actual_new_ids = {str(row[0]) for row in cur.execute("select id from erp.journal_entries").fetchall()} - set(preserved["journals"])
        assert actual_new_ids == {inverse_id}, "OW04_SIGNED_ZERO_DIFF_FAKE_OR_EXTRA_JOURNAL"
        assert cmd.delta(preserved["accounts"], cmd.accounts(cur)) == {
            cmd.mapping(cur, "FG_INVENTORY"): D("-10.00"), cmd.mapping(cur, "COGS"): D("10.00")}
        for table, before in finance_before.items():
            assert _rows(cur, table) == before, ("OW04_SIGNED_ZERO_DIFF_FAKE_FINANCIAL_FACT", table)
        assert native.journal(cur, recognition["document"]["header"]["id"]) == recognition
        for ident, old in preserved["journals"].items():
            if ident != earlier["journal"]["document"]["header"]["id"]:
                assert native.journal(cur, ident) == old
        private_after = signed._private(cur)
        for table, before in preserved["private"].items():
            assert all(row in private_after[table]["document"] for row in before["document"]), (
                "OW04_SIGNED_ZERO_DIFF_OLD_PRIVATE_HISTORY_CHANGED", table)
        native.assert_payment_unchanged(cur, x)
        assert native._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s", (later["return_id"],)) == preserved["return_header"]
        assert native._array(cur, "erp.sales_return_items", "return_id=%s", (later["return_id"],)) == later_items
        now_earlier = native._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s", (earlier["result"]["return_id"],))["document"]
        assert dict(now_earlier, status=earlier_header["document"]["status"]) == earlier_header["document"]
        assert native._array(cur, "erp.sales_return_items", "return_id=%s", (earlier["result"]["return_id"],)) == earlier["items"]
        assert native._array(cur, "erp.hpp_versions", "lot_id=%s", (f["lot"],)) == preserved["hpp"]
        stock = native._array(cur, "erp.fg_stock_movements", "lot_id=%s", (f["lot"],))["document"]
        old_stock = preserved["stock"]["document"]
        assert all(row in stock for row in old_stock)
        additions = [row for row in stock if row["id"] not in {old["id"] for old in old_stock}]
        assert len(additions) == 1
        move, original = additions[0], earlier["movement"]
        assert (move["movement_type"], move["source_type"], move["source_id"], move["reversal_of_id"], move["product_id"],
                move["lot_id"], move["location_id"], move["quality_grade"], D(str(move["qty_signed"])),
                D(str(move["unit_hpp_snapshot"])), move["customer_id"]) == (
            "REVERSAL", "FG_MOVEMENT_REVERSAL", original["id"], original["id"], f["product"], f["lot"], f["destination"],
            "GRADE_A", D("-1"), D("10.00"), f["customer"])
        pair = (inverse["document"]["header"]["economic_date"], inverse["document"]["header"]["transaction_date"])
        assert cur.execute("select m.physical_at>=o.physical_at and(m.physical_at at time zone'Asia/Jakarta')::date=%s::date "
            "from erp.fg_stock_movements m join erp.fg_stock_movements o on o.id=m.reversal_of_id where m.id=%s",
            (pair[0], move["id"])).fetchone() == (True,)
        assert cur.execute("select cached_qty_pcs from erp.fg_lots where id=%s", (f["lot"],)).fetchone() == (6,)
        operations = _rows(cur, "source_operation_materializations_v1", "sale_id=%s", (f["sale"],))["document"]
        assert len(operations) == 1, "OW04_SIGNED_ZERO_DIFF_SOURCE_OPERATION_REQUIRED"
        operation = operations[0]
        assert (operation["actor"], operation["request_id"], operation["action"], operation["source_id"],
                operation["expected_version"], operation["payload"], str(operation["operation_ordinal"]), operation["predecessor_operation_id"]) == (
            native.auth.base.OPERATOR_AUTH, str(request), "RETURN_REVERSE", earlier["result"]["return_id"],
            version, payload, "1", None)
        assert operation["plan_manifest"] == [] and operation["actual_objects"] == [] and operation["financial_marker_id"] is None
        for key in ("before_ordinal_result", "actual_ordinal_result"):
            families = operation[key]["families"]
            assert len(families) == 2 and all(row["reconciliation_components"] == [] and row["has_reconciliation_effect"] is False for row in families)
        assert _rows(cur, "source_operation_plans_v1", "operation_id=%s", (operation["operation_id"],))["document"] == []
        assert _rows(cur, "source_operation_part_seals_v1", "operation_id=%s", (operation["operation_id"],))["document"] == []
        completion = _rows(cur, "source_operation_completions_v1", "operation_id=%s", (operation["operation_id"],))["document"]
        assert len(completion) == 1, "OW04_SIGNED_ZERO_DIFF_NATIVE_COMPLETION_REQUIRED"
        initial._sha(completion[0]["final_manifest_sha256"])
        assert _rows(cur, "source_operation_work_v1")["document"] == []
        cur.execute("set constraints all immediate")
        complete = signed._observe(cur, x)
        assert cmd.command(cur, "RETURN_REVERSE", payload, version, request) == result
        assert payload == frozen and signed._observe(cur, x) == complete, "OW04_SIGNED_ZERO_DIFF_REPLAY_CHANGED_FACTS"
        cur.execute("set constraints all immediate")
        return dict(status="PASS", classification="ACTUAL_NATIVE_ZERO_DIFF_SOURCE_CASE_ONLY_WHEN_RUN",
                    native_executed=True, production_go=False, expected_id=CASE_ID, request_id=str(request),
                    actual_outcome=result, actual_inverse=inverse, actual_profile=gold["after"],
                    actual_operation_id=operation["operation_id"], actual_completion=completion[0],
                    no_new_recognition_or_financial_marker=True, replay_additional_effects=0,
                    deferred_constraints_forced_before_fixture_rollback=True)


def cases(cur, today):
    """Pure registration; SQL is deferred into the closed harness case call."""
    gold = expected()
    return [(CASE_ID, lambda: _zero_difference(cur, today, gold))]
