"""Read-only Native reorder inputs; A owns composition and caller installation.

No connection/commit, Native DML, existing body change, endpoint or schedule.
The caller layer must be removed before this stateless helper is inverted;
A's global after-use/backup guard still governs the composed release.
"""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_production_stage import _row
from cp7_ow04_restore_bundle import _catalog_rows

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_reorder_inputs'
FUNCTIONS = {'cp7_reorder_inputs.history(jsonb,jsonb)': 'i',
             'cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)': 'i',
             'cp7_reorder_inputs.source_within(integer)': 's'}


def sources():
    return {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
            if p.is_file() and p.suffix in ('.py', '.json', '.sql')}


def verify_sources():
    manifest = json.loads((ROOT/'MANIFEST.json').read_text())
    for filename, digest in manifest['sql_sha256'].items():
        if sha256((ROOT/filename).read_bytes()).hexdigest() != digest:
            raise ValueError('OW10_REORDER_INPUTS_SOURCE_CHANGED: '+filename)
    return sources()


def prerequisites(cur):
    for signature, digest in json.loads((ROOT/'MANIFEST.json').read_text())['existing_body_sha256'].items():
        row = _row(cur, signature)
        if sha256(row[1].encode()).hexdigest() != digest or row[2] != 'cp7_capture':
            raise ValueError('OW10_REORDER_INPUTS_NATIVE_PREDECESSOR_CHANGED: '+signature)


def declared(group, key):
    return (group == 'schemas' and key == SCHEMA) or (group == 'functions' and key in FUNCTIONS)


def own_catalog(catalog):
    return {group: {key: row for key, row in rows.items() if declared(group, key)}
            for group, rows in catalog.items()}


def verify(cur, state):
    if verify_sources() != state['sources']:
        raise ValueError('OW10_REORDER_INPUTS_SOURCE_CHANGED')
    prerequisites(cur)
    bodies = {}
    for filename in ('history.sql', 'points.sql', 'source.sql'):
        bodies.update(re.findall(r'create function (cp7_reorder_inputs\.[a-z_]+)\([^;]*?\).*?as \$\$(.*?)\$\$;',
                                 (ROOT/filename).read_text(), re.S))
    if set(bodies) != {sig.split('(')[0] for sig in FUNCTIONS}:
        raise ValueError('OW10_REORDER_INPUTS_PRIVATE_SET_CHANGED')
    for signature in FUNCTIONS:
        row = _row(cur, signature)
        if row[1] != bodies[signature.split('(')[0]] or row[2:6] != ['cp7_capture', False, FUNCTIONS[signature], ['search_path=""', 'TimeZone=UTC']]:
            raise ValueError('OW10_REORDER_INPUTS_PRIVATE_BODY_OR_AUTHORITY_CHANGED: '+signature)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0]:
                raise ValueError('OW10_REORDER_INPUTS_PRIVATE_EXECUTE_EXPOSED: '+signature+':'+role)
    actual = own_catalog(_catalog_rows(cur))
    if actual != state['new_catalog'] or set(actual['schemas']) != {SCHEMA} or set(actual['functions']) != set(FUNCTIONS):
        raise ValueError('OW10_REORDER_INPUTS_PRIVATE_CATALOG_CHANGED')
    if actual['schemas'][SCHEMA][0] != 'cp7_capture':
        raise ValueError('OW10_REORDER_INPUTS_SCHEMA_OWNER_CHANGED')
    for group in ('schemas', 'functions'):
        for key, row in actual[group].items():
            for grant in row[-1]:
                if grant[0] != 'cp7_capture' or grant[1] != 'cp7_capture' or grant[3] is not False:
                    raise ValueError('OW10_REORDER_INPUTS_UNDECLARED_GRANT: '+key)
    return dict(stage='cp7.reorder-inputs-stage.v2', private_functions=3, hook_bodies=0,
                Native_DML=False, live_ROP_caller_changed=False,
                full_A_chain_qualified=False, production_go=False)


def install_delta(cur):
    pins = verify_sources()
    if cur.execute('select to_regnamespace(%s)is not null', (SCHEMA,)).fetchone()[0]:
        raise ValueError('OW10_REORDER_INPUTS_ALREADY_INSTALLED')
    prerequisites(cur)
    for filename in ('history.sql', 'points.sql', 'source.sql'):
        cur.execute((ROOT/filename).read_text(), prepare=False)
    state = dict(sources=pins, new_catalog=own_catalog(_catalog_rows(cur)))
    verify(cur, state)
    return state


def admit_catalog(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('OW10_REORDER_INPUTS_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if old is None and new is not None and declared(group, key) and new == state['new_catalog'][group].get(key):
                continue
            raise ValueError('OW10_REORDER_INPUTS_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur, state):
    verify(cur, state)
    # These pure helpers keep no runs or business data. Never drop a helper
    # while an installed SQL caller still references it. The composed caller
    # owns any retained evaluations and its own after-use/backup boundary.
    if cur.execute("select exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                   "where n.nspname<>%s and case when p.prokind in('f','p') "
                   "then position(%s in pg_get_functiondef(p.oid))>0 else false end)",
                   (SCHEMA, SCHEMA+'.')).fetchone()[0]:
        raise ValueError('OW10_REORDER_INPUTS_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    cur.execute('drop schema cp7_reorder_inputs cascade', prepare=False)
