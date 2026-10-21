"""Predeclared Native signed-source fixtures; registration is not execution.

Registration never connects, installs, commits or runs SQL. The closed Native
harness owns the supplied cursor, transaction, case savepoint and restoration.
All money/stock documents use retained public writers; only disposable masters,
period inputs and authority revocation are labelled administrative fixtures.
"""
from collections import Counter
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import copy
import json
import re
import uuid

import psycopg
import cp7_ow04_initial_settlement_cases as initial
import cp7_ow04_native_source_fixture as native

b, auth, cmd, source = native.b, native.auth, native.cmd, native.source
EXPECTED_SHA = "9b038e877372848b4e7f86695107d6e99695013b4e443ecda55e1fa6e989dffd"
IDS = (
    "OW04_SIGNED_RETURN_REVERSE_UNCONSUMED_CREDIT",
    "OW04_SIGNED_PAYMENT_REVERSE_UNCONSUMED_CREDIT",
    "OW04_SIGNED_REVOKED_AUTHORITY_DENIES_FRESH_AND_REPLAY",
    "OW04_SIGNED_CONSUMED_REFUND_BLOCKS_RETURN_REVERSE",
)
SCHEMAS = (
    "cp7_credit", "cp7_sales", "ow04_ordinal_wrapper",
    "ow04_source_proposal", "ow04_pure_kernel",
)


def expected():
    raw = Path(__file__).with_name("EXPECTED.json").read_bytes()
    assert sha256(raw).hexdigest() == EXPECTED_SHA, "OW04_SIGNED_FROZEN_EXPECTED_CHANGED"
    value = json.loads(raw)
    assert value["native_executed"] is False and value["production_go"] is False
    assert value["case_count"] == len(IDS) == 4
    assert tuple(row["id"] for row in value["cases"]) == IDS
    return value


def _business_day(cur):
    b.api.admin(cur)
    return cur.execute("select(clock_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]


def _assert_same_business_day(cur, began):
    # Native journals use statement_timestamp, stock uses clock_timestamp.
    # This explicit fixture precondition cannot imply they share a date when
    # a real command crosses midnight; no clock or product rule is changed.
    assert _business_day(cur) == began, "OW04_SIGNED_FIXTURE_CROSSED_BUSINESS_MIDNIGHT"


def _private(cur):
    """Catalog inventory of fixed private schemas includes new root tables."""
    b.api.admin(cur)
    names = cur.execute(
        "select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname=any(%s::text[])and c.relkind in('r','p')order by 1,2",
        (list(SCHEMAS),),
    ).fetchall()
    answer = {}
    for schema, table in names:
        assert re.fullmatch("[a-z_][a-z_0-9]*", schema)
        assert re.fullmatch("[a-z_][a-z_0-9]*", table)
        identity = schema + "." + table
        answer[identity] = native._array(cur, identity, "true", ())
    return answer


def _observe(cur, x):
    """Full refusal/replay observation; never a product authority reader."""
    b.api.admin(cur)
    f = x["f"]
    return dict(
        boundary=b.boundary.snapshot(cur),
        private=_private(cur),
        source=native.source_manifest(cur, x),
        hpp=native._array(cur, "erp.hpp_versions", "lot_id=%s", (f["lot"],)),
        inventory=native._array(cur, "erp.fg_inventory_balances", "product_id=%s", (f["product"],)),
        opening_state=native._array(cur, "erp.opening_lot_hpp_gl_state", "lot_id=%s", (f["lot"],)),
        daily=native._array(cur, "erp.account_daily_balances", "true", ()),
        journals=native._array(cur, "erp.journal_entries", "true", ()),
        lines=native._array(cur, "erp.journal_lines", "true", ()),
        audit=native._array(cur, "erp.audit_logs", "true", ()),
    )


def _preserved(cur, x, actual):
    b.api.admin(cur)
    f = x["f"]
    ids = [str(row[0]) for row in cur.execute("select id from erp.journal_entries").fetchall()]
    return dict(
        private=_private(cur),
        journals={ident: native.journal(cur, ident) for ident in ids},
        payment=native.payment_snapshot(cur, f["payment"]),
        return_header=native._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s",
                                  (actual["family"]["document"][0]["first_return_id"],)),
        return_items=actual["return_items"],
        sale_identity=native._raw(cur,
            "select to_jsonb(h)-array['status','row_version','updated_at']from erp.sales_headers h where id=%s",
            (f["sale"],)),
        sale_items=native._array(cur, "erp.sales_items", "sale_id=%s", (f["sale"],)),
        allocations=native._raw(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')"
            "from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s",
            (f["sale"],)),
        lot_identity=native._raw(cur,
            "select to_jsonb(l)-array['cached_qty_pcs','is_open']from erp.fg_lots l where id=%s", (f["lot"],)),
        hpp=native._array(cur, "erp.hpp_versions", "lot_id=%s", (f["lot"],)),
        stock=native._array(cur, "erp.fg_stock_movements", "lot_id=%s", (f["lot"],)),
        accounts=cmd.accounts(cur),
    )


