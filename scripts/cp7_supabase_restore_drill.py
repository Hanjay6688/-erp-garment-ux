"""Restore drill into a fresh Supabase environment with hosted-like privileges (owner decision 13 Oct 2026, D13-8b).

The owner's condition "before production, prove the restore into a separate Supabase project" is met without a third
hosted project: a fresh, disposable local Supabase stack on the GitHub runner (same Postgres image and extensions)
stands for the new project, and the restore runs as its `postgres` role, which is not a superuser there, as on
hosted. Boundary, recorded in every result: passing here does not by itself prove a restore into Supabase hosted.

One drill:
  1. Take one night from the store (rclone remote or local folder): the encrypted dump and its receipt. The file's
     SHA-256 must equal the receipt's, and after decryption the dump's SHA-256 must equal the receipt's too. Then
     the target must be a fresh one: its role `postgres`, not a superuser, the managed tables empty and `public`
     without objects (DRILL_TARGET_NOT_FRESH otherwise: a target restored into before is refused).
  2. List what the fresh target already has: a schema-only dump of it, taken as its `postgres` role, read with the
     same pg_restore. An entry of the night's listing (kind, schema, name, owner) that the target already lists is
     Supabase's own and is left as the target has it.
  3. Restore, as the target's `postgres` (checked: not a superuser), the way a new project is filled:
       - every definition the target does not list yet: the application's schemas, its objects in `public`, the
         extensions the target lacks, and what the application added inside Supabase's schemas (on ERP, the
         trigger trg_cp45_guard_last_owner_auth_delete on auth.users);
       - privileges, comments and default privileges the target lists too, replayed when their owner is a role the
         restoring role can act as; others stay as the target has them;
       - the data of the application's schemas, and of the chosen Supabase-managed tables (default auth.users then
         auth.identities: the logins), loaded in that order because the target already has the foreign key;
       - roles that own or hold privileges on the source and are missing on the target (NOLOGIN, granted to the
         restoring role so it can hand ownership to them).
     pg_cron (schema cron, its extension and jobs) is left out, as in the nightly check; database-level entries too.
     A listing entry of a kind this drill does not know stops the drill (DRILL_TOC_UNKNOWN).
  4. Compare with the source (in CI the disposable source the night was taken from, unchanged since): row count and
     md5 of every table of the application's schemas and of the managed tables, sequence state of the application's
     schemas, and the whole structure fingerprint of the off-site tool (every schema, owners, privileges), both the
     compared (normalized) form and the raw form, with every raw difference recorded. Tables outside those that hold
     rows in the source and were not restored are counted (left_behind), never silently dropped from the record.
The drill prints one JSON line of codes and counts. Nothing of the database's content is printed.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg
from psycopg import sql

import cp7_offsite_backup as off

CONTRACT = 'cp7.supabase-restore-drill.v1'
BOUNDARY = ('Restored into a fresh local Supabase stack on the runner, as its non-superuser postgres role, with the same '
            'Postgres image and extensions. This does not by itself prove a restore into Supabase hosted.')
MANAGED_DATA = ('auth.users', 'auth.identities')
# Every kind pg_dump 17 writes into a listing (pg_restore -l). Several are more than one word.
KINDS = {'ACCESS METHOD', 'ACL', 'AGGREGATE', 'BLOB', 'BLOB DATA', 'BLOB METADATA', 'BLOBS', 'CAST', 'CHECK CONSTRAINT',
         'COLLATION', 'COMMENT', 'CONSTRAINT', 'CONVERSION', 'DATABASE', 'DATABASE PROPERTIES', 'DEFAULT', 'DEFAULT ACL',
         'DOMAIN', 'ENCODING', 'EVENT TRIGGER', 'EXTENSION', 'FK CONSTRAINT', 'FOREIGN DATA WRAPPER', 'FOREIGN SERVER',
         'FOREIGN TABLE', 'FUNCTION', 'INDEX', 'INDEX ATTACH', 'LARGE OBJECT', 'MATERIALIZED VIEW',
         'MATERIALIZED VIEW DATA', 'OPERATOR', 'OPERATOR CLASS', 'OPERATOR FAMILY', 'POLICY', 'PROCEDURAL LANGUAGE',
         'PROCEDURE', 'PUBLICATION', 'PUBLICATION TABLE', 'PUBLICATION TABLES IN SCHEMA', 'ROW SECURITY', 'RULE',
         'SCHEMA', 'SEARCHPATH', 'SECURITY LABEL', 'SEQUENCE', 'SEQUENCE OWNED BY', 'SEQUENCE SET', 'SHELL TYPE',
         'STATISTICS', 'STDSTRINGS', 'SUBSCRIPTION', 'SUBSCRIPTION TABLE', 'TABLE', 'TABLE ATTACH', 'TABLE DATA',
         'TEXT SEARCH CONFIGURATION', 'TEXT SEARCH DICTIONARY', 'TEXT SEARCH PARSER', 'TEXT SEARCH TEMPLATE',
         'TRANSFORM', 'TRIGGER', 'TYPE', 'USER MAPPING', 'VIEW'}
MULTI = sorted((k for k in KINDS if ' ' in k), key=len, reverse=True)
PRIVILEGE_KINDS = {'ACL', 'COMMENT', 'DEFAULT ACL', 'SECURITY LABEL'}
DATA_KINDS = {'TABLE DATA', 'SEQUENCE SET', 'MATERIALIZED VIEW DATA', 'BLOB', 'BLOB DATA', 'BLOB METADATA', 'BLOBS',
              'LARGE OBJECT'}
DATABASE_KINDS = {'DATABASE', 'DATABASE PROPERTIES', 'ENCODING', 'STDSTRINGS', 'SEARCHPATH'}
TOC = re.compile(r'^(\d+); (\d+) (\d+) (.*)$')
# Objects of `public` that are not an extension's: none on a fresh project, so a target restored into before is refused.
PUBLIC_OBJECTS = """select (select count(*) from pg_class c where c.relnamespace='public'::regnamespace
      and not exists(select 1 from pg_depend d where d.classid='pg_class'::regclass and d.objid=c.oid and d.deptype='e'))
    + (select count(*) from pg_proc p where p.pronamespace='public'::regnamespace
      and not exists(select 1 from pg_depend d where d.classid='pg_proc'::regclass and d.objid=p.oid and d.deptype='e'))
    + (select count(*) from pg_type t where t.typnamespace='public'::regnamespace and t.typtype in ('e','d','r','m')
      and not exists(select 1 from pg_depend d where d.classid='pg_type'::regclass and d.objid=t.oid and d.deptype='e'))"""


def parse_toc(text):
    """[(line, kind, schema, name, owner, key)] of a pg_restore -l listing (comment lines skipped). The key is the
    entry without its dump ids, so listings of two databases compare by kind, schema, name and owner."""
    out = []
    for line in text.splitlines():
        m = TOC.match(line)
        if not m:
            continue
        key = m.group(4)
        kind = next((d for d in MULTI if key.startswith(d + ' ')), key.split(' ', 1)[0])
        assert kind in KINDS, ('DRILL_TOC_UNKNOWN', kind[:60])
        schema, _, tail = key[len(kind) + 1:].partition(' ')
        name, _, owner = tail.rpartition(' ')  # pg_restore writes the owner last, empty when there is none
        out.append((line, kind, schema, name, owner, key))
    return out


def _cron(kind, schema, name):
    return (schema == 'cron' or (kind == 'SCHEMA' and name == 'cron') or (kind == 'EXTENSION' and name == 'pg_cron')
            or (kind in PRIVILEGE_KINDS and name in ('EXTENSION pg_cron', 'SCHEMA cron')))


def select_toc(entries, target_keys, app_schemas, managed, assumable):
    """(listing lines to restore, {reason: count}) for a fresh target (see the module docstring). `managed` is
    ordered: its tables' data is loaded in that order."""
    keep, why = [], {}
    for line, kind, schema, name, owner, key in entries:
        if kind in DATABASE_KINDS or (kind in PRIVILEGE_KINDS and name.startswith('DATABASE ')):
            reason, ok = 'database_level', False
        elif _cron(kind, schema, name):
            reason, ok = 'pg_cron', False
        elif kind in DATA_KINDS:
            ok = schema in app_schemas or (kind == 'TABLE DATA' and '%s.%s' % (schema, name) in managed)
            reason = 'data' if ok else 'data_outside_application'
        elif key not in target_keys:
            reason, ok = 'absent_on_target', True
        elif kind in PRIVILEGE_KINDS and owner in assumable:
            reason, ok = 'privilege_replayed', True
        else:
            reason, ok = 'present_on_target', False
        why[reason] = why.get(reason, 0) + 1
        if ok:
            keep.append(line)
    # The managed tables' data in the given order (auth.identities references auth.users, and the target already
    # has that foreign key), at the place of the first of them.
    by_name = {'%s.%s' % (schema, name): line for line, kind, schema, name, owner, key in entries if kind == 'TABLE DATA'}
    lines = [by_name[m] for m in managed if m in by_name and by_name[m] in keep]
    if lines:
        at = min(keep.index(x) for x in lines)
        rest = [x for x in keep if x not in lines]
        keep = rest[:at] + lines + rest[at:]
    return keep, why


