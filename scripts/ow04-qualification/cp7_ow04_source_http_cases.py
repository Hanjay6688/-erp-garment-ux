"""Predeclared real Auth source HTTP cases; registration is not execution.

Native helper calls below are disposable setup or fresh read assertions. Every
source inverse and committed replay calls the real Auth user's public RPC.
No result or token is constructed to impersonate an HTTP response.
"""
from pathlib import Path
from hashlib import sha256
from decimal import Decimal as D
import copy
import json
import uuid

import cp7_ow04_http_cases as initial_http
import cp7_ow04_signed_source_cases as signed
import cp7_ow04_signed_zero_difference_cases as zero_native

initial, nf, cmd = signed.initial, signed.native, signed.cmd
SOURCE_RPC = "erp_cp7_save_sale_v1"
REVIEW_RPC = "erp_cp7_get_sales_v1"
EXPECTED_SHA = "58ee491c469a08ede6c3751353cd4a373804c4df6898cf447f8f93b75d167140"
IDS = (
    "OW04_HTTP_SOURCE_RETURN_REVERSE_CREDIT_COMMIT_REPLAY",
    "OW04_HTTP_SOURCE_PAYMENT_REVERSE_CREDIT_COMMIT_REPLAY",
    "OW04_HTTP_SOURCE_ZERO_DIFF_RETURN_REVERSE_COMMIT_REPLAY",
    "OW04_HTTP_SOURCE_REVOKED_AUTHORITY_FRESH_AND_REPLAY",
    "OW04_HTTP_SOURCE_CONSUMED_REFUND_RETURN_REVERSE_REFUSAL",
    "OW04_HTTP_SOURCE_CHANGED_REQUEST_REFUSAL",
)


def expected():
    raw = Path(__file__).with_name("SOURCE_HTTP_EXPECTED.json").read_bytes()
    assert sha256(raw).hexdigest() == EXPECTED_SHA
    value = json.loads(raw)
    assert tuple(row["id"] for row in value["cases"]) == IDS
    assert value["case_count"] == 6 and value["executed"] is False
    assert value["native_expected_sha256"] == signed.EXPECTED_SHA
    assert value["native_zero_expected_sha256"] == zero_native.EXPECTED_SHA
    return value


def _rows(cur, table, predicate="true", args=()):
    return nf._array(cur, "cp7_credit." + table, predicate, args)


def _request(cur, user, action, payload, version, request, result):
    # Do not call signed._assert_request: its SQL fixture actor is deliberately
    # fixed. HTTP provenance belongs to the actual Auth login used above.
    rows = cur.execute("select action,payload,expected_version,response from cp7_sales.requests "
        "where actor=%s and request_id=%s", (user.auth_user_id, request)).fetchall()
    assert rows == [(action, payload, version, result)]


def _review(http, user, x, action, source):
    before = initial_http.snapshot(http)
    answer = initial_http.response(user.rpc(REVIEW_RPC,
        dict(p_query=dict(sale_id=x["f"]["sale"], q=x["f"]["tag"], limit=1, offset=0))))
    assert initial_http.snapshot(http) == before, "OW04_HTTP_SOURCE_REVIEW_WROTE"
    detail = answer["detail"]
    assert detail["id"] == x["f"]["sale"]
    payload = dict(sale_id=detail["id"], review_token=detail["review_token"],
                  change_reason="Reviewed exact source inverse and retained signed credit")
    payload["return_id" if action == "RETURN_REVERSE" else "payment_id"] = source
    return payload, detail["row_version"]


def _args(action, payload, version, request):
    return dict(p_action=action, p_payload=copy.deepcopy(payload),
                p_request=str(request), p_expected=version)


def _day(http):
    with http.connect()as conn,conn.cursor()as cur:
        value=signed._business_day(cur)
        conn.rollback()
        return value


def _source_command(http,user,args):
    # Same explicit real-day precondition as the frozen Native source cases;
    # never fabricate a physical date for stock clock_timestamp at midnight.
    began=_day(http)
    reply=user.rpc(SOURCE_RPC,copy.deepcopy(args))
    assert _day(http)==began,"OW04_HTTP_SOURCE_FIXTURE_CROSSED_BUSINESS_MIDNIGHT"
    return reply