def _setup(cur, today, mode="CREDIT"):
    initial._require_installed(cur)
    gold = next(row for row in initial.expected()["cases"]
                if row["id"] == "OW04_INITIAL_1000_OPEN_" + mode)
    x = native.prepared(cur, today, "1000.00", "OPEN")
    credit = initial._credit_master(cur)
    query = initial._input(x, gold, credit)
    x["lot_identity_before"] = native._raw(cur,
        "select to_jsonb(l)-array['cached_qty_pcs','is_open']from erp.fg_lots l where id=%s", (x["f"]["lot"],))
    x["journal_ids_before"] = {str(row[0]) for row in cur.execute("select id from erp.journal_entries").fetchall()}
    stock_before = {
        row["id"]: native._array(cur, "erp.fg_stock_movements", "id=%s", (row["id"],))
        for row in x["source_before"]["stock"]["document"]
    }
    before_quote = _observe(cur, x)
    quote = native.call_quote(cur, query)
    assert _observe(cur, x) == before_quote, "OW04_SIGNED_INITIAL_QUOTE_WROTE"
    initial._assert_quote(cur, quote, query, x, gold, credit)
    envelope = initial._envelope(query, quote)
    request = uuid.uuid4()
    result = initial._settle(cur, envelope, request)
    initial._assert_outcome(result, request, envelope, quote, mode)
    actual = initial._assert_actual(cur, x, gold, credit, result, request, stock_before)
    # Verify genuine initial completion before a later operation, then restore
    # deferred semantics for the next complete owning source transaction.
    cur.execute("set constraints all immediate")
    cur.execute("set constraints all deferred")
    return x, credit, result, actual


