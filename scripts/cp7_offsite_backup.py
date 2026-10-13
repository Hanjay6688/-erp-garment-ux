"""CP7C off-site nightly backup (owner decisions 13 Oct 2026, D13-5, D13-6 and D13-7; zero budget).

One night, in this order:
  1. The source database is read in one exported snapshot: pg_dump (custom format, --snapshot) and, in the same
     transaction, the row count and md5 of every table, the state of every sequence and a structure fingerprint
     (schemas, relations, columns, constraints, indexes, triggers, rules, policies, functions, views, types,
     sequences, extensions, publications, event triggers, owners, ACLs and default ACLs). pg_cron's schema and
     extension are left out: pg_cron lives only in the database named postgres and its jobs are installed by
     scripts/cp7_schedule.py, not restored.
  2. The dump is encrypted (gpg, symmetric AES256, passphrase from a file the scheduler writes from a secret). The
     plain dump is removed at once.
  3. The encrypted file is copied to the remote with rclone (D13-5: a private store outside the database; the tool
     takes any rclone remote, e.g. Cloudflare R2/S3 or Google Drive). A name that already exists on the remote is
     refused before anything is written.
  4. The file is fetched back from the remote into an empty directory; its SHA-256 must equal the uploaded one, and
     after decryption the dump's SHA-256 must equal the one made in step 1 (D13-6: the stored file is the one that
     is restored).
  5. That fetched copy is restored into a database of its own on a separate scratch server: the runner's own
     PostgreSQL of the same major version and extensions (D13-6), never the source server and never a non-local
     server. The database is created with an OID chosen here and marked, and dropped only by that OID
     (scripts/cp7_nightly_backup.py, Astra ASR-OPS-01). Roles that own objects or hold privileges in the source and
     are missing on the scratch server are created there first (NOLOGIN), so owners and ACLs restore as they are;
     roles this night created are dropped again at the end.
  6. Data (rows per table, sequences) and the structure fingerprint of the restored database are compared with
     step 1. Only an identical result is restore_verified.
  7. Two receipts go to the remote: `<night>.receipt.json` (plain: file names, sizes, SHA-256, times, versions,
     counts and codes; no table names, no values) and `<night>.detail.json.gpg` (encrypted: per-object differences,
     pg_dump/pg_restore messages, created role names).
  8. Remote retention (D13-5): the newest `keep` verified nights stay (14). Older nights are removed only after
     tonight verified; the newest verified night is never removed; a failed night removes nothing.

Nothing of the database's content reaches the console, a log or an artifact: the tool prints one JSON line of codes
and counts, pg_dump/pg_restore output goes into the encrypted detail only, and the local work directory is removed at
the end. The restore check proves the dump on a PostgreSQL of the same version; it does not prove that a hosted
Supabase project's own configuration (Auth settings, Storage files, network, keys) comes back. That proof is the
separate restore into a Supabase project the owner asked for before production.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import sql

import cp7_nightly_backup as v1

CONTRACT = 'cp7.offsite-backup-receipt.v1'
KEEP = 14
NIGHT = re.compile(r'^(erp-\d{8}-\d{6}-WIB-[0-9a-f]{12})\.(dump\.gpg|receipt\.json|detail\.json\.gpg)$')
SKIP = "n.nspname not in ('pg_catalog','information_schema','cron') and n.nspname not like 'pg\\_toast%' and n.nspname not like 'pg\\_temp%'"
LOCAL_HOSTS = ('127.0.0.1', 'localhost', '::1', '')

# Structure fingerprint: one sorted list of lines per category. Names are schema-qualified (search_path is
# pg_catalog only while these run), owners and ACLs are role names, so two servers compare by meaning, not by OID.
STRUCTURE = {
    'schemas': f"""select n.nspname||' owner='||pg_get_userbyid(n.nspowner)||' acl='||case when exists(select 1 from pg_init_privs i where i.classoid='pg_namespace'::regclass and i.objoid=n.oid and i.objsubid=0 and i.privtype='e') then 'EXTENSION_INITIAL' else coalesce((select string_agg(x::text,',' order by x::text) from unnest(coalesce(n.nspacl,acldefault('n'::"char",n.nspowner))) x),'-') end
        from pg_namespace n where {SKIP}""",
    'relations': f"""select c.relkind::text||' '||n.nspname||'.'||c.relname||' owner='||pg_get_userbyid(c.relowner)||' acl='||case when exists(select 1 from pg_init_privs i where i.classoid='pg_class'::regclass and i.objoid=c.oid and i.objsubid=0 and i.privtype='e') then 'EXTENSION_INITIAL' else coalesce((select string_agg(x::text,',' order by x::text) from unnest(coalesce(c.relacl,acldefault(case when c.relkind='S' then 's'::"char" else 'r'::"char" end,c.relowner))) x),'-') end
        ||' rls='||c.relrowsecurity||'/'||c.relforcerowsecurity||' persistence='||c.relpersistence::text||' options='||coalesce(c.reloptions::text,'-')
        ||' replident='||c.relreplident::text||coalesce(' partition='||pg_get_expr(c.relpartbound,c.oid),'')
        from pg_class c join pg_namespace n on n.oid=c.relnamespace where {SKIP} and c.relkind in ('r','p','v','m','S','f','c')""",
    'columns': f"""select n.nspname||'.'||c.relname||' #'||row_number() over (partition by c.oid order by a.attnum)||' '||a.attname
        ||' '||format_type(a.atttypid,a.atttypmod)||' notnull='||a.attnotnull||' identity='||a.attidentity::text||' generated='||a.attgenerated::text
        ||' default='||coalesce(pg_get_expr(d.adbin,d.adrelid),'-')||' collation='||coalesce(co.collname,'-')||' acl='||coalesce((select string_agg(x::text,',' order by x::text) from unnest(a.attacl) x),'-')
        from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
        left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
        left join pg_collation co on co.oid=a.attcollation and a.attcollation<>(select t.typcollation from pg_type t where t.oid=a.atttypid)
        where {SKIP} and c.relkind in ('r','p','v','m','f','c') and a.attnum>0 and not a.attisdropped""",
    'constraints': f"""select coalesce(n.nspname||'.'||c.relname,'type '||tn.nspname||'.'||t.typname)||' '||k.conname||' '||k.contype::text||' '||pg_get_constraintdef(k.oid)
        ||' deferrable='||k.condeferrable||'/'||k.condeferred||' valid='||k.convalidated
        from pg_constraint k left join pg_class c on c.oid=k.conrelid left join pg_namespace n on n.oid=c.relnamespace
        left join pg_type t on t.oid=k.contypid left join pg_namespace tn on tn.oid=t.typnamespace
        where coalesce(n.nspname,tn.nspname) is not null and not (coalesce(n.nspname,tn.nspname) in ('pg_catalog','information_schema','cron')
          or coalesce(n.nspname,tn.nspname) like 'pg\\_toast%' or coalesce(n.nspname,tn.nspname) like 'pg\\_temp%')""",
    'indexes': f"""select pg_get_indexdef(i.indexrelid)||' valid='||i.indisvalid||' clustered='||i.indisclustered||' replident='||i.indisreplident
        from pg_index i join pg_class c on c.oid=i.indexrelid join pg_namespace n on n.oid=c.relnamespace where {SKIP}""",
    'triggers': f"""select n.nspname||'.'||c.relname||' '||pg_get_triggerdef(t.oid)||' enabled='||t.tgenabled::text
        from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where {SKIP} and not t.tgisinternal""",
    'rules': f"""select n.nspname||'.'||c.relname||' '||r.rulename||' enabled='||r.ev_enabled::text||' body=', pg_get_ruledef(r.oid)
        from pg_rewrite r join pg_class c on c.oid=r.ev_class join pg_namespace n on n.oid=c.relnamespace where {SKIP} and r.rulename<>'_RETURN'""",
    'views': f"""select n.nspname||'.'||c.relname||' body=', pg_get_viewdef(c.oid)
        from pg_class c join pg_namespace n on n.oid=c.relnamespace where {SKIP} and c.relkind in ('v','m')""",
    'policies': f"""select n.nspname||'.'||c.relname||' '||p.polname||' cmd='||p.polcmd::text||' permissive='||p.polpermissive
        ||' roles='||coalesce((select string_agg(case when r=0 then 'public' else pg_get_userbyid(r) end,',' order by case when r=0 then 'public' else pg_get_userbyid(r) end) from unnest(p.polroles) r),'-')
        ||' using='||coalesce(pg_get_expr(p.polqual,p.polrelid),'-')||' check='||coalesce(pg_get_expr(p.polwithcheck,p.polrelid),'-')
        from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where {SKIP}""",
    'functions': f"""select p.oid::regprocedure::text||' kind='||p.prokind::text||' owner='||pg_get_userbyid(p.proowner)||' acl='||case when exists(select 1 from pg_init_privs i where i.classoid='pg_proc'::regclass and i.objoid=p.oid and i.objsubid=0 and i.privtype='e') then 'EXTENSION_INITIAL' else coalesce((select string_agg(x::text,',' order by x::text) from unnest(coalesce(p.proacl,acldefault('f'::"char",p.proowner))) x),'-') end
        ||' definer='||p.prosecdef||' volatile='||p.provolatile::text||' strict='||p.proisstrict||' leakproof='||p.proleakproof
        ||' config='||coalesce(p.proconfig::text,'-')||' returns='||pg_get_function_result(p.oid)
        ||' body=', case when p.prokind='a' then coalesce(p.prosrc,'') else pg_get_functiondef(p.oid) end
        from pg_proc p join pg_namespace n on n.oid=p.pronamespace where {SKIP}""",
    'types': f"""select t.typtype::text||' '||n.nspname||'.'||t.typname||' owner='||pg_get_userbyid(t.typowner)||' acl='||case when exists(select 1 from pg_init_privs i where i.classoid='pg_type'::regclass and i.objoid=t.oid and i.objsubid=0 and i.privtype='e') then 'EXTENSION_INITIAL' else coalesce((select string_agg(x::text,',' order by x::text) from unnest(coalesce(t.typacl,acldefault('T'::"char",t.typowner))) x),'-') end
        ||' base='||coalesce(format_type(nullif(t.typbasetype,0),t.typtypmod),'-')||' notnull='||t.typnotnull
        ||' default='||coalesce(t.typdefault,'-')
        ||' labels='||coalesce((select string_agg(e.enumlabel,',' order by e.enumsortorder) from pg_enum e where e.enumtypid=t.oid),'-')
        from pg_type t join pg_namespace n on n.oid=t.typnamespace where {SKIP} and t.typtype in ('e','d','r','m')""",
    'sequences': f"""select n.nspname||'.'||c.relname||' '||format_type(s.seqtypid,null)||' start='||s.seqstart||' inc='||s.seqincrement
        ||' min='||s.seqmin||' max='||s.seqmax||' cache='||s.seqcache||' cycle='||s.seqcycle
        ||' owned_by='||coalesce((select oc.relname||'.'||oa.attname from pg_depend d join pg_class oc on oc.oid=d.refobjid
             join pg_attribute oa on oa.attrelid=d.refobjid and oa.attnum=d.refobjsubid
             where d.classid='pg_class'::regclass and d.objid=c.oid and d.deptype in ('a','i') limit 1),'-')
        from pg_sequence s join pg_class c on c.oid=s.seqrelid join pg_namespace n on n.oid=c.relnamespace where {SKIP}""",
    'extensions': """select e.extname||' '||e.extversion||' schema='||n.nspname||' owner='||pg_get_userbyid(e.extowner)
        from pg_extension e join pg_namespace n on n.oid=e.extnamespace where e.extname<>'pg_cron'""",
    'default_acls': """select coalesce(n.nspname,'*')||' '||pg_get_userbyid(d.defaclrole)||' '||d.defaclobjtype::text||' '||coalesce((select string_agg(x::text,',' order by x::text) from unnest(d.defaclacl) x),'-')
        from pg_default_acl d left join pg_namespace n on n.oid=d.defaclnamespace
        where n.nspname is null or n.nspname not in ('pg_catalog','information_schema','cron')""",
    'publications': """select p.pubname||' owner='||pg_get_userbyid(p.pubowner)||' all='||p.puballtables||' ops='||p.pubinsert||p.pubupdate||p.pubdelete||p.pubtruncate
        ||' tables='||coalesce((select string_agg(t.schemaname||'.'||t.tablename,',' order by t.schemaname,t.tablename) from pg_publication_tables t where t.pubname=p.pubname),'-')
        from pg_publication p""",
    'event_triggers': """select e.evtname||' '||e.evtevent||' owner='||pg_get_userbyid(e.evtowner)||' fn='||e.evtfoid::regprocedure::text
        ||' enabled='||e.evtenabled::text||' tags='||coalesce(e.evttags::text,'-') from pg_event_trigger e""",
    # Objects whose privileges an extension recorded as initial (pg_init_privs): pg_dump writes only the change from
    # those, and on the restore server the extension's own script sets them again, without what the source server ran
    # around it (on Supabase, event triggers that grant access when an extension is created). Compared, and reported
    # apart as explained (structure.explained), never folded into the strict categories.
    'extension_initial_acls': f"""select 'n '||n.nspname||' '||coalesce((select string_agg(x::text,',' order by x::text) from unnest(coalesce(n.nspacl,acldefault('n'::"char",n.nspowner))) x),'-') from pg_namespace n where {SKIP} and exists(select 1 from pg_init_privs i where i.classoid='pg_namespace'::regclass and i.objoid=n.oid and i.objsubid=0 and i.privtype='e')
        union all select c.relkind::text||' '||n.nspname||'.'||c.relname||' '||coalesce((select string_agg(x::text,',' order by x::text) from unnest(coalesce(c.relacl,acldefault(case when c.relkind='S' then 's'::"char" else 'r'::"char" end,c.relowner))) x),'-')
          from pg_class c join pg_namespace n on n.oid=c.relnamespace where {SKIP} and exists(select 1 from pg_init_privs i where i.classoid='pg_class'::regclass and i.objoid=c.oid and i.objsubid=0 and i.privtype='e')
        union all select 'f '||p.oid::regprocedure::text||' '||coalesce((select string_agg(x::text,',' order by x::text) from unnest(coalesce(p.proacl,acldefault('f'::"char",p.proowner))) x),'-')
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace where {SKIP} and exists(select 1 from pg_init_privs i where i.classoid='pg_proc'::regclass and i.objoid=p.oid and i.objsubid=0 and i.privtype='e')
        union all select 'T '||n.nspname||'.'||t.typname||' '||coalesce((select string_agg(x::text,',' order by x::text) from unnest(coalesce(t.typacl,acldefault('T'::"char",t.typowner))) x),'-')
          from pg_type t join pg_namespace n on n.oid=t.typnamespace where {SKIP} and exists(select 1 from pg_init_privs i where i.classoid='pg_type'::regclass and i.objoid=t.oid and i.objsubid=0 and i.privtype='e')""",
    'large_objects': """select 'count='||count(*)||' owners='||coalesce(string_agg(distinct pg_get_userbyid(lomowner),','),'-') from pg_largeobject_metadata""",
}

# The same fingerprint without any normalization (ACLs as stored, no default, no extension marking, no canonical
# form): compared too, and every difference is recorded (structure.raw_differ, detail structure_raw_differ), so what
# the normalization set aside stays visible (owner, 13 Oct 2026: "perbedaan aslinya tetap tercatat").
_NORMALIZED_ACL = re.compile(r"case when exists\(select 1 from pg_init_privs i where i\.classoid='[a-z_]+'::regclass and i\.objoid=[a-z]\.oid and i\.objsubid=0 "
                             r"and i\.privtype='e'\) then 'EXTENSION_INITIAL' else coalesce\(\(select string_agg\(x::text,',' order by x::text\) "
                             r"from unnest\(coalesce\(([a-z]\.[a-z]+),acldefault\(.*?\)\)\) x\),'-'\) end")
_SORTED_ACL = re.compile(r"coalesce\(\(select string_agg\(x::text,',' order by x::text\) from unnest\(([a-z]\.[a-z]+)\) x\),'-'\)")
RAW_STRUCTURE = {k: _SORTED_ACL.sub(r"coalesce(\1::text,'-')", _NORMALIZED_ACL.sub(r"coalesce(\1::text,'-')", q))
                 for k, q in STRUCTURE.items() if k != 'extension_initial_acls'}
assert all('acldefault' not in q and 'EXTENSION_INITIAL' not in q and 'order by x::text' not in q for q in RAW_STRUCTURE.values()), 'RAW_STRUCTURE'

# Every role that owns an object or appears in an ACL or policy of the source (pg_* built-in roles aside).
ROLES = f"""with acl as (
    select n.nspacl a, n.nspowner o from pg_namespace n where {SKIP}
    union all select c.relacl, c.relowner from pg_class c join pg_namespace n on n.oid=c.relnamespace where {SKIP}
    union all select p.proacl, p.proowner from pg_proc p join pg_namespace n on n.oid=p.pronamespace where {SKIP}
    union all select t.typacl, t.typowner from pg_type t join pg_namespace n on n.oid=t.typnamespace where {SKIP}
    union all select a.attacl, null from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace
      where {SKIP} and a.attacl is not null
    union all select d.defaclacl, d.defaclrole from pg_default_acl d
    union all select null, e.extowner from pg_extension e
    union all select null, p.pubowner from pg_publication p
    union all select null, e.evtowner from pg_event_trigger e
    union all select null, l.lomowner from pg_largeobject_metadata l),
  ids as (
    select o r from acl where o is not null
    union select (aclexplode(a)).grantee from acl where a is not null
    union select (aclexplode(a)).grantor from acl where a is not null
    union select unnest(p.polroles) from pg_policy p join pg_class c on c.oid=p.polrelid join pg_namespace n on n.oid=c.relnamespace where {SKIP})
  select distinct r.rolname from ids join pg_roles r on r.oid=ids.r where r.rolname !~ '^pg_' order by 1"""

SEQUENCES = f"""select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where c.relkind='S' and {SKIP} order by 1,2"""


# One known form PostgreSQL itself changes when a definition goes through pg_dump and back: an array of typed
# literals cast as a whole, e.g. (ARRAY['A'::character varying, 'B'::character varying])::text[] (what
# CHECK (status IN ('A','B')) on a varchar column is stored as), is read back as
# ARRAY[('A'::character varying)::text, ('B'::character varying)::text]. Both sides are brought to the second form
# before comparing; nothing else is rewritten, so any other difference still counts.
_LITERAL = re.compile(r"'(?:[^']|'')*'::[a-z][a-z0-9_ ]*(?:\([0-9, ]+\))?")
_ARRAY_CAST = re.compile(r"\(ARRAY\[((?:%s)(?:, (?:%s))*)\]\)::([a-z][a-z0-9_ ]*(?:\([0-9, ]+\))?)\[\]" % (_LITERAL.pattern, _LITERAL.pattern))


def canonical(text):
    def element_casts(m):
        return 'ARRAY[%s]' % ', '.join('(%s)::%s' % (e, m.group(2)) for e in _LITERAL.findall(m.group(1)))
    return _ARRAY_CAST.sub(element_casts, text)


def structure(cur, raw=False):
    """The structure fingerprint as {category: sorted lines}, read with the cursor's snapshot. A row of two columns
    is a line and a definition body; the body enters the line as the md5 of its canonical form (raw: as stored)."""
    cur.execute("select set_config('search_path','pg_catalog',true)")
    form = (lambda t: t) if raw else canonical
    out = {}
    for k, q in (RAW_STRUCTURE if raw else STRUCTURE).items():
        lines = []
        for row in cur.execute(q).fetchall():
            if row[0] is None:
                continue
            line = form(row[0])
            if len(row) > 1:
                line += hashlib.md5(form(row[1] or '').encode()).hexdigest()
            lines.append(line)
        out[k] = sorted(lines)
    return out


def sequence_state(cur):
    out = {}
    for schema, name in cur.execute(SEQUENCES).fetchall():
        last, called = cur.execute(sql.SQL('select last_value,is_called from {}.{}').format(sql.Identifier(schema), sql.Identifier(name))).fetchone()
        out[schema + '.' + name] = [int(last), bool(called)]
    return out


EXPLAINED = ('extension_initial_acls',)


_ACL = re.compile(r' acl=\S+')


def compare_structure(a, b):
    """(strict differences, explained differences) per category. An object whose privileges the source recorded as
    an extension's initial privileges is compared without its ACL in the strict categories, whatever the restored side
    recorded (on Supabase such an object can be created around CREATE EXTENSION and, restored by pg_dump, come back as
    a plain object); its ACL itself is compared in the explained category extension_initial_acls."""
    out, explained = {}, {}
    marked = {_ACL.sub(' acl=*', line) for lines in a.values() for line in lines if ' acl=EXTENSION_INITIAL' in line}
    b = {k: [_ACL.sub(' acl=EXTENSION_INITIAL', line) if _ACL.sub(' acl=*', line) in marked else line for line in lines]
         for k, lines in b.items()}
    for k in sorted(set(a) | set(b)):
        x, y = set(a.get(k, [])), set(b.get(k, []))
        if x != y:
            (explained if k in EXPLAINED else out)[k] = dict(only_source=sorted(x - y)[:200], only_restored=sorted(y - x)[:200], count=len(x ^ y))
    return out, explained


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def is_local(url):
    u = urlparse(url)
    return (u.hostname or '') in LOCAL_HOSTS


def server_identity(url):
    """(major version, system identifier or None) of the server at url."""
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        major = int(cur.execute("select current_setting('server_version_num')::int/10000").fetchone()[0])
        try:
            ident = cur.execute('select system_identifier::text from pg_control_system()').fetchone()[0]
        except psycopg.Error:
            conn.rollback()
            ident = None
        return major, ident


class Remote:
    """rclone on one remote path, e.g. 'erpbackup:erp-garment-backup/nightly'. Output of rclone is kept out of the
    console; failures surface as codes."""

    def __init__(self, path, config=None, rclone='rclone'):
        self.path, self.base = path.rstrip('/'), [rclone] + (['--config', config] if config else [])

    def _run(self, *args, check=True):
        r = subprocess.run(self.base + list(args), capture_output=True, text=True)
        if check and r.returncode != 0:
            raise RemoteError(args[0], r.returncode, r.stderr[-500:])
        return r

    def names(self):
        r = self._run('lsjson', '--files-only', '--no-modtime', '--no-mimetype', self.path, check=False)
        if r.returncode != 0:
            # A path that does not exist yet is an empty remote; any other failure is not.
            if 'directory not found' in r.stderr.lower() or 'not found' in r.stderr.lower():
                return []
            raise RemoteError('lsjson', r.returncode, r.stderr[-500:])
        return sorted(x['Name'] for x in json.loads(r.stdout or '[]'))

    def put(self, local, name):
        self._run('copyto', '--immutable', str(local), self.path + '/' + name)

    def get(self, name, local):
        self._run('copyto', self.path + '/' + name, str(local))

    def cat(self, name):
        return self._run('cat', self.path + '/' + name).stdout

    def delete(self, name):
        self._run('deletefile', self.path + '/' + name)

    def about(self):
        """Free and total bytes of the remote's storage when the backend reports them (Google Drive does), else None."""
        r = self._run('about', '--json', self.path.split(':', 1)[0] + ':' if ':' in self.path else self.path, check=False)
        try:
            a = json.loads(r.stdout) if r.returncode == 0 else None
        except ValueError:
            a = None
        return None if not a else dict(free=a.get('free'), total=a.get('total'), used=a.get('used'))