def _setup(http, today, user, mode="CREDIT"):
    f = initial_http.prepared(http, today, paid="1000.00", profile="OPEN", mode=mode)
    committed = initial_http.committed(http, user, f)  # real HTTP quote/settle/replay
    with http.connect() as conn, conn.cursor() as cur:
        nf.b.api.admin(cur)
        actual = initial._assert_actual(cur, f["x"], f["gold"], f["master"],
            committed["outcome"], committed["request"], f["original_movements"])
        before = signed._preserved(cur, f["x"], actual)
        conn.rollback()
    return dict(f=f, initial=committed, actual=actual, before=before)


def _operation(cur, user, x, action, source, payload, version, request, result, count):
    assert (result["contract_version"], result["kind"], result["action"], result["request_id"], result["sale_id"]) == (
        "cp7.sales-outcome.v1", "COMMITTED_OUTCOME", action, str(request), x["f"]["sale"])
    _request(cur, user, action, payload, version, request, result)
    operations = _rows(cur, "source_operation_materializations_v1", "actor=%s and request_id=%s",
                       (user.auth_user_id, request))["document"]
    assert len(operations) == 1
    op = operations[0]
    assert (op["actor"], op["sale_id"], op["action"], op["source_id"], op["payload"], op["expected_version"]) == (
        user.auth_user_id, x["f"]["sale"], action, source, payload, version)
    assert str(op["operation_ordinal"]) == "1" and op["predecessor_operation_id"] is None
    plans = _rows(cur, "source_operation_plans_v1", "operation_id=%s", (op["operation_id"],))["document"]
    assert len(plans) == count
    assert len(op["plan_manifest"]) == count
    assert {row["plan_id"] for row in plans} == {row["plan_id"] for row in op["plan_manifest"]}
    for row in plans:
        own = _rows(cur, "recognition_plans", "id=%s", (row["plan_id"],))["document"]
        assert len(own) == 1 and (own[0]["actor"], own[0]["request_id"], own[0]["owning_action"]) == (
            user.auth_user_id, str(request), action)
    assert (op["financial_marker_id"] is None) is (count == 0)
    completion = _rows(cur, "source_operation_completions_v1", "operation_id=%s", (op["operation_id"],))["document"]
    assert len(completion) == 1
    final = completion[0]["final_native_source"]["sale"]
    assert (final["status"], str(final["row_version"])) == (result["status"], result["row_version"])
    initial._sha(op["actual_manifest_sha256"])
    initial._sha(completion[0]["final_manifest_sha256"])
    assert _rows(cur, "source_operation_work_v1", "operation_id=%s", (op["operation_id"],))["document"] == []
    # A successful HTTP result has already crossed the actual COMMIT boundary,
    # where deferred owning closure must pass. This connection sees real facts.
    cur.execute("set constraints all immediate")
    return op, completion[0]


def _public_profile(user, x, gold):
    detail = initial_http.response(user.rpc(REVIEW_RPC,
        dict(p_query=dict(sale_id=x["f"]["sale"], limit=1, offset=0))))["detail"]
    assert detail["status"] == gold["sale_status"]
    assert {k: detail["financial"][k] for k in ("gross_total", "net_total", "paid_total", "open_balance")} == dict(
        gross_total=gold["gross"], net_total=gold["net"], paid_total=gold["E"], open_balance=gold["AR"])


def _positive(http, today, user, gold):
    state = _setup(http, today, user)
    f, original = state["f"], state["initial"]["outcome"]
    x, credit, action = f["x"], f["master"], gold["action"]
    source = original["return_id"] if action == "RETURN_REVERSE" else x["f"]["payment"]
    payload, version = _review(http, user, x, action, source)
    request = uuid.uuid4()
    args = _args(action, payload, version, request)
    result = initial_http.response(_source_command(http,user,args))
    native_gold = next(row for row in signed.expected()["cases"] if row["id"] == gold["native_expected_id"])
    with http.connect() as conn, conn.cursor() as cur:
        nf.b.api.admin(cur)
        evidence = signed._assert_positive(cur, x, credit, original, state["actual"],
            native_gold, request, result, state["before"])
        operation, completion = _operation(cur, user, x, action, source,
            payload, version, request, result, 1)
        conn.rollback()
    _public_profile(user, x, gold["after"])
    before = initial_http.snapshot(http)
    assert initial_http.response(user.rpc(SOURCE_RPC, copy.deepcopy(args))) == result
    assert initial_http.snapshot(http) == before, "OW04_HTTP_SOURCE_COMMITTED_REPLAY_CHANGED_FACTS"
    return dict(state=state, args=args, request=request, result=result,
                operation=operation, completion=completion, evidence=evidence)


