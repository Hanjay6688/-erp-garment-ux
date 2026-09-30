"""P09 native receipt/transfer fixture with read-only browser outcome checks."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_f03_e24_issue_cases as cases

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(target)
    assert u.hostname in ('localhost','127.0.0.1') and u.path=='/cp6_auditor_browser'
    op,p=sys.argv[1],json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            out=cases.fixture(cur,date.fromisoformat(p['today']));out['before']=cases.observe(cur,out)
        elif op=='read':out=cases.observe(cur,p)
        elif op=='verify_posted':out=cases.assert_posted(cur,p,p['before'])
        else:raise ValueError('Unknown E24 fixture operation')
        cases.bc.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
