"""Audit-only reconstruction v1 of six advance cases; native NOT_RUN.

Provenance: recovered continuation/business/business_scenarios.py SHA-256
7720ced7417375ba766e4552dae03804673ae080d3377d7a3835f1822b9e93d0.
The later lost scenario (reported SHA-256 prefix 44b075c7) is NOT recovered.
This file has new bytes and needs its own SHA-256 at any later dispatch.

Oracle: restored ERP_V3_2_Master_Pulih_20260923.md M:629-646 and
M:3816-3820. Only SUPPLIER/CUSTOMER/VENDOR ordered and backdated capacity
cases are included. Four former COUNT cases are EXCLUDED. No side connection,
commit, schema grant, installed-function edit, or production target is used.
The supplied auditor runner must isolate and roll back each case.
"""

from datetime import timedelta
from decimal import Decimal
import json
import traceback
import uuid

import psycopg
import cp6_ao_ap_installed as api

D = Decimal
KINDS = ("SUPPLIER", "CUSTOMER", "VENDOR")
PLANNED_CASE_IDS = (
    "BCR1-ADVANCE-SUPPLIER-ORDERED_CONTROL",
    "BCR1-ADVANCE-SUPPLIER-DATED_CAPACITY",
    "BCR1-ADVANCE-CUSTOMER-ORDERED_CONTROL",
    "BCR1-ADVANCE-CUSTOMER-DATED_CAPACITY",
    "BCR1-ADVANCE-VENDOR-ORDERED_CONTROL",
    "BCR1-ADVANCE-VENDOR-DATED_CAPACITY",
)


def plain(value):
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if isinstance(value, (D, uuid.UUID)):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def tag():
    return "BCR1" + uuid.uuid4().hex[:15]


def opening(cur, today):
    cutover = today - timedelta(days=8)
    # Disposable-fixture setup inherited from the older source; no commit.
    api.production.prior.set_open_period(cur, cutover - timedelta(days=1))
    api.admin(cur)
    observed = cur.execute(
        "select erp._cp3_business_date(statement_timestamp()),closed_through "
        "from erp.accounting_period_control where singleton_id=1"
    ).fetchone()
    if observed != (today, cutover - timedelta(days=1)):
        raise RuntimeError("ADVANCE_FIXTURE_OPEN_PERIOD_MISMATCH")
    code = tag()
    batch = api.call(cur, "CREATE", {"batch_code": code, "cutover_date": str(cutover)})["batch_id"]
    return code, batch, cutover


def fixture(cur, today, kind):
    code, batch, cutover = opening(cur, today)
    entity, field, name = {
        "SUPPLIER": ("SUPPLIER", "supplier_code", "supplier_name"),
        "CUSTOMER": ("CUSTOMER", "customer_code", "customer_name"),
        "VENDOR": ("LAUNDRY_VENDOR", "vendor_code", "vendor_name"),
    }[kind]
    api.upload(cur, batch, entity, [{field: code, name: "Independent advance party"}])
    customer = kind == "CUSTOMER"
    api.upload(cur, batch, "CHART_ACCOUNT", [
        dict(account_code=code + "B", account_name="Independent bank", account_type="ASSET",
             report_group="CURRENT_ASSETS", normal_balance="DEBIT"),
        dict(account_code=code + "A", account_name="Independent dedicated advance",
             account_type="LIABILITY" if customer else "ASSET",
             report_group="CURRENT_LIABILITIES" if customer else "CURRENT_ASSETS",
             normal_balance="CREDIT" if customer else "DEBIT"),
    ])
    api.upload(cur, batch, "CASH_ACCOUNT", [dict(cash_account_code=code,
        cash_account_name="Independent bank", coa_account_code=code + "B", account_kind="BANK")])
    api.upload(cur, batch, "OPENING_BALANCE_ITEM", [dict(balance_type="CASH_BANK",
        cash_account_code=code, amount="100.00", control_key="BANK")])
    api.upload(cur, batch, "OPENING_ADVANCE", [dict(party_type=kind, party_code=code,
        coa_account_code=code + "A", document_number=code + "DEP",
        document_date=str(cutover - timedelta(days=30)), original_amount="100.00",
        settled_before_cutover="32.75", amount="67.25", control_key="ADV")])
    api.upload(cur, batch, "OPENING_CONTROL", [
        dict(control_key="BANK", balance_type="CASH_BANK", amount="100.00"),
        dict(control_key="ADV", balance_type=kind + "_ADVANCE", amount="67.25"),
    ])
    checked = api.invoke(cur, "VALIDATE", batch)
    if checked.get("error_rows") != 0:
        raise RuntimeError("ADVANCE_FIXTURE_VALIDATION_FAILED: " + json.dumps(plain(checked)))
    posted = api.invoke(cur, "FINALIZE", batch)
    if posted.get("status") != "POSTED":
        raise RuntimeError("ADVANCE_FIXTURE_NOT_POSTED: " + json.dumps(plain(posted)))
    api.admin(cur)
    advance, account = cur.execute(
        "select id,coa_account_id from erp.initial_import_prepayments where batch_id=%s", (batch,)
    ).fetchone()
    cash, bank_account = cur.execute(
        "select id,coa_account_id from erp.cash_accounts where cash_account_code=%s", (code,)
    ).fetchone()
    return dict(batch=batch, advance=advance, account=account, cash=cash,
                bank_account=bank_account, cutover=cutover, kind=kind)


