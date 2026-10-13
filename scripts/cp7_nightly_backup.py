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

P20 F03 (independent audit 9 Oct 2026, AS20-45): every attempt has its own name (the WIB second plus a random
token), and an existing dump or receipt of that name is refused before anything is written, so a retry in
the same second never replaces an earlier dump or its receipt.

Independent audit Fable (12 Oct 2026, full CP7 audit of d0b9e9c2):
  * F-OPS-01: the scratch database was dropped and recreated whatever it was, so a --scratch naming another
    existing database deleted it and the backup still verified. The tool now marks the database it creates (a
    database comment) and drops only a database that carries its mark. An existing database without the mark
    is refused (BACKUP_SCRATCH_EXISTS_NOT_OURS) and left as it is; the night records the refusal, verifies
    nothing and removes nothing. A database that takes the name after that check makes the night refuse
    (BACKUP_SCRATCH_NOT_CREATED) and is left as it is. Any name other than the source and postgres is accepted
    (default cp7_backup_verify). Since ASR-OPS-01 (below) the restore itself goes into the attempt's own database.
  * F-OPS-03: the restore was compared with the live source after the restore, so any write during the backup
    made the night unverified. The source is now read in one exported snapshot: pg_dump takes that snapshot
    (--snapshot) and the source's rows are hashed in the same transaction, so the comparison is with exactly
    what the dump holds, whatever is written meanwhile.

Independent audit Astra (13 Oct 2026, retest of 7a0b4a90), ASR-OPS-01: a leftover scratch read as ours before the
dump was dropped by name after the dump, so a database an administrator put under that name in between was
deleted and the night still verified. Ownership is now bound to the database itself, not to its name:
  * every attempt restores into its own database, created under a name nobody can know beforehand
    (`<scratch>_<random>`) with an OID the tool chooses (CREATE DATABASE ... OID, PostgreSQL 15+), and marked with
    the attempt's token and that OID; a mark is only ours on the database whose OID it names. The configured
    --scratch name is only checked (a database holding it, ours or not, makes the night refuse as before) and
    never restored into;
  * a database is dropped only by OID: it must still carry this tool's mark (and the attempt's token for the
    attempt's own database); it is first moved under a fresh random name and its OID is checked again, and only
    then dropped. A name that by then points at another database is put back and the night is refused
    (BACKUP_SCRATCH_REPLACED); nothing is dropped, verified or pruned;
  * a leftover of an earlier night (the configured name, or `<scratch>_<random>`, carrying the mark) is read
    with its OID before the dump and dropped after it under the same OID rule;
  * the attempt's database is checked by OID before and after the restore, and the hashing connection checks
    the OID of the database it is connected to; any change records BACKUP_SCRATCH_REPLACED, unverified.
  Operating boundary (stated, not assumed approved): an administrator who lists the databases during a backup
  and deliberately replaces the attempt's database under its random name between the OID check and pg_restore
  connecting can receive the restored tables in the replacement. Nothing is dropped and the night is recorded
  unverified (BACKUP_SCRATCH_REPLACED).

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
import secrets
import shutil
import subprocess
import time
import uuid
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
SCRATCH_MARK = 'cp7-nightly-backup scratch: restored, compared and dropped by scripts/cp7_nightly_backup.py'
CRON_ERROR = re.compile(r'^pg_restore: error: could not execute query: ERROR:  (can only create extension in database postgres'
                        r'|extension "pg_cron" does not exist|schema "cron" does not exist|relation "cron\.[a-z_]+" does not exist)$')


def db_url(url, name):
    u = urlparse(url)
    return urlunparse(u._replace(path='/' + name))


def user_of(url):
    return urlparse(url).username or 'postgres'