class RemoteError(Exception):
    def __init__(self, op, code, stderr):
        super().__init__('BACKUP_REMOTE_FAILED', op, code)
        self.op, self.code, self.stderr = op, code, stderr


def gpg(args, passphrase_file, home):
    return subprocess.run(['gpg', '--homedir', str(home), '--batch', '--yes', '--quiet', '--pinentry-mode', 'loopback',
                           '--passphrase-file', str(passphrase_file), *args], capture_output=True, text=True)


def encrypt(src, dst, passphrase_file, home):
    r = gpg(['--symmetric', '--cipher-algo', 'AES256', '--s2k-digest-algo', 'SHA512', '--compress-algo', 'none', '-o', str(dst), str(src)],
            passphrase_file, home)
    assert r.returncode == 0 and Path(dst).stat().st_size > 0, ('BACKUP_ENCRYPT_FAILED', r.returncode)


def decrypt(src, dst, passphrase_file, home):
    r = gpg(['--decrypt', '-o', str(dst), str(src)], passphrase_file, home)
    assert r.returncode == 0, ('BACKUP_DECRYPT_FAILED', r.returncode)


def restore_category(line):
    if v1.CRON_ERROR.match(line):
        return 'CRON'
    low = line.lower()
    if 'permission denied' in low or 'must be owner' in low or 'must be superuser' in low:
        return 'PERMISSION'
    if 'extension' in low:
        return 'EXTENSION'
    if 'does not exist' in low and 'role' in low:
        return 'ROLE'
    return 'OTHER'


