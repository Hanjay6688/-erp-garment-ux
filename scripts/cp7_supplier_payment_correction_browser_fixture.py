"""Native-only fixture observations for actual supplier editor browsers."""
from datetime import date
from decimal import Decimal as D
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_supplier_payment_correction_cases as cases
def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    p=json.loads(sys.stdin.read());op=sys.argv[1]
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            f=cases.fixture(cur,date.fromisoformat(p['today']),historical=True);w=cases.workspace(cur,f)
            out=dict(fixture=f,workspace=w,payment=w['document'])
        elif op=='state':
            f=p['fixture'];links=cur.execute('select original_id::text,replacement_id::text,reason from cp7_supplier_payment_correction.links where purchase_id=%s order by recorded_at,original_id',(f['receipt']['purchase_id'],)).fetchall()
            current=links[-1][1]if links else f['payment'];w=cases.workspace(cur,f,current)
            original=cases.original_fact(cur,f['payment']);omit=('status','updated_at','row_version')
            out=dict(workspace=w,original=cases.workspace(cur,f,f['payment'])['document'],current=w['document'],chain=[dict(original_id=a,replacement_id=b,reason=r)for a,b,r in links],
              cash_balance=str(cases.misc.cash_balance(cur,f['cash'])),stock_HPP_unchanged=cases.supplier.physical_state(cur)==f['physical'],
              original_all_non_lifecycle_fields_unchanged={k:v for k,v in original.items()if k not in omit}=={k:v for k,v in f['original_fact'].items()if k not in omit})
        else:raise ValueError('Unknown supplier correction fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