def _zero_setup(http, today):
    # Reuse the frozen genuine Native setup, including ordinary public-SQL
    # refund0 return followed by actual public quote/settle CREDIT. It does not
    # fabricate posted rows. Only this zero fixture uses SQL-auth setup; its
    # inverse and committed replay below still use the real HttpUser token.
    with http.connect() as conn, conn.cursor() as cur:
        nf.b.api.admin(cur)
        before_acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:
            cur.execute("grant usage on schema erp to authenticated")
        x, credit, earlier, later, cohort, recognition = zero_native._setup(cur, today, zero_native.expected())
        nf.b.api.admin(cur)
        if not had:
            cur.execute("revoke usage on schema erp from authenticated")
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == before_acl
        family = _rows(cur, "return_families", "first_return_id=%s", (later["return_id"],))
        items = nf._array(cur, "erp.sales_return_items", "return_id=%s", (later["return_id"],))
        before = signed._preserved(cur, x, dict(family=family, return_items=items))
        finance = {table: _rows(cur, table) for table in zero_native.FINANCIAL_TABLES}
        earlier_header = nf._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s", (earlier["result"]["return_id"],))
        conn.commit()
    return dict(x=x, credit=credit, earlier=earlier, later=later, cohort=cohort,
                recognition=recognition, before=before, finance=finance, items=items,
                earlier_header=earlier_header)