def ensure_roles(admin_url, names):
    """Create on the scratch server, NOLOGIN, every named role that does not exist there yet; return those created."""
    made = []
    with psycopg.connect(v1.db_url(admin_url, 'postgres'), autocommit=True) as conn:
        have = {r[0] for r in conn.execute('select rolname from pg_roles').fetchall()}
        for name in names:
            if name not in have:
                conn.execute(sql.SQL('create role {} nologin').format(sql.Identifier(name)))
                made.append(name)
    return made


def drop_roles(admin_url, names):
    """Drop the roles this night created; a role that still owns or holds something anywhere is kept and reported."""
    kept = []
    with psycopg.connect(v1.db_url(admin_url, 'postgres'), autocommit=True) as conn:
        for name in reversed(names):
            try:
                conn.execute(sql.SQL('drop role if exists {}').format(sql.Identifier(name)))
            except psycopg.Error:
                kept.append(name)
    return kept


def receipts(remote):
    out = []
    for name in remote.names():
        m = NIGHT.match(name)
        if m and m.group(2) == 'receipt.json':
            try:
                r = json.loads(remote.cat(name))
            except (ValueError, RemoteError):
                continue
            if r.get('contract') == CONTRACT and r.get('night') == m.group(1):
                out.append(r)
    return out


