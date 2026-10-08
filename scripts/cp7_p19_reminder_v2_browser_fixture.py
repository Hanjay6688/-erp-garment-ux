"""Disposable Native business setup for the reminders v2 browser cases; browser observations never change facts."""
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
            # The plan v2 fixture (an exact-size production gap through the ordinary Native writers); the staged run is the browser's own.
            x = cases.fixture(cur, date.fromisoformat(p['today']))
            out = dict(target_key=x['target'], root=x['root'])
        elif op == 'state':
            q = lambda sql: cur.execute(sql, (p['actor'],)).fetchone()[0]
            out = dict(sets=q('select count(*)from cp7_reminder_native.staged_condition_sets where actor=%s'),
                       claims=q('select count(*)from cp7_reminder_native.staged_claims where actor=%s'),
                       rechecks=q('select count(*)from cp7_reminder_native.staged_rechecks where actor=%s'),
                       v1_claims=q('select count(*)from cp7_reminder_native.local_claims where actor=%s'))
        else:
            raise ValueError('UNKNOWN_REMINDER_V2_BROWSER_CONTROL')
        cases.b.api.admin(cur)
        if not had:
            cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
