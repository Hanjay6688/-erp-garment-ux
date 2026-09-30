"""Lawful two-receipt setup; browser outcome oracle never writes an outcome."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_supplier_return_document_cases as cases


def observe(cur,p):
    f,g=p['first'],p['second']
    workspace=cases.source.read(cur,f,f['location'])
    return dict(amounts=[cases.source.amounts(cur,x) for x in (f,g)],
      documents=workspace['page']['rows'],
      accounts={str(k):str(v) for k,v in cur.execute('select account_id,sum(debit_total-credit_total) from erp.account_daily_balances group by account_id').fetchall()},
      contexts=cur.execute('select count(*) from cp7_supplier_return.execution_context').fetchone()[0])


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(target)
    assert u.hostname in ('localhost','127.0.0.1') and u.path=='/cp6_auditor_browser'
    op,p=sys.argv[1],json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            f,g=cases.fixture(cur,date.fromisoformat(p['today']))
            out=dict(first=f,second=g,return_number=f['tag']+'-UI-COMBINED',return_at=cases.payload(f,g)['physical_at'])
            out['before']=observe(cur,out)
        elif op=='read':out=observe(cur,p)
        else:raise ValueError('Unknown complete return fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