def table_data(cur, schemas, managed):
    """Row count and md5 of every table in the schemas and of the managed tables; sequence state in the schemas."""
    tables = cur.execute("""select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
        where c.relkind in ('r','p') and (n.nspname = any(%s) or (n.nspname||'.'||c.relname) = any(%s)) order by 1,2""",
                         (sorted(schemas), sorted(managed))).fetchall()
    data = {}
    for schema, table in tables:
        n, h = cur.execute(sql.SQL("select count(*),md5(coalesce(string_agg(x::text,chr(10) order by x::text),'')) from {}.{} x").format(
            sql.Identifier(schema), sql.Identifier(table))).fetchone()
        data[schema + '.' + table] = dict(rows=n, md5=h)
    seqs = {}
    for schema, name in cur.execute("""select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
            where c.relkind='S' and n.nspname = any(%s) order by 1,2""", (sorted(schemas),)).fetchall():
        last, called = cur.execute(sql.SQL('select last_value,is_called from {}.{}').format(sql.Identifier(schema), sql.Identifier(name))).fetchone()
        seqs[schema + '.' + name] = [int(last), bool(called)]
    return data, seqs


def fingerprint(url, schemas, managed):
    with psycopg.connect(url) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        with conn.cursor() as cur:
            data, seqs = table_data(cur, schemas, managed)
            return dict(data=data, sequences=seqs, structure=off.structure(cur), structure_raw=off.structure(cur, raw=True))