def _profile(cur, x, credit, cohort):
    b.api.admin(cur)
    f = x["f"]
    ar = cmd.mapping(cur, "AR_CUSTOMER")
    gross, returned, paid = cur.execute(
        "select(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=%s),"
        "(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id "
        "where r.sale_id=%s and r.status='POSTED'),"
        "(select coalesce(sum(amount),0)from erp.sales_payments where sale_id=%s and status='POSTED')",
        (f["sale"], f["sale"], f["sale"]),
    ).fetchone()
    issued = cur.execute(
        "select coalesce(sum(l.debit-l.credit),0)from cp7_credit.recognition_plans rp "
        "join cp7_credit.recognition_components cc on cc.plan_id=rp.id "
        "join cp7_credit.component_parts pp on pp.component_id=cc.id "
        "join cp7_credit.component_journals cj on cj.part_id=pp.id "
        "join erp.journal_lines l on l.journal_entry_id=cj.journal_id "
        "where rp.cohort_id=%s and l.account_id=%s and l.customer_id=%s",
        (cohort, ar, f["customer"]),
    ).fetchone()[0]
    used, applied = cur.execute(
        "select(select coalesce(sum(amount),0)from cp7_credit.consumption_events where cohort_id=%s),"
        "(select coalesce(sum(amount),0)from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=%s)",
        (cohort, f["sale"]),
    ).fetchone()
    ar_balance, liability = cur.execute(
        "select(select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s and customer_id=%s),"
        "(select coalesce(sum(credit-debit),0)from erp.journal_lines where account_id=%s and customer_id=%s)",
        (ar, f["customer"], credit["id"], f["customer"]),
    ).fetchone()
    bank = native.payments.bank_account(cur, f)
    cash = cur.execute("select coalesce(sum(debit-credit),0)from erp.journal_lines where account_id=%s", (bank,)).fetchone()[0]
    qty, stock_value = cur.execute(
        "select coalesce(sum(qty_signed),0),coalesce(sum(qty_signed*unit_hpp_snapshot),0)"
        "from erp.fg_stock_movements where lot_id=%s", (f["lot"],),
    ).fetchone()
    status, payment_status = cur.execute(
        "select h.status,p.status from erp.sales_headers h join erp.sales_payments p on p.sale_id=h.id "
        "where h.id=%s and p.id=%s", (f["sale"], f["payment"]),
    ).fetchone()
    return_status = cur.execute("select status from erp.sales_returns where id=(select source_return_id from cp7_credit.cohorts where id=%s)",
                                (cohort,)).fetchone()[0]
    net, effective = gross-returned, paid+applied-issued
    assert ar_balance == net-effective, "OW04_SIGNED_RAW_GL_AR_DIFFERS_FROM_P_U_I"
    money = lambda value: format(D(value), ".2f")
    answer = dict(gross=money(gross), net=money(net), P=money(paid), U=money(applied),
                  I=money(issued), E=money(effective), AR=money(ar_balance),
                  liability_credit=money(liability), C=money(used), cash=money(cash),
                  stock_qty=str(qty), stock_value=money(stock_value), sale_status=status,
                  return_status=return_status, payment_status=payment_status)
    detail = source.read(cur, f)["detail"]
    assert detail["status"] == status
    assert {key: detail["financial"][key] for key in
            ("gross_total", "net_total", "paid_total", "open_balance")} == dict(
                gross_total=answer["gross"], net_total=answer["net"],
                paid_total=answer["E"], open_balance=answer["AR"])
    factual = cur.execute("select cp7_credit.inspect_current_materialized_profile(%s,%s,%s)",
                          (f["sale"], f["sale"], f["sale"])).fetchone()[0]
    assert D(str(factual["I"])) == issued and D(str(factual["U"])) == applied
    return answer


def _intent(cur, x, initial_result, action):
    payload, version = cmd.review(cur, x["f"])
    payload["return_id" if action == "RETURN_REVERSE" else "payment_id"] = (
        initial_result["return_id"] if action == "RETURN_REVERSE" else x["f"]["payment"])
    payload["change_reason"] = "Reviewed exact source inverse and signed customer credit adjustment"
    return payload, version


def _assert_request(cur, action, payload, version, request, result):
    b.api.admin(cur)
    rows = cur.execute("select action,payload,expected_version,response from cp7_sales.requests "
                       "where actor=%s and request_id=%s",
                       (auth.base.OPERATOR_AUTH, request)).fetchall()
    assert rows == [(action, payload, version, result)], "OW04_SIGNED_EXACT_OWNING_REQUEST_RECEIPT_REQUIRED"


def _inverse_vector(document):
    return Counter((row["account_id"], D(str(row["debit"])), D(str(row["credit"])),
                    row["customer_id"], row["vendor_id"], row["contractor_id"],
                    row["po_id"], row["product_id"]) for row in document["lines"])


def _assert_old_journal_status_only(cur, old, expected_status):
    now = native.journal(cur, old["document"]["header"]["id"])
    before_header, after_header = dict(old["document"]["header"]), dict(now["document"]["header"])
    before_header.pop("status")
    assert after_header.pop("status") == expected_status
    assert before_header == after_header and now["document"]["lines"] == old["document"]["lines"]


