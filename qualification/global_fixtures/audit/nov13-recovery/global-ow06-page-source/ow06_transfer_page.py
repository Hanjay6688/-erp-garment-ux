"""OW06 transfer pagination callback for the admitted first Global caller."""

from contextlib import closing
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

from race_observer import Refusal, begin, idle, observe, reply_bytes, require


CASE = "OW06_TRANSFER_PAGE_25_TO_26"
GETTER = "select public.erp_cp7_get_supplier_transfer_v1(%s::jsonb)::text"
PAUSE = "erp.chart_accounts"
PREFIX = ("erp.app_users", "erp.suppliers", "erp.material_purchase_headers",
          "erp.supplier_payments", "erp.journal_lines")
DAY = "SKU_CURRENT_AUTOMATIC_WIB_BUSINESS_DAY"
PAGE_SIZE = 25
BASE_AMOUNTS = ("1.00", "2.00")
NEW_AMOUNTS = ("400.00", "600.00")
CAPITAL = "1075.00"
FIXTURE_PINS = {
    "cp7_supplier_transfer/cases.py": "0d3f8c697ec14dd0a1dcde44cafb066f7da796f805c43040b443ce0162af83e7",
    "cp7_supplier_payment_create_cases.py": "ac07bfdb55751b5e8da86e599eec1bf97e870768c39c930af3a76d871a19c292",
    "cp7_supplier_payment_cases.py": "b95ff7cdb52603935cee2cf87b1d3e2cee2fc7f51c3574ea18683c2a16ad82d3",
    "cp7_procurement_cases.py": "460b4541154ba2950425c5fbaa1c0872f941cfc4646a9810841802ce72e9f3d1",
    "cp6_bc_probe.py": "147de7092ba2284312ba376f8cae82bf05c0fbb77e28956f45966cdfa6c8adb1",
    "cp7_cash_funding.py": "df5917e8312721c0619e9685bd08f327a6843fb18b3f14fa50022ea912077ee8",
    "cp7_misc_cases.py": "0610bc358b9d9321e42bb18c11c0c32cb0b12b6122534d93b93d4c60cdef0f09",
    "cp7_snapshot_cases.py": "b0f96102c7c508984d830028bbd191804703b7844d8963817ce2917b2050f9f4",
}
RPC_KEYS = {"contract_version", "captured_at", "supplier", "can_write", "review_token", "query",
            "receipts", "cash_accounts", "transfers", "selected"}
ROW_KEYS = ("id", "number", "status", "amount", "payment_date")


def actual_day(cur):
    day, = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()
    require(day.isoformat() == os.environ.get(DAY), CASE + "_EXACT_OWNING_WIB_DAY_REQUIRED")
    return day


def fixture_sources():
    from cp7_supplier_transfer import cases

    single = cases.single
    source = Path(cases.__file__).resolve().parents[1]
    modules = (cases, single, single.supplier, single.invoice.receipt, single.bc, single.funding,
               single.misc, cases.auth)
    actual = {}
    for module in modules:
        path = Path(module.__file__).resolve()
        name = path.relative_to(source).as_posix()
        actual[name] = sha256(path.read_bytes()).hexdigest()
    require(actual == FIXTURE_PINS, CASE + "_EXACT_NATIVE_FIXTURE_SOURCES_REQUIRED", actual)
    return cases


def workspace(cur, cases, fixture, offset, record=None):
    actual_day(cur)
    request = dict(supplier_id=fixture["supplier"], transfer_offset=offset, bank_q=fixture["bank_code"])
    request_text = json.dumps(request)
    cases.auth.actor(cur)
    response_text, = cur.execute(GETTER, (request_text,)).fetchone()
    cases.b.api.admin(cur)
    if record is not None:
        record.append(dict(pid=cur.connection.info.backend_pid, request=request_text, response=response_text))
    response = json.loads(response_text)
    expected_query = dict(request, transfer_id=None, purchase_q="", purchase_offset=0, bank_offset=0)
    require(type(response) is dict and set(response) == RPC_KEYS
            and response["contract_version"] == "cp7.supplier-transfer-workspace.v1"
            and response["can_write"] is True and response["query"] == expected_query
            and response["supplier"]["id"] == fixture["supplier"] and response["selected"] is None
            and isinstance(response["review_token"], str) and len(response["review_token"]) == 32,
            CASE + "_EXACT_PUBLIC_PAGE_REQUEST_AND_CONTRACT_REQUIRED", response)
    actual_day(cur)
    return response


