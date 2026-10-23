"""Private reorder cache; A owns composition and the global after-use boundary."""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_production_stage import _row
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_reorder_inputs as inputs

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_reorder_reader'
TABLES = {SCHEMA+'.cache', SCHEMA+'.use_marks'}
FUNCTIONS = {SCHEMA+'.snapshot(jsonb)': 'v', SCHEMA+'.immutable_use()': 'v'}


def sources():
    return {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
            if p.is_file() and p.suffix in ('.py', '.json', '.sql')}


def verify_sources():
    for filename, digest in json.loads((ROOT/'MANIFEST.json').read_text())['sql_sha256'].items():
        if sha256((ROOT/filename).read_bytes()).hexdigest() != digest:
            raise ValueError('OW10_REORDER_READER_SOURCE_CHANGED: '+filename)
    return sources()


def declared(group, key):
    return (group == 'schemas' and key == SCHEMA) or (group in
            ('relations', 'columns', 'constraints', 'indexes', 'triggers', 'functions', 'types', 'type_implementation', 'policies')
            and key.startswith(SCHEMA+'.'))


def own_catalog(catalog):
    return {group: {key: row for key, row in rows.items() if declared(group, key)}
            for group, rows in catalog.items()}


def verify(cur, state):
    if verify_sources() != state['sources']:
        raise ValueError('OW10_REORDER_READER_SOURCE_CHANGED')
    inputs.verify(cur, state['inputs'])
    bodies = dict(re.findall(r'create function (cp7_reorder_reader\.[a-z_]+)\([^;]*?\).*?as \$\$(.*?)\$\$;',
                             (ROOT/'cache.sql').read_text(), re.S))
    if set(bodies) != {sig.split('(')[0] for sig in FUNCTIONS}:
        raise ValueError('OW10_REORDER_READER_PRIVATE_SET_CHANGED')
    for sig in FUNCTIONS:
        row = _row(cur, sig)
        if row[1] != bodies[sig.split('(')[0]] or row[2:6] != ['cp7_capture', False, FUNCTIONS[sig], ['search_path=""', 'TimeZone=UTC']]:
            raise ValueError('OW10_REORDER_READER_BODY_OR_AUTHORITY_CHANGED: '+sig)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, sig)).fetchone()[0]:
                raise ValueError('OW10_REORDER_READER_FUNCTION_EXPOSED: '+sig+':'+role)
    actual = own_catalog(_catalog_rows(cur))
    if actual != state['new_catalog'] or set(actual['schemas']) != {SCHEMA} or set(actual['functions']) != set(FUNCTIONS):
        raise ValueError('OW10_REORDER_READER_PRIVATE_CATALOG_CHANGED')
    indexes = {SCHEMA+'.cache_pkey', SCHEMA+'.use_marks_pkey'}
    if set(actual['relations']) != TABLES | indexes or set(actual['indexes']) != indexes \
            or set(actual['policies']) != {SCHEMA+'.cache:reorder_cache_no_access', SCHEMA+'.use_marks:reorder_use_no_access'} \
            or set(actual['triggers']) != {SCHEMA+'.use_marks:reorder_use_immutable'} or len(actual['types']) != 4:
        raise ValueError('OW10_REORDER_READER_PRIVATE_OBJECT_SET_CHANGED')
    for table in TABLES:
        owner, rls = cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass', (table,)).fetchone()
        if owner != 'cp7_capture' or rls is not True:
            raise ValueError('OW10_REORDER_READER_TABLE_AUTHORITY_CHANGED: '+table)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')", (role, table)).fetchone()[0]:
                raise ValueError('OW10_REORDER_READER_TABLE_EXPOSED: '+table+':'+role)
            if cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (role, SCHEMA)).fetchone()[0]:
                raise ValueError('OW10_REORDER_READER_SCHEMA_EXPOSED: '+role)
    if actual['schemas'][SCHEMA][0] != 'cp7_capture':
        raise ValueError('OW10_REORDER_READER_SCHEMA_OWNER_CHANGED')
    for group in ('schemas', 'functions', 'relations'):
        for key, row in actual[group].items():
            for grant in row[-1]:
                if grant[0] != 'cp7_capture' or grant[1] != 'cp7_capture' or grant[3] is not False:
                    raise ValueError('OW10_REORDER_READER_UNDECLARED_GRANT: '+key)
    return dict(stage='cp7.reorder-reader-stage.v1', private_functions=2, private_tables=2,
                hook_bodies=0, Native_DML=False, live_ROP_caller_changed=False,
                full_A_chain_qualified=False, production_go=False)


def install_delta(cur):
    pins = verify_sources()
    if cur.execute('select to_regnamespace(%s)is not null', (SCHEMA,)).fetchone()[0]:
        raise ValueError('OW10_REORDER_READER_ALREADY_INSTALLED')
    before = _catalog_rows(cur)
    input_state = dict(sources=inputs.verify_sources(), new_catalog=inputs.own_catalog(before))
    inputs.verify(cur, input_state)
    cur.execute((ROOT/'cache.sql').read_text(), prepare=False)
    state = dict(sources=pins, inputs=input_state, new_catalog=own_catalog(_catalog_rows(cur)))
    verify(cur, state)
    return state


def admit_catalog(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('OW10_REORDER_READER_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if old is None and new is not None and declared(group, key) and new == state['new_catalog'][group].get(key):
                continue
            raise ValueError('OW10_REORDER_READER_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur, state):
    verify(cur, state)
    if cur.execute('select exists(select 1 from cp7_reorder_reader.use_marks)or exists(select 1 from cp7_reorder_reader.cache)').fetchone()[0]:
        raise ValueError('OW10_REORDER_READER_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    cur.execute('drop schema cp7_reorder_reader cascade', prepare=False)