def _assert_actual_inverse(cur, old):
    old_id = old["document"]["header"]["id"]
    ids = cur.execute(
        "select id::text from erp.journal_entries where source_type='JOURNAL_REVERSAL'"
        "and source_id=%s and reversal_of_id=%s", (old_id, old_id),
    ).fetchall()
    assert len(ids) == 1, ("OW04_SIGNED_EXACT_SOURCE_INVERSE_REQUIRED", ids)
    actual = native.journal(cur, ids[0][0])
    header = actual["document"]["header"]
    assert header["status"] == "POSTED"
    assert cur.execute(
        "select economic_date=(posting_at at time zone'Asia/Jakarta')::date "
        "and transaction_date=economic_date from erp.journal_entries where id=%s", (ids[0][0],),
    ).fetchone() == (True,), "OW04_SIGNED_ACTUAL_NATIVE_CURRENT_OPEN_PAIR_REQUIRED"
    assert header["economic_date"] >= old["document"]["header"]["economic_date"]
    assert header["transaction_date"] >= old["document"]["header"]["transaction_date"]
    assert cur.execute("select n.posting_at>=o.posting_at from erp.journal_entries n "
                       "join erp.journal_entries o on o.id=n.reversal_of_id where n.id=%s",
                       (ids[0][0],)).fetchone() == (True,)
    flipped = copy.deepcopy(old["document"])
    for line in flipped["lines"]:
        line["debit"], line["credit"] = line["credit"], line["debit"]
    assert _inverse_vector(actual["document"]) == _inverse_vector(flipped)
    _assert_old_journal_status_only(cur, old, "REVERSED")
    return actual


