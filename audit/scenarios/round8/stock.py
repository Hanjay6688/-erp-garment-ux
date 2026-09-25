"""Independent CP6 stock/import cases for the frozen 9add57e candidate.

Oracle: Master contract 359-379, 1024-1025, 3816-3823.
No native run is claimed by the presence of this file. Writer helpers are used
only for authenticated RPC transport/fixture setup; all decisions below are
independent. Unexpected errors are INCOMPLETE, never a successful refusal.
"""
from datetime import timedelta
from decimal import Decimal
import json
import uuid

import cp6_ao_ap_installed as transport


def _need(condition, message):
    if not condition:
        raise RuntimeError("FIXTURE_INCOMPLETE: " + message)


def _attempt(cur, operation):
    cur.execute("savepoint si_attempt")
    try:
        result = operation()
    except Exception as exc:
        message = getattr(getattr(exc, "diag", None), "message_primary", None) or str(exc)
        sqlstate = getattr(exc, "sqlstate", None)
        cur.execute("rollback to savepoint si_attempt")
        transport.admin(cur)
        cur.execute("release savepoint si_attempt")
        return None, dict(message=message, sqlstate=sqlstate)
    cur.execute("release savepoint si_attempt")
    return result, None


def _call(cur, action, payload, request_id=None):
    return transport.call(cur, action, payload, request_id or uuid.uuid4())


def _invoke(cur, action, batch):
    revision = transport.read(cur, batch)["batch"]["revision"]
    return _call(cur, action, dict(batch_id=batch, expected_revision=revision))


def _fixture(cur, today, finalize=True):
    """Eight identified, valued WIP pcs, two unrelated same-model/size products."""
    code = "SI" + uuid.uuid4().hex[:12]
    batch = _call(cur, "CREATE", dict(batch_code=code, cutover_date=str(today-timedelta(days=8))))["batch_id"]
    rows = {
        "MODEL": [dict(model_code=code, model_name="Independent WIP model")],
        "SIZE": [dict(size_code=code)],
        "BRAND": [dict(brand_code=code+"A", brand_name="Source brand"),
                  dict(brand_code=code+"B", brand_name="Unrelated brand")],
        "PRODUCT": [dict(sku=code+suffix, product_name="Independent "+suffix,
                         model_code=code, brand_code=code+suffix, color_name=color, size_code=code)
                    for suffix, color in [("A", "Blue"), ("B", "Red")]],
        "CONTRACTOR": [dict(contractor_code=code, contractor_name="WIP holder", contractor_type="MANDOR")],
        "LOCATION": [dict(location_code=code, location_name="Independent FG", location_type="FG_WAREHOUSE")],
        "OPEN_PO": [dict(po_number=code, model_code=code, contractor_code=code,
                         target_qty_pcs="8", status="SEWING", current_stage="SEWING")],
        "OPENING_BALANCE_ITEM": [dict(balance_type="WIP", po_number=code, product_sku=code+"A",
                         brand_code=code+"A", model_code=code, color_name="Blue", size_code=code,
                         contractor_code=code, stage="SEWING", qty="8", unit_cost="5", amount="40.00",
                         opening_source_key="WIP", control_key="WIP", accessory_cost_included="true")],
        "OPENING_CONTROL": [dict(control_key="WIP", balance_type="WIP", qty="8", amount="40.00")],
    }
    for entity, payloads in rows.items():
        transport.upload(cur, batch, entity, payloads)
    result = _invoke(cur, "VALIDATE", batch)
    _need(result.get("error_rows") == 0, "valid WIP fixture was refused: "+json.dumps(result, default=str))
    if finalize:
        result = _invoke(cur, "FINALIZE", batch)
        _need(result.get("status") == "POSTED", "WIP fixture not posted: "+json.dumps(result, default=str))
    return dict(batch=batch, code=code)


def _source(cur, fixture):
    sources = transport.read(cur, fixture["batch"])["batch"]["production_sources"]
    _need(len(sources) == 1, "expected precisely one WIP source")
    return sources[0]


