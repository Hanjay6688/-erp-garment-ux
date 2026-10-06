"""Native-only fixture observations for the actual new-supplier-payment browsers."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_supplier_payment_create_cases as cases
def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    p=json.loads(sys.stdin.read());op=sys.argv[1]
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            f=cases.fixture(cur,date.fromisoformat(p['today']))
            code,name=cur.execute('select cash_account_code,cash_account_name from erp.cash_accounts where id=%s',(f['cash'],)).fetchone()
            number=cur.execute('select purchase_number from erp.material_purchase_headers where id=%s',(f['receipt']['purchase_id'],)).fetchone()[0]
            out=dict(fixture=dict(receipt=dict(purchase_id=f['receipt']['purchase_id']),cash=f['cash'],cash_before=str(f['cash_before'])),number=number,bank_code=code,bank_name=name)
        elif op=='state':
            f=dict(p['fixture']);w=cases.read(cur,f)
            out=dict(remaining=w['Native_AP']['remaining'],paid=w['Native_AP']['paid'],state=cases.state(cur,f),
              cash_delta=str(cases.misc.cash_balance(cur,f['cash'])-cases.D(f['cash_before'])),
              payments=[dict(amount=str(a),status=s,notes=n)for a,s,n in cur.execute('select amount,status,notes from erp.supplier_payments where purchase_id=%s order by created_at,id',(f['receipt']['purchase_id'],)).fetchall()])
        else:raise ValueError('Unknown supplier payment create fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