def _assert_positive(cur, x, credit, initial_result, actual, gold, request, result, before):
    b.api.admin(cur)
    f, action = x["f"], gold["action"]
    cohort = actual["cohorts"]["document"][0]
    assert (result["contract_version"], result["kind"], result["action"], result["request_id"],
            result["sale_id"], result["status"]) == (
        "cp7.sales-outcome.v1", "COMMITTED_OUTCOME", action, str(request), f["sale"], gold["after"]["sale_status"])
    source_key = "return_id" if action == "RETURN_REVERSE" else "payment_id"
    source_id = initial_result["return_id"] if action == "RETURN_REVERSE" else f["payment"]
    assert result[source_key] == source_id
    assert result["return_status" if action == "RETURN_REVERSE" else "payment_status"] == "REVERSED"
    assert _profile(cur, x, credit, cohort["id"]) == gold["after"]
    original = actual["native_return_journal"] if action == "RETURN_REVERSE" else before["payment"]["original_journal"]
    inverse = _assert_actual_inverse(cur, original)
    pair = (inverse["document"]["header"]["economic_date"], inverse["document"]["header"]["transaction_date"])
    plans = native._array(cur, "cp7_credit.recognition_plans", "cohort_id=%s", (cohort["id"],))["document"]
    new_plans = [row for row in plans if row["id"] != cohort["initial_plan_id"]]
    assert len(plans) == 2 and len(new_plans) == 1
    plan = new_plans[0]
    assert (plan["plan_kind"], plan["owning_action"], plan["request_id"], D(str(plan["net_amount"])),
            plan["has_recognition_effect"], plan["expected_component_count"], plan["expected_part_count"]) == (
        "ADJUSTMENT", action, str(request), D("-200.00"), True, 1, 1)
    components = native._array(cur, "cp7_credit.recognition_components", "plan_id=%s", (plan["id"],))["document"]
    assert len(components) == 1
    component = components[0]
    assert (component["ordinal"], component["economic_date"], component["transaction_date"],
            D(str(component["amount"]))) == (1, *pair, D("-200.00"))
    assert component["corners"] == dict(d_here="-200.00", d_prev_economic="0.00",
                                       d_prev_transaction="0.00", d_prev_both="0.00")
    parts = native._array(cur, "cp7_credit.component_parts", "component_id=%s", (component["id"],))["document"]
    assert len(parts) == 1 and parts[0]["ordinal"] == 1 and D(str(parts[0]["amount"])) == D("-200.00")
    links = native._array(cur, "cp7_credit.component_journals", "part_id=%s", (parts[0]["id"],))["document"]
    assert len(links) == 1
    adjustment = initial._journal_matches(cur, links[0]["journal_id"], "CP7_CUSTOMER_CREDIT_RECOGNITION",
        parts[0]["id"], pair, ((cohort["ar_account_id"], D("-200.00")), (credit["id"], D("200.00"))), f["customer"])
    assert len(adjustment["document"]["lines"]) == 2
    assert all(row[key] is None for row in adjustment["document"]["lines"]
               for key in ("vendor_id", "contractor_id", "po_id", "product_id"))
    new_ids = {str(row[0]) for row in cur.execute("select id from erp.journal_entries").fetchall()} - set(before["journals"])
    assert new_ids == {inverse["document"]["header"]["id"], adjustment["document"]["header"]["id"]}
    source_old_id = original["document"]["header"]["id"]
    for ident, row in before["journals"].items():
        if ident != source_old_id:
            assert native.journal(cur, ident) == row, ("OW04_SIGNED_ORIGINAL_JOURNAL_REWRITTEN", ident)
    assert native.journal(cur, actual["recognition_journal"]["document"]["header"]["id"]) == actual["recognition_journal"]
    private_after = _private(cur)
    for table, rows in before["private"].items():
        assert all(row in private_after[table]["document"] for row in rows["document"]), (
            "OW04_SIGNED_OLD_IMMUTABLE_PRIVATE_FACT_REWRITTEN", table)
    assert native._array(cur, "erp.hpp_versions", "lot_id=%s", (f["lot"],)) == before["hpp"]
    assert native._array(cur, "erp.sales_items", "sale_id=%s", (f["sale"],)) == before["sale_items"]
    assert native._raw(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')"
        "from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s",
        (f["sale"],)) == before["allocations"]
    assert native._raw(cur, "select to_jsonb(h)-array['status','row_version','updated_at']from erp.sales_headers h where id=%s",
                       (f["sale"],)) == before["sale_identity"]
    assert native._raw(cur, "select to_jsonb(l)-array['cached_qty_pcs','is_open']from erp.fg_lots l where id=%s",
                       (f["lot"],)) == before["lot_identity"]
    assert native._array(cur, "erp.sales_return_items", "return_id=%s", (initial_result["return_id"],)) == before["return_items"]
    stock = native._array(cur, "erp.fg_stock_movements", "lot_id=%s", (f["lot"],))["document"]
    old_stock = before["stock"]["document"]
    assert all(row in stock for row in old_stock)
    additions = [row for row in stock if row["id"] not in {old["id"] for old in old_stock}]
    assert len(additions) == gold["new_stock_reversal_count"]
    if action == "RETURN_REVERSE":
        native.assert_payment_unchanged(cur, x)
        header = native._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s", (initial_result["return_id"],))["document"]
        old_header = before["return_header"]["document"]
        assert dict(header, status=old_header["status"]) == old_header
        original_move = actual["return_movement"]["document"][0]
        move = additions[0]
        assert (move["movement_type"], move["source_type"], move["source_id"], move["reversal_of_id"],
                move["product_id"], move["lot_id"], move["location_id"], move["quality_grade"],
                D(str(move["qty_signed"])), D(str(move["unit_hpp_snapshot"])), move["customer_id"]) == (
            "REVERSAL", "FG_MOVEMENT_REVERSAL", original_move["id"], original_move["id"],
            f["product"], f["lot"], f["destination"], "GRADE_A", D("-1"), D("10.00"), f["customer"])
        assert cur.execute("select m.physical_at>=o.physical_at and "
            "(m.physical_at at time zone'Asia/Jakarta')::date=%s::date "
            "from erp.fg_stock_movements m join erp.fg_stock_movements o on o.id=m.reversal_of_id where m.id=%s",
            (pair[0], move["id"])).fetchone() == (True,)
        wanted = {cmd.mapping(cur, "SALES_REVENUE"): D("-200.00"), cmd.mapping(cur, "FG_INVENTORY"): D("-10.00"),
                  cmd.mapping(cur, "COGS"): D("10.00"), credit["id"]: D("200.00")}
    else:
        assert native._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s",
                           (initial_result["return_id"],)) == before["return_header"]
        payment = native.payment_snapshot(cur, f["payment"])
        old_payment = before["payment"]["payment"]["document"]
        now_payment = payment["payment"]["document"]
        assert dict(now_payment["header"], status=old_payment["header"]["status"]) == old_payment["header"]
        assert now_payment["posting_facts"] == old_payment["posting_facts"]
        assert old_payment["reversal_facts"] == [] and len(now_payment["reversal_facts"]) == 1
        fact = now_payment["reversal_facts"][0]
        assert (fact["payment_id"], fact["original_journal_entry_id"], fact["reversal_journal_entry_id"],
                fact["reversal_economic_date"], fact["reversal_transaction_date"], fact["reversal_posting_at"]) == (
            f["payment"], source_old_id, inverse["document"]["header"]["id"], *pair, inverse["document"]["header"]["posting_at"])
        wanted = {cohort["ar_account_id"]: D("800.00"), native.payments.bank_account(cur, f): D("-1000.00"),
                  credit["id"]: D("200.00")}
    assert cmd.delta(before["accounts"], cmd.accounts(cur)) == wanted, "OW04_SIGNED_FULL_GLOBAL_GL_DELTA_WRONG"
    assert native._array(cur, "cp7_credit.consumption_events", "cohort_id=%s", (cohort["id"],))["document"] == []
    assert cur.execute("select cached_qty_pcs from erp.fg_lots where id=%s", (f["lot"],)).fetchone()[0] == int(gold["after"]["stock_qty"])
    cur.execute("set constraints all immediate")
    return dict(source_inverse=inverse, adjustment=adjustment, plan=plan,
                component=component, part=parts[0], actual_profile=gold["after"])