def prune(remote, keep, tonight_verified):
    """Keep the newest `keep` verified nights; remove older nights (dump, receipt, detail, also a night that never
    got its receipt) only after tonight's night verified. The night name begins with its WIB time, so names order
    nights."""
    if not tonight_verified:
        return dict(removed=[], reason='TONIGHT_NOT_VERIFIED_NOTHING_REMOVED')
    verified = sorted((r['night'] for r in receipts(remote) if r.get('restore_verified') is True), reverse=True)
    kept = verified[:max(keep, 1)]
    if not kept:
        return dict(removed=[], reason='NO_VERIFIED_NIGHT_NOTHING_REMOVED')
    oldest = kept[-1]
    removed = []
    for name in remote.names():
        m = NIGHT.match(name)
        if m and m.group(1) < oldest and m.group(1) not in kept:
            remote.delete(name)
            removed.append(name)
    return dict(kept=kept, removed=removed, reason='NEWEST_VERIFIED_KEPT')


def read_source(source_url, dump_file, pg_dump='pg_dump', dump_args=()):
    """pg_dump in an exported snapshot, and the data and structure of the source in that same snapshot."""
    with psycopg.connect(source_url) as snap:
        snap.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        snap.read_only = True
        with snap.cursor() as cur:
            snapshot = cur.execute('select pg_export_snapshot()').fetchone()[0]
            t0 = time.monotonic()
            d = subprocess.run([pg_dump, '--dbname=' + source_url, '--snapshot=' + snapshot, '-Fc', *dump_args, '-f', str(dump_file)],
                               capture_output=True, text=True)
            seconds = round(time.monotonic() - t0, 1)
            assert d.returncode == 0 and dump_file.exists() and dump_file.stat().st_size > 0, ('BACKUP_DUMP_FAILED', d.returncode, d.stderr[-2000:])
            data, seqs = v1.table_hashes(cur), sequence_state(cur)
            shape, shape_raw, roles = structure(cur), structure(cur, raw=True), [r[0] for r in cur.execute(ROLES).fetchall()]
            version = cur.execute("select current_setting('server_version')").fetchone()[0]
        snap.rollback()
    return dict(snapshot=snapshot, seconds=seconds, stderr=d.stderr[-4000:], data=data, sequences=seqs, structure=shape,
                structure_raw=shape_raw, roles=roles, version=version)