def left_behind(url, schemas, managed):
    """{table: rows} of the source's tables outside the restored ones that hold rows (counted one by one; a table the
    role cannot read is reported as None)."""
    out = {}
    with psycopg.connect(url, autocommit=True) as conn:
        tables = conn.execute("""select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
            where c.relkind in ('r','p') and n.nspname !~ '^pg_' and n.nspname not in ('information_schema','cron')
              and not (n.nspname = any(%s)) and not ((n.nspname||'.'||c.relname) = any(%s)) order by 1,2""",
                              (sorted(schemas), sorted(managed))).fetchall()
        for schema, table in tables:
            try:
                n = conn.execute(sql.SQL('select count(*) from {}.{}').format(sql.Identifier(schema), sql.Identifier(table))).fetchone()[0]
            except psycopg.Error:
                n = None
            if n != 0:
                out[schema + '.' + table] = n
    return out


def diff(a, b):
    return {k: dict(only_source=sorted(set(a.get(k, [])) - set(b.get(k, [])))[:200], only_restored=sorted(set(b.get(k, [])) - set(a.get(k, [])))[:200],
                    count=len(set(a.get(k, [])) ^ set(b.get(k, []))))
            for k in sorted(set(a) | set(b)) if set(a.get(k, [])) != set(b.get(k, []))}


def fetch_night(remote, night, passphrase_file, work):
    """The night's dump, decrypted, after both SHA-256 checks against its receipt."""
    receipt = json.loads(remote.cat(night + '.receipt.json'))
    assert receipt.get('contract') == off.CONTRACT and receipt.get('night') == night, ('DRILL_RECEIPT_INVALID', night)
    enc, plain, home = work / (night + '.dump.gpg'), work / (night + '.dump'), work / 'gnupg'
    home.mkdir(mode=0o700)
    remote.get(night + '.dump.gpg', enc)
    assert off.sha256_file(enc) == receipt['encrypted']['sha256'], ('DRILL_REMOTE_COPY_DIFFERS', 'encrypted')
    off.decrypt(enc, plain, passphrase_file, home)
    enc.unlink()
    assert off.sha256_file(plain) == receipt['dump']['sha256'], ('DRILL_REMOTE_COPY_DIFFERS', 'dump')
    return plain, receipt


