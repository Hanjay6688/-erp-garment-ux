"""Lawful opening-HPP fixture for the first Global refusal paths."""

from decimal import Decimal
from uuid import UUID, uuid4


ISSUE = "RELEVANT_EXISTING_CLASS_OR_IDENTITY_ADAPTER_REQUIRED"
CASE_IDS = (
    "GLOBAL_DIRTY_D1_REVIEW_REFUSED",
    "GLOBAL_DIRTY_E_REVIEW_REFUSED",
    "GLOBAL_DIRTY_SOURCE_RETURN_REVERSE_REFUSED",
)
INSPECT = "select cp7_global_nonpo_native_graph.inspect_v1(%s::uuid[])"
CORRECTION = """
select l.product_id::text,l.lot_origin,l.po_id,l.initial_qty_pcs,
       c.previous_hpp_snapshot,c.corrected_hpp,c.effective_date,h.is_current,h.total_cost
from erp.opening_hpp_corrections c
join erp.fg_lots l on l.id=c.lot_id
join erp.hpp_versions h on h.id=c.hpp_version_id and h.lot_id=l.id
where c.id=%s and c.lot_id=%s
"""


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def graph(cur, sale_id):
    evidence, = cur.execute(INSPECT, ([UUID(str(sale_id))],)).fetchone()
    require(evidence["contract"] == "cp7.global-nonpo-native-graph.readonly-inspector.v1"
            and evidence["authority"]["known_functions_exact"] is True
            and evidence["authority"]["new_private_acl_closed"] is True
            and evidence["read_only"] is True, "GLOBAL_DIRTY_EXACT_INSPECTOR_AUTHORITY_REQUIRED")
    return evidence


def witness(cur, lanes, today, sale, product, location):
    require(cur.connection.info.host in ("127.0.0.1", "localhost")
            and cur.connection.info.port == 54322 and cur.connection.info.dbname == "cp6_rollback",
            "GLOBAL_DIRTY_FIXED_OWNING_DATABASE_REQUIRED")
    lanes.verify_child(cur)
    native = lanes.graph.moving.f
    native.admin(cur)
    before = graph(cur, sale)
    require(before["status"] == "OBSERVED_QUIESCENT_SOURCE_ONLY" and before["issues"] == []
            and str(product) in before["scope"]["relevant"]["product_ids"],
            "GLOBAL_DIRTY_SAME_CLEAN_RELEVANT_PRODUCT_REQUIRED")
    lot = native.opening(cur, product, 1, "10.00", today, location)
    correction = native.b.internal(cur, "post_opening_hpp_correction", lot, Decimal("11.00"),
                                   "Uji terisolasi koreksi HPP saldo awal", today)
    native.admin(cur)
    row = cur.execute(CORRECTION, (correction, lot)).fetchone()
    require(row == (str(product), "OPENING", None, 1, Decimal("10.00"), Decimal("11.00"),
                    today, True, Decimal("11.00")), "GLOBAL_DIRTY_LAWFUL_OPENING_HPP_CORRECTION_REQUIRED")
    after = graph(cur, sale)
    require(after["status"] == "OBSERVED_REFUSAL_SOURCE_ONLY" and after["issues"] == [ISSUE]
            and after["scope"]["financial_sale_ids"] == before["scope"]["financial_sale_ids"]
            and str(lot) in after["scope"]["relevant"]["lot_ids"]
            and str(lot) not in before["scope"]["relevant"]["lot_ids"]
            and after["basis_sha256"] != before["basis_sha256"],
            "GLOBAL_DIRTY_EXACT_LAWFUL_RELEVANT_BRANCH_REQUIRED")
    return dict(sale=str(sale), product=str(product), lot=str(lot), correction=str(correction),
                previous_HPP="10.00", corrected_HPP="11.00", business_day=today.isoformat(),
                clean_inspector=before, dirty_inspector=after)


def finish(cur, lanes, evidence, state, refusal, expected):
    lanes.graph.moving.f.admin(cur)
    require(refusal["sqlstate"] == "P0001" and refusal["message"] == expected,
            "GLOBAL_DIRTY_EXACT_FIRST_REFUSAL_REQUIRED")
    require(graph(cur, evidence["sale"]) == evidence["dirty_inspector"]
            and lanes.full_state(cur) == state, "GLOBAL_DIRTY_REFUSAL_CHANGED_ROWS_SEQUENCES_OR_FULL25")
    return dict(status="PASS", lawful_fixture=evidence, refusal=refusal,
                full25_rows_sequences_unchanged=True)


def d1_case(cur, today, lanes):
    d1 = lanes.graph.d1
    pair = d1.fixture.prepare(cur, today)
    request, version, quote = d1.payload(cur, pair)
    require(quote["state"] == "READY" and quote["source_authority_proven"] is True,
            "GLOBAL_DIRTY_D1_VALID_CLEAN_REQUEST_REQUIRED")
    f = pair["source"]["f"]
    evidence = witness(cur, lanes, today, f["sale"], f["product"], f["location"])
    state = lanes.full_state(cur)
    expected = "CP7_CREDIT_DE_REVIEW_REFUSED"
    outcome = d1.refusal(cur, pair, lambda: d1.correction.correct(cur, request, version, uuid4()), expected)
    return finish(cur, lanes, evidence, state, outcome, expected)


def e_case(cur, today, lanes):
    e = lanes.graph.e
    pair = e.fixture.prepare(cur, today)
    e.basic.apply(cur, pair, "80.00")
    request, version, basis = e.intent(cur, pair)
    require(basis["issues"] == [] and request["credit_carry_review"]["transfer_amount"] == "80.00",
            "GLOBAL_DIRTY_E_VALID_CLEAN_REQUEST_REQUIRED")
    f = pair["target"]
    evidence = witness(cur, lanes, today, f["sale"], f["product"], f["location"])
    state = lanes.full_state(cur)
    expected = "CP7_CREDIT_NOTE_CARRY_REVIEW_REFUSED"
    outcome = e.refusal(cur, pair, lambda: e.note.correct(cur, request, version, uuid4()), expected)
    return finish(cur, lanes, evidence, state, outcome, expected)


def source_case(cur, today, lanes, signed):
    action = "RETURN_REVERSE"
    setup, _, original, _ = signed._setup(cur, today)
    request, version = signed._intent(cur, setup, original, action)
    f = setup["f"]
    evidence = witness(cur, lanes, today, f["sale"], f["product"], f["location"])
    state = lanes.full_state(cur)
    expected = "CP7_CREDIT_SOURCE_GLOBAL_HPP_GRAPH_UNQUALIFIED"
    outcome = signed._refuse(cur, lambda: signed.cmd.command(cur, action, request, version, uuid4()),
                             "P0001", expected)
    return finish(cur, lanes, evidence, state, outcome, expected)
