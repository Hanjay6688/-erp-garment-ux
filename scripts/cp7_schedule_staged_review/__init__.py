"""Additive B schedule review from real staged references; A owns composition.

No connection, commit, default installer or production migration is made here.
Existing work validators/Native functions and their bounded refusal stay exact.
"""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows
from . import render

ROOT = Path(__file__).resolve().parent
SCHEMA = render.SCHEMA
PUBLIC = {'public.erp_cp7_get_staged_production_schedule_v1(uuid)',
          'public.erp_cp7_save_staged_production_schedule_v1(jsonb,uuid)'}
FUNCTIONS = {SCHEMA+'.current_source()': ('s', False),
             SCHEMA+'.workspace(uuid)': ('v', False),
             SCHEMA+'.save(jsonb,uuid)': ('v', False),
             **{name: ('v', True) for name in PUBLIC}}
DYNAMIC_DEPENDENCIES = ('cp7_supply_native.fingerprint(jsonb)',
                        'cp7_analysis_native.source_within(integer,integer)',
                        'cp7_analysis_native.fingerprint(jsonb)', 'cp7_analysis_stage.require_kept(uuid)')


def sources():
    return {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
            if p.is_file() and p.suffix in ('.sql', '.json', '.py')}


def manifest():
    return json.loads((ROOT/'MANIFEST.json').read_text())


def verify_sources():
    m = manifest()
    if sha256(render.NATIVE.read_bytes()).hexdigest() != m['native_schedule_file_sha256']:
        raise ValueError('STAGED_SCHEDULE_FROZEN_NATIVE_SOURCE_CHANGED')
    sql = (ROOT/'review.sql').read_text()
    if sql != render.render() or sha256(sql.encode()).hexdigest() != m['sql_sha256']:
        raise ValueError('STAGED_SCHEDULE_RENDERED_SOURCE_CHANGED')
    return sources()


def dependencies(cur):
    for signature, expected in manifest()['native_dependencies'].items():
        row = _row(cur, signature)
        if sha256(row[1].encode()).hexdigest() != expected['body_sha256'] or row[2] != expected['owner']:
            raise ValueError('STAGED_SCHEDULE_NATIVE_DEPENDENCY_CHANGED: '+signature)
    for signature in DYNAMIC_DEPENDENCIES:
        if cur.execute('select to_regprocedure(%s)is null', (signature,)).fetchone()[0]:
            raise ValueError('STAGED_SCHEDULE_STAGED_DEPENDENCY_MISSING: '+signature)


def declared(group, key):
    return (group == 'schemas' and key == SCHEMA) or (group == 'functions' and key in PUBLIC) or (
        group in ('functions',) and key.startswith(SCHEMA+'.'))


def own_catalog(catalog):
    return {g: {k: v for k, v in rows.items() if declared(g, k)} for g, rows in catalog.items()}


def verify(cur, state):
    if verify_sources() != state['sources']:
        raise ValueError('STAGED_SCHEDULE_SOURCE_CHANGED')
    dependencies(cur)
    if own_catalog(_catalog_rows(cur)) != state['catalog']:
        raise ValueError('STAGED_SCHEDULE_CATALOG_CHANGED')
    sql = (ROOT/'review.sql').read_text()
    for signature, (volatility, definer) in FUNCTIONS.items():
        row = _row(cur, signature)
        expected = re.search(r'create function '+re.escape(signature.split('(')[0])+r'\(.*?\$\$;', sql, re.S)[0]
        if row[0] != state['definitions'][signature] or row[1] != _body(expected) or row[2:6] != ['cp7_capture', definer, volatility, ['search_path=""', 'TimeZone=UTC']]:
            raise ValueError('STAGED_SCHEDULE_FUNCTION_OR_AUTHORITY_CHANGED: '+signature)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_capture'):
            allowed = role == 'cp7_capture' or (signature in PUBLIC and role == 'authenticated')
            if cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')', (role, signature)).fetchone()[0] != allowed:
                raise ValueError('STAGED_SCHEDULE_FUNCTION_EXPOSED: '+signature+':'+role)
    if set(state['catalog']['functions']) != set(FUNCTIONS):
        raise ValueError('STAGED_SCHEDULE_FUNCTION_SET_CHANGED')
    for role in ('anon', 'authenticated', 'service_role'):
        if cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')', (role, SCHEMA)).fetchone()[0]:
            raise ValueError('STAGED_SCHEDULE_PRIVATE_SCHEMA_EXPOSED: '+role)
    for signature, row in state['dependency_rows'].items():
        if _row(cur, signature) != row:
            raise ValueError('STAGED_SCHEDULE_NATIVE_AUTHORITY_CHANGED: '+signature)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('STAGED_SCHEDULE_PUBLIC_CREATE_LEFT_OPEN')
    return dict(stage='cp7.schedule-staged-review.v1', public_rpcs=2, private_functions=3,
                new_tables=0, old_function_replacements=0, Native_ERP_DML=False,
                schedule_metadata_written_only_by_explicit_SAVE=True,
                Native_qualified=False, full_A_chain_qualified=False, production_go=False)


def install_delta(cur):
    pins = verify_sources()
    dependencies(cur)
    if cur.execute('select to_regnamespace(%s)is not null', (SCHEMA,)).fetchone()[0]:
        raise ValueError('STAGED_SCHEDULE_ALREADY_INSTALLED')
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('STAGED_SCHEDULE_PUBLIC_CREATE_PREEXISTS')
    dependency_rows = {s: _row(cur, s) for s in (*manifest()['native_dependencies'], *DYNAMIC_DEPENDENCIES)}
    cur.execute((ROOT/'review.sql').read_text(), prepare=False)
    state = dict(sources=pins, catalog=own_catalog(_catalog_rows(cur)), dependency_rows=dependency_rows,
                 definitions={s: _row(cur, s)[0] for s in FUNCTIONS})
    verify(cur, state)
    return state


def admit_catalog(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('STAGED_SCHEDULE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if old is None and new is not None and declared(group, key) and new == state['catalog'][group].get(key):
                continue
            raise ValueError('STAGED_SCHEDULE_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur, state):
    verify(cur, state)
    if cur.execute("select exists(select 1 from cp7_schedule_native.commands where payload->>'staged_review_contract'=%s)",
                   (render.CONTRACT,)).fetchone()[0]:
        raise ValueError('STAGED_SCHEDULE_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    for signature in sorted(PUBLIC):
        cur.execute('drop function '+signature+' restrict')
    for signature in (SCHEMA+'.save(jsonb,uuid)', SCHEMA+'.workspace(uuid)', SCHEMA+'.current_source()'):
        cur.execute('drop function '+signature+' restrict')
    cur.execute('drop schema '+SCHEMA+' restrict')
