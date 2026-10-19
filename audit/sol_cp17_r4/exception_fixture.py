"""Own readbacks for claim and ordinary same-product free rewash UI cases."""
from datetime import date, timedelta
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
import uuid

from journey_fixture import prepare, observe, WIB, c
import psycopg


def rewash_prepare(cur, today):
    # Exact lawful Native starting fixture of the already-qualified SG03; stop
    # before creating its rewash order. New UI case owns create/partial/finish/inverse.
    combined = c.nota.combined
    f = combined.fixture(cur, today)
    washed = combined.wash(cur, f, range(4), 11)
    combined.finish(cur, f, [washed], range(4), 13, bs={3: 2})
    c.b.api.admin(cur)
    bs = str(cur.execute("select id from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'", (f["po"], f["roots"][3])).fetchone()[0])
    c.nota.b.chain.bs_action(cur, "CLASSIFY_BS", dict(bs_case_id=bs, cause_source="UNKNOWN", components=[dict(work_component_id=combined.prod.COMPONENT, completed_before_bs_qty=0)], change_reason="Sol lawful same-product free rewash fixture"), c.nota.b.chain.version(cur, "bs_cases", bs))
    c.b.api.admin(cur)
    number = "SOLR4-REWASH-" + uuid.uuid4().hex[:12]
    # Native combined fixture uses seconds, so truncating its when(15) could
    # precede QC. Select the current completed minute after the actual QC;
    # equal send/completion is lawful (Native refuses only completion < send).
    now = cur.execute("select clock_timestamp()").fetchone()[0].astimezone(WIB)
    aligned = now.replace(second=0, microsecond=0)
    latest = cur.execute("select max(q.physical_at) from erp.qc_inspections q join erp.qc_inspection_items i on i.inspection_id=q.id join erp.cutting_groups g on g.id=i.cutting_group_id where g.po_id=%s", (f["po"],)).fetchone()[0]
    assert latest is not None and latest <= aligned <= now, ("SOL_REWASH_TIME_PREREQUISITE", str(latest), str(aligned), str(now))
    return dict(bs=bs, po=f["po"], product=str(f["roots"][3]), vendor=f["vendor"],
                bs_number=cur.execute("select bs_number from erp.bs_cases where id=%s", (bs,)).fetchone()[0],
                location=str(combined.base.LOCATION), number=number,
                send_local=aligned.strftime("%Y-%m-%dT%H:%M"),
                complete_local=aligned.strftime("%Y-%m-%dT%H:%M"),
                latest_native_qc=latest.isoformat(), fixture_observation_clock=now.isoformat())


def rewash_observe(cur, p):
    c.b.api.admin(cur)
    rows = cur.execute("select id::text,status,qty_sent,qty_good_returned,qty_bs_returned,good_fg_lot_id::text from erp.rework_orders where rework_number=%s order by id", (p["number"],)).fetchall()
    orders = []
    for rid, status, qty, good, bad, lot in rows:
        stock = cur.execute("select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s", (lot,)).fetchone()[0] if lot else 0
        product = cur.execute("select product_id::text from erp.fg_lots where id=%s", (lot,)).fetchone()[0] if lot else None
        journals = cur.execute("select count(*) from erp.journal_entries where source_id=%s", (rid,)).fetchone()[0]
        components = cur.execute("select count(*) from erp.rework_component_lines where rework_order_id=%s", (rid,)).fetchone()[0]
        orders.append(dict(id=rid,status=status,qty=int(qty),good=int(good),bs=int(bad),lot=lot,stock=int(stock),product=product,journals=journals,work_components=components))
    return dict(orders=orders,
                vendor_lines=cur.execute("select count(*) from erp.journal_lines where vendor_id=%s", (p["vendor"],)).fetchone()[0],
                vendor_ap=str(cur.execute("select coalesce(sum(l.credit-l.debit),0)::numeric(18,2) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR') and j.status in('POSTED','REVERSED')", (p["vendor"],)).fetchone()[0]),
                bs_status=cur.execute("select status from erp.bs_cases where id=%s", (p["bs"],)).fetchone()[0])


def main():
    target=os.environ["AUDITOR_BROWSER_DB_URL"];parsed=urlparse(target)
    assert parsed.hostname in ("localhost","127.0.0.1") and parsed.path=="/cp6_auditor_browser"
    p=json.load(sys.stdin);op=sys.argv[1]
    assert op in ("prepare","observe","rewash_prepare","rewash_observe")
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute("grant usage on schema erp to authenticated")
        if op=="prepare":
            out=prepare(cur,date.fromisoformat(p["today"]))
            out.update(today=p["today"],claim_number="SOLR4-CL-"+out["po"][:12])
        elif op=="observe":
            out=observe(cur,p);c.b.api.admin(cur)
            out["claims"]=[list(x)for x in cur.execute("select id::text,claim_number,status,compensation_amount::text,resolution_date::text from erp.laundry_claims where claim_number=%s order by id",(p["claim_number"],)).fetchall()]
        elif op=="rewash_prepare":out=rewash_prepare(cur,date.fromisoformat(p["today"]))
        else:out=rewash_observe(cur,p)
        c.b.api.admin(cur)
        if not had:cur.execute("revoke usage on schema erp from authenticated")
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=="__main__":main()
