"""Disposable controls for the K2 retention browser cases: the plan v2 production fixture, and the labelled
SYNTHETIC aging of the actor's finished staged jobs (their finish time moved back 8 days)."""
from contextlib import redirect_stdout
from datetime import date
from urllib.parse import urlparse
import os, sys, json
import psycopg
import cp7_p19_plan_v2_cases as cases


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    op, p = sys.argv[1], json.load(sys.stdin)
    # stdout carries only the JSON answer; the fixtures' own output goes to stderr.
    with redirect_stdout(sys.stderr), psycopg.connect(target) as conn, conn.cursor() as cur:
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:
            cur.execute('grant usage on schema erp to authenticated')
        if op == 'prepare':
            x = cases.fixture(cur, date.fromisoformat(p['today']))
            out = dict(target_key=x['target'])
        elif op == 'age':
            n = cur.execute("update cp7_analysis_stage.jobs set updated_at=updated_at-interval'8 days' where actor=%s and state='DONE'", (p['actor'],)).rowcount
            out = dict(aged=n)
        elif op == 'state':
            out = dict(done=cur.execute("select count(*)from cp7_analysis_stage.jobs where actor=%s and state='DONE'", (p['actor'],)).fetchone()[0],
                       logs=cur.execute('select count(*)from cp7_analysis_stage.retention_log l join cp7_analysis_stage.jobs j on j.id=l.job_id where j.actor=%s', (p['actor'],)).fetchone()[0])
        else:
            raise ValueError('UNKNOWN_K2_RETENTION_BROWSER_CONTROL')
        cases.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