def _positive(cur, today, gold):
    with native.isolated(cur):
        x, credit, original, actual = _setup(cur, today)
        cohort = actual["cohorts"]["document"][0]["id"]
        assert _profile(cur, x, credit, cohort) == gold["before"]
        payload, version = _intent(cur, x, original, gold["action"])
        frozen = copy.deepcopy(payload)
        request = uuid.uuid4()
        before = _preserved(cur, x, actual)
        began = _business_day(cur)
        result = cmd.command(cur, gold["action"], payload, version, request)
        _assert_same_business_day(cur, began)
        _assert_request(cur, gold["action"], payload, version, request, result)
        evidence = _assert_positive(cur, x, credit, original, actual, gold, request, result, before)
        complete = _observe(cur, x)
        assert cmd.command(cur, gold["action"], payload, version, request) == result
        assert payload == frozen and _observe(cur, x) == complete, "OW04_SIGNED_REPLAY_ADDED_EFFECT"
        cur.execute("set constraints all immediate")
        return dict(status="PASS", classification="ACTUAL_NATIVE_SIGNED_SOURCE_CASE_ONLY_WHEN_RUN",
                    native_executed=True, production_go=False, expected_id=gold["id"],
                    request_id=str(request), actual_outcome=result, evidence=evidence,
                    replay_same_outcome=True, replay_additional_effects=0,
                    deferred_constraints_forced_before_fixture_rollback=True)


def _refuse(cur, operation, sqlstate, message):
    b.api.admin(cur)
    savepoint = "ow04_signed_refuse_" + uuid.uuid4().hex
    cur.execute("savepoint " + savepoint)
    try:
        operation()
    except psycopg.Error as error:
        result = dict(sqlstate=error.sqlstate, message=error.diag.message_primary,
                      detail=error.diag.message_detail or "")
        cur.execute("rollback to savepoint " + savepoint)
        b.api.admin(cur)
        cur.execute("release savepoint " + savepoint)
        assert (result["sqlstate"], result["message"]) == (sqlstate, message), result
        return result
    cur.execute("rollback to savepoint " + savepoint)
    b.api.admin(cur)
    cur.execute("release savepoint " + savepoint)
    raise AssertionError("OW04_SIGNED_EXPECTED_REFUSAL:" + message)


