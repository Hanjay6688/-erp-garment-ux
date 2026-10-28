"""Native-built fixture/readback for A OW08b money UI, disposable browser copy only."""
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
import json,os,sys,uuid
import psycopg

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from cp7_vendor_receivable import cases as native

operation=sys.argv[1];payload=json.loads(sys.stdin.read())
url=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(url)
assert parsed.hostname in('127.0.0.1','localhost')and parsed.path=='/cp6_auditor_browser'
with psycopg.connect(url)as connection,connection.cursor()as cur:
    assert cur.execute('select current_database()').fetchone()[0]=='cp6_auditor_browser'
    if operation=='prepare':
        day=date.fromisoformat(payload['today']);native.bd.api.admin(cur)
        grant=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if grant:cur.execute('grant usage on schema erp to authenticated')
        try:
            fixture=native.fixture(cur,day);credit=native.correction(cur,fixture);target=None
            if payload.get('next_invoice')is True:
                _,target=native.bd.correction(cur,fixture,fixture['line'],'1000.25',fixture['invoice'],day)
        except Exception:
            connection.rollback();raise
        finally:
            native.bd.api.admin(cur)
            if grant:cur.execute('revoke usage on schema erp from authenticated')
        if target:target['invoice_number']=cur.execute('select invoice_number from erp.bd_laundry_invoices_v1 where id=%s',(target['invoice_id'],)).fetchone()[0]
        before=native.state(cur,fixture);truth_before=native.bd.all_truth(cur)
        number=cur.execute('select invoice_number from erp.bd_laundry_invoices_v1 where id=%s',(credit['invoice_id'],)).fetchone()[0]
        connection.commit()
        result=dict(fixture=fixture,credit_id=credit['invoice_id'],credit_number=number,before=before,next_invoice=target,financial_truth_before=truth_before,
            fixture_source='EXISTING_NATIVE_WRITERS_NOT_SCREEN_CREATION',actual_browser_posting=False)
    elif operation=='truth':
        result=native.bd.all_truth(cur);connection.rollback()
    elif operation=='state':
        fixture=payload['fixture'];result=native.state(cur,fixture)
        rows=cur.execute("select r.id::text,r.amount::text,case when x.refund_id is null then 'POSTED'else 'REVERSED'end from cp7_vendor_receivable.refunds_v1 r left join cp7_vendor_receivable.reversals_v1 x on x.refund_id=r.id where r.correction_id=%s order by r.id",(payload['credit_id'],)).fetchall()
        result['refunds']=[dict(id=key,amount=amount,status=status)for key,amount,status in rows]
        applications=cur.execute("select a.id::text,a.amount::text from erp.bd_claim_credit_applications_v1 a join erp.vendor_payments p on p.id=a.vendor_payment_id where a.correction_invoice_id=%s and p.status='POSTED'order by a.id",(payload['credit_id'],)).fetchall()
        result['applications']=[dict(id=key,amount=amount)for key,amount in applications]
        result['ledger']=native.screen(cur,fixture)['ledger'];connection.rollback()
    elif operation=='revoke':
        actor=str(uuid.UUID(payload['actor']))
        role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(actor,)).fetchone()[0]
        removed=cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.view','finance.hpp.manage')returning permission_key",(role,)).fetchall()
        connection.commit();result=dict(removed=[r[0]for r in removed],actual_role_permission_rows_changed=True)
    else:raise ValueError('UNDECLARED_VENDOR_BROWSER_FIXTURE_OPERATION')
print(json.dumps(result,default=str))
