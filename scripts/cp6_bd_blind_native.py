"""Independent business probes on the unmodified full BD T1 schema.

Setup rows are synthetic and privileged; these are function-level business
cases, not claims about authenticated HTTP, UI, or production data.
"""
from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bd-blind-native-results.json"
VENDOR_A = uuid.UUID("a1000000-0000-4000-8000-000000000001")
VENDOR_B = uuid.UUID("b1000000-0000-4000-8000-000000000002")
GARMENT = uuid.UUID("a2000000-0000-4000-8000-000000000001")
SPRAY = uuid.UUID("a2000000-0000-4000-8000-000000000002")
WHISKER = uuid.UUID("a2000000-0000-4000-8000-000000000003")
B_GARMENT = uuid.UUID("b2000000-0000-4000-8000-000000000001")
B_UNKNOWN = uuid.UUID("b2000000-0000-4000-8000-000000000002")
B_NO_VERSION = uuid.UUID("b2000000-0000-4000-8000-000000000003")
PACKAGE = uuid.UUID("a3000000-0000-4000-8000-000000000001")
SIZE_M = uuid.UUID("a4000000-0000-4000-8000-000000000001")
SIZE_L = uuid.UUID("a4000000-0000-4000-8000-000000000002")
PROCESS = uuid.UUID("a5000000-0000-4000-8000-000000000001")
BATCH = uuid.UUID("a6000000-0000-4000-8000-000000000001")


def refuse(cur, query: str, params: tuple, code: str) -> str:
    try:
        cur.execute(query, params)
    except psycopg.Error as error:
        message = error.diag.message_primary
        assert code in message, (code, message)
        return message
    raise AssertionError(f"Expected refusal {code}")


def quote(cur, vendor: uuid.UUID, pricing: dict) -> dict:
    delivery = {"vendor_id": str(vendor), "wash_process_id": str(PROCESS),
        "distribution_batch_id": str(BATCH), "physical_at": "2026-09-26T11:00:00+07:00",
        "target_dyeing_color": "NAVY",
        "lines": [{"size_id": str(SIZE_M), "qty_sent_pcs": 8},
                  {"size_id": str(SIZE_L), "qty_sent_pcs": 5}]}
    return cur.execute("select erp.bd_compute_pricing_v1(%s::jsonb,%s::jsonb)",
        (json.dumps(delivery), json.dumps(pricing))).fetchone()[0]


