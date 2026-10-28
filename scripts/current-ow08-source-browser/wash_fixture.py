"""Existing Native delivery setup and exact readback for actual screen writes.

Only preparation writes here; the failed attempt and its price must come from
the browser's public commands. No hosted connection or alternate money engine.
"""
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from cp7_laundry_unknown_wash import cases as wash

operation=sys.argv[1];payload=json.loads(sys.stdin.read())
url=os.environ['AUDITOR_BROWSER_DB_URL'];address=urlparse(url)
assert address.hostname in('127.0.0.1','localhost')and address.path=='/cp6_auditor_browser'
with psycopg.connect(url)as connection,connection.cursor()as cur:
    assert cur.execute('select current_database()').fetchone()[0]=='cp6_auditor_browser'
    wash.b.api.admin(cur)
    grant=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    if grant:cur.execute('grant usage on schema erp to authenticated')
    try:
        if operation=='prepare':
            w=wash.fixture(cur,date.fromisoformat(payload['today']),'BROWSE')
            wash.b.api.admin(cur)
            number=wash.one(cur,'select delivery_number from erp.laundry_deliveries where id=%s',(w['delivery'],))
            result=dict(fixture=w,number=number,physical_local=str(w['day'])+'T12:00',money_before=wash.money(cur,w['po']),
                fixture_source='EXISTING_NATIVE_DELIVERY_ONLY_FAILED_ATTEMPT_AND_PRICE_MUST_BE_UI')
        elif operation=='state':
            w=payload['fixture'];r=payload['response'];attempt=str(r['failed_wash_attempt_id'])
            row=cur.execute("""select r.receipt_number from erp.laundry_failed_wash_attempts a
                join erp.laundry_receipt_lines l on l.id=a.receipt_line_id
                join erp.laundry_receipts r on r.id=l.receipt_id where a.id=%s and a.delivery_id=%s""",(attempt,w['delivery'])).fetchone()
            assert row,'ACTUAL_FAILED_WASH_NOT_LINKED_TO_FIXTURE_DELIVERY'
            p=cur.execute('select price_status,rate_per_pcs::text,price_reason,priced_by is not null,priced_at is not null from cp7_laundry_unknown_wash.prices_v1 where attempt_id=%s',(attempt,)).fetchall()
            result=dict(receipt_number=row[0],line=wash.attempt_line(cur,attempt),money=wash.money(cur,w['po']),
                physical=wash.physical(cur,w,r),price_rows=p,
                own_close_blockers=wash.mine(wash.readiness(cur,date.fromisoformat(w['day'])),attempt))
        else:raise ValueError('UNDECLARED_OW08_WASH_FIXTURE_OPERATION')
    except Exception:
        connection.rollback();raise
    finally:
        wash.b.api.admin(cur)
        if grant:cur.execute('revoke usage on schema erp from authenticated')
    if operation=='prepare':connection.commit()
    else:connection.rollback()
print(json.dumps(result,default=str))