def table_hashes(cur):
    """Every table of every non-system schema: row count and md5 of the rows (cron aside), as `cur` sees them."""
    tables = cur.execute("""select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where c.relkind in('r','p') and n.nspname not in('pg_catalog','information_schema','cron')
        and n.nspname not like 'pg\\_toast%' and n.nspname not like 'pg\\_temp%' order by 1,2""").fetchall()
    out = {}
    for schema, table in tables:
        n, h = cur.execute(sql.SQL("select count(*),md5(coalesce(string_agg(x::text,chr(10) order by x::text),'')) from {}.{} x").format(
            sql.Identifier(schema), sql.Identifier(table))).fetchone()
        out[schema + '.' + table] = dict(rows=n, md5=h)
    return out


def data_hashes(url, expected_oid=None):
    """Row hashes of every table of the database at `url`. With expected_oid the connection first checks that it
    is connected to that very database (ASR-OPS-01), so the hashes are never read from a replacement."""
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        conn.read_only = True
        if expected_oid is not None:
            got = cur.execute('select oid from pg_database where datname=current_database()').fetchone()[0]
            assert got == expected_oid, ('BACKUP_SCRATCH_REPLACED', 'hash connection is on another database', expected_oid, got)
        return table_hashes(cur)


ATTEMPT_MARK = re.compile(re.escape(SCRATCH_MARK) + r' attempt=([0-9a-f]{16}) oid=([0-9]+)')


def is_mark(comment, oid, token=None):
    """This tool's mark on the database with this OID. Only an attempt's mark counts: it names the attempt's token and
    the OID the database was created with, so a mark that ever landed on another database never counts as ours there.
    The plain mark earlier versions wrote (SCRATCH_MARK alone, no token or OID) is not ours anywhere: its text can be
    copied onto any database (independent audit Fable F-OPS-05, owner D13-12), and no night ran outside CI with it."""
    m = ATTEMPT_MARK.fullmatch(comment or '')
    return bool(m) and int(m.group(2)) == oid and (token is None or m.group(1) == token)


def identity(admin_url, name):
    """(oid, comment) of the database that has the name now, or None."""
    with psycopg.connect(db_url(admin_url, 'postgres')) as conn, conn.cursor() as cur:
        return cur.execute("select d.oid,shobj_description(d.oid,'pg_database') from pg_database d where d.datname=%s", (name,)).fetchone()


def scratch_state(admin_url, name):
    """None when no database has the name; OURS when it carries this tool's mark; FOREIGN otherwise."""
    r = identity(admin_url, name)
    return None if r is None else 'OURS' if is_mark(r[1], r[0]) else 'FOREIGN'


def mark_scratch(admin_url, name, token, oid):
    """Mark a database as one attempt's own: the attempt's token and the OID it was created with."""
    assert isinstance(token, str) and re.fullmatch(r'[0-9a-f]{16}', token) and isinstance(oid, int), ('BACKUP_MARK_INVALID', token, oid)
    mark = '%s attempt=%s oid=%d' % (SCRATCH_MARK, token, oid)
    with psycopg.connect(db_url(admin_url, 'postgres'), autocommit=True) as conn:
        conn.execute(sql.SQL('comment on database {} is {}').format(sql.Identifier(name), sql.Literal(mark)))


def create_attempt(admin_url, name):
    """Create the attempt's database with an OID chosen here (CREATE DATABASE ... OID, PostgreSQL 15+), so its
    identity is known before anything else can reach it. Never drops first: a taken name or OID fails."""
    with psycopg.connect(db_url(admin_url, 'postgres'), autocommit=True) as conn:
        for _ in range(8):
            oid = secrets.randbelow(4_000_000_000 - 1_000_000_000) + 1_000_000_000
            if conn.execute('select 1 from pg_database where oid=%s', (oid,)).fetchone():
                continue
            conn.execute(sql.SQL('create database {} oid {} template template0').format(sql.Identifier(name), sql.Literal(oid)))
            return oid
    raise AssertionError(('BACKUP_SCRATCH_NOT_CREATED', 'no free database OID found'))


