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
VENDOR_B = uuid.UUID("10000000-0000-4000-8000-00000000000b")
COMPONENT = uuid.UUID("20000000-0000-4000-8000-000000000002")
OTHER_COMPONENT = uuid.UUID("20000000-0000-4000-8000-00000000000b")
UNKNOWN_COMPONENT = uuid.UUID("20000000-0000-4000-8000-00000000000c")
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
    policy = exact_source("scripts/cp6_bd_objects_policy.sql")
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
                    select case when p_component='20000000-0000-4000-8000-00000000000c'::uuid
                        then 'UNKNOWN' else 'KNOWN' end::text,
                        case when p_component='20000000-0000-4000-8000-00000000000c'::uuid
                            then null else 1000 end::numeric,
                        '70000000-0000-4000-8000-000000000007'::uuid
                $$
            """)
            cur.execute(
                "insert into erp.bd_laundry_components_v1 values(%s,%s,'Whisker',true)",
                (COMPONENT, VENDOR),
            )
            cur.execute(
                "insert into erp.bd_laundry_components_v1 values(%s,%s,'Whisker',true),(%s,%s,'Spray',true)",
                (OTHER_COMPONENT, VENDOR_B, UNKNOWN_COMPONENT, VENDOR),
            )
            cur.execute(function(pricing, "bd_split_amount_v1"))
            cur.execute(function(pricing, "bd_component_charge_v1"))
            cur.execute(function(policy, "bd_amount_v1"))
            component_input = {"component_id": str(COMPONENT), "covered_qty": 5}
            row = cur.execute(
                """select erp.bd_component_charge_v1(%s,%s::jsonb,now(),
                           array[%s,%s]::uuid[],array[8,5]::integer[],13,
                           'COMPONENT',array[]::uuid[])""",
                (VENDOR, json.dumps(component_input), SIZE_M, SIZE_L),
            ).fetchone()[0]
            shares = [x["amount"] for x in row["shares"]]
            assert Decimal(row["amount"]) == Decimal("5000.00") and [Decimal(x) for x in shares] == [Decimal("3076.92"), Decimal("1923.08")], row
            try:
                cur.execute("""select erp.bd_component_charge_v1(%s,%s::jsonb,now(),
                    array[%s,%s]::uuid[],array[8,5]::integer[],13,'COMPONENT',array[]::uuid[])""",
                    (VENDOR, json.dumps({"component_id": str(OTHER_COMPONENT), "covered_qty": 5}), SIZE_M, SIZE_L))
                other_vendor = "UNEXPECTED_SUCCESS"
            except psycopg.Error as error:
                other_vendor = error.diag.message_primary
            assert "BD_COMPONENT_UNKNOWN" in other_vendor, other_vendor
            unknown = cur.execute("""select erp.bd_component_charge_v1(%s,%s::jsonb,now(),
                array[%s,%s]::uuid[],array[8,5]::integer[],13,'COMPONENT',array[]::uuid[])""",
                (VENDOR, json.dumps({"component_id": str(UNKNOWN_COMPONENT), "covered_qty": 5}), SIZE_M, SIZE_L)).fetchone()[0]
            assert unknown["rate_status"] == "UNKNOWN" and unknown["amount"] is None and all(
                x["amount"] is None for x in unknown["shares"]), unknown
            try:
                cur.execute("select erp.bd_amount_v1('\"0.00\"'::jsonb,'rate',true)")
                zero_rate = "UNEXPECTED_SUCCESS"
            except psycopg.Error as error:
                zero_rate = error.diag.message_primary
            assert "BD_AMOUNT_INVALID" in zero_rate, zero_rate

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

            # Execute the unmodified POST_INVOICE function itself with the
            # smallest schema needed to reach its billing-line weight loop.
            cur.execute("create table erp.laundry_vendors(id uuid primary key)")
            cur.execute("create table erp.vendor_invoices(vendor_id uuid, invoice_number text, status text)")
            cur.execute("create table erp.laundry_delivery_lines(id uuid primary key, cutting_group_id uuid)")
            cur.execute("create table erp.laundry_receipt_lines(id uuid primary key, delivery_line_id uuid)")
            cur.execute("create table erp.bd_opening_laundry_uninvoiced_v1(id uuid primary key)")
            cur.execute("""
                create table erp.bd_laundry_invoices_v1(
                    id uuid primary key, vendor_id uuid, invoice_number text,
                    invoice_date date, status text, row_version bigint,
                    corrects_invoice_id uuid, discount_amount numeric(18,2),
                    tax_amount numeric(18,2), rounding_amount numeric(18,2),
                    header_total numeric(18,2))
            """)
            cur.execute("""
                create table erp.bd_laundry_invoice_lines_v1(
                    id uuid primary key, invoice_id uuid, line_no integer,
                    line_kind text, receipt_line_id uuid,
                    opening_uninvoiced_id uuid, amount numeric(18,2))
            """)
            cur.execute("create function erp.require_owner_admin() returns void language plpgsql as $$ begin return; end $$")
            cur.execute("create function erp.require_permission(text) returns void language plpgsql as $$ begin return; end $$")
            cur.execute("""
                create function erp._cp3_assert_closed_json_object(jsonb,text[],text[],text)
                returns void language plpgsql as $$ begin return; end $$
            """)
            cur.execute("""
                create function erp.bd_require_policy_v1(text,text)
                returns jsonb language sql as $$ select '{"billable":["GOOD"]}'::jsonb $$
            """)
            cur.execute("create function erp.bd_policy_version_v1(text) returns integer language sql as $$ select 1 $$")
            cur.execute(function(invoice, "bd_post_invoice_v1"))
            invoice_id = uuid.UUID("80000000-0000-4000-8000-000000000008")
            opening_id = uuid.UUID("90000000-0000-4000-8000-000000000009")
            cur.execute("insert into erp.laundry_vendors values(%s)", (VENDOR,))
            cur.execute("insert into erp.bd_opening_laundry_uninvoiced_v1 values(%s)", (opening_id,))
            cur.execute("""
                insert into erp.bd_laundry_invoices_v1
                    values(%s,%s,'INV-22M','2026-09-26','DRAFT',1,null,0,0,0,22000000.00)
            """, (invoice_id, VENDOR))
            cur.execute("""
                insert into erp.bd_laundry_invoice_lines_v1
                    values(%s,%s,1,'BILL',null,%s,22000000.00)
            """, (uuid.uuid4(), invoice_id, opening_id))
            try:
                cur.execute("select erp.bd_post_invoice_v1(%s::jsonb,%s)",
                    (json.dumps({"invoice_id": str(invoice_id), "expected_version": "1"}), uuid.uuid4()))
                actual_post = "UNEXPECTED_SUCCESS"
            except psycopg.errors.NumericValueOutOfRange as error:
                actual_post = error.sqlstate
            invoice_after = cur.execute("select status from erp.bd_laundry_invoices_v1 where id=%s", (invoice_id,)).fetchone()[0]
            assert actual_post == "22003" and invoice_after == "DRAFT", (actual_post, invoice_after)

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
                "bd_reverse_invoice_v1",
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
            try:
                cur.execute(
                    "select erp.save_laundry_bd_action_v1('SET_REDYE_PRICE','{}'::jsonb,%s)",
                    (uuid.uuid4(),),
                )
                redye = "UNEXPECTED_SUCCESS"
            except psycopg.Error as error:
                redye = error.diag.message_primary
            assert "BD_ACTION_UNKNOWN" in redye, redye
            print(json.dumps({
                "candidate": BASE,
                "label": "ISOLATED_SOURCE_FUNCTIONS_ONLY",
                "component_partial": {"size_8": shares[0], "size_5": shares[1],
                    "total": row["amount"], "expected_if_only_size_5_serviced": ["0.00", "5000.00"]},
                "component_cross_vendor": other_vendor,
                "unknown_price": {"status": unknown["rate_status"], "amount": unknown["amount"],
                    "size_shares": [x["amount"] for x in unknown["shares"]]},
                "zero_rate_without_free_policy": zero_rate,
                "invoice_weight": overflow,
                "invoice_post_22m": {"sqlstate": actual_post, "status_after": invoice_after},
                "replay_after_permission_revoked": {
                    "first_saved": first["status"], "replayed_after_revocation": replay["replayed"],
                    "new_request_after_revocation": new_request},
                "redye_from_bd_ui_action": redye,
                "production_go": False,
            }, indent=2))


if __name__ == "__main__":
    main()
