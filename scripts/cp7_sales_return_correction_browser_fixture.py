"""Declared disposable Native fixture and stock/account observations for UI."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_sales_return_correction_cases as cases

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
            f=p['fixture'];links=cur.execute('select original_id::text,replacement_id::text,reason from '+cases.bundle.SCHEMA+'.links where sale_id=%s order by recorded_at,id',(f['sale'],)).fetchall()
            current=links[-1][1]if links else f['return'];w=cases.workspace(cur,f,current)
            out=dict(workspace=w,original=cases.workspace(cur,f,f['return'])['document'],current=w['document'],
                chain=[dict(original_id=a,replacement_id=b,reason=r)for a,b,r in links],available=cases.cmd.available(cur,f),
                positions={str(k):v for k,v in cases.returns.positions(cur,f).items()},accounts=cases.cmd.accounts(cur),
                original_physical_input_unchanged=cases.original_fact(cur,f['return'])==f['original_fact'],
                original_sale_input_unchanged=cases.note.unchanged_facts(cur,f['sale'])==f['sale_fact'])
        else:raise ValueError('Unknown return correction fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