def drop_owned(admin_url, oid, token=None, created_here=False):
    """Drop the database with this OID, only while it carries this tool's mark (the attempt's token when given).
    It is first moved under a fresh random name and checked again by OID, so a database that took its name in
    the meantime is never dropped: that one is put back under its name and REPLACED is returned. created_here: the
    attempt created this OID itself and may have stopped before marking it, so no comment at all also counts."""
    with psycopg.connect(db_url(admin_url, 'postgres'), autocommit=True) as conn:
        row = conn.execute("select datname,shobj_description(oid,'pg_database') from pg_database where oid=%s", (oid,)).fetchone()
        if row is None:
            return dict(result='ABSENT', oid=oid)
        name, comment = row
        if not (is_mark(comment, oid, token) or (created_here and comment is None)):
            return dict(result='NOT_OURS', oid=oid, name=name)
        tomb = 'cp7bv_drop_' + secrets.token_hex(12)
        for attempt in range(20):
            # Only sessions on this OID are ended (the attempt's own, or a leftover's); a session that is still
            # leaving makes the rename wait and retry.
            conn.execute('select pg_terminate_backend(pid) from pg_stat_activity where datid=%s and pid<>pg_backend_pid()', (oid,))
            try:
                conn.execute(sql.SQL('alter database {} rename to {}').format(sql.Identifier(name), sql.Identifier(tomb)))
                break
            except psycopg.errors.ObjectInUse as exc:
                detail = str(exc).splitlines()[0][:300]
                time.sleep(0.2)
                now = conn.execute('select datname from pg_database where oid=%s', (oid,)).fetchone()
                if now is None or now[0] != name:
                    return dict(result='REPLACED', oid=oid, name=name, detail='moved or dropped while waiting: ' + detail)
            except psycopg.Error as exc:
                return dict(result='REPLACED', oid=oid, name=name, detail=str(exc).splitlines()[0][:300])
        else:
            return dict(result='IN_USE', oid=oid, name=name, detail=detail)
        moved = conn.execute('select oid from pg_database where datname=%s', (tomb,)).fetchone()
        if moved is None or moved[0] != oid:
            if moved is not None:  # another database had the name at the rename: give it its name back
                conn.execute(sql.SQL('alter database {} rename to {}').format(sql.Identifier(tomb), sql.Identifier(name)))
            return dict(result='REPLACED', oid=oid, name=name, found=None if moved is None else moved[0])
        conn.execute(sql.SQL('drop database {} with (force)').format(sql.Identifier(tomb)))
        return dict(result='DROPPED', oid=oid, name=name)


def leftovers(admin_url, scratch):
    """Databases an earlier night of this tool left: the configured name or `<scratch>_<random>`, carrying an attempt's
    mark for its own OID (is_mark)."""
    pattern = '^' + re.escape(attempt_prefix(scratch)) + '_[0-9a-f]{16}$'
    with psycopg.connect(db_url(admin_url, 'postgres')) as conn, conn.cursor() as cur:
        rows = cur.execute("""select d.oid,d.datname,shobj_description(d.oid,'pg_database') from pg_database d
            where d.datname=%s or d.datname ~ %s order by d.datname""", (scratch, pattern)).fetchall()
    return [dict(oid=o, name=n) for o, n, c in rows if is_mark(c, o)]


def attempt_prefix(scratch):
    return scratch[:44]