def _zero(http, today, user, gold):
    state = _zero_setup(http, today)
    x, earlier = state["x"], state["earlier"]
    source = earlier["result"]["return_id"]
    payload, version = _review(http, user, x, "RETURN_REVERSE", source)
    request = uuid.uuid4()
    args = _args("RETURN_REVERSE", payload, version, request)
    result = initial_http.response(_source_command(http,user,args))
    assert (result["action"], result["request_id"], result["sale_id"], result["status"],
            result["return_id"], result["return_status"]) == (
        "RETURN_REVERSE", str(request), x["f"]["sale"], "PAID", source, "REVERSED")
    with http.connect() as conn, conn.cursor() as cur:
        nf.b.api.admin(cur)
        assert signed._profile(cur, x, state["credit"], state["cohort"]["id"]) == gold["after"]
        inverse = signed._assert_actual_inverse(cur, earlier["journal"])
        new_ids = {str(r[0]) for r in cur.execute("select id from erp.journal_entries").fetchall()} - set(state["before"]["journals"])
        assert new_ids == {inverse["document"]["header"]["id"]}
        assert cmd.delta(state["before"]["accounts"], cmd.accounts(cur)) == {
            cmd.mapping(cur, "FG_INVENTORY"): D("-10.00"), cmd.mapping(cur, "COGS"): D("10.00")}
        for table, before in state["finance"].items():
            assert _rows(cur, table) == before, ("OW04_HTTP_ZERO_DIFF_FAKE_FINANCIAL_FACT", table)
        private_after = signed._private(cur)
        for table, before in state["before"]["private"].items():
            assert all(row in private_after[table]["document"] for row in before["document"])
        for ident, old in state["before"]["journals"].items():
            if ident != earlier["journal"]["document"]["header"]["id"]:
                assert nf.journal(cur, ident) == old
        assert nf.journal(cur, state["recognition"]["document"]["header"]["id"]) == state["recognition"]
        nf.assert_payment_unchanged(cur, x)
        assert nf._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s", (state["later"]["return_id"],)) == state["before"]["return_header"]
        assert nf._array(cur, "erp.sales_return_items", "return_id=%s", (state["later"]["return_id"],)) == state["items"]
        assert nf._array(cur, "erp.sales_return_items", "return_id=%s", (source,)) == earlier["items"]
        now_earlier = nf._raw(cur, "select to_jsonb(r)from erp.sales_returns r where id=%s", (source,))["document"]
        assert dict(now_earlier, status=state["earlier_header"]["document"]["status"]) == state["earlier_header"]["document"]
        assert nf._array(cur, "erp.sales_items", "sale_id=%s", (x["f"]["sale"],)) == state["before"]["sale_items"]
        assert nf._raw(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a "
            "join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s", (x["f"]["sale"],)) == state["before"]["allocations"]
        assert nf._raw(cur, "select to_jsonb(h)-array['status','row_version','updated_at']from erp.sales_headers h where id=%s",
            (x["f"]["sale"],)) == state["before"]["sale_identity"]
        assert nf._raw(cur, "select to_jsonb(l)-array['cached_qty_pcs','is_open']from erp.fg_lots l where id=%s",
            (x["f"]["lot"],)) == state["before"]["lot_identity"]
        assert nf._array(cur, "erp.hpp_versions", "lot_id=%s", (x["f"]["lot"],)) == state["before"]["hpp"]
        stock = nf._array(cur, "erp.fg_stock_movements", "lot_id=%s", (x["f"]["lot"],))["document"]
        old = state["before"]["stock"]["document"]
        assert all(row in stock for row in old)
        additions = [row for row in stock if row["id"] not in {r["id"] for r in old}]
        assert len(additions) == 1
        move, original = additions[0], earlier["movement"]
        assert (move["movement_type"], move["source_type"], move["source_id"], move["reversal_of_id"],
                D(str(move["qty_signed"])), D(str(move["unit_hpp_snapshot"]))) == (
            "REVERSAL", "FG_MOVEMENT_REVERSAL", original["id"], original["id"], D("-1"), D("10.00"))
        assert all(move[key] == original[key] for key in ("product_id", "lot_id", "location_id", "quality_grade", "customer_id"))
        pair = (inverse["document"]["header"]["economic_date"], inverse["document"]["header"]["transaction_date"])
        assert cur.execute("select m.physical_at>=o.physical_at and(m.physical_at at time zone'Asia/Jakarta')::date=%s::date "
            "from erp.fg_stock_movements m join erp.fg_stock_movements o on o.id=m.reversal_of_id where m.id=%s",
            (pair[0], move["id"])).fetchone() == (True,)
        assert cur.execute("select cached_qty_pcs from erp.fg_lots where id=%s", (x["f"]["lot"],)).fetchone() == (6,)
        operation, completion = _operation(cur, user, x, "RETURN_REVERSE", source,
            payload, version, request, result, 0)
        assert operation["actual_objects"] == [] and operation["financial_marker_id"] is None
        for key in ("before_ordinal_result", "actual_ordinal_result"):
            families = operation[key]["families"]
            assert len(families) == 2 and all(row["reconciliation_components"] == [] and row["has_reconciliation_effect"] is False for row in families)
        assert _rows(cur, "source_operation_part_seals_v1", "operation_id=%s", (operation["operation_id"],))["document"] == []
        conn.rollback()
    _public_profile(user, x, gold["after"])
    before = initial_http.snapshot(http)
    assert initial_http.response(user.rpc(SOURCE_RPC, copy.deepcopy(args))) == result
    assert initial_http.snapshot(http) == before
    return dict(status="PASS", real_auth=True, real_HTTP_source_commit_and_replay=True,
                actual_auth_user_id=user.auth_user_id, source_operation_id=operation["operation_id"],
                completion=completion, outcome=result, source_inverse=inverse,
                zero_ADJ_and_zero_financial_marker=True, production_go=False)


