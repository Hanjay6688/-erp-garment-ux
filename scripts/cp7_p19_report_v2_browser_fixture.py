"""Disposable Native business setup for the report v2 browser cases; browser observations never change facts."""
from datetime import date
from urllib.parse import urlparse
import os, sys, json
import psycopg
import cp7_p19_report_v2_cases as cases


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    op, p = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:
            cur.execute('grant usage on schema erp to authenticated')
        if op == 'prepare':
            # The E01 real workload through the ordinary Native writers; the staged run and the report are the browser's own.
            cases.load.real_workload(cur, date.fromisoformat(p['today']))
            out = dict(status='PASS')
        elif op == 'state':
            q = lambda sql: cur.execute(sql, (p['actor'],)).fetchone()[0]
            out = dict(jobs=q('select count(*)from cp7_analysis_stage.report_jobs where actor=%s'),
                       publications=q('select count(*)from cp7_analysis_stage.report_publications where actor=%s'),
                       finance=q("select count(*)from cp7_analysis_stage.report_publications where actor=%s and finance='INCLUDED'"),
                       v1_publications=q('select count(*)from cp7_analysis_native.publications where actor=%s'))
        else:
            raise ValueError('UNKNOWN_REPORT_V2_BROWSER_CONTROL')
        cases.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
