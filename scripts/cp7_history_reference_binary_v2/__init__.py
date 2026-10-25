"""Private read-only history reference inputs; not a staged job or SAVE grant.

No connection/commit, default installer, old replacement, table or facade.
The immutable reference and old raw incompleteness status remain untouched.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows
from . import render
import cp7_history_reference as parent_reference

ROOT = Path(__file__).resolve().parent
SCHEMA = render.SCHEMA
FUNCTIONS = {SCHEMA+'.stock_digest(jsonb,timestamp with time zone)': 's'}


def sources():
    return {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
            if p.is_file() and p.suffix in ('.py', '.sql', '.json')}


def verify_sources():
    sql = (ROOT/'digest.sql').read_text()
    manifest = json.loads((ROOT/'MANIFEST.json').read_text())
    if (manifest['contract'], manifest['postgres_major'], manifest['server_encoding'], manifest['field_count'], manifest['encoding'], manifest['layout_sha256']) != ('cp7.history-reference-stage.v2', 17, 'UTF8', 15, render.ENCODING, render.LAYOUT_SHA256):
        raise ValueError('HISTORY_REFERENCE_BINARY_V2_DECLARATION_CHANGED')
    if sql != render.render((ROOT.parent/'cp7_history_reference/digest.sql').read_text()) or sha256(sql.encode()).hexdigest() != manifest['sql_sha256']:
        raise ValueError('HISTORY_REFERENCE_BINARY_V2_RENDERED_SOURCE_CHANGED')
    return sources()


def dependencies(cur):
    parent_reference.verify_sources()
    for signature, expected in parent_reference.render.dependencies().items():
        row = _row(cur, signature)
        if sha256(row[1].encode()).hexdigest() != expected['body_sha256'] or row[2] != expected['owner']:
            raise ValueError('HISTORY_REFERENCE_BINARY_V2_DEPENDENCY_CHANGED: '+signature)


def declared(group, key):
    return (group == 'schemas' and key == SCHEMA) or (group == 'functions' and key in FUNCTIONS)


def own_catalog(catalog):
    return {g: {k: v for k, v in rows.items() if declared(g, k)} for g, rows in catalog.items()}


def verify(cur, state):
    if verify_sources() != state['sources']:
        raise ValueError('HISTORY_REFERENCE_BINARY_V2_SOURCES_CHANGED')
    dependencies(cur)
    catalog = own_catalog(_catalog_rows(cur))
    if catalog != state['catalog'] or set(catalog['schemas']) != {SCHEMA} or set(catalog['functions']) != set(FUNCTIONS):
        raise ValueError('HISTORY_REFERENCE_BINARY_V2_CATALOG_CHANGED')
    sql = (ROOT/'digest.sql').read_text()
    for signature, volatility in FUNCTIONS.items():
        row = _row(cur, signature)
        expected = re.search(r'create function '+re.escape(signature.split('(')[0])+r'\(.*?\$\$;', sql, re.S)[0]
        if row[0] != state['definitions'][signature] or row[1] != _body(expected) or row[2:6] != ['cp7_capture', False, volatility, ['search_path=""', 'TimeZone=UTC']]:
            raise ValueError('HISTORY_REFERENCE_BINARY_V2_FUNCTION_CHANGED: '+signature)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0]:
                raise ValueError('HISTORY_REFERENCE_BINARY_V2_EXECUTE_EXPOSED: '+signature+':'+role)
    for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (role, SCHEMA)).fetchone()[0]:
            raise ValueError('HISTORY_REFERENCE_BINARY_V2_SCHEMA_EXPOSED: '+role)
    for group in ('schemas', 'functions'):
        for key, row in catalog[group].items():
            for grant in row[-1]:
                if grant[0] != 'cp7_capture' or grant[1] != 'cp7_capture' or grant[3] is not False:
                    raise ValueError('HISTORY_REFERENCE_BINARY_V2_UNDECLARED_GRANT: '+key)
    return dict(stage='cp7.history-reference-stage.v2', private_functions=1, new_tables=0, public_rpcs=0,
                old_replacements=0, Native_DML=False, staged_job_integration=False, v1_reference_unchanged=True, v2_hash_intentionally_distinct=True,
                actual_checked_SAVE2000_qualified=False, production_go=False)


def install_delta(cur):
    pins = verify_sources()
    if cur.execute('select to_regnamespace(%s)is not null', (SCHEMA,)).fetchone()[0]:
        raise ValueError('HISTORY_REFERENCE_BINARY_V2_ALREADY_INSTALLED')
    dependencies(cur)
    cur.execute((ROOT/'digest.sql').read_text(), prepare=False)
    state = dict(sources=pins, catalog=own_catalog(_catalog_rows(cur)),
                 definitions={sig: _row(cur, sig)[0] for sig in FUNCTIONS})
    verify(cur, state)
    return state


def admit_catalog(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('HISTORY_REFERENCE_BINARY_V2_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if old is None and new is not None and declared(group, key) and new == state['catalog'][group].get(key):
                continue
            raise ValueError('HISTORY_REFERENCE_BINARY_V2_UNDECLARED_DELTA: '+group+':'+key)


def rollback_preuse(cur, state):
    verify(cur, state)
    if cur.execute("select exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                   "where n.nspname<>%s and case when p.prokind in('f','p') "
                   "then position(%s in pg_get_functiondef(p.oid))>0 else false end)",
                   (SCHEMA, SCHEMA+'.')).fetchone()[0]:
        raise ValueError('HISTORY_REFERENCE_BINARY_V2_REFERENCED_REQUIRES_COMPOSED_RESTORE')
    for signature in FUNCTIONS:
        cur.execute('drop function '+signature+' restrict')
    cur.execute('drop schema '+SCHEMA+' restrict')