def drill(remote, night, passphrase_file, source_url, target_url, managed=MANAGED_DATA, pg_dump='pg_dump', pg_restore='pg_restore',
          target_role='postgres'):
    out = dict(contract=CONTRACT, night=night, boundary=BOUNDARY, managed_data=list(managed), production_go=False, codes=[])
    detail = {}
    work = Path(tempfile.mkdtemp(prefix='cp7-drill-'))
    try:
        plain, receipt = fetch_night(remote, night, passphrase_file, work)
        out['fetched'] = dict(encrypted_sha256_equal=True, dump_sha256_equal=True)
        with psycopg.connect(target_url, autocommit=True) as t:
            who = t.execute('select current_user, rolsuper from pg_roles where rolname=current_user').fetchone()
            assert who[0] == target_role and who[1] is False, ('DRILL_TARGET_ROLE_NOT_HOSTED_LIKE', who[0], who[1])
            target_schemas = {r[0] for r in t.execute("select nspname from pg_namespace where nspname !~ '^pg_' and nspname <> 'information_schema'")}
            target_ext = {r[0]: r[1] for r in t.execute('select extname, extversion from pg_extension')}
            fresh = {m: t.execute(sql.SQL('select count(*) from {}.{}').format(*map(sql.Identifier, m.split('.')))).fetchone()[0] for m in managed}
            fresh['public'] = t.execute(PUBLIC_OBJECTS).fetchone()[0]
            version = t.execute("select current_setting('server_version')").fetchone()[0]
        assert all(v == 0 for v in fresh.values()), ('DRILL_TARGET_NOT_FRESH', fresh)
        out['target'] = dict(role=who[0], superuser=False, server_version=version, schemas=len(target_schemas))
        # What the fresh target already has, listed by the same pg_dump/pg_restore as the night.
        r = subprocess.run([pg_dump, '--schema-only', '--format=custom', '--no-password', '--file', str(work / 'target.dump'), target_url],
                           capture_output=True, text=True)
        assert r.returncode == 0, ('DRILL_TARGET_LISTING_FAILED', r.stderr[-1500:])
        target_keys = {e[5] for e in parse_toc(subprocess.run([pg_restore, '-l', str(work / 'target.dump')], capture_output=True, text=True, check=True).stdout)}
        with psycopg.connect(source_url) as s:
            source_schemas = {r[0] for r in s.execute("select nspname from pg_namespace where nspname !~ '^pg_' and nspname not in ('information_schema','cron')")}
            source_ext = {r[0]: r[1] for r in s.execute("select extname, extversion from pg_extension where extname <> 'pg_cron'")}
            s.execute("select set_config('search_path','pg_catalog',false)")
            needed = [r[0] for r in s.execute(off.ROLES).fetchall()]
        app = (source_schemas - target_schemas) | {'public'}
        added = sorted(set(source_ext) - set(target_ext))
        ext_version_differs = sorted(e for e in source_ext if e in target_ext and source_ext[e] != target_ext[e])
        out['scope'] = dict(application_schemas=len(app), extensions_added=len(added), extension_versions_differ=len(ext_version_differs))
        detail.update(application_schemas=sorted(app), extensions_added=added, extension_versions_differ=ext_version_differs)
        # Roles the night needs; created on the target and granted to the restoring role.
        made = []
        with psycopg.connect(target_url, autocommit=True) as t:
            have = {r[0] for r in t.execute('select rolname from pg_roles')}
            for name in needed:
                if name not in have:
                    t.execute(sql.SQL('create role {} nologin').format(sql.Identifier(name)))
                    t.execute(sql.SQL('grant {} to current_user').format(sql.Identifier(name)))
                    made.append(name)
            assumable = {r[0] for r in t.execute("select rolname from pg_roles where pg_has_role(current_user, oid, 'MEMBER')")}
        out['roles_created'] = len(made)
        detail['roles_created'] = made
        entries = parse_toc(subprocess.run([pg_restore, '-l', str(plain)], capture_output=True, text=True, check=True).stdout)
        chosen, why = select_toc(entries, target_keys, app, tuple(managed), assumable)
        chosen_set = set(chosen)
        foreign = sorted({e[4] for e in entries if e[0] in chosen_set and e[4] and e[4] not in assumable})
        outside = [e[5] for e in entries if e[0] in chosen_set and e[1] not in DATA_KINDS and e[2] not in app
                   and not (e[2] == '-' and (e[3] in app or e[3].split(' ', 1)[-1] in app))]
        out['toc'] = dict(entries=len(entries), restored=len(chosen), by_reason=why, owners_not_assumable=len(foreign),
                          restored_outside_application_schemas=len(outside))
        detail.update(toc_owners_not_assumable=foreign, toc_restored_outside_application_schemas=outside[:200])
        (work / 'list').write_text('\n'.join(chosen) + '\n')
        r = subprocess.run([pg_restore, '--dbname=' + target_url, '--no-password', '-L', str(work / 'list'), str(plain)], capture_output=True, text=True)
        plain.unlink()
        errors = [line for line in r.stderr.splitlines() if line.startswith('pg_restore: error:')]
        cats = {}
        for line in errors:
            c = off.restore_category(line)
            cats[c] = cats.get(c, 0) + 1
        out['restore'] = dict(exit=r.returncode, errors=len(errors), by_category=cats)
        detail['pg_restore_errors'] = errors[:200]
        if errors:
            out['codes'].append('DRILL_RESTORE_ERRORS')
        a = fingerprint(source_url, app, managed)
        b = fingerprint(target_url, app, managed)
        data_differ = {k: dict(source=a['data'].get(k), restored=b['data'].get(k)) for k in sorted(set(a['data']) | set(b['data'])) if a['data'].get(k) != b['data'].get(k)}
        seq_differ = {k: dict(source=a['sequences'].get(k), restored=b['sequences'].get(k)) for k in sorted(set(a['sequences']) | set(b['sequences']))
                      if a['sequences'].get(k) != b['sequences'].get(k)}
        strict, explained = off.compare_structure(a['structure'], b['structure'])
        raw = diff(a['structure_raw'], b['structure_raw'])
        behind = left_behind(source_url, app, managed)
        out['data'] = dict(tables=len(a['data']), rows=sum(v['rows'] for v in a['data'].values()), sequences=len(a['sequences']),
                           tables_differ=len(data_differ), sequences_differ=len(seq_differ),
                           managed_rows={m: a['data'].get(m, {}).get('rows') for m in managed},
                           left_behind=dict(tables=len(behind), rows=sum(v or 0 for v in behind.values()),
                                            unreadable=sum(1 for v in behind.values() if v is None)))
        out['structure'] = dict(objects={k: len(v) for k, v in a['structure'].items()}, differ={k: v['count'] for k, v in strict.items()},
                                explained={k: v['count'] for k, v in explained.items()}, raw_differ={k: v['count'] for k, v in raw.items()})
        detail.update(data_differ=data_differ, sequences_differ=seq_differ, structure_differ=strict, structure_explained=explained,
                      structure_raw_differ=raw, left_behind=behind)
        if data_differ or seq_differ:
            out['codes'].append('DRILL_DATA_DIFFERS')
        if strict:
            out['codes'].append('DRILL_STRUCTURE_DIFFERS')
        if ext_version_differs:
            out['codes'].append('DRILL_EXTENSION_VERSION_DIFFERS')
        out['restore_verified'] = not out['codes'] and len(a['data']) > 0
    except AssertionError as exc:
        a0 = exc.args[0] if exc.args else None
        out['codes'].append(a0[0] if isinstance(a0, tuple) else str(a0))
        out['restore_verified'] = False
        detail['error'] = [str(x)[:2000] for x in (a0 if isinstance(a0, tuple) else (a0,))]
    except Exception as exc:  # the result records the failure
        out['codes'].append('DRILL_FAILED')
        out['restore_verified'] = False
        out['error'] = dict(type=type(exc).__name__, sqlstate=getattr(exc, 'sqlstate', None))
        detail['error'] = [str(exc)[:2000]]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return out, detail


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--remote', required=True)
    p.add_argument('--night', required=True)
    p.add_argument('--passphrase-file', required=True)
    p.add_argument('--source-url', required=True, help='the disposable source the night was taken from (CI)')
    p.add_argument('--target-url', required=True, help="a fresh local Supabase stack's postgres role (not a superuser)")
    p.add_argument('--rclone-config')
    p.add_argument('--detail-out', help='write the full detail here (disposable runs only)')
    a = p.parse_args()
    out, detail = drill(off.Remote(a.remote, a.rclone_config), a.night, a.passphrase_file, a.source_url, a.target_url)
    if a.detail_out:
        Path(a.detail_out).write_text(json.dumps(detail, indent=1, default=str) + '\n')
    print(json.dumps(out, default=str))
    sys.exit(0 if out.get('restore_verified') else 1)


if __name__ == '__main__':
    main()