def create(cur, cases, fixture, amounts, request, expected_token=None):
    payload = cases.payload(cur, fixture, amounts, at=fixture["payment_date"])
    if expected_token is not None:
        require(payload["review_token"] == expected_token, CASE + "_WRITER_PREIMAGE_TOKEN_CHANGED", payload)
    response = cases.command(cur, payload, request)
    require(response == dict(contract_version="cp7.supplier-transfer-outcome.v1", kind="COMMITTED_OUTCOME",
                             action="CREATE", request_id=str(request), request_payload=payload,
                             supplier_id=fixture["supplier"], transfer_id=response.get("transfer_id"),
                             original_transfer_id=None, status="POSTED")
            and isinstance(response["transfer_id"], str), CASE + "_EXACT_PUBLIC_CREATE_OUTCOME_REQUIRED", response)
    return response


def native_state(cur, cases, fixture, outcomes):
    """Check the Native AP, transfer validator, journal, cash and stock/HPP together."""
    cur.execute("set local time zone 'UTC'")
    cases.auth.actor(cur)
    native, = cur.execute("select public.erp_get_supplier_credit_v1(%s::jsonb)",
                          (json.dumps(dict(supplier_id=fixture["supplier"], page=1)),)).fetchone()
    cases.b.api.admin(cur)
    transfers, = cur.execute("""
        select coalesce(jsonb_agg(jsonb_build_object(
          'id',t.id,'number',t.number,'status',t.status,'amount',t.amount::text,
          'payment_date',t.payment_date,'recorded_at',t.recorded_at,'cash_account_id',t.cash_account_id,
          'request_id',t.request_id,'actor',t.actor,
          'valid',cp7_supplier_transfer.valid_transfer_v1(t.id),
          'allocations',(select jsonb_agg(jsonb_build_object(
              'purchase_id',a.purchase_id,'payment_id',a.payment_id,'amount',a.amount::text)
              order by a.purchase_id) from cp7_supplier_transfer.allocations_v1 a where a.transfer_id=t.id),
          'journal',to_jsonb(j),'lines',(select jsonb_agg(to_jsonb(l) order by l.debit desc,l.id)
              from erp.journal_lines l where l.journal_entry_id=j.id)
        ) order by t.recorded_at desc,t.id),'[]') from cp7_supplier_transfer.transfers_v1 t
        left join erp.journal_entries j on j.id=t.journal_id where t.supplier_id=%s
    """, (fixture["supplier"],)).fetchone()
    requests, = cur.execute("""
        select coalesce(jsonb_object_agg(r.request_id,r.response),'{}')
        from cp7_supplier_transfer.requests_v1 r
        where r.payload->>'supplier_id'=%s
    """, (fixture["supplier"],)).fetchone()
    expected_requests = {outcome["request_id"]: outcome for outcome in outcomes}
    by_id = {outcome["transfer_id"]: outcome for outcome in outcomes}
    require(len(by_id) == len(transfers) == len(outcomes) and {row["id"] for row in transfers} == set(by_id)
            and requests == expected_requests, CASE + "_NATIVE_TRANSFERS_AND_REQUESTS_REQUIRED", transfers)
    paid = {purchase: Decimal(0) for purchase in fixture["receipts"]}
    for row in transfers:
        payload = by_id[row["id"]]["request_payload"]
        allocations = {entry["purchase_id"]: entry["amount"] for entry in payload["allocations"]}
        actual_allocations = {entry["purchase_id"]: entry["amount"] for entry in row["allocations"]}
        require(set(allocations) == set(paid) and len(row["allocations"]) == len(paid)
                and actual_allocations == allocations and row["valid"] is True
                and row["status"] == row["journal"]["status"] == "POSTED"
                and row["cash_account_id"] == fixture["cash"] and row["amount"] == payload["amount"]
                and row["request_id"] == by_id[row["id"]]["request_id"] and row["actor"] == fixture["actor"]
                and len(row["lines"]) == 2 and row["journal"]["reversal_of_id"] is None,
                CASE + "_NATIVE_ALLOCATIONS_AND_AGGREGATE_JOURNAL_REQUIRED", row)
        for purchase, amount in allocations.items():
            paid[purchase] += Decimal(amount)
    ap = native["purchases"]
    require({row["id"] for row in ap} == set(paid) and len(ap) == len(paid)
            and all(Decimal(row["final_ap"]) == 1000 and Decimal(row["paid"]) == paid[row["id"]]
                    and Decimal(row["remaining"]) == 1000 - paid[row["id"]] for row in ap),
            CASE + "_NATIVE_AP_TOTAL_PAID_REMAINING_REQUIRED", ap)
    cash = cases.single.misc.cash_balance(cur, fixture["cash"])
    stock_hpp = cases.single.supplier.physical_state(cur)
    require(cash == Decimal(CAPITAL) - sum(paid.values()) and stock_hpp == fixture["stock_hpp"],
            CASE + "_NATIVE_CASH_AND_UNCHANGED_STOCK_HPP_REQUIRED", cash)
    require(cur.execute("select count(*) from cp7_supplier_transfer.context_v1").fetchone() == (0,),
            CASE + "_NATIVE_TRANSFER_CONTEXT_MUST_BE_CLOSED")
    return dict(transfers=transfers, requests=requests, Native_AP=ap, cash=f"{cash:.2f}", stock_HPP=stock_hpp)