def main() -> None:
    with psycopg.connect(os.environ["PGURL"], autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("select set_config('request.jwt.claims','{\"role\":\"service_role\"}',false)")
        pending = cur.execute("select count(*) from erp.bd_policy_settings_v1 where status='PENDING_POLICY_VALUE'").fetchone()[0]
        assert pending == 6, pending
        pending_refusal = refuse(cur, "select erp.bd_require_policy_v1('LAU_DEC02','tagihan')", (), "BD_POLICY_PENDING")

        cur.execute("""insert into erp.laundry_vendors(id,vendor_code,vendor_name) values
            (%s,'AUD-A','Audit Vendor A'),(%s,'AUD-B','Audit Vendor B')""", (VENDOR_A, VENDOR_B))
        cur.execute("""insert into erp.bd_laundry_vendor_terms_v1(vendor_id,pricing_mode,pricing_unit,reason)
            values(%s,'PACKAGE','PCS','Audit package'),(%s,'COMPONENTS','PCS','Audit components')""",
            (VENDOR_A, VENDOR_B))
        for cid, vendor, code in (
            (GARMENT, VENDOR_A, "GARMENT"), (SPRAY, VENDOR_A, "SPRAY"),
            (WHISKER, VENDOR_A, "WHISKER"), (B_GARMENT, VENDOR_B, "GARMENT"),
            (B_UNKNOWN, VENDOR_B, "UNKNOWN"), (B_NO_VERSION, VENDOR_B, "NO_VERSION"),
        ):
            cur.execute("""insert into erp.bd_laundry_components_v1
                (id,vendor_id,component_code,component_name) values(%s,%s,%s,%s)""",
                (cid, vendor, code, code.title()))
        for cid, status, price in ((WHISKER, "KNOWN", "1000.00"),
                                  (B_GARMENT, "KNOWN", "2000.00"),
                                  (B_UNKNOWN, "UNKNOWN", None)):
            cur.execute("""insert into erp.bd_laundry_component_rates_v1
                (component_id,rate_status,rate_per_pcs,effective_from,reason)
                values(%s,%s,%s,'2026-09-20T00:00:00+07:00','Audit rate')""",
                (cid, status, price))
        cur.execute("""insert into erp.bd_laundry_packages_v1
            (id,vendor_id,package_code,package_name) values(%s,%s,'GSP','Garment Spray')""",
            (PACKAGE, VENDOR_A))
        cur.execute("insert into erp.bd_laundry_package_components_v1 values(%s,%s),(%s,%s)",
                    (PACKAGE, GARMENT, PACKAGE, SPRAY))
        cur.execute("""insert into erp.bd_laundry_package_rates_v1
            (package_id,rate_per_pcs,effective_from,reason)
            values(%s,12000,'2026-09-20T00:00:00+07:00','Audit fixed package')""", (PACKAGE,))

        extra = {"package_id": str(PACKAGE),
                 "extras": [{"component_id": str(WHISKER), "covered_qty": 5,
                             "reason": "Whisker hanya lima L"}]}
        pending_extra = refuse(cur, "select erp.bd_compute_pricing_v1(%s::jsonb,%s::jsonb)",
            (json.dumps({"vendor_id": str(VENDOR_A), "wash_process_id": str(PROCESS),
              "distribution_batch_id": str(BATCH), "physical_at": "2026-09-26T11:00:00+07:00",
              "target_dyeing_color": "NAVY", "lines": [{"size_id": str(SIZE_M), "qty_sent_pcs": 8},
                {"size_id": str(SIZE_L), "qty_sent_pcs": 5}]}), json.dumps(extra)), "BD_POLICY_PENDING")
        set_policy = cur.execute("""select erp.save_laundry_bd_action_v1('SET_POLICY',%s::jsonb,%s)""",
            (json.dumps({"policy_key": "LAU_DEC03", "operation": "SET",
                "expected_version": "1", "reason": "Audit extra policy",
                "value": {"discount": "REFUSED", "extra": "ALLOWED", "rounding": "REFUSED"}}), uuid.uuid4())).fetchone()[0]
        assert set_policy["status"] == "SAVED" and set_policy["version"] == "2", set_policy

        package_only = quote(cur, VENDOR_A, {"package_id": str(PACKAGE)})
        package_extra = quote(cur, VENDOR_A, extra)
        assert package_only["qty"] == 13 and Decimal(package_only["total_known"]) == 156000, package_only
        assert package_extra["qty"] == 13 and Decimal(package_extra["total_known"]) == 161000, package_extra
        assert [ch["kind"] for ch in package_extra["charges"]] == ["PACKAGE", "EXTRA"], package_extra
        duplicate = refuse(cur, "select erp.bd_compute_pricing_v1(%s::jsonb,%s::jsonb)",
            (json.dumps({"vendor_id": str(VENDOR_A), "wash_process_id": str(PROCESS),
              "distribution_batch_id": str(BATCH), "physical_at": "2026-09-26T11:00:00+07:00",
              "target_dyeing_color": "NAVY", "lines": [{"size_id": str(SIZE_M), "qty_sent_pcs": 8},
                {"size_id": str(SIZE_L), "qty_sent_pcs": 5}]}),
             json.dumps({"package_id": str(PACKAGE), "extras": [{"component_id": str(GARMENT),
                 "covered_qty": 5, "reason": "Double included"}]})), "BD_COMPONENT_ALREADY_INCLUDED")
        wrong_vendor = refuse(cur, "select erp.bd_compute_pricing_v1(%s::jsonb,%s::jsonb)",
            (json.dumps({"vendor_id": str(VENDOR_B), "wash_process_id": str(PROCESS),
              "distribution_batch_id": str(BATCH), "physical_at": "2026-09-26T11:00:00+07:00",
              "target_dyeing_color": "NAVY", "lines": [{"size_id": str(SIZE_M), "qty_sent_pcs": 8},
                {"size_id": str(SIZE_L), "qty_sent_pcs": 5}]}),
             json.dumps({"components": [{"component_id": str(WHISKER), "covered_qty": 5}]})),
            "BD_COMPONENT_UNKNOWN")
        b_partial = quote(cur, VENDOR_B, {"components": [{"component_id": str(B_GARMENT), "covered_qty": 5}]})
        assert Decimal(b_partial["total_known"]) == 10000 and b_partial["qty"] == 13, b_partial
        b_unknown = quote(cur, VENDOR_B, {"components": [
            {"component_id": str(B_GARMENT), "covered_qty": 5},
            {"component_id": str(B_UNKNOWN), "covered_qty": 5}]})
        assert b_unknown["complete"] is False and Decimal(b_unknown["total_known"]) == 10000, b_unknown
        assert b_unknown["charges"][1]["rate_status"] == "UNKNOWN" and b_unknown["charges"][1]["amount"] is None
        no_version = refuse(cur, "select erp.bd_compute_pricing_v1(%s::jsonb,%s::jsonb)",
            (json.dumps({"vendor_id": str(VENDOR_B), "wash_process_id": str(PROCESS),
              "distribution_batch_id": str(BATCH), "physical_at": "2026-09-26T11:00:00+07:00",
              "target_dyeing_color": "NAVY", "lines": [{"size_id": str(SIZE_M), "qty_sent_pcs": 8},
                {"size_id": str(SIZE_L), "qty_sent_pcs": 5}]}),
             json.dumps({"components": [{"component_id": str(B_NO_VERSION), "covered_qty": 5}]})),
            "BD_COMPONENT_RATE_NOT_EXACT")
        redye = refuse(cur, "select erp.save_laundry_bd_action_v1('SET_REDYE_PRICE','{}'::jsonb,%s)",
            (uuid.uuid4(),), "BD_ACTION_UNKNOWN")
        result = {"status": "FULL_SCHEMA_FUNCTION_PROBES", "candidate": "08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec",
            "pending_default": pending, "pending_invoice_policy": pending_refusal,
            "package_total": package_only["total_known"], "package_plus_extra_total": package_extra["total_known"],
            "package_duplicate_refusal": duplicate, "pending_extra_refusal": pending_extra,
            "cross_vendor_refusal": wrong_vendor, "partial_component_total": b_partial["total_known"],
            "unknown_known_subtotal": b_unknown["total_known"], "unknown_complete": b_unknown["complete"],
            "missing_rate_refusal": no_version, "redye_router_refusal": redye,
            "production_go": False}
        OUT.write_text(json.dumps(result, indent=2) + "\n")
        print(OUT.read_text(), flush=True)


if __name__ == "__main__":
    main()
