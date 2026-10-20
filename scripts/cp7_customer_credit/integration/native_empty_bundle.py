"""Atomic, explicit development-only Native EMPTY extension.

The owning bundle verifies its actual Native/predecessor installation first.
No connection, authority bypass, installer commit or public API exists here.
"""
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'native-empty'
SQL_FILES = tuple('native-empty/'+n for n in (
    '01_native_empty_facts.sql','02_native_empty_callbacks.sql','04_exact_overlays.sql'))
TABLES = ('native_empty_work','native_empty_operations','native_empty_completions',
          'native_empty_source_scope','return_families','return_family_members','financial_materializations')


def digest(value):
    return sha256(value.encode()).hexdigest()


def declarations():
    pins = json.loads((DIR/'SOURCE_PINS.json').read_text())
    for name, expected in pins['files'].items():
        if sha256((DIR/name).read_bytes()).hexdigest() != expected:
            raise ValueError('OW04_NATIVE_EMPTY_SOURCE_FILE_CHANGED: '+name)
    manifest = json.loads((DIR/'OVERLAY_MANIFEST.json').read_text())
    if len(manifest['overlays']) != 14 or len({x['identity'] for x in manifest['overlays']}) != 14:
        raise ValueError('OW04_NATIVE_EMPTY_OVERLAY_SET_CHANGED')
    for name, expected in manifest['frozen_sources'].items():
        if sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('OW04_NATIVE_EMPTY_PREDECESSOR_SOURCE_CHANGED: '+name)
    if manifest['generated_sql_sha256'] != digest((DIR/'04_exact_overlays.sql').read_text()):
        raise ValueError('OW04_NATIVE_EMPTY_GENERATED_SQL_CHANGED')
    return pins, manifest


@contextmanager
def catalog_path(cur):
    before = cur.execute('show search_path').fetchone()[0]
    cur.execute("select set_config('search_path','',true)")
    try:
        yield
    finally:
        # Catalog reads do not mutate business facts. A failed SQL statement
        # must retain its original exception until the caller rolls back.
        from psycopg.pq import TransactionStatus
        if cur.connection.info.transaction_status != TransactionStatus.INERROR:
            cur.execute("select set_config('search_path',%s,true)",(before,))


def helper_metadata(cur, identity):
    with catalog_path(cur):
        row = cur.execute("select pg_get_functiondef(p.oid),encode(pg_catalog.sha256(convert_to(p.prosrc,'UTF8')),'hex'),"
            "pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig,p.proacl::text[] "
            "from pg_proc p where p.oid=%s::regprocedure",(identity,)).fetchone()
    if row is None:
        raise ValueError('OW04_NATIVE_EMPTY_REQUIRED_HELPER_MISSING: '+identity)
    return dict(zip(('definition','body_sha256','owner','security_definer','volatility','config','acl'),row))


def relations(cur):
    with catalog_path(cur):
        return cur.execute("select c.relname,pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,"
            "(select jsonb_agg(jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,"
            "pg_get_expr(d.adbin,d.adrelid))order by a.attnum)from pg_attribute a left join pg_attrdef d "
            "on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped),"
            "(select jsonb_agg(jsonb_build_array(k.conname,k.contype,k.condeferrable,k.condeferred,k.convalidated,"
            "pg_get_constraintdef(k.oid,false))order by k.conname)from pg_constraint k where k.conrelid=c.oid),"
            "(select jsonb_agg(jsonb_build_array(t.tgname,t.tgenabled,pg_get_triggerdef(t.oid,false))order by t.tgname)"
            "from pg_trigger t where t.tgrelid=c.oid and not t.tgisinternal) "
            "from pg_class c join pg_namespace n on n.oid=c.relnamespace "
            "where n.nspname='cp7_credit'and c.relname=any(%s::text[])order by c.relname",(list(TABLES),)).fetchall()


def install(cur, load_sql):
    pins, manifest = declarations()
    before = {}
    for item in manifest['overlays']:
        identity = item['identity']
        actual = helper_metadata(cur,identity)
        if actual['body_sha256'] != item['before_body_sha256'] or actual['owner'] != 'postgres' \
                or not actual['security_definer'] or actual['volatility'] != item['volatility'] \
                or actual['config'] != ['search_path=""','TimeZone=UTC']:
            raise ValueError('OW04_NATIVE_EMPTY_PREDECESSOR_HELPER_CHANGED: '+identity)
        before[identity] = actual
    for name in SQL_FILES:
        cur.execute(load_sql(name),prepare=False)
    state = dict(source_pins=pins,manifest=manifest,before_helpers=before,
                 installed_helpers={x['identity']:helper_metadata(cur,x['identity'])for x in manifest['overlays']},
                 installed_relations=relations(cur))
    verify(cur,state)
    return state


def verify(cur, state):
    pins, manifest = declarations()
    if pins != state['source_pins'] or manifest != state['manifest']:
        raise ValueError('OW04_NATIVE_EMPTY_DECLARATION_CHANGED')
    for item in manifest['overlays']:
        identity = item['identity']
        actual = helper_metadata(cur,identity)
        if actual != state['installed_helpers'][identity] or actual['body_sha256'] != item['after_body_sha256']:
            raise ValueError('OW04_NATIVE_EMPTY_INSTALLED_HELPER_CHANGED: '+identity)
        if any(actual[k] != state['before_helpers'][identity][k]for k in
               ('owner','security_definer','volatility','config','acl')):
            raise ValueError('OW04_NATIVE_EMPTY_PREDECESSOR_METADATA_CHANGED: '+identity)
    current = relations(cur)
    if len(current) != len(TABLES) or current != state['installed_relations']:
        raise ValueError('OW04_NATIVE_EMPTY_RELATION_OR_DEFERRED_CLOSURE_CHANGED')
    return dict(classification='SOURCE_AND_METADATA_VERIFICATION_NOT_NATIVE_EXECUTION',
                overlays=14,relations=len(current),production_go=False)
