"""Cases for scripts/cp7_offsite_backup.py (owner decisions 13 Oct 2026, D13-5/6/7), on disposable servers only.

usage: python scripts/cp7_offsite_backup_cases.py SOURCE_URL SCRATCH_ADMIN_URL REMOTE PASSPHRASE_FILE OUT.json

SOURCE_URL is a disposable copy of the ERP database (CI: the aligned CP6 copy in the runner's Supabase container),
SCRATCH_ADMIN_URL a second PostgreSQL on the runner (same image), REMOTE an rclone remote path (CI: a MinIO bucket on
the runner, and a local directory). The cases add one audit-owned canary table and one role to the source and remove
them at the end; every assertion reads the real tool's receipts, remote files and databases. Each case prints one
JSON line; the last line is the suite verdict.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg import sql

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cp7_nightly_backup as v1
import cp7_offsite_backup as off

CANARY_TABLE = 'cp7_offsite_canary'
CANARY_ROLE = 'cp7_offsite_reader'
IDS = ['OFB_VERIFIED_FROM_FETCHED_COPY', 'OFB_NO_CONTENT_OUTSIDE_THE_REMOTE', 'OFB_TAMPERED_REMOTE_COPY_UNVERIFIED',
       'OFB_DATA_DIFFERENCE_DETECTED', 'OFB_STRUCTURE_DIFFERENCE_DETECTED', 'OFB_SEQUENCE_DIFFERENCE_DETECTED',
       'OFB_VERIFIED_UNDER_WRITES', 'OFB_REMOTE_RETENTION_14_VERIFIED', 'OFB_NAME_COLLISION_REFUSED',
       'OFB_SCRATCH_SERVER_GUARDS', 'OFB_FOREIGN_SCRATCH_NAME_REFUSED']


def main(source_url, scratch_url, remote_path, passphrase_file, out_path):
    remote = off.Remote(remote_path)
    marker = 'CP7_OFFSITE_CANARY_' + uuid.uuid4().hex
    source_db = source_url.rsplit('/', 1)[-1].split('?')[0]
    results = {}

    def night(**kw):
        return off.backup(source_url, scratch_url, remote, passphrase_file, with_detail=True, **kw)

    def why(r):
        """Failure message of a case: the summary plus, on these disposable servers only, the night's error and its
        first restore errors (the encrypted detail of a real night is never printed)."""
        d = r.get('_detail') or {}
        return dict(summary=why(r), error=d.get('error'), restore_errors=(d.get('pg_restore_errors') or [])[:8],
                    structure_differ={k: dict(only_source=v['only_source'][:5], only_restored=v['only_restored'][:5])
                                      for k, v in (d.get('structure_differ') or {}).items()},
                    data_differ=list(d.get('data_differ') or {})[:10])

    def remote_files():
        return remote.names()

    def source_state():
        with psycopg.connect(source_url) as c, c.cursor() as cur:
            return v1.table_hashes(cur), off.sequence_state(cur)

    def scratch_attempts():
        with psycopg.connect(v1.db_url(scratch_url, 'postgres')) as c:
            return [r[0] for r in c.execute("select datname from pg_database where datname like 'cp7\\_offsite\\_verify\\_%'").fetchall()]

    def scratch_has_role(name):
        with psycopg.connect(v1.db_url(scratch_url, 'postgres')) as c:
            return c.execute('select 1 from pg_roles where rolname=%s', (name,)).fetchone() is not None

    def clean_remote():
        for name in remote_files():
            remote.delete(name)

    def run(case_id, fn):
        t0 = time.monotonic()
        try:
            out = fn()
            out = dict(case=case_id, status='PASS', seconds=round(time.monotonic() - t0, 1), **out)
        except Exception as exc:  # the first failure stays as it is
            out = dict(case=case_id, status='FAIL', error=repr(exc)[:3000])
        results[case_id] = out
        print(json.dumps(dict(group='CP7_OFFSITE_BACKUP', **out), default=str), flush=True)

    # Fixture: one canary table with a unique marker value, readable by one role that the scratch server lacks.
    with psycopg.connect(source_url, autocommit=True) as c:
        if not c.execute('select 1 from pg_roles where rolname=%s', (CANARY_ROLE,)).fetchone():
            c.execute(sql.SQL('create role {} nologin').format(sql.Identifier(CANARY_ROLE)))
        c.execute(sql.SQL('drop table if exists public.{}').format(sql.Identifier(CANARY_TABLE)))
        c.execute(sql.SQL('create table public.{}(id bigint generated always as identity primary key, v text not null)').format(sql.Identifier(CANARY_TABLE)))
        c.execute(sql.SQL('insert into public.{}(v) select %s||g from generate_series(1,200) g').format(sql.Identifier(CANARY_TABLE)), (marker,))
        c.execute(sql.SQL('grant select on public.{} to {}').format(sql.Identifier(CANARY_TABLE), sql.Identifier(CANARY_ROLE)))
    assert not scratch_has_role(CANARY_ROLE), 'the scratch server must not have the canary role beforehand'
    clean_remote()
    try:
        before = source_state()

        def verified():
            r = night()
            names = remote_files()
            assert r['restore_verified'] is True and r['codes'] == [], why(r)
            assert sorted(names) == sorted([r['file'], r['detail'], r['night'] + '.receipt.json']), names
            assert r['fetched_back'] == dict(sha256_equal=True, dump_sha256_equal=True), r['fetched_back']
            assert r['data']['tables_differ'] == 0 and r['data']['sequences_differ'] == 0 and r['structure']['differ'] == {}, r
            assert r['scratch_attempt']['drop']['result'] == 'DROPPED' and scratch_attempts() == [], r['scratch_attempt']
            assert r['roles']['created'] >= 1 and CANARY_ROLE in r['_detail']['roles_created'] and not scratch_has_role(CANARY_ROLE), r['roles']
            assert source_state() == before, 'source changed'
            with tempfile.TemporaryDirectory() as d:
                enc = Path(d) / 'f.gpg'
                remote.get(r['file'], enc)
                assert not enc.read_bytes().startswith(b'PGDMP'), 'stored file is not encrypted'
                wrong = Path(d) / 'wrong'
                wrong.write_text('not-the-passphrase')
                home = Path(d) / 'g'
                home.mkdir(mode=0o700)
                bad = off.gpg(['--decrypt', '-o', str(Path(d) / 'x'), str(enc)], wrong, home)
                assert bad.returncode != 0, 'wrong passphrase decrypted the file'
            stored = json.loads(remote.cat(r['night'] + '.receipt.json'))
            assert stored['restore_verified'] is True and stored['encrypted']['sha256'] == r['encrypted']['sha256'], stored
            return dict(restore_verified=True, tables=r['data']['tables'], rows=r['data']['rows'], sequences=r['data']['sequences'],
                        structure_objects=r['structure']['objects'], roles_created=r['roles']['created'], restore_errors=r['restore'],
                        versions=r['versions'], remote_files=3, wrong_passphrase_refused=True, source_unchanged=True)
        run(IDS[0], verified)

        def no_content():
            # The scheduler's command line, as a separate process: the console carries codes and counts only.
            env = dict(os.environ, PYTHONPATH=os.path.dirname(os.path.abspath(__file__)))
            p = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cp7_offsite_backup.py'),
                                '--source-url', source_url, '--scratch-admin-url', scratch_url, '--remote', remote_path,
                                '--passphrase-file', passphrase_file], capture_output=True, text=True, env=env)
            console = p.stdout + p.stderr
            assert p.returncode == 0 and json.loads(p.stdout.strip().splitlines()[-1])['restore_verified'] is True, console[-2000:]
            assert marker not in console and CANARY_TABLE not in console and CANARY_ROLE not in console, 'content in console'
            leaked = []
            with tempfile.TemporaryDirectory() as d:
                for name in remote_files():
                    f = Path(d) / name
                    remote.get(name, f)
                    raw = f.read_bytes()
                    if marker.encode() in raw or CANARY_TABLE.encode() in raw or CANARY_ROLE.encode() in raw or raw.startswith(b'PGDMP'):
                        leaked.append(name)
            assert leaked == [], leaked
            return dict(console_lines=len(console.splitlines()), marker_in_console=False, plain_content_on_remote=False)
        run(IDS[1], no_content)
        clean_remote()

        def tampered():
            existing = remote_files()
            def corrupt(name):
                subprocess.run(['rclone', 'rcat', remote.path + '/' + name], input=b'not the uploaded file', check=True, capture_output=True)
            r = night(hooks=dict(after_upload=corrupt))
            assert r['restore_verified'] is False and 'BACKUP_REMOTE_COPY_DIFFERS' in r['codes'], why(r)
            assert r['retention']['reason'] == 'TONIGHT_NOT_VERIFIED_NOTHING_REMOVED' and set(existing) <= set(remote_files()), r['retention']
            assert scratch_attempts() == [] and source_state() == before
            return dict(code='BACKUP_REMOTE_COPY_DIFFERS', nothing_restored=r.get('restore') is None, nothing_removed=True)
        run(IDS[2], tampered)

        def with_restore_hook(sql_text):
            def hook(url):
                with psycopg.connect(url, autocommit=True) as c:
                    c.execute(sql_text)
            return night(hooks=dict(after_restore=hook))

        def data_difference():
            r = with_restore_hook(f"update public.{CANARY_TABLE} set v=v||'x' where id=1")
            assert r['restore_verified'] is False and r['codes'] == ['BACKUP_DATA_DIFFERS'] and r['data']['tables_differ'] == 1, why(r)
            assert list(r['_detail']['data_differ']) == ['public.' + CANARY_TABLE] and r['retention']['removed'] == [], r['_detail']['data_differ']
            return dict(code='BACKUP_DATA_DIFFERS', tables_differ=1, nothing_removed=True)
        run(IDS[3], data_difference)

        def structure_difference():
            r = with_restore_hook(f'revoke select on public.{CANARY_TABLE} from {CANARY_ROLE}; '
                                  f'alter table public.{CANARY_TABLE} alter column v drop not null')
            differ = r['structure']['differ']
            assert r['restore_verified'] is False and r['codes'] == ['BACKUP_STRUCTURE_DIFFERS'], why(r)
            assert set(differ) == {'relations', 'columns'}, differ
            return dict(code='BACKUP_STRUCTURE_DIFFERS', categories=differ, acl_and_column_change_seen=True)
        run(IDS[4], structure_difference)

        def sequence_difference():
            r = with_restore_hook(f"select setval(pg_get_serial_sequence('public.{CANARY_TABLE}','id'), 999999)")
            assert r['restore_verified'] is False and r['codes'] == ['BACKUP_DATA_DIFFERS'] and r['data']['sequences_differ'] == 1, why(r)
            return dict(code='BACKUP_DATA_DIFFERS', sequences_differ=1)
        run(IDS[5], sequence_difference)

        def under_writes():
            stop, written = threading.Event(), [0]
            with psycopg.connect(source_url, autocommit=True) as c:
                c.execute('create table if not exists public.cp7_offsite_writes(n bigint)')

            def writer():
                with psycopg.connect(source_url, autocommit=True) as c:
                    while not stop.is_set():
                        c.execute('insert into public.cp7_offsite_writes values(1)')
                        written[0] += 1
            t = threading.Thread(target=writer)
            t.start()
            try:
                time.sleep(0.5)
                r = night()
            finally:
                stop.set()
                t.join(30)
                with psycopg.connect(source_url, autocommit=True) as c:
                    c.execute('drop table if exists public.cp7_offsite_writes')
            assert r['restore_verified'] is True and written[0] > 0, (why(r), written)
            return dict(restore_verified_while_writing=True, rows_written=written[0], compared_with=r['data']['compared_with'])
        run(IDS[6], under_writes)

        def retention():
            clean_remote()
            base = datetime.now(timezone.utc) - timedelta(days=40)
            with tempfile.TemporaryDirectory() as d:
                def synthetic(i, ok, receipt=True):
                    at = base + timedelta(days=i)
                    n = 'erp-%s-%012x' % (at.astimezone(v1.WIB).strftime('%Y%m%d-%H%M%S-WIB'), i)
                    f = Path(d) / 'x'
                    f.write_bytes(b'synthetic encrypted dump %d' % i)
                    remote.put(f, n + '.dump.gpg')
                    if receipt:
                        f.write_text(json.dumps(dict(contract=off.CONTRACT, night=n, restore_verified=ok)))
                        remote.put(f, n + '.receipt.json')
                    return n
                nights = [synthetic(i, ok=i not in (3, 9)) for i in range(16)] + [synthetic(16, ok=False, receipt=False)]
                before_failed = remote_files()
                bad = night(hooks=dict(after_upload=lambda name: subprocess.run(['rclone', 'rcat', remote.path + '/' + name],
                                                                                    input=b'x', check=True, capture_output=True)))
                assert bad['restore_verified'] is False and set(before_failed) <= set(remote_files()), 'a failed night removed something'
                good = night()
            verified_synthetic = [n for i, n in enumerate(nights[:16]) if i not in (3, 9)]
            kept_expected = sorted([good['night']] + verified_synthetic[-13:], reverse=True)
            assert good['restore_verified'] is True and good['retention']['kept'] == kept_expected, good['retention']
            left = {off.NIGHT.match(n).group(1) for n in remote_files()}
            oldest = kept_expected[-1]
            assert all(n >= oldest for n in left) and set(kept_expected) <= left, sorted(left)
            assert bad['night'] in left and nights[16] in left, 'nights newer than the oldest kept stay'
            return dict(kept_verified=len(kept_expected), removed_files=len(good['retention']['removed']),
                        failed_night_removed_nothing=True, unverified_and_orphan_newer_than_oldest_kept_stay=True)
        run(IDS[7], retention)
        clean_remote()

        def collision():
            real = off.secrets.token_hex
            fixed = {6: 'abcdefabcdef'}
            off.secrets.token_hex = lambda n=None: fixed.get(n) or real(n)
            try:
                at = datetime.now(timezone.utc).replace(microsecond=0)
                name = 'erp-%s-abcdefabcdef' % at.astimezone(v1.WIB).strftime('%Y%m%d-%H%M%S-WIB')
                with tempfile.TemporaryDirectory() as d:
                    f = Path(d) / 'x'
                    f.write_bytes(b'an earlier night with this name')
                    remote.put(f, name + '.dump.gpg')
                r = night(now=at)
            finally:
                off.secrets.token_hex = real
            assert r['restore_verified'] is False and r['codes'] == ['BACKUP_NAME_COLLISION'], why(r)
            assert remote_files() == [name + '.dump.gpg'] and remote.cat(name + '.dump.gpg') == 'an earlier night with this name'
            return dict(code='BACKUP_NAME_COLLISION', existing_file_unchanged=True, nothing_written=True)
        run(IDS[8], collision)
        clean_remote()

        def scratch_guards():
            refused = {}
            for label, url in (('same_server', v1.db_url(source_url, 'postgres')), ('not_local', 'postgresql://postgres@scratch.example.com:5432/postgres')):
                try:
                    off.backup(source_url, url, remote, passphrase_file)
                    refused[label] = None
                except AssertionError as exc:
                    refused[label] = str(exc.args[0])
                except psycopg.Error as exc:
                    refused[label] = 'CONNECT_REFUSED:' + type(exc).__name__
            real = off.server_identity
            off.server_identity = lambda url: (real(url)[0] + (1 if url == scratch_url else 0), real(url)[1])
            try:
                mism = night()
            finally:
                off.server_identity = real
            assert refused == dict(same_server='BACKUP_SCRATCH_SERVER_IS_SOURCE', not_local='BACKUP_SCRATCH_SERVER_NOT_LOCAL'), refused
            assert mism['codes'] == ['BACKUP_SCRATCH_VERSION_MISMATCH'] and remote_files() == [], why(mism)
            return dict(refused=refused, version_mismatch='BACKUP_SCRATCH_VERSION_MISMATCH', nothing_written=True)
        run(IDS[9], scratch_guards)

        def foreign_scratch():
            with psycopg.connect(v1.db_url(scratch_url, 'postgres'), autocommit=True) as c:
                c.execute('drop database if exists cp7_offsite_verify')
                c.execute('create database cp7_offsite_verify template template0')
            try:
                r = night()
                with psycopg.connect(v1.db_url(scratch_url, 'postgres')) as c:
                    kept = c.execute("select 1 from pg_database where datname='cp7_offsite_verify'").fetchone() is not None
            finally:
                with psycopg.connect(v1.db_url(scratch_url, 'postgres'), autocommit=True) as c:
                    c.execute('drop database if exists cp7_offsite_verify')
            assert r['codes'] == ['BACKUP_SCRATCH_EXISTS_NOT_OURS'] and kept and remote_files() == [], why(r)
            return dict(code='BACKUP_SCRATCH_EXISTS_NOT_OURS', foreign_database_kept=True, nothing_written=True)
        run(IDS[10], foreign_scratch)
        after = source_state()
    finally:
        clean_remote()
        with psycopg.connect(source_url, autocommit=True) as c:
            c.execute(sql.SQL('drop table if exists public.{}').format(sql.Identifier(CANARY_TABLE)))
            c.execute('drop table if exists public.cp7_offsite_writes')
            c.execute(sql.SQL('drop role if exists {}').format(sql.Identifier(CANARY_ROLE)))
    verdict = dict(group='CP7_OFFSITE_BACKUP', planned=IDS, final={k: results.get(k, {}).get('status', 'MISSING') for k in IDS},
                   source_database=source_db, source_unchanged_by_the_backups=after == before,
                   status='PASS' if all(results.get(k, {}).get('status') == 'PASS' for k in IDS) and after == before else 'FAIL')
    print(json.dumps(verdict), flush=True)
    Path(out_path).write_text(json.dumps(dict(verdict=verdict, cases=results), indent=1, default=str) + '\n')
    return verdict['status'] == 'PASS'


if __name__ == '__main__':
    sys.exit(0 if main(*sys.argv[1:6]) else 1)
