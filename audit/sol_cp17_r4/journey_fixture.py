"""Synthetic Native starting point and SQL observations for one UI lineage.

Only the existing loopback browser copy is accepted. No business command after
prepare is executed by this helper: the browser must perform every continuation.
"""
from datetime import date, timedelta, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / "auditor"
sys.path.insert(0, str(PRODUCT / "scripts"))
import psycopg
import cp7_cp17_fix_cases as c
import cp7_r3_qc_note_cases as qc

WIB = timezone(timedelta(hours=7))


def prepare(cur, today):
    # Accepted Native receipt/cutting/pickup, no sewing/delivery/receipt/QC/invoice.
    g = c.pickup_fixture(cur, today)
    c.work_rates(cur, g)
    wash = c.laundry_for(cur, g)  # explicit vendor/process rate 2.00 per PCS
    c.bd.invoice_policies(cur, billable=("GOOD",), mode="PRODUCT_COST", after="REFUSE")
    c.b.api.admin(cur)
    product = str(c.bd.chain.base.create_product(cur, "SOLR4-JOURNEY-" + g["po"][:8]))
    bank = str(c.s.cash(cur, "8.00"))
    c.b.api.admin(cur)
    one = lambda sql, args=(): cur.execute(sql, args).fetchone()
    number, po_number = one("select g.group_number,p.po_number from erp.cutting_groups g join erp.production_orders p on p.id=g.po_id where g.id=%s", (g["group"],))
    size, sku = one("select s.size_code,p.sku from erp.products p join erp.sizes s on s.id=p.size_id where p.id=%s", (product,))
    out = dict(group=g["group"], po=g["po"], number=number, po_number=po_number,
               mandor=g["mandor"], vendor=wash["vendor"], process=wash["process"],
               batch=wash["batch"], product=product, size_code=size, sku=sku,
               location=str(c.bd.chain.base.LOCATION), bank=bank, day=str(g["day"]),
               invoice_number="SOLR4-INV-" + g["po"][:16])
    for name, hour in (("sewing", 10), ("send", 11), ("receive", 12), ("qc", 13)):
        out[name + "_local"] = g["at"](hour).astimezone(WIB).strftime("%Y-%m-%dT%H:%M")
    return out


def observe(cur, p):
    c.b.api.admin(cur)
    one = lambda sql, args=(): cur.execute(sql, args).fetchone()
    g, po, vendor = p["group"], p["po"], p["vendor"]
    ready = c.sewn_ready(cur, p)
    works = cur.execute("select id::text,status from erp.work_completion_events where cutting_group_id=%s order by created_at,id", (g,)).fetchall()
    wage = [[wid, state, [str(v) for v in c.wage_journal(cur, wid)]] for wid, state in works]
    deliveries = cur.execute("select id::text,delivery_number,status from erp.laundry_deliveries where vendor_id=%s order by id", (vendor,)).fetchall()
    receipts = cur.execute("select r.id::text,r.receipt_number,r.status,l.id::text,x.id::text,l.qty_good_received from erp.laundry_receipts r join erp.laundry_receipt_lines l on l.receipt_id=r.id join erp.laundry_receipt_batch_size_lines x on x.receipt_line_id=l.id join erp.laundry_deliveries d on d.id=r.delivery_id where d.vendor_id=%s order by r.id,x.id", (vendor,)).fetchall()
    invoices = cur.execute("select id::text,invoice_number,status,total_amount::text from erp.vendor_invoices where vendor_id=%s order by id", (vendor,)).fetchall()
    payments = cur.execute("select v.id::text,v.status,v.amount::text,v.payment_method from erp.vendor_payments v join erp.vendor_invoices i on i.id=v.vendor_invoice_id where i.vendor_id=%s order by v.created_at,v.id", (vendor,)).fetchall()
    ap = one("select coalesce(sum(l.credit-l.debit),0)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR') and j.status in('POSTED','REVERSED')", (vendor,))[0]
    bank = c.balance(cur, p["bank"])
    qs = qc.qc_state(cur, p)
    journals = qc.journals(cur, "x.po_id=%s or x.vendor_id=%s", (po, vendor))
    return dict(sewn=int(ready[0]), ready=int(ready[1]), work=wage,
                deliveries=[list(x) for x in deliveries], receipts=[list(x) for x in receipts],
                invoices=[list(x) for x in invoices], payments=[list(x) for x in payments],
                ap=str(Decimal(ap).quantize(Decimal("0.01"))),
                bank=str(Decimal(bank).quantize(Decimal("0.01"))),
                qc=qs, journals=journals,
                all_journals_balanced=all(x["balanced"] for x in journals))


def main():
    target = os.environ["AUDITOR_BROWSER_DB_URL"]
    parsed = urlparse(target)
    assert parsed.hostname in ("localhost", "127.0.0.1") and parsed.path == "/cp6_auditor_browser", "SOL_JOURNEY_LOOPBACK_BROWSER_ONLY"
    payload = json.load(sys.stdin)
    operation = sys.argv[1]
    assert operation in ("prepare", "observe")
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        # Same temporary fixture-only USAGE lease as the pinned CP17 fixture.
        # No new EXECUTE grants; restore the exact schema ACL before committing.
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:
            cur.execute("grant usage on schema erp to authenticated")
        result = prepare(cur, date.fromisoformat(payload["today"])) if operation == "prepare" else observe(cur, payload)
        c.b.api.admin(cur)
        if not had:
            cur.execute("revoke usage on schema erp from authenticated")
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
