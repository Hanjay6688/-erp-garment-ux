"""Disposable controls for the K3b cleanup browser cases: the plan v2 production fixture, the server schedule's
cleanup entry run exactly as pg_cron runs it (cp7_ops.cleanup_tick as the scheduler role postgres), and the actor's
staged jobs with their cleanup logs and temporary rows (read only)."""
from contextlib import redirect_stdout
from datetime import date
from urllib.parse import urlparse
import os, sys, json
import psycopg
import cp7_p19_plan_v2_cases as cases

TEMPORARY = ('outputs', 'target_rows', 'pair_rows', 'pair_lists', 'fragments')


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
            out = dict(target_key=x['target'], location_id=str(x['fabric']['location']), material_id=str(x['fabric']['material']))
        elif op == 'clean':
            cur.execute('set local role postgres')
            r = cur.execute('select cp7_ops.cleanup_tick()').fetchone()[0]
            cur.execute('reset role')
            out = dict(cleaned=[c['job_id'] for c in r['cleaned']], failed=r['failed'], deferred=r['deferred'])
        elif op == 'state':
            jobs = [x[0] for x in cur.execute("select id::text from cp7_analysis_stage.jobs where actor=%s and state='DONE'", (p['actor'],)).fetchall()]
            out = dict(done=jobs, logs=cur.execute('select count(*)from cp7_analysis_stage.cleanups where job_id=any(%s::uuid[])', (jobs,)).fetchone()[0],
                       temporary={t: cur.execute(f'select count(*)from cp7_analysis_stage.{t} where job_id=any(%s::uuid[])', (jobs,)).fetchone()[0] for t in TEMPORARY})
        else:
            raise ValueError('UNKNOWN_K3_CLEANUP_BROWSER_CONTROL')
        cases.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