def http_cases(http, today):
    values = expected()["cases"]
    users = {}
    def owner():
        if "owner" not in users:
            users["owner"] = http.login("OWNER", label="ow04-source-http-owner")
        return users["owner"]
    def positive(index):
        user = owner()
        result = _positive(http, today, user, values[index])
        return dict(status="PASS", real_auth=True, real_HTTP_source_commit_and_replay=True,
            actual_auth_user_id=user.auth_user_id, actual_source_operation=result["operation"],
            actual_completion=result["completion"], actual_outcome=result["result"],
            actual_financial_evidence=result["evidence"], production_go=False)
    def revoked():
        user = owner()
        result = _positive(http, today, user, values[0])
        x = result["state"]["f"]["x"]
        payload, version = _review(http, user, x, "PAYMENT_REVERSE", x["f"]["payment"])
        fresh = _args("PAYMENT_REVERSE", payload, version, uuid.uuid4())
        # Preserve another real active OWNER; no forged Auth UUID/token.
        http.login("OWNER", label="ow04-source-http-owner-keeper")
        with http.connect() as conn, conn.cursor() as cur:
            prior = cur.execute("select is_active from erp.app_users where auth_user_id=%s", (user.auth_user_id,)).fetchone()
            assert prior == (True,)
            cur.execute("update erp.app_users set is_active=false where auth_user_id=%s", (user.auth_user_id,))
            assert cur.rowcount == 1
            conn.commit()
        before = initial_http.snapshot(http)
        try:
            for args in (result["args"], fresh):
                denied = initial_http.response(user.rpc(SOURCE_RPC, copy.deepcopy(args)), 403, "CP7_SALES_ACCESS_DENIED")
                assert denied["code"] == "42501"
                assert initial_http.snapshot(http) == before
        finally:
            with http.connect() as conn, conn.cursor() as cur:
                cur.execute("update erp.app_users set is_active=%s where auth_user_id=%s", (prior[0], user.auth_user_id))
                assert cur.rowcount == 1
                conn.commit()
        return dict(status="PASS", actual_Auth_membership_revocation=True,
                    cached_and_fresh_source_HTTP_denied=True, partial_effects=0, production_go=False)
    def consumed():
        user = owner()
        state = _setup(http, today, user, "REFUND")
        x, outcome = state["f"]["x"], state["initial"]["outcome"]
        events = state["actual"]["consumptions"]["document"]
        assert len(events) == 1 and events[0]["event_kind"] == "REFUND" and D(str(events[0]["amount"])) == D("200.00")
        event = events[0]
        with http.connect() as conn, conn.cursor() as cur:
            nf.b.api.admin(cur)
            assert signed._profile(cur, x, state["f"]["master"], event["cohort_id"]) == values[4]["before"]
            conn.rollback()
        payload, version = _review(http, user, x, "RETURN_REVERSE", outcome["return_id"])
        before = initial_http.snapshot(http)
        denied = initial_http.response(user.rpc(SOURCE_RPC,
            _args("RETURN_REVERSE", payload, version, uuid.uuid4())), 400, "CP7_CREDIT_SOURCE_CONSUMERS_REQUIRE_UNDO")
        assert denied["code"] == "P0001"
        detail = json.loads(denied["details"])
        cohort = state["actual"]["cohorts"]["document"][0]
        assert detail == [dict(event_id=event["id"],cohort_id=event["cohort_id"],event_kind="REFUND",
            journal_id=event["journal_id"],source_sale_id=cohort["source_sale_id"],
            source_return_id=cohort["source_return_id"])], "OW04_HTTP_SOURCE_EXACT_CONSUMER_DEPENDENCY"
        assert initial_http.snapshot(http) == before
        return dict(status="PASS", real_HTTP_consumer_refusal=True, actual_consumer=event,
                    actual_refusal=denied, partial_effects=0, production_go=False)
    def changed():
        user = owner()
        result = _positive(http, today, user, values[0])
        before = initial_http.snapshot(http)
        mutations = []
        a = copy.deepcopy(result["args"]); a["p_payload"]["change_reason"] += " changed valid intent"; mutations.append(a)
        a = copy.deepcopy(result["args"]); a["p_payload"]["return_id"] = str(uuid.uuid4()); mutations.append(a)
        a = copy.deepcopy(result["args"]); a["p_expected"] = str(int(a["p_expected"]) + 1); mutations.append(a)
        for args in mutations:
            denied = initial_http.response(user.rpc(SOURCE_RPC, args), 400, "CP7_SALES_REQUEST_CHANGED")
            assert denied["code"] == "P0001"
            assert initial_http.snapshot(http) == before
        return dict(status="PASS", real_HTTP_changed_cached_request_refused=True,
                    changed_payload_source_and_version_refused=True, partial_effects=0, production_go=False)
    return list(zip(IDS, [lambda: positive(0), lambda: positive(1),
        lambda: _zero(http, today, owner(), values[2]), revoked, consumed, changed]))
