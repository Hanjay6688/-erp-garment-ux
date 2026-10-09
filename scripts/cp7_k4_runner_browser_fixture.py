"""Disposable controls for the K4 runner browser cases: the server runner registered with the real pg_cron for the
browser copy only (TEST_SCHEDULE_OVERRIDE every 5 seconds, labelled) and removed after, and the actor's staged jobs
with their stored units and page-set identity (read only)."""
from contextlib import redirect_stdout
from urllib.parse import urlparse, urlunparse
import json
import os
import sys
import time

import psycopg

import cp7_schedule as schedule

RUNNER = 'cp7-staged-runner'
OVERRIDE = '5 seconds'


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    database = url.path.lstrip('/')
    cron_url = urlunparse(url._replace(path='/postgres'))
    op, p = sys.argv[1], json.load(sys.stdin)
    # stdout carries only the JSON answer; anything else goes to stderr.
    with redirect_stdout(sys.stderr):
        if op == 'runner_on':
            with psycopg.connect(target) as conn, conn.cursor() as cur:
                defs = [d for d in schedule.definitions(cur) if d['name'] == RUNNER]
            assert len(defs) == 1, defs
            with psycopg.connect(cron_url, autocommit=True) as cron, cron.cursor() as cc:
                version = cc.execute("select extversion from pg_extension where extname='pg_cron'").fetchone()
                assert version and tuple(int(x) for x in version[0].split('.')[:2]) >= (1, 5), ('K4R_PG_CRON_SECONDS_REQUIRED', version)
                # TEST_SCHEDULE_OVERRIDE (labelled): every 5 seconds on the disposable browser copy only.
                ids = schedule.install(cc, database, 'postgres', defs, {RUNNER: OVERRIDE})
            deadline, seen = time.monotonic() + 90, None
            while time.monotonic() < deadline:
                with psycopg.connect(target) as conn, conn.cursor() as cur:
                    seen = cur.execute("select last_tick_at>clock_timestamp()-interval'2 minutes' from cp7_analysis_stage.runner").fetchone()
                if seen and seen[0]:
                    break
                time.sleep(1)
            assert seen and seen[0], 'K4R_RUNNER_NEVER_TICKED'
            out = dict(installed=ids, test_schedule_override=OVERRIDE, pg_cron=version[0])
        elif op == 'state':
            with psycopg.connect(target) as conn, conn.cursor() as cur:
                rows = cur.execute("""select j.request_id::text,j.state,j.units_done,j.unit_count,j.run_id::text,
                    (select count(distinct o.idx) from cp7_analysis_stage.outputs o where o.job_id=j.id),
                    (select count(*) from cp7_analysis_stage.outputs o where o.job_id=j.id),
                    (select s.identity_hash from cp7_analysis_stage.page_sets s where s.run_id=j.run_id and j.state='DONE')
                    from cp7_analysis_stage.jobs j where j.actor=%s order by j.created_at""", (p['actor'],)).fetchall()
            out = dict(jobs=[dict(request_id=r[0], state=r[1], units_done=r[2], unit_count=r[3], run_id=r[4] if r[1] == 'DONE' else None,
                                  distinct_units=r[5], stored_units=r[6], identity_hash=r[7]) for r in rows])
        elif op == 'runner_off':
            with psycopg.connect(cron_url, autocommit=True) as cron, cron.cursor() as cc:
                ids = [j['jobid'] for j in schedule.installed(cc, database)]
                removed = schedule.uninstall(cc, database)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    cc.execute('select pg_stat_clear_snapshot()')
                    if not cc.execute("select count(*) from pg_stat_activity where datname=%s and application_name='pg_cron'", (database,)).fetchone()[0]:
                        break
                    time.sleep(0.5)
                else:
                    raise AssertionError('K4R_PG_CRON_SESSION_LEFT')
                runs = cc.execute("select count(*),count(*)filter(where status='succeeded') from cron.job_run_details where jobid=any(%s)", (ids,)).fetchone()
                cc.execute('delete from cron.job_run_details where jobid=any(%s)', (ids,))
                assert schedule.installed(cc, database) == []
            out = dict(removed=removed, cron_runs=runs[0], cron_runs_succeeded=runs[1])
        else:
            raise ValueError('UNKNOWN_K4_RUNNER_BROWSER_CONTROL')
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