def check_pages(first, next_page, native, fixture):
    count = len(native["transfers"])
    require(count in (25, 26), CASE + "_EXACT_25_OR_26_NATIVE_TRANSFERS_REQUIRED", count)
    for offset, response in ((0, first), (PAGE_SIZE, next_page)):
        visible = [{name: row[name] for name in ROW_KEYS}
                   for row in native["transfers"][offset:offset + PAGE_SIZE]]
        expected = dict(rows=visible, total=str(count), offset=offset, limit=PAGE_SIZE,
                        next_offset=PAGE_SIZE if offset == 0 and count == 26 else None)
        require(response["transfers"] == expected, CASE + "_TRANSFER_PAGE_NATIVE_ORDER_OR_COUNT_CHANGED", response)
        receipt_page = response["receipts"]
        amounts = [(row["id"], row["remaining"], "0.00", row["remaining"]) for row in native["Native_AP"]]
        actual = [(row["id"], row["remaining"], row["release_on_correction"], row["payable_after_release"])
                  for row in receipt_page["rows"]]
        require(receipt_page == dict(rows=receipt_page["rows"], total="2", offset=0, limit=PAGE_SIZE,
                                     next_offset=None) and actual == amounts,
                CASE + "_PUBLIC_RECEIPT_CHOICES_MUST_MATCH_NATIVE_AP", receipt_page)
        bank_page = response["cash_accounts"]
        require(bank_page == dict(rows=bank_page["rows"], total="1", offset=0, limit=PAGE_SIZE,
                                  next_offset=None)
                and [row["id"] for row in bank_page["rows"]] == [fixture["cash"]],
                CASE + "_EXACT_FILTERED_FUNDING_BANK_REQUIRED", bank_page)
    require(first["review_token"] == next_page["review_token"], CASE + "_PAGE_REVIEW_TOKENS_DISAGREE")