class Tools:
    """pg_dump/pg_restore/createdb/dropdb either inside a disposable container or with the local client."""

    def __init__(self, admin_url, container=None):
        self.admin_url, self.container, self.user = admin_url, container, user_of(admin_url)

    def _run(self, args, check=True):
        cmd = ['docker', 'exec', self.container, *args] if self.container else args
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def _db(self, name):
        return ['-U', self.user, '-d', name] if self.container else ['--dbname=' + db_url(self.admin_url, name)]

    def dump(self, source, target, snapshot):
        if self.container:
            inner = '/tmp/' + target.name
            r = self._run(['pg_dump', *self._db(source), '--snapshot=' + snapshot, '-Fc', '-f', inner], check=False)
            if r.returncode == 0:
                subprocess.run(['docker', 'cp', f'{self.container}:{inner}', str(target)], check=True, capture_output=True)
            return r
        return self._run(['pg_dump', *self._db(source), '--snapshot=' + snapshot, '-Fc', '-f', str(target)], check=False)

    def restore(self, name, file):
        if self.container:
            inner = '/tmp/' + file.name
            return self._run(['pg_restore', *self._db(name), '--no-password', inner], check=False)
        return self._run(['pg_restore', *self._db(name), '--no-password', str(file)], check=False)

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
    # The scratch database can never be the database backed up; only databases this tool created and marked are
    # ever dropped, and only by OID (Fable F-OPS-01, Astra ASR-OPS-01).
    assert scratch and source and scratch != source and scratch != 'postgres', 'BACKUP_SCRATCH_MUST_BE_SEPARATE'
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    started = now or datetime.now(timezone.utc)
    name = 'erp-%s-%s.dump' % (started.astimezone(WIB).strftime('%Y%m%d-%H%M%S-WIB'), uuid.uuid4().hex[:12])
    file = dest / name
    receipt_path = dest / (name + '.receipt.json')
    if file.exists() or receipt_path.exists():
        raise FileExistsError('BACKUP_NAME_COLLISION: %s' % name)
    # Claim the receipt name first (exclusive create): two attempts can never write the same receipt.
    with open(receipt_path, 'x') as claim:
        claim.write(json.dumps(dict(contract=CONTRACT, file=name, state='STARTED', started_at_utc=started.isoformat(), restore_verified=False)) + '\n')
    tools = Tools(admin_url, container)
    token = secrets.token_hex(8)
    attempt_db = '%s_%s' % (attempt_prefix(scratch), token)
    receipt = dict(contract=CONTRACT, label='CP7C_NIGHTLY_BACKUP', schedule=SCHEDULE, file=name, source_database=source,
                   scratch_database=scratch, started_at_utc=started.isoformat(), started_at_wib=started.astimezone(WIB).isoformat(),
                   scratch_attempt=dict(database=attempt_db, token=token, oid=None), restore_verified=False, production_go=False)
    attempt_oid = None
    try:
        state = scratch_state(admin_url, scratch)
        receipt['scratch_before'] = state or 'ABSENT'
        assert state != 'FOREIGN', ('BACKUP_SCRATCH_EXISTS_NOT_OURS', scratch)
        # Leftovers of earlier nights are identified now, by OID, and dropped after the dump under that same OID.
        old = leftovers(admin_url, scratch)
        t0 = time.monotonic()
        try:
            snap = psycopg.connect(db_url(admin_url, source))
        except psycopg.Error as exc:
            raise AssertionError(('BACKUP_DUMP_FAILED', 'source not readable', str(exc)[:300]))
        with snap:
            # One snapshot for the dump and for the source's hashes: the comparison is with what the dump holds.
            snap.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            snap.read_only = True
            with snap.cursor() as sc:
                snapshot = sc.execute('select pg_export_snapshot()').fetchone()[0]
                d = tools.dump(source, file, snapshot)
                receipt['dump'] = dict(exit=d.returncode, stderr=d.stderr[-2000:], seconds=round(time.monotonic() - t0, 1), snapshot=snapshot)
                assert d.returncode == 0 and file.exists() and file.stat().st_size > 0, 'BACKUP_DUMP_FAILED'
                a = table_hashes(sc)
            snap.rollback()
        data = file.read_bytes()
        receipt.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        receipt['leftovers'] = [dict(row, **drop_owned(admin_url, row['oid'])) for row in old]
        # DROPPED, or ABSENT (gone meanwhile; whatever holds its name now is caught just below). Anything else means
        # the name no longer leads to the database read before the dump.
        if any(r['result'] not in ('DROPPED', 'ABSENT') for r in receipt['leftovers']):
            raise AssertionError(('BACKUP_SCRATCH_REPLACED', 'a leftover is no longer the database read before the dump',
                                  [r for r in receipt['leftovers'] if r['result'] not in ('DROPPED', 'ABSENT')]))
        # The configured name must be free; a database holding it now (ours or not) is never used or dropped.
        now_state = scratch_state(admin_url, scratch)
        if now_state is not None:
            code = 'BACKUP_SCRATCH_REPLACED' if any(r['name'] == scratch for r in old) else 'BACKUP_SCRATCH_NOT_CREATED'
            raise AssertionError((code, 'the scratch name is taken by a database this attempt did not create', scratch, now_state))
        try:
            attempt_oid = create_attempt(admin_url, attempt_db)
        except psycopg.Error as exc:
            raise AssertionError(('BACKUP_SCRATCH_NOT_CREATED', str(exc).splitlines()[0][:300]))
        receipt['scratch_attempt']['oid'] = attempt_oid
        mark_scratch(admin_url, attempt_db, token, attempt_oid)
        made = identity(admin_url, attempt_db)
        assert made is not None and made[0] == attempt_oid and is_mark(made[1], attempt_oid, token), (
            'BACKUP_SCRATCH_REPLACED', 'attempt database not found with its OID and mark', attempt_db)
        t1 = time.monotonic()
        before_restore = identity(admin_url, attempt_db)
        assert before_restore is not None and before_restore[0] == attempt_oid, ('BACKUP_SCRATCH_REPLACED', 'before restore', attempt_db)
        r = tools.restore(attempt_db, file)
        after_restore = identity(admin_url, attempt_db)
        assert after_restore is not None and after_restore[0] == attempt_oid, ('BACKUP_SCRATCH_REPLACED', 'after restore', attempt_db)
        errors = [line for line in r.stderr.splitlines() if line.startswith('pg_restore: error:')]
        unexplained = [line for line in errors if not CRON_ERROR.match(line)]
        receipt['restore'] = dict(exit=r.returncode, seconds=round(time.monotonic() - t1, 1), errors=errors[:40], unexplained=unexplained[:40])
        b = data_hashes(db_url(admin_url, attempt_db), expected_oid=attempt_oid)
        differ = {t: dict(source=a.get(t), restored=b.get(t)) for t in sorted(set(a) | set(b)) if a.get(t) != b.get(t)}
        receipt['data'] = dict(tables=len(a), rows=sum(v['rows'] for v in a.values()), differ=differ, compared_with='source in the dump snapshot')
        receipt['restore_verified'] = not unexplained and not differ and len(a) > 0
    except Exception as exc:  # the receipt records the failure; nothing is removed
        receipt['error'] = str(exc)[:2000]
        receipt['restore_verified'] = False
    finally:
        # Only the database this attempt created is dropped, by its OID and token; nothing is dropped by name.
        try:
            receipt['scratch_attempt']['drop'] = drop_owned(admin_url, attempt_oid, token, created_here=True) if attempt_oid is not None else dict(result='NOT_CREATED')
            if receipt['scratch_attempt']['drop']['result'] not in ('DROPPED', 'NOT_CREATED', 'ABSENT'):
                receipt['restore_verified'] = False
                receipt.setdefault('error', str(('BACKUP_SCRATCH_REPLACED', 'final drop', receipt['scratch_attempt']['drop']))[:2000])
            receipt['scratch_after'] = scratch_state(admin_url, scratch) or 'ABSENT'
        except psycopg.Error as exc:
            receipt['scratch_after'] = 'UNKNOWN: ' + str(exc)[:300]
            receipt['restore_verified'] = False
        tools.remove_inner(file)
    finished = datetime.now(timezone.utc)
    receipt.update(finished_at_utc=finished.isoformat(), finished_at_wib=finished.astimezone(WIB).isoformat())
    receipt_path.write_text(json.dumps(receipt, indent=1, default=str) + '\n')
    receipt['retention'] = prune(dest, keep, receipt['restore_verified'])
    receipt_path.write_text(json.dumps(receipt, indent=1, default=str) + '\n')
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