def asof(cur, account, day, normal=1):
    api.admin(cur)
    return D(str(cur.execute(
        "select coalesce(sum(debit_total-credit_total),0) from erp.account_daily_balances "
        "where account_id=%s and balance_date<=%s", (account, day)
    ).fetchone()[0])) * normal


def source(cur, fx):
    api.admin(cur)
    # Compare source identity and original facts, not future derived/cache fields.
    return cur.execute(
        "select id,batch_id,source_row_id,party_type,party_id,supplier_id,customer_id,vendor_id,"
        "coa_account_id,document_number,document_date,cutover_date,original_amount,"
        "settled_before_cutover,amount from erp.initial_import_prepayments where id=%s",
        (fx["advance"],)
    ).fetchone()


def events(cur, fx):
    api.admin(cur)
    return cur.execute(
        "select event_type,component,delta,effective_date "
        "from erp.initial_import_prepayment_events where advance_id=%s "
        "order by effective_date,event_type", (fx["advance"],)
    ).fetchall()


def balances(cur, fx, dates, normal):
    return {str(day): dict(advance=asof(cur, fx["account"], day, normal),
                           bank=asof(cur, fx["bank_account"], day)) for day in dates}


def case(cur, today, kind, backdated):
    fx = fixture(cur, today, kind)
    normal = -1 if kind == "CUSTOMER" else 1
    opening_advance = asof(cur, fx["account"], today, normal)
    opening_bank = asof(cur, fx["bank_account"], today)
    if (opening_advance, opening_bank) != (D("67.25"), D("100.00")):
        raise RuntimeError("ADVANCE_FIXTURE_OPENING_LEDGER_MISMATCH")
    original = source(cur, fx)
    correction_day = today - timedelta(days=2 if backdated else 4)
    refund_day = today - timedelta(days=4 if backdated else 2)
    correction = dict(batch_id=fx["batch"],
        expected_revision=api.read(cur, fx["batch"])["batch"]["revision"],
        advance_id=fx["advance"], operation="CORRECT", amount="100.00",
        effective_date=str(correction_day), reason="Independent correction source")
    corrected = api.call(cur, "PREPAYMENT", correction)
    if not isinstance(corrected, dict):
        raise RuntimeError("ADVANCE_CORRECTION_MALFORMED_RESULT")
    before_refund = events(cur, fx)
    if before_refund != [("CORRECTION", "CORRECTION", D("32.75"), correction_day)]:
        raise RuntimeError("ADVANCE_CORRECTION_FIXTURE_EVENT_MISMATCH")
    refund = dict(batch_id=fx["batch"],
        expected_revision=api.read(cur, fx["batch"])["batch"]["revision"],
        advance_id=fx["advance"], operation="REFUND", amount="100.00",
        effective_date=str(refund_day), cash_account_id=fx["cash"],
        reason="Independent dated refund")
    key = uuid.uuid4()
    api.admin(cur)
    cur.execute("savepoint advance_refund_attempt")
    try:
        result = api.call(cur, "PREPAYMENT", refund, key)
    except psycopg.Error as exc:
        error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
        cur.execute("rollback to savepoint advance_refund_attempt")
        api.admin(cur)
        cur.execute("release savepoint advance_refund_attempt")
        # The reviewed contract specifies capacity/invariant but no exact refusal.
        # Permission/setup/unrelated SQL errors must never become PASS.
        after_refusal = events(cur, fx)
        return plain(dict(status="INCOMPLETE", kind=kind, backdated=backdated,
            stage="REFUND_REFUSED_UNCLASSIFIED", refusal=error,
            atomic_event_observation=after_refusal == before_refund,
            source_unchanged=source(cur, fx) == original,
            expected="Dated-capacity refusal needs an exact contract/product oracle; arbitrary SQL refusal is not PASS."))
    cur.execute("release savepoint advance_refund_attempt")
    api.admin(cur)
    count_before_replay = len(events(cur, fx))
    replay = api.call(cur, "PREPAYMENT", refund, key)
    count_after_replay = len(events(cur, fx))
    dates = sorted({fx["cutover"], correction_day, refund_day, today})
    observed = balances(cur, fx, dates, normal)
    observed_events = events(cur, fx)
    expected_events = sorted([
        ("CORRECTION", "CORRECTION", D("32.75"), correction_day),
        ("REFUND", "REFUND", D("-100.00"), refund_day),
    ], key=lambda row: (row[3], row[0]))
    raw_journal = cur.execute(
        "select j.economic_date,j.transaction_date,j.source_type,l.debit,l.credit "
        "from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id "
        "where l.account_id=%s order by j.transaction_date,j.posting_at,j.id",
        (fx["account"],)
    ).fetchall()
    dated = len(raw_journal) == 3 and all(row[0] == row[1] for row in raw_journal)
    source_immutable = source(cur, fx) == original
    replay_exact = result == replay and count_before_replay == count_after_replay
    if backdated:
        # At refund day: 67.25 - 100 = -32.75 until the later correction.
        negative = {day: value["advance"] for day, value in observed.items()
                    if value["advance"] < 0}
        status = "COUNTEREXAMPLE" if (negative and dated and observed_events == expected_events
                                      and source_immutable and replay_exact) else "INCOMPLETE"
        expected = "No negative dated capacity prefix; an exact refusal oracle remains unspecified."
    else:
        expected = {str(day): dict(
            advance=D("67.25") + (D("32.75") if day >= correction_day else 0)
                                  - (D("100.00") if day >= refund_day else 0),
            bank=D("100.00") + (D("-100.00" if kind == "CUSTOMER" else "100.00")
                                  if day >= refund_day else 0),
        ) for day in dates}
        status = "PASS" if (observed == expected and dated and observed_events == expected_events
                            and source_immutable and replay_exact) else "COUNTEREXAMPLE"
    return plain(dict(status=status, kind=kind, backdated=backdated, fixture=fx,
        correction_day=correction_day, refund_day=refund_day,
        opening_advance=opening_advance, opening_bank=opening_bank,
        expected=expected, observed=observed, raw_journal=raw_journal,
        events=observed_events, source_immutable=source_immutable,
        economic_and_posting_dates_preserved=dated, exact_replay=replay_exact,
        scope="Public native import RPC with ordinary authenticated actor; no HTTP/UI proof."))


def guarded(cur, operation):
    cur.execute("savepoint advance_case")
    try:
        result = operation()
        api.admin(cur)
        cur.execute("release savepoint advance_case")
        return result
    except Exception as exc:
        cur.execute("rollback to savepoint advance_case")
        api.admin(cur)
        cur.execute("release savepoint advance_case")
        return dict(status="INCOMPLETE", stage="FIXTURE_OR_ACTION_EXCEPTION",
                    error_type=type(exc).__name__, error=str(exc),
                    sqlstate=getattr(exc, "sqlstate", None),
                    traceback=traceback.format_exc()[-1800:])


def cases(cur, today):
    # Registration is pure: no DB access until one returned callable executes.
    result = [("BCR1-ADVANCE-" + kind + ("-DATED_CAPACITY" if backdated else "-ORDERED_CONTROL"),
               lambda k=kind, b=backdated: guarded(cur, lambda: case(cur, today, k, b)))
              for kind in KINDS for backdated in (False, True)]
    assert tuple(key for key, _ in result) == PLANNED_CASE_IDS
    return result