def read_restored(url, expected_oid):
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        conn.read_only = True
        got = cur.execute('select oid from pg_database where datname=current_database()').fetchone()[0]
        assert got == expected_oid, ('BACKUP_SCRATCH_REPLACED', 'restored database is not the attempt database')
        return dict(data=v1.table_hashes(cur), sequences=sequence_state(cur), structure=structure(cur), structure_raw=structure(cur, raw=True))


def backup(source_url, scratch_admin_url, remote, passphrase_file, scratch='cp7_offsite_verify', keep=KEEP, work=None,
           now=None, pg_dump='pg_dump', pg_restore='pg_restore', hooks=None, dump_args=(), with_detail=False):
    """One night. Returns the plain receipt (also uploaded). `dump_args` are extra pg_dump arguments fixed at
    installation (recorded in the receipt). `hooks` (after_upload(name), after_restore(attempt_url)) and
    `with_detail` (the unencrypted detail returned under `_detail`, never uploaded or printed) are for the test
    cases; the scheduler passes neither."""
    hooks = hooks or {}
    assert is_local(scratch_admin_url), 'BACKUP_SCRATCH_SERVER_NOT_LOCAL'
    src_major, src_ident = server_identity(source_url)
    scr_major, scr_ident = server_identity(scratch_admin_url)
    su, cu = urlparse(source_url), urlparse(scratch_admin_url)
    same_server = (src_ident is not None and src_ident == scr_ident) or (
        src_ident is None and (su.hostname, su.port or 5432) == (cu.hostname, cu.port or 5432))
    assert not same_server, 'BACKUP_SCRATCH_SERVER_IS_SOURCE'
    started = now or datetime.now(timezone.utc)
    night = 'erp-%s-%s' % (started.astimezone(v1.WIB).strftime('%Y%m%d-%H%M%S-WIB'), secrets.token_hex(6))
    enc_name, receipt_name, detail_name = night + '.dump.gpg', night + '.receipt.json', night + '.detail.json.gpg'
    token = secrets.token_hex(8)
    attempt_db = '%s_%s' % (v1.attempt_prefix(scratch), token)
    receipt = dict(contract=CONTRACT, label='CP7C_OFFSITE_BACKUP', night=night, file=enc_name, detail=detail_name,
                   source_database=urlparse(source_url).path.lstrip('/'), started_at_utc=started.isoformat(),
                   started_at_wib=started.astimezone(v1.WIB).isoformat(), versions=dict(source_major=src_major, scratch_major=scr_major),
                   scratch_attempt=dict(token=token, oid=None), restore_verified=False, production_go=False, codes=[])
    detail = dict(night=night)
    tmp = Path(tempfile.mkdtemp(prefix='cp7-offsite-', dir=work))
    home = tmp / 'gnupg'
    home.mkdir(mode=0o700)
    attempt_oid, created_roles, uploaded = None, [], False
    try:
        assert scr_major == src_major, ('BACKUP_SCRATCH_VERSION_MISMATCH', src_major, scr_major)
        taken = [n for n in remote.names() if n.startswith(night)]
        assert not taken, ('BACKUP_NAME_COLLISION', night)
        state = v1.scratch_state(scratch_admin_url, scratch)
        assert state != 'FOREIGN', ('BACKUP_SCRATCH_EXISTS_NOT_OURS', scratch)
        old = v1.leftovers(scratch_admin_url, scratch)
        dump = tmp / (night + '.dump')
        receipt['dump_args'] = list(dump_args)
        src = read_source(source_url, dump, pg_dump, dump_args)
        dump_sha = sha256_file(dump)
        receipt['dump'] = dict(seconds=src['seconds'], bytes=dump.stat().st_size, sha256=dump_sha, snapshot_read=True)
        receipt['versions']['source'] = src['version']
        detail['pg_dump_stderr'] = src['stderr']
        enc = tmp / enc_name
        encrypt(dump, enc, passphrase_file, home)
        dump.unlink()
        enc_sha = sha256_file(enc)
        receipt['encrypted'] = dict(bytes=enc.stat().st_size, sha256=enc_sha, cipher='gpg symmetric AES256')
        # D13-8: 14 verified nights are kept while the store's quota allows; a low quota is a warning, never a reason
        # to remove a good night (a failed upload removes nothing either).
        space = remote.about()
        receipt['remote_space'] = space
        if space and space.get('free') is not None and space['free'] < 3 * receipt['encrypted']['bytes']:
            receipt.setdefault('warnings', []).append('BACKUP_REMOTE_SPACE_LOW')
        remote.put(enc, enc_name)
        uploaded = True
        enc.unlink()
        if 'after_upload' in hooks:
            hooks['after_upload'](enc_name)
        fetched_dir = tmp / 'fetched'
        fetched_dir.mkdir()
        fetched = fetched_dir / enc_name
        remote.get(enc_name, fetched)
        fetched_sha = sha256_file(fetched)
        receipt['fetched_back'] = dict(sha256_equal=fetched_sha == enc_sha)
        assert fetched_sha == enc_sha, ('BACKUP_REMOTE_COPY_DIFFERS', 'encrypted file fetched back is not the uploaded one')
        plain = fetched_dir / (night + '.dump')
        decrypt(fetched, plain, passphrase_file, home)
        fetched.unlink()
        receipt['fetched_back']['dump_sha256_equal'] = sha256_file(plain) == dump_sha
        assert receipt['fetched_back']['dump_sha256_equal'], ('BACKUP_REMOTE_COPY_DIFFERS', 'decrypted dump is not the dumped one')
        # Scratch server: leftovers of earlier nights read before the dump are dropped now by their OID.
        receipt['leftovers'] = [dict(row, **v1.drop_owned(scratch_admin_url, row['oid'])) for row in old]
        assert all(r['result'] in ('DROPPED', 'ABSENT') for r in receipt['leftovers']), ('BACKUP_SCRATCH_REPLACED', 'leftover')
        assert v1.scratch_state(scratch_admin_url, scratch) is None, ('BACKUP_SCRATCH_NOT_CREATED', scratch)
        created_roles = ensure_roles(scratch_admin_url, src['roles'])
        receipt['roles'] = dict(referenced=len(src['roles']), created=len(created_roles))
        detail['roles_created'] = created_roles
        attempt_oid = v1.create_attempt(scratch_admin_url, attempt_db)
        receipt['scratch_attempt']['oid'] = attempt_oid
        v1.mark_scratch(scratch_admin_url, attempt_db, token, attempt_oid)
        made = v1.identity(scratch_admin_url, attempt_db)
        assert made and made[0] == attempt_oid and v1.is_mark(made[1], attempt_oid, token), ('BACKUP_SCRATCH_REPLACED', 'attempt')
        t1 = time.monotonic()
        attempt_url = v1.db_url(scratch_admin_url, attempt_db)
        r = subprocess.run([pg_restore, '--dbname=' + attempt_url, '--no-password', str(plain)], capture_output=True, text=True)
        plain.unlink()
        after = v1.identity(scratch_admin_url, attempt_db)
        assert after and after[0] == attempt_oid, ('BACKUP_SCRATCH_REPLACED', 'after restore')
        if 'after_restore' in hooks:
            hooks['after_restore'](attempt_url)
        errors = [line for line in r.stderr.splitlines() if line.startswith('pg_restore: error:')]
        cats = {}
        for line in errors:
            cats[restore_category(line)] = cats.get(restore_category(line), 0) + 1
        unexplained = sum(n for c, n in cats.items() if c != 'CRON')
        receipt['restore'] = dict(exit=r.returncode, seconds=round(time.monotonic() - t1, 1), errors=len(errors), by_category=cats, unexplained=unexplained)
        detail['pg_restore_errors'] = errors[:200]
        got = read_restored(attempt_url, attempt_oid)
        data_differ = {t: dict(source=src['data'].get(t), restored=got['data'].get(t)) for t in sorted(set(src['data']) | set(got['data']))
                       if src['data'].get(t) != got['data'].get(t)}
        seq_differ = {s: dict(source=src['sequences'].get(s), restored=got['sequences'].get(s))
                      for s in sorted(set(src['sequences']) | set(got['sequences'])) if src['sequences'].get(s) != got['sequences'].get(s)}
        shape_differ, shape_explained = compare_structure(src['structure'], got['structure'])
        raw_differ = {k: dict(only_source=sorted(set(src['structure_raw'][k]) - set(got['structure_raw'].get(k, [])))[:200],
                              only_restored=sorted(set(got['structure_raw'].get(k, [])) - set(src['structure_raw'][k]))[:200],
                              count=len(set(src['structure_raw'][k]) ^ set(got['structure_raw'].get(k, []))))
                      for k in src['structure_raw'] if set(src['structure_raw'][k]) != set(got['structure_raw'].get(k, []))}
        receipt['data'] = dict(tables=len(src['data']), rows=sum(v['rows'] for v in src['data'].values()), sequences=len(src['sequences']),
                               tables_differ=len(data_differ), sequences_differ=len(seq_differ), compared_with='source in the dump snapshot')
        receipt['structure'] = dict(objects={k: len(v) for k, v in src['structure'].items()},
                                    differ={k: v['count'] for k, v in shape_differ.items()},
                                    explained={k: v['count'] for k, v in shape_explained.items()},
                                    raw_differ={k: v['count'] for k, v in raw_differ.items()},
                                    normalization=['ARRAY_CAST_FORM', 'ACL_DEFAULT_AND_ORDER', 'EXTENSION_INITIAL_ACLS_EXPLAINED'])
        detail.update(data_differ=data_differ, sequences_differ=seq_differ, structure_differ=shape_differ, structure_explained=shape_explained,
                      structure_raw_differ=raw_differ)
        for code, bad in (('BACKUP_RESTORE_ERRORS', unexplained), ('BACKUP_DATA_DIFFERS', data_differ or seq_differ),
                          ('BACKUP_STRUCTURE_DIFFERS', shape_differ)):
            if bad:
                receipt['codes'].append(code)
        receipt['restore_verified'] = not receipt['codes'] and len(src['data']) > 0
    except RemoteError as exc:
        receipt['codes'].append('BACKUP_REMOTE_FAILED')
        receipt['error'] = dict(code='BACKUP_REMOTE_FAILED', op=exc.op, exit=exc.code)
        detail['remote_stderr'] = exc.stderr
    except AssertionError as exc:
        a = exc.args[0] if exc.args else None
        code = a[0] if isinstance(a, tuple) else str(a)
        receipt['codes'].append(code)
        receipt['error'] = dict(code=code)
        detail['error'] = [str(x)[:2000] for x in (a if isinstance(a, tuple) else (a,))]
    except Exception as exc:  # the receipt records the failure; nothing is removed
        receipt['codes'].append('BACKUP_FAILED')
        receipt['error'] = dict(code='BACKUP_FAILED', type=type(exc).__name__, sqlstate=getattr(exc, 'sqlstate', None))
        detail['error'] = [str(exc)[:2000]]
    finally:
        try:
            if attempt_oid is not None:
                receipt['scratch_attempt']['drop'] = v1.drop_owned(scratch_admin_url, attempt_oid, token, created_here=True)
                if receipt['scratch_attempt']['drop']['result'] not in ('DROPPED', 'ABSENT'):
                    receipt['restore_verified'] = False
                    receipt['codes'].append('BACKUP_SCRATCH_REPLACED')
            if created_roles:
                kept = drop_roles(scratch_admin_url, created_roles)
                receipt['roles']['kept_after_night'] = len(kept)
        except psycopg.Error as exc:
            receipt['restore_verified'] = False
            receipt['codes'].append('BACKUP_SCRATCH_CLEANUP_FAILED')
            detail['cleanup_error'] = str(exc)[:500]
        finished = datetime.now(timezone.utc)
        receipt.update(finished_at_utc=finished.isoformat(), finished_at_wib=finished.astimezone(v1.WIB).isoformat())
        try:
            # Receipts reach the remote only for a night whose dump reached it; a night refused earlier has
            # nothing there to describe and writes nothing.
            if uploaded:
                d = tmp / 'detail.json'
                d.write_text(json.dumps(detail, default=str))
                encrypt(d, tmp / detail_name, passphrase_file, home)
                d.unlink()
                remote.put(tmp / detail_name, detail_name)
                p = tmp / receipt_name
                p.write_text(json.dumps(receipt, indent=1, default=str) + '\n')
                remote.put(p, receipt_name)
                receipt['retention'] = prune(remote, keep, receipt['restore_verified'])
            else:
                receipt['retention'] = dict(removed=[], reason='NOTHING_UPLOADED_NOTHING_REMOVED')
        except (RemoteError, AssertionError) as exc:
            receipt['restore_verified'] = False
            receipt['codes'].append('BACKUP_RECEIPT_NOT_STORED')
            receipt['retention'] = dict(removed=[], reason='RECEIPT_NOT_STORED_NOTHING_REMOVED')
        shutil.rmtree(tmp, ignore_errors=True)
    if with_detail:
        receipt['_detail'] = detail
    return receipt