def _output_payload(cur, fixture, day, qty="8", suffix="A"):
    source = _source(cur, fixture)
    return dict(batch_id=fixture["batch"], opening_item_id=source["opening_item_id"],
                expected_remaining=str(source["remaining_qty_pcs"]), operation="COMPLETE", qty_pcs=qty,
                product_sku=fixture["code"]+suffix, brand_code=fixture["code"]+suffix,
                location_code=fixture["code"], date=str(day), reason="Independent checked WIP output")


def _facts(cur, item_id):
    return cur.execute("""
      select jsonb_build_object('item',to_jsonb(i),'source',to_jsonb(s),
        'outputs',coalesce((select jsonb_agg(to_jsonb(o) order by o.physical_at,o.id)
            from erp.initial_import_wip_outputs o where o.opening_item_id=i.id),'[]'::jsonb),
        'reversals',coalesce((select jsonb_agg(to_jsonb(r) order by r.physical_at,r.output_id)
            from erp.initial_import_wip_output_reversals r join erp.initial_import_wip_outputs o on o.id=r.output_id
            where o.opening_item_id=i.id),'[]'::jsonb))
      from erp.opening_balance_items i join erp.initial_import_production_sources s on s.opening_item_id=i.id
      where i.id=%s
    """, (item_id,)).fetchone()[0]


def identity_case(cur, today):
    fixture = _fixture(cur, today)
    source = _source(cur, fixture)
    result, error = _attempt(cur, lambda: _call(cur, "WIP_OUTPUT",
                          _output_payload(cur, fixture, today-timedelta(days=2), "4", "B")))
    if error:
        return dict(status="INCOMPLETE", reason="No exact source-identity refusal exists in candidate; do not infer PASS from an error", error=error)
    evidence = cur.execute("""select i.product_id::text,l.product_id::text,p.color_name,b.brand_code,
          lp.color_name,lb.brand_code,i.qty,l.initial_qty_pcs
        from erp.opening_balance_items i join erp.products p on p.id=i.product_id
        join erp.brands b on b.id=p.brand_id
        join erp.fg_lots l on l.id=%s join erp.products lp on lp.id=l.product_id
        join erp.brands lb on lb.id=lp.brand_id where i.id=%s""",
        (result["lot_id"], source["opening_item_id"])).fetchone()
    _need(evidence is not None, "source/output identity evidence missing")
    return dict(status="COUNTEREXAMPLE" if evidence[0] != evidence[1] else "PASS",
                oracle="Identified blue brand-A WIP must not become unrelated red brand-B FG without a conversion source",
                actual=dict(zip(["source_product_id","output_product_id","source_color","source_brand",
                                 "output_color","output_brand","source_qty","output_qty"], evidence)), rpc=result)


def dated_capacity_case(cur, today):
    fixture = _fixture(cur, today)
    first = _call(cur, "WIP_OUTPUT", _output_payload(cur, fixture, today-timedelta(days=3)))
    source = _source(cur, fixture)
    reversal = _call(cur, "WIP_OUTPUT", dict(batch_id=fixture["batch"], opening_item_id=source["opening_item_id"],
                      expected_remaining=str(source["remaining_qty_pcs"]), operation="REVERSE",
                      output_id=first["output_id"], reason="Independent WIP restoration today"))
    second, error = _attempt(cur, lambda: _call(cur, "WIP_OUTPUT",
                          _output_payload(cur, fixture, today-timedelta(days=1))))
    if error:
        return dict(status="INCOMPLETE", reason="No exact dated-WIP capacity refusal exists in candidate; do not infer PASS from an error", error=error)
    timeline = cur.execute("""with e as (
        select id,physical_at,created_at,source_type,stage_from,stage_to,qty_pcs,
          case when stage_to='SEWING' then qty_pcs else 0 end-
          case when stage_from='SEWING' then qty_pcs else 0 end as delta
        from erp.wip_stage_events where po_id=%s
      ) select physical_at::text,source_type,stage_from,stage_to,qty_pcs,
          sum(delta) over(order by physical_at,created_at,id) as sewing_remaining
        from e order by physical_at,created_at,id""", (source["po_id"],)).fetchall()
    minimum = min(row[-1] for row in timeline)
    return dict(status="COUNTEREXAMPLE" if minimum < 0 else "PASS",
                oracle="WIP quantity must remain nonnegative at every physical timeline prefix",
                minimum_sewing_pcs=minimum, timeline=timeline, first=first, reversal=reversal, second=second,
                source=_facts(cur, source["opening_item_id"]))


