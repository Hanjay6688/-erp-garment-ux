"""Native disposable controls for the real payment-editor browser journey."""
from datetime import date
from decimal import Decimal as D
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_payment_correction_cases as cases

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op=sys.argv[1];p=json.loads(sys.stdin.read())
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            f=cases.fixture(cur,date.fromisoformat(p['today']),historical=True)
            out=dict(fixture=f,document=cases.source.read(cur,f)['detail'],payment=f['original'])
        elif op=='state':
            f=p['fixture'];links=cur.execute('select original_id::text,replacement_id::text,reason from cp7_payment_correction.links where sale_id=%s order by recorded_at,original_id',(f['sale'],)).fetchall()
            current=links[-1][1]if links else f['payment'];original=cases.workspace(cur,f,f['payment'])['document'];active=cases.workspace(cur,f,current)['document']
            out=dict(document=cases.source.read(cur,f)['detail'],original=original,current=active,
                     chain=[dict(original_id=a,replacement_id=b,reason=r)for a,b,r in links],
                     cash_received=str(cases.cmd.accounts(cur).get(cases.payments.bank_account(cur,f),D('0'))),
                     stock_HPP_unchanged=cases.unchanged_stock(cur,f)==f['stock_hash'],
                     original_posting_fact_unchanged=cases.payment_fact(cur,f['payment'])==tuple(f['original_fact']))
        else:raise ValueError('Unknown payment-correction fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
