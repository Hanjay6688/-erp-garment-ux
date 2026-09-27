"""Independent, isolated PostgreSQL probes against exact BD source functions.

The disposable schema only supplies the minimum prerequisites for those
functions. No production database, writer fixture, or writer oracle is used.
This verifies local function behavior, not end-to-end ERP acceptance.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from decimal import Decimal
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
BASE = "08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec"
VENDOR = uuid.UUID("10000000-0000-4000-8000-000000000001")
COMPONENT = uuid.UUID("20000000-0000-4000-8000-000000000002")
SIZE_M = uuid.UUID("30000000-0000-4000-8000-000000000003")
SIZE_L = uuid.UUID("40000000-0000-4000-8000-000000000004")
ACTOR = uuid.UUID("50000000-0000-4000-8000-000000000005")
REQUEST = uuid.UUID("60000000-0000-4000-8000-000000000006")


def exact_source(relative: str) -> str:
    present = (ROOT / relative).read_text()
    original = subprocess.check_output(["git", "show", f"{BASE}:{relative}"], cwd=ROOT, text=True)
    assert present == original, f"CANDIDATE_SOURCE_DRIFT: {relative}"
    return original


def function(source: str, name: str) -> str:
    marker = f"CREATE OR REPLACE FUNCTION erp.{name}("
    start = source.index(marker)
    match = re.search(r"\$function\$;", source[start:])
    assert match, name
    return source[start : start + match.end()]


def main() -> None:
    pricing = exact_source("scripts/cp6_bd_objects_pricing.sql")
    invoice = exact_source("scripts/cp6_bd_objects_invoice.sql")
    router = exact_source("scripts/cp6_bd_objects_router.sql")
    assert "v_weights:=v_weights||round(l.amount*100)::integer" in invoice
    assert "v_split:=erp.bd_split_amount_v1(v_amount,p_qtys)" in pricing
    assert "return v_prior.response||jsonb_build_object('replayed',true)" in router

    with psycopg.connect(os.environ["PGURL"], autocommit=True) as connection:
        with connection.cursor() as cur:
            cur.execute("create schema erp")
            cur.execute("""
                create table erp.bd_laundry_components_v1(
                    id uuid primary key, vendor_id uuid not null, component_name text not null,
                    is_active boolean not null)
            """)
            cur.execute("""
                create table erp.bd_requests_v1(
                    request_id uuid primary key, action text not null, actor uuid,
                    payload jsonb not null, response jsonb not null)
            """)
            cur.execute("""
                create function erp.bd_uuid_v1(p jsonb, f text, required boolean)
                returns uuid language sql immutable as $$
                    select (p->>f)::uuid
                $$
            """)
            cur.execute("""
                create function erp.bd_qty_v1(p jsonb, f text)
                returns integer language sql immutable as $$
                    select (p#>>'{}')::integer
                $$
            """)
            cur.execute("""
                create function erp.bd_component_rate_at_v1(
                    p_component uuid,p_at timestamptz,
                    out rate_status text,out rate_per_pcs numeric,out version_id uuid)
                language sql stable as $$
                    select 'KNOWN'::text,1000::numeric,
                           '70000000-0000-4000-8000-000000000007'::uuid
                $$
            """)
            cur.execute(
                "insert into erp.bd_laundry_components_v1 values(%s,%s,'Whisker',true)",
                (COMPONENT, VENDOR),
            )
            cur.execute(function(pricing, "bd_split_amount_v1"))
            cur.execute(function(pricing, "bd_component_charge_v1"))
            component_input = {"component_id": str(COMPONENT), "covered_qty": 5}
            row = cur.execute(
                """select erp.bd_component_charge_v1(%s,%s::jsonb,now(),
                           array[%s,%s]::uuid[],array[8,5]::integer[],13,
                           'COMPONENT',array[]::uuid[])""",
                (VENDOR, json.dumps(component_input), SIZE_M, SIZE_L),
            ).fetchone()[0]
            shares = [x["amount"] for x in row["shares"]]
            assert Decimal(row["amount"]) == Decimal("5000.00") and shares == ["3076.92", "1923.08"], row

            overflow = []
            for amount in ("21474836.47", "21474836.48", "22000000.00"):
                try:
                    value = cur.execute(
                        "select round(%s::numeric*100)::integer", (amount,)
                    ).fetchone()[0]
                    overflow.append({"amount": amount, "weight": value})
                except psycopg.errors.NumericValueOutOfRange as error:
                    overflow.append({"amount": amount, "sqlstate": error.sqlstate})
            assert overflow == [
                {"amount": "21474836.47", "weight": 2147483647},
                {"amount": "21474836.48", "sqlstate": "22003"},
                {"amount": "22000000.00", "sqlstate": "22003"},
            ], overflow

            cur.execute("""
                create function erp.current_app_user_id()
                returns uuid language sql stable as $$
                    select current_setting('audit.actor')::uuid
                $$
            """)
            # The unused dispatch branches need signatures to allow the exact
            # router function to compile; only SET_POLICY is called here.
            stubs = [
                "bd_post_priced_delivery_v1", "bd_set_charge_price_v1",
                "bd_save_invoice_draft_v1", "bd_cancel_invoice_draft_v1",
                "bd_post_invoice_v1", "bd_reverse_invoice_v1",
                "bd_set_opening_estimate_v1", "bd_apply_claim_credit_v1",
                "bd_pay_vendor_document_v1", "bd_reverse_vendor_settlement_v1",
            ]
            for name in stubs:
                cur.execute(
                    f"create function erp.{name}(jsonb,uuid) returns jsonb "
                    "language sql as $$ select '{}'::jsonb $$"
                )
            cur.execute("""
                create function erp.bd_save_master_v1(text,jsonb,uuid)
                returns jsonb language sql as $$ select '{}'::jsonb $$
            """)
            cur.execute("""
                create function erp.bd_set_policy_v1(jsonb,uuid)
                returns jsonb language plpgsql as $$
                begin
                    if current_setting('audit.allowed') <> 'on' then
                        raise exception 'PERMISSION_DENIED';
                    end if;
                    return '{"applied":true}'::jsonb;
                end $$
            """)
            cur.execute(function(router, "save_laundry_bd_action_v1"))
            cur.execute("select set_config('audit.actor',%s,false)", (str(ACTOR),))
            cur.execute("select set_config('audit.allowed','on',false)")
            payload = {"policy_key": "LAU_DEC03", "operation": "SET"}
            first = cur.execute(
                "select erp.save_laundry_bd_action_v1('SET_POLICY',%s::jsonb,%s)",
                (json.dumps(payload), REQUEST),
            ).fetchone()[0]
            cur.execute("select set_config('audit.allowed','off',false)")
            replay = cur.execute(
                "select erp.save_laundry_bd_action_v1('SET_POLICY',%s::jsonb,%s)",
                (json.dumps(payload), REQUEST),
            ).fetchone()[0]
            try:
                cur.execute(
                    "select erp.save_laundry_bd_action_v1('SET_POLICY',%s::jsonb,%s)",
                    (json.dumps(payload), uuid.uuid4()),
                )
                new_request = "UNEXPECTED_SUCCESS"
            except psycopg.Error:
                new_request = "PERMISSION_DENIED"
            assert first["applied"] and replay["replayed"] and new_request == "PERMISSION_DENIED"
            print(json.dumps({
                "candidate": BASE,
                "label": "ISOLATED_SOURCE_FUNCTIONS_ONLY",
                "component_partial": {"size_8": shares[0], "size_5": shares[1],
                    "total": row["amount"], "expected_if_only_size_5_serviced": ["0.00", "5000.00"]},
                "invoice_weight": overflow,
                "replay_after_permission_revoked": {
                    "first_saved": first["status"], "replayed_after_revocation": replay["replayed"],
                    "new_request_after_revocation": new_request},
                "production_go": False,
            }, indent=2))


if __name__ == "__main__":
    main()