def seed(cur, cases):
    day = actual_day(cur)
    cases.auth.actor(cur)
    actor, role = cur.execute("""
        select auth.uid()::text, erp.current_app_role()
        where erp.has_permission('warehouse.procurement.view') and erp.has_permission('finance.ap.view')
          and erp.has_permission('finance.ap.pay')
    """).fetchone() or (None, None)
    cases.b.api.admin(cur)
    require(actor == str(cases.auth.base.OPERATOR_AUTH) and role in ("OWNER", "ADMIN"),
            CASE + "_SEEDED_NATIVE_ACTOR_AND_EFFECTIVE_PERMISSIONS_REQUIRED")
    single = cases.single
    master = single.bc.fixture(cur, day, zones=False, purchase=False)
    receipts = []
    for _ in range(2):
        receipt = single.invoice.receipt.fixture(cur, day, "100", "10", True)
        payload = dict(receipt["payload"], supplier_id=master["supplier"])
        draft = single.invoice.receipt.command(cur, "SAVE_DRAFT", payload)
        posted = single.invoice.receipt.post(cur, draft)
        require(posted["status"] == "POSTED", CASE + "_NATIVE_RECEIPT_POST_REQUIRED", posted)
        receipts.append(posted["purchase_id"])
    funding = single.funding.fund(cur, master["cash"], CAPITAL, receipt["day"])
    cases.b.api.admin(cur)
    fixture = dict(actor=actor, role=role, supplier=master["supplier"], cash=master["cash"],
                   bank_code=master["code"], funding_journal=str(funding), receipts=receipts,
                   payment_date=single.invoice.aa.at(day - timedelta(days=1), 12).isoformat(),
                   stock_hpp=single.supplier.physical_state(cur))
    require(single.misc.cash_balance(cur, fixture["cash"]) == Decimal(CAPITAL),
            CASE + "_EXACT_NATIVE_BANK_FUNDING_REQUIRED")
    outcomes = [create(cur, cases, fixture, BASE_AMOUNTS, uuid4()) for _ in range(PAGE_SIZE)]
    cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
    native = native_state(cur, cases, fixture, outcomes)
    raw = []
    first = workspace(cur, cases, fixture, 0, raw)
    next_page = workspace(cur, cases, fixture, PAGE_SIZE, raw)
    check_pages(first, next_page, native, fixture)
    require(actual_day(cur) == day, CASE + "_SETUP_WIB_DAY_CHANGED")
    return fixture, outcomes, native, dict(day=day.isoformat(), fixture=fixture, outcomes=outcomes,
                                           native=native, workspace_raw=raw)


def absent_after_abort(cur, entry):
    children = [allocation["payment_id"] for allocation in entry["allocations"]]
    absent = cur.execute("""
        select not exists (select from cp7_supplier_transfer.transfers_v1 where id=%s)
           and not exists (select from cp7_supplier_transfer.allocations_v1 where transfer_id=%s)
           and not exists (select from erp.supplier_payments where id=any(%s::uuid[]))
           and not exists (select from erp.journal_entries where id=%s or source_id=%s)
           and not exists (select from erp.journal_lines where journal_entry_id=%s)
           and not exists (select from cp7_supplier_transfer.requests_v1 where actor=%s and request_id=%s)
    """, (entry["id"], entry["id"], children, entry["journal"]["id"], entry["id"], entry["journal"]["id"],
          entry["actor"], entry["request_id"])).fetchone()
    require(absent == (True,), CASE + "_ABORTED_TRANSFER_CHILDREN_JOURNAL_OR_REQUEST_REMAIN", entry)


