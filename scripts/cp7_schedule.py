"""CP7C server schedule with pg_cron: plan, install, verify and remove the agreed jobs (cp7_ops.schedules()).

Owner decision 9 Oct 2026 WIB: finished analyses are cleaned on the server's own schedule and expired ones purged
after 7 days; the database is backed up every night (scripts/cp7_nightly_backup.py, outside the database).
Registering the jobs on a real database is the installation step: it waits for the audit and the owner's
installation permission, so `install` refuses unless --installation-approved is given. Tests register them
only on a disposable copy, with a labelled TEST_SCHEDULE_OVERRIDE so a job fires within a minute.

pg_cron keeps its jobs in the database named postgres (cron_cur); each job runs in the ERP database
(`database`) as the scheduler role (`username`, normally postgres, the only role that may run the cp7_ops
entries). The definitions come from the ERP database itself, so the installed jobs are exactly the package's.

P20 F02 (independent audit 9 Oct 2026, AS20-43): pg_cron replaces a job of the same name and user, so the job
name carries the database (`cp7-staged-cleanup@<database>`): installing for database B never moves A's jobs,
installing again when the jobs already match changes nothing (same job ids), and uninstall removes only the
target database's jobs. A same-named job of the same user pointing at another database is refused before any
change.
"""
import argparse
import json

import psycopg

PREFIX = 'cp7-'


def definitions(erp_cur):
    return erp_cur.execute('select cp7_ops.schedules()').fetchone()[0]


def job_name(name, database):
    """The pg_cron job name of one package schedule for one database."""
    return name + '@' + database


def installed(cron_cur, database):
    rows = cron_cur.execute("""select jobid,jobname,schedule,command,database,username,active from cron.job
        where jobname like %s and database=%s order by jobname""", (PREFIX + '%', database)).fetchall()
    return [dict(jobid=r[0], name=r[1], schedule=r[2], command=r[3], database=r[4], username=r[5], active=r[6]) for r in rows]


def foreign(cron_cur, database, username, names):
    """Jobs of these names and this user that point at another database (pg_cron would move them)."""
    rows = cron_cur.execute("select jobid,jobname,database from cron.job where jobname=any(%s) and username=%s and database<>%s",
                            (list(names), username, database)).fetchall()
    return [dict(jobid=r[0], name=r[1], database=r[2]) for r in rows]


def uninstall(cron_cur, database):
    removed = []
    for job in installed(cron_cur, database):
        cron_cur.execute('select cron.unschedule(%s::bigint)', (job['jobid'],))
        removed.append(job['name'])
    return removed


def install(cron_cur, database, username, defs, override=None):
    """Make this database's cp7 jobs exactly `defs` (job names carry the database). Nothing changes when they already
    match; another database's jobs are never touched. `override` maps a package name to a test schedule (tests only)."""
    wanted = [dict(d, schedule=(override or {}).get(d['name'], d['schedule'])) for d in defs]
    clash = foreign(cron_cur, database, username, [job_name(d['name'], database) for d in wanted])
    if clash:
        raise RuntimeError('CP7_SCHEDULE_NAME_USED_BY_ANOTHER_DATABASE: %s' % json.dumps(clash))
    ok, _ = matches(cron_cur, database, username, wanted)
    if ok:
        return {d['name']: j['jobid'] for d in wanted for j in installed(cron_cur, database) if j['name'] == job_name(d['name'], database)}
    uninstall(cron_cur, database)
    ids = {}
    for d in wanted:
        ids[d['name']] = cron_cur.execute('select cron.schedule_in_database(%s,%s,%s,%s,%s,true)',
                                          (job_name(d['name'], database), d['schedule'], d['command'], database, username)).fetchone()[0]
    return ids


def matches(cron_cur, database, username, defs):
    """The installed jobs are exactly the package's definitions (name@database, schedule, command, database, user, active)."""
    want = sorted((job_name(d['name'], database), d['schedule'], d['command'], database, username, True) for d in defs)
    have = sorted((j['name'], j['schedule'], j['command'], j['database'], j['username'], j['active']) for j in installed(cron_cur, database))
    return want == have, dict(expected=want, installed=have)


def runs(cron_cur, jobid, since):
    rows = cron_cur.execute("""select runid,status,return_message,start_time,end_time from cron.job_run_details
        where jobid=%s and start_time>=%s order by start_time""", (jobid, since)).fetchall()
    return [dict(runid=r[0], status=r[1], message=r[2], start=r[3], end=r[4]) for r in rows]


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('action', choices=('plan', 'install', 'verify', 'uninstall'))
    p.add_argument('--erp-url', required=True, help='the ERP database (definitions come from cp7_ops.schedules())')
    p.add_argument('--cron-url', help='the database named postgres where pg_cron keeps its jobs')
    p.add_argument('--database', help='the ERP database name the jobs run in')
    p.add_argument('--username', default='postgres')
    p.add_argument('--installation-approved', action='store_true',
                   help='required for install: the audit passed and the owner approved installing the schedule')
    a = p.parse_args()
    with psycopg.connect(a.erp_url) as erp, erp.cursor() as cur:
        defs = definitions(cur)
    if a.action == 'plan':
        print(json.dumps(dict(definitions=defs, installs=False), indent=1))
        return
    assert a.cron_url and a.database, 'CP7_SCHEDULE_CRON_URL_AND_DATABASE_REQUIRED'
    if a.action == 'install' and not a.installation_approved:
        raise SystemExit('CP7_SCHEDULE_INSTALL_NOT_APPROVED: installing waits for the audit and the owner\'s installation permission')
    with psycopg.connect(a.cron_url, autocommit=True) as cron, cron.cursor() as cur:
        if a.action == 'install':
            out = dict(installed=install(cur, a.database, a.username, defs))
        elif a.action == 'uninstall':
            out = dict(removed=uninstall(cur, a.database))
        else:
            ok, detail = matches(cur, a.database, a.username, defs)
            out = dict(matches=ok, **detail)
    print(json.dumps(out, indent=1, default=str))


if __name__ == '__main__':
    main()
