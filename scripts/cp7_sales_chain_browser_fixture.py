"""Disposable actual Native sale-chain fixture and independent fact observations."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_sales_chain_cases as cases
def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    p=json.loads(sys.stdin.read());op=sys.argv[1]
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            f=cases.fixture(cur,date.fromisoformat(p['today']),historical=True)
            out=dict(fixture=f,workspace=cases.workspace(cur,f),invoice=cases.source.read(cur,f)['detail'])
        elif op=='state':
            f=p['fixture'];d=cases.source.read(cur,f)['detail']
            out=dict(invoice=d,available=cases.cmd.available(cur,f),positions={str(k):v for k,v in cases.returns.positions(cur,f).items()},
                accounts=cases.cmd.accounts(cur),original_facts_unchanged=cases.facts(cur,f)==f['original_facts'],
                history=cur.execute('select jsonb_agg(jsonb_build_object(\'request_id\',request_id,\'sale_id\',sale_id,\'steps\',steps,\'reviewed_source\',reviewed_source)order by recorded_at)from '+cases.bundle.SCHEMA+'.history where sale_id=%s',(f['sale'],)).fetchone()[0]or[],
                payments=cur.execute('select jsonb_agg(jsonb_build_object(\'id\',id,\'status\',status)order by id)from erp.sales_payments where sale_id=%s',(f['sale'],)).fetchone()[0]or[],
                returns=cur.execute('select jsonb_agg(jsonb_build_object(\'id\',id,\'status\',status)order by id)from erp.sales_returns where sale_id=%s',(f['sale'],)).fetchone()[0]or[])
        else:raise ValueError('Unknown sale-chain fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