def exercise(*, provider, parent_raw, profile_raw, state, verify, trusted_connection, require_quiet, retain):
    """Run only in the owning restore boundary after its admitted setup and Auth commit."""
    parent, profile = provider.admission.runtime_admission(parent_raw, profile_raw)
    current = state.global_installation
    require(current["parent"] == parent and current["inputs"] == profile and current["contract"] == provider.CONTRACT,
            CASE + "_EXACT_INSTALLED_GLOBAL_PROFILE_REQUIRED")
    scoped = {".".join(row[:2]) for row in current["sealed"]["expected_relations"]}
    require({PAUSE, *PREFIX} <= scoped, CASE + "_LIVE_LOCK_RELATIONS_MUST_BE_SEALED")
    cases = fixture_sources()

    def connect():
        connection = trusted_connection()
        identity = (connection.info.dbname, connection.info.host, connection.info.port, connection.info.user)
        if identity != ("cp6_rollback", "127.0.0.1", 54322, "cp6_maintenance_admission"):
            connection.close()
            raise Refusal(CASE + "_EXACT_DISPOSABLE_MAINTENANCE_CONNECTION_REQUIRED")
        return connection

    require_quiet()
    try:
        with closing(connect()) as connection:
            idle(connection)
            database = begin(connection, read_only=False)
            with connection.cursor() as cur:
                verify(cur)
                provider.verify(cur, current)
                fixture, baseline, before, setup = seed(cur, cases)
            require(connection.execute("COMMIT").statusmessage == "COMMIT", CASE + "_SETUP_COMMIT_REQUIRED")
        setup_receipt = retain("GLOBAL_" + CASE + "_SETUP", setup)
        require_quiet()
    except Exception as error:
        retain_failure(retain, "SETUP", error, [])
        raise

    terminals = {}
    for terminal in ("ABORT", "COMMIT"):
        raw = []
        staged = {}

        def read(cur):
            return workspace(cur, cases, fixture, 0, raw)

        def write(cur, old):
            outcome = create(cur, cases, fixture, NEW_AMOUNTS, uuid4(), old["review_token"])
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
            staged["native"] = native_state(cur, cases, fixture, [*baseline, outcome])
            staged["page25"] = workspace(cur, cases, fixture, PAGE_SIZE, raw)
            return outcome

        proof = None
        try:
            proof = observe(connect, pause_relation=PAUSE, prefix_relations=PREFIX,
                            reader_statement=GETTER.replace("%s", "$1"), read=read, write=write,
                            terminal=terminal, database_anchor=database[1:5])
            outcome = proof["writer_outcome"]
            entry, *prior = staged["native"]["transfers"]
            require(entry["id"] == outcome["transfer_id"] and prior == before["transfers"]
                    and proof["staged"]["review_token"] != proof["old"]["review_token"],
                    CASE + "_NEW_TRANSFER_MUST_LEAD_PAGE_AND_PUSH_OLDEST_TO_26", staged)
            require(reply_bytes(proof["old"]) == reply_bytes(json.loads(setup["workspace_raw"][0]["response"])),
                    CASE + "_BASELINE_TRANSFER_PAGE_CHANGED", proof["old"])
            check_pages(proof["staged"], staged["page25"], staged["native"], fixture)
            with closing(connect()) as connection:
                idle(connection)
                require(begin(connection, read_only=True)[1:5] == database[1:5],
                        CASE + "_FOLLOWING_ORACLE_WRONG_DATABASE")
                with connection.cursor() as cur:
                    committed = terminal == "COMMIT"
                    following = native_state(cur, cases, fixture, [*baseline, outcome] if committed else baseline)
                    require(following == (staged["native"] if committed else before),
                            CASE + "_FOLLOWING_NATIVE_STATE_DIFFERS", following)
                    if not committed:
                        absent_after_abort(cur, entry)
                    following_page25 = workspace(cur, cases, fixture, PAGE_SIZE, raw)
                    check_pages(proof["following"], following_page25, following, fixture)
                connection.execute("ROLLBACK")
            require_quiet()
            reader = proof["reader_pid"]
            writer = proof["writer_pid"]
            require(len(raw) == 6 and [row["pid"] for row in raw[:5]] == [reader, writer, writer, reader, reader]
                    and raw[5]["pid"] not in (reader, writer)
                    and [json.loads(row["response"]) for row in raw]
                    == [proof["old"], staged["page25"], proof["staged"], proof["active"],
                        proof["following"], following_page25], CASE + "_RAW_RPC_BODIES_REQUIRED", raw)
        except Exception as error:
            retain_failure(retain, terminal, error, raw, proof)
            raise
        proof.update(raw_public_requests_responses=raw, staged_native=staged["native"],
                     following_native=following, actual_case_credit=0)
        terminals[terminal] = dict(reader_pid=reader, writer_pid=writer,
                                   original=retain("GLOBAL_" + CASE + "_" + terminal, proof))
    require(len({entry[role] for entry in terminals.values() for role in ("reader_pid", "writer_pid")}) == 4,
            CASE + "_DISTINCT_TERMINAL_BACKENDS_REQUIRED")
    return dict(status=CASE + "_OBSERVED_PENDING_OWNING_RESTORE_AND_GATES",
                setup=setup_receipt, terminals=terminals, actual_case_credit=0, production_go=False)


def retain_failure(retain, phase, error, raw, proof=None):
    retain("GLOBAL_" + CASE + "_" + phase + "_FIRST_FAILURE",
           dict(error=str(error), sqlstate=getattr(error, "sqlstate", None),
                evidence=getattr(error, "evidence", None), raw_public_requests_responses=raw,
                observer=proof, actual_case_credit=0))
