"""CP7C nightly backup of the ERP database (owner decision 9 Oct 2026 WIB: "backup malam yang sudah disepakati").

One run makes one full logical backup (pg_dump, custom format) of the ERP database and writes it outside
the database (`dest`). It then proves the backup: the file is restored into a separate scratch database
and every table of every non-system schema (cron aside: pg_cron lives only in the database named postgres)
is compared with the source by row count and an md5 over its rows. Only a backup whose restore gives the
same rows is `restore_verified`. The receipt (cp7.nightly-backup-receipt.v1, written next to the file)
names the file, its bytes and SHA-256, the source database, the times in UTC and WIB, every restore error
and every difference.

Retention: the newest `keep` verified backups stay (14 nights by default). Older backups are removed only
after tonight's backup verified, and the newest verified backup is never removed; a failed or unverified
night removes nothing. The scratch database is dropped at the end either way.

Schedule: every night at 01:00 WIB (18:00 UTC), run by a scheduler outside the database (the template
.github/workflows/cp7-nightly-backup.yml stays disabled until the installation is approved). The tool
never chooses a database by itself: the source, the scratch server and the destination are arguments.
`container` runs pg_dump/pg_restore inside a disposable Supabase container (tests); without it the local
client binaries are used with the URLs.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql

CONTRACT = 'cp7.nightly-backup-receipt.v1'
SCHEDULE = dict(cron='0 18 * * *', timezone='UTC', meaning='01:00 WIB nightly')
KEEP = 14
WIB = timezone(timedelta(hours=7))
# The restore errors a backup may explain: only pg_cron, which cannot be created outside the database postgres.
CRON_ERROR = re.compile(r'^pg_restore: error: could not execute query: ERROR:  (can only create extension in database postgres'
                        r'|extension "pg_cron" does not exist|schema "cron" does not exist|relation "cron\.[a-z_]+" does not exist)$')


def db_url(url, name):
    u = urlparse(url)
    return urlunparse(u._replace(path='/' + name))


def user_of(url):
    return urlparse(url).username or 'postgres'


def data_hashes(url):
    """Every table of every non-system schema: row count and md5 of the rows (cron aside)."""
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        conn.read_only = True
        tables = cur.execute("""select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
            where c.relkind in('r','p') and n.nspname not in('pg_catalog','information_schema','cron')
            and n.nspname not like 'pg\\_toast%' and n.nspname not like 'pg\\_temp%' order by 1,2""").fetchall()
        out = {}
        for schema, table in tables:
            n, h = cur.execute(sql.SQL("select count(*),md5(coalesce(string_agg(x::text,chr(10) order by x::text),'')) from {}.{} x").format(
                sql.Identifier(schema), sql.Identifier(table))).fetchone()
            out[schema + '.' + table] = dict(rows=n, md5=h)
        return out


class Tools:
    """pg_dump/pg_restore/createdb/dropdb either inside a disposable container or with the local client."""

    def __init__(self, admin_url, container=None):
        self.admin_url, self.container, self.user = admin_url, container, user_of(admin_url)

    def _run(self, args, check=True):
        cmd = ['docker', 'exec', self.container, *args] if self.container else args
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def _db(self, name):
        return ['-U', self.user, '-d', name] if self.container else ['--dbname=' + db_url(self.admin_url, name)]

    def dump(self, source, target):
        if self.container:
            inner = '/tmp/' + target.name
            r = self._run(['pg_dump', *self._db(source), '-Fc', '-f', inner], check=False)
            if r.returncode == 0:
                subprocess.run(['docker', 'cp', f'{self.container}:{inner}', str(target)], check=True, capture_output=True)
            return r
        return self._run(['pg_dump', *self._db(source), '-Fc', '-f', str(target)], check=False)

    def recreate(self, name):
        base = ['-U', self.user] if self.container else ['--maintenance-db=' + db_url(self.admin_url, 'postgres')]
        self._run(['dropdb', *base, '--if-exists', '--force', name], check=False)
        if self.container:
            return self._run(['createdb', '-U', self.user, '-T', 'template0', name], check=False)
        return self._run(['createdb', *base, '-T', 'template0', name], check=False)

    def restore(self, name, file):
        if self.container:
            inner = '/tmp/' + file.name
            return self._run(['pg_restore', *self._db(name), '--no-password', inner], check=False)
        return self._run(['pg_restore', *self._db(name), '--no-password', str(file)], check=False)

    def drop(self, name):
        if self.container:
            self._run(['dropdb', '-U', self.user, '--if-exists', '--force', name], check=False)
        else:
            self._run(['dropdb', '--maintenance-db=' + db_url(self.admin_url, 'postgres'), '--if-exists', '--force', name], check=False)

    def remove_inner(self, file):
        if self.container:
            self._run(['rm', '-f', '/tmp/' + file.name], check=False)


def receipts(dest):
    out = []
    for p in sorted(Path(dest).glob('*.receipt.json')):
        try:
            r = json.loads(p.read_text())
        except ValueError:
            continue
        if r.get('contract') == CONTRACT:
            out.append((p, r))
    return out


def prune(dest, keep, tonight_verified):
    """Keep the newest `keep` verified backups; remove older ones only after tonight's backup verified."""
    if not tonight_verified:
        return dict(kept=[r['file'] for _, r in receipts(dest)], removed=[], reason='TONIGHT_NOT_VERIFIED_NOTHING_REMOVED')
    rows = sorted(receipts(dest), key=lambda x: x[1]['started_at_utc'], reverse=True)
    verified = [r for r in rows if r[1].get('restore_verified') is True]
    kept = verified[:max(keep, 1)]
    oldest_kept = kept[-1][1]['started_at_utc']
    removed = []
    for path, r in rows:
        if (path, r) in kept or r['started_at_utc'] >= oldest_kept:
            continue
        (Path(dest) / r['file']).unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        removed.append(r['file'])
    return dict(kept=[r['file'] for _, r in kept], removed=removed, reason='NEWEST_VERIFIED_KEPT')


