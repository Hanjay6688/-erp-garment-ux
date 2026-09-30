"""Lawful isolated E03 source setup and read-only browser oracle."""
from datetime import date
from urllib.parse import urlparse
import json
import os
import sys
import psycopg
import cp7_f03_e03_cases as cases


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost','127.0.0.1') and url.path == '/cp6_auditor_browser'
    op,p = sys.argv[1],json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op == 'prepare':
            out = cases.fixture(cur,date.fromisoformat(p['today']))
            out['before'] = cases.observe(cur,out)
        elif op == 'read':out = cases.observe(cur,p)
        elif op == 'verify':
            # JSON transport makes decimal observations text; restore only the
            # exact money/quantity values, never an expected production result.
            before = dict(p['before'],accounts={k:cases.D(v) for k,v in p['before']['accounts'].items()},accessory_qty=cases.D(p['before']['accessory_qty']))
            out = cases.assert_service(cur,p,before,p['expected_returned'])
        else:raise ValueError('Unknown E03 fixture operation')
        cases.bc.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__ == '__main__':main()