def summary(receipt):
    """The only line printed: codes and counts, no names or values."""
    keys = ('night', 'restore_verified', 'codes', 'warnings', 'error', 'remote_space', 'versions', 'dump', 'encrypted', 'fetched_back', 'restore', 'data', 'structure', 'roles', 'retention')
    out = {k: receipt.get(k) for k in keys}
    if out.get('dump'):
        out['dump'] = {k: out['dump'][k] for k in ('bytes', 'seconds') if k in out['dump']}
    if out.get('retention'):
        out['retention'] = dict(reason=out['retention'].get('reason'), removed=len(out['retention'].get('removed', [])),
                                kept=len(out['retention'].get('kept', [])))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--source-url', required=True, help='read access to the ERP database (environment CP7_BACKUP_SOURCE_URL recommended)')
    p.add_argument('--scratch-admin-url', required=True, help="the runner's own PostgreSQL (same major version), never the source")
    p.add_argument('--remote', required=True, help="rclone remote path, e.g. erpbackup:erp-garment-backup/nightly")
    p.add_argument('--passphrase-file', required=True)
    p.add_argument('--rclone-config')
    p.add_argument('--scratch', default='cp7_offsite_verify')
    p.add_argument('--keep', type=int, default=KEEP)
    a = p.parse_args()
    for tool in ('pg_dump', 'pg_restore', 'gpg', 'rclone'):
        if shutil.which(tool) is None:
            raise SystemExit('CP7_BACKUP_TOOLS_MISSING')
    r = backup(a.source_url, a.scratch_admin_url, Remote(a.remote, a.rclone_config), a.passphrase_file, a.scratch, a.keep)
    print(json.dumps(summary(r), default=str))
    raise SystemExit(0 if r['restore_verified'] else 1)


if __name__ == '__main__':
    main()
