"""UI gallery fixture (writer; not a test, not evidence). Commits BD laundry data on the auditor runtime's disposable browser
copy so the owner's look-and-feel gallery (scripts/cp6_ui_gallery.mjs) shows the Laundry "Harga & tagihan" tab filled:
  vendor A (components): GARMENT at a synthetic 5,000/PCS and SPRAY intentionally UNKNOWN; one priced delivery of 10 PCS with
            SPRAY covering 4 (the unknown price stays "belum diketahui");
  vendor B (process rate 7,000/PCS): a delivery of 10 received GOOD, one posted invoice of 6 PCS and one draft of 4 PCS.
It uses the BD probe's own helpers and the HTTP mode's transaction-only schema grant (revoked before commit). Invoice
posting needs LAU-DEC02/06, so those two owner settings are set on this copy only (the gallery says so). Refuses any database
but the browser copy. Prints one JSON line with the vendor ids the gallery opens.
usage (from the writer checkout, as the HTTP mode imports it): python ../auditor/scripts/cp6_ui_gallery_fixture.py
"""
from datetime import timedelta
from urllib.parse import urlparse
import json,os
import psycopg
import cp6_bd_probe as bdp
import cp6_bd_modes as modes

url=os.environ['AUDITOR_BROWSER_DB_URL']
assert urlparse(url).path=='/cp6_auditor_browser','UI_GALLERY_ONLY_ON_THE_BROWSER_COPY'
with psycopg.connect(url) as conn,conn.cursor() as cur:
    cur.execute("set timezone='Asia/Jakarta'")
    today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    bdp.bcp.REAL_TODAY=today
    day=today-timedelta(days=1)
    bdp.api.admin(cur)
    with modes._fixture_usage(cur):
        a=bdp.fixture(cur,day,'Galeri komponen')
        garment=bdp.component(cur,a,'GARMENT','5000.00');spray=bdp.component(cur,a,'SPRAY',None,status='UNKNOWN');bdp.terms(cur,a,'COMPONENTS')
        bdp.post_priced(cur,a,dict(components=[dict(component_id=garment,covered_qty=10),dict(component_id=spray,covered_qty=4)]))
        b=bdp.fixture(cur,day,'Galeri invoice');bdp.process_rate(cur,b,'7000.00');bdp.invoice_policies(cur)
        line=bdp.receipt_line(cur,bdp.receive(cur,bdp.plain_delivery(cur,b,10,11),b,10,13)['receipt_id'])
        bdp.invoice(cur,b,[dict(line=line,qty=6,amount='42000.00')],'42000.00',number='GALERI-INV-1')
        bdp.invoice(cur,b,[dict(line=line,qty=4,amount='28000.00')],'28000.00',number='GALERI-INV-2',post=False)
    conn.commit()
    usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];conn.rollback()
assert usage is False,'UI_GALLERY_FIXTURE_GRANT_LEFT'
print(json.dumps(dict(vendor_components=a['vendor'],vendor_invoice=b['vendor'])))