def _revoked(cur, today, gold):
    with native.isolated(cur):
        x, credit, original, actual = _setup(cur, today)
        positive = expected()["cases"][0]
        payload, version = _intent(cur, x, original, "RETURN_REVERSE")
        request = uuid.uuid4()
        before = _preserved(cur, x, actual)
        began = _business_day(cur)
        result = cmd.command(cur, "RETURN_REVERSE", payload, version, request)
        _assert_same_business_day(cur, began)
        _assert_request(cur, "RETURN_REVERSE", payload, version, request, result)
        _assert_positive(cur, x, credit, original, actual, positive, request, result, before)
        fresh, fresh_version = _intent(cur, x, original, "PAYMENT_REVERSE")
        # ADMINISTRATIVE_AUTHORITY_FIXTURE, matching retained inverse tests:
        # preserve another real OWNER before revoking the current operator.
        b.api.admin(cur)
        cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)"
            "select %s,%s,'OW04 signed replay second owner fixture',role,role_id,true "
            "from erp.app_users where auth_user_id=%s",
            (uuid.uuid4(), uuid.uuid4(), auth.base.OPERATOR_AUTH))
        cur.execute("update erp.app_users set is_active=false where auth_user_id=%s", (auth.base.OPERATOR_AUTH,))
        baseline = _observe(cur, x)
        errors = []
        for operation, wanted in zip((
            lambda: cmd.command(cur, "RETURN_REVERSE", payload, version, request),
            lambda: cmd.command(cur, "PAYMENT_REVERSE", fresh, fresh_version, uuid.uuid4()),
        ), gold["attempts"], strict=True):
            errors.append(_refuse(cur, operation, wanted["sqlstate"], wanted["message"]))
            assert _observe(cur, x) == baseline, "OW04_SIGNED_REVOKED_COMMAND_CHANGED_FACTS"
        cur.execute("set constraints all immediate")
        return dict(status="PASS", classification="ACTUAL_NATIVE_CURRENT_AUTHORITY_REFUSAL_ONLY_WHEN_RUN",
                    native_executed=True, production_go=False, expected_id=gold["id"], errors=errors,
                    cached_and_fresh_current_authority_refused=True, partial_effects=0)


def _consumed(cur, today, gold):
    with native.isolated(cur):
        x, credit, original, actual = _setup(cur, today, "REFUND")
        cohort = actual["cohorts"]["document"][0]["id"]
        assert _profile(cur, x, credit, cohort) == gold["before"]
        events = actual["consumptions"]["document"]
        assert len(events) == 1 and events[0]["event_kind"] == "REFUND" and D(str(events[0]["amount"])) == D("200.00")
        event = events[0]
        payload, version = _intent(cur, x, original, "RETURN_REVERSE")
        before = _observe(cur, x)
        error = _refuse(cur, lambda: cmd.command(cur, "RETURN_REVERSE", payload, version, uuid.uuid4()),
                        gold["sqlstate"], gold["message"])
        assert _observe(cur, x) == before, "OW04_SIGNED_CONSUMER_REFUSAL_LEFT_PARTIAL_EFFECT"
        assert all(key in error["detail"] for key in gold["required_detail_fields"]), error
        assert all(value in error["detail"] for value in
                   (event["id"], cohort, "REFUND", event["journal_id"])), error
        assert _profile(cur, x, credit, cohort) == gold["before"]
        cur.execute("set constraints all immediate")
        return dict(status="PASS", classification="ACTUAL_NATIVE_CONSUMER_DEPENDENCY_REFUSAL_ONLY_WHEN_RUN",
                    native_executed=True, production_go=False, expected_id=gold["id"],
                    actual_consumer=event, refusal=error, partial_effects=0)


def cases(cur, today):
    """Pure case registration; all SQL is inside deferred case invocations."""
    values = expected()["cases"]
    return [
        (values[0]["id"], lambda: _positive(cur, today, values[0])),
        (values[1]["id"], lambda: _positive(cur, today, values[1])),
        (values[2]["id"], lambda: _revoked(cur, today, values[2])),
        (values[3]["id"], lambda: _consumed(cur, today, values[3])),
    ]