def backup(admin_url, source, scratch, dest, keep=KEEP, container=None, now=None):
    # The scratch database is dropped and recreated: it can never be the database backed up.
    assert scratch and source and scratch != source and scratch != 'postgres', 'BACKUP_SCRATCH_MUST_BE_SEPARATE'
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    started = now or datetime.now(timezone.utc)
    name = 'erp-%s.dump' % started.astimezone(WIB).strftime('%Y%m%d-%H%M%S-WIB')
    file = dest / name
    tools = Tools(admin_url, container)
    receipt = dict(contract=CONTRACT, label='CP7C_NIGHTLY_BACKUP', schedule=SCHEDULE, file=name, source_database=source,
                   scratch_database=scratch, started_at_utc=started.isoformat(), started_at_wib=started.astimezone(WIB).isoformat(),
                   restore_verified=False, production_go=False)
    try:
        t0 = time.monotonic()
        d = tools.dump(source, file)
        receipt['dump'] = dict(exit=d.returncode, stderr=d.stderr[-2000:], seconds=round(time.monotonic() - t0, 1))
        assert d.returncode == 0 and file.exists() and file.stat().st_size > 0, 'BACKUP_DUMP_FAILED'
        data = file.read_bytes()
        receipt.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        c = tools.recreate(scratch)
        assert c.returncode == 0, ('BACKUP_SCRATCH_NOT_CREATED', c.stderr[-500:])
        t1 = time.monotonic()
        r = tools.restore(scratch, file)
        errors = [line for line in r.stderr.splitlines() if line.startswith('pg_restore: error:')]
        unexplained = [line for line in errors if not CRON_ERROR.match(line)]
        receipt['restore'] = dict(exit=r.returncode, seconds=round(time.monotonic() - t1, 1), errors=errors[:40], unexplained=unexplained[:40])
        a, b = data_hashes(db_url(admin_url, source)), data_hashes(db_url(admin_url, scratch))
        differ = {t: dict(source=a.get(t), restored=b.get(t)) for t in sorted(set(a) | set(b)) if a.get(t) != b.get(t)}
        receipt['data'] = dict(tables=len(a), rows=sum(v['rows'] for v in a.values()), differ=differ)
        receipt['restore_verified'] = not unexplained and not differ and len(a) > 0
    except Exception as exc:  # the receipt records the failure; nothing is removed
        receipt['error'] = str(exc)[:2000]
    finally:
        tools.drop(scratch)
        tools.remove_inner(file)
    finished = datetime.now(timezone.utc)
    receipt.update(finished_at_utc=finished.isoformat(), finished_at_wib=finished.astimezone(WIB).isoformat())
    (dest / (name + '.receipt.json')).write_text(json.dumps(receipt, indent=1, default=str) + '\n')
    receipt['retention'] = prune(dest, keep, receipt['restore_verified'])
    (dest / (name + '.receipt.json')).write_text(json.dumps(receipt, indent=1, default=str) + '\n')
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--admin-url', required=True, help='a role that can read every ERP table and create the scratch database')
    p.add_argument('--source', required=True, help='the ERP database name')
    p.add_argument('--scratch', default='cp7_backup_verify', help='the scratch database restored into and dropped')
    p.add_argument('--dest', required=True, help='directory outside the database where backups are kept')
    p.add_argument('--keep', type=int, default=KEEP)
    p.add_argument('--container', help='run the client tools inside this disposable container (tests)')
    a = p.parse_args()
    if shutil.which('docker' if a.container else 'pg_dump') is None:
        raise SystemExit('CP7_BACKUP_TOOLS_MISSING')
    r = backup(a.admin_url, a.source, a.scratch, a.dest, a.keep, a.container)
    print(json.dumps({k: r.get(k) for k in ('file', 'bytes', 'sha256', 'restore_verified', 'retention', 'error')}, default=str))
    raise SystemExit(0 if r['restore_verified'] else 1)


if __name__ == '__main__':
    main()