def retry_case(cur, today):
    fixture = _fixture(cur, today)
    payload = _output_payload(cur, fixture, today-timedelta(days=2), "3")
    request_id = uuid.uuid4()
    first = _call(cur, "WIP_OUTPUT", payload, request_id)
    before = _facts(cur, payload["opening_item_id"])
    replay = _call(cur, "WIP_OUTPUT", payload, request_id)
    after = _facts(cur, payload["opening_item_id"])
    if first != replay or before != after:
        return dict(status="COUNTEREXAMPLE", reason="Identical request replay changed response or source facts", first=first, replay=replay)
    different = dict(payload, qty_pcs="4")
    result, error = _attempt(cur, lambda: _call(cur, "WIP_OUTPUT", different, request_id))
    if error is None:
        return dict(status="COUNTEREXAMPLE", reason="Same UUID accepted different payload", actual=result)
    expected = "client_request_id was already used with a different payload"
    if error["message"] != expected:
        return dict(status="INCOMPLETE", expected_refusal=expected, actual_error=error)
    final = _facts(cur, payload["opening_item_id"])
    return dict(status="PASS" if final == before else "COUNTEREXAMPLE",
                identical_response=first == replay, exact_refusal=error["message"], facts_unchanged=final == before)


def prepared_edit_case(cur, today):
    fixture = _fixture(cur, today, finalize=False)
    transport.ordinary(cur)
    cur.execute("select erp.apply_migration_master_rows(%s)", (fixture["batch"],))
    cur.execute("select erp.apply_migration_open_pos(%s)", (fixture["batch"],))
    header = cur.execute("select erp.prepare_migration_opening_balance(%s)", (fixture["batch"],)).fetchone()[0]
    cur.execute("select set_config('app.change_reason','Independent allowed DRAFT item correction',true)")
    cur.execute("update erp.opening_balance_items set qty=4,amount=20,unit_cost_snapshot=5 where opening_id=%s", (header,))
    _need(cur.rowcount == 1, "expected to edit one prepared WIP item")
    transport.admin(cur)
    result, error = _attempt(cur, lambda: _invoke(cur, "FINALIZE", fixture["batch"]))
    if error:
        return dict(status="INCOMPLETE", reason="No exact prepared-source reconciliation refusal identified", error=error)
    source = cur.execute("""select i.qty,i.amount,s.qty_pcs,s.original_amount,h.status,
            (select sum(qty_pcs) from erp.wip_stage_events where source_type='INITIAL_IMPORT_WIP_OPENING' and source_id=i.id)
        from erp.opening_balance_items i join erp.initial_import_production_sources s on s.opening_item_id=i.id
        join erp.opening_balance_headers h on h.id=i.opening_id where h.id=%s""", (header,)).fetchone()
    _need(source is not None, "prepared-source evidence missing")
    drift = source[4] == "POSTED" and (source[0] != source[2] or source[1] != source[3] or source[0] != source[5])
    return dict(status="COUNTEREXAMPLE" if drift else "INCOMPLETE",
                oracle="Latest editable draft must be reconciled with controls and physical source before posting",
                rpc=result, actual=dict(zip(["item_qty","item_amount","source_qty","source_original_amount","header_status","opening_stage_qty"],source)),
                caveat="Exercises owner-authorized native prepare and ordinary DRAFT item editing; runtime itself grants erp schema USAGE before cases")


def cases(cur, today):
    return [
        ("SI-01-identified-wip-output-identity", lambda: identity_case(cur, today)),
        ("SI-02-reversed-wip-dated-capacity", lambda: dated_capacity_case(cur, today)),
        ("SI-03-wip-retry-exact-envelope", lambda: retry_case(cur, today)),
        ("SI-04-prepared-wip-latest-item", lambda: prepared_edit_case(cur, today)),
    ]
