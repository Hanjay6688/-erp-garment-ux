"""FG caller delta. A owns the transaction, envelope and composed release."""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_production_stage import _row
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_reorder_reader_stage as reader
import cp7_reorder_inputs as inputs

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_reorder_caller'
TABLES = {SCHEMA+'.evaluations', SCHEMA+'.use_marks'}
FUNCTIONS = {SCHEMA+'.evaluate(jsonb,jsonb)': 'i', SCHEMA+'.wire_row(jsonb,timestamp with time zone)': 'i'}


def manifest():
    return json.loads((ROOT/'MANIFEST.json').read_text())


def sources():
    return {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
            if p.is_file() and p.suffix in ('.py', '.json', '.sql')}


def verify_sources():
    m = manifest()
    for filename, digest in m['sql_sha256'].items():
        if sha256((ROOT/filename).read_bytes()).hexdigest() != digest:
            raise ValueError('OW10_REORDER_CALLER_SOURCE_CHANGED: '+filename)
    for signature, item in m['hooks'].items():
        if sha256((ROOT.parents[1]/item['source']).read_bytes()).hexdigest() != item['source_sha256']:
            raise ValueError('OW10_REORDER_CALLER_PREDECESSOR_FILE_CHANGED: '+signature)
    return sources()


def declared(group, key):
    return (group == 'schemas' and key == SCHEMA) or (group in
            ('relations', 'columns', 'constraints', 'indexes', 'triggers', 'functions', 'types', 'type_implementation', 'policies')
            and key.startswith(SCHEMA+'.'))


def own_catalog(catalog):
    return {group: {key: row for key, row in rows.items() if declared(group, key)}
            for group, rows in catalog.items()}


def verify_dependencies(cur):
    for signature, item in manifest()['dependency_bodies'].items():
        row = _row(cur, signature)
        if sha256(row[1].encode()).hexdigest() != item['sha256'] \
                or row[2:6] != ['cp7_capture', False, item['volatility'], ['search_path=""', 'TimeZone=UTC']]:
            raise ValueError('OW10_REORDER_CALLER_SUPPLY_DEPENDENCY_CHANGED: '+signature)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0]:
                raise ValueError('OW10_REORDER_CALLER_SUPPLY_DEPENDENCY_EXPOSED: '+signature+':'+role)


def verify(cur, state):
    if verify_sources() != state['sources']:
        raise ValueError('OW10_REORDER_CALLER_SOURCE_CHANGED')
    reader.verify(cur, state['reader'])
    verify_dependencies(cur)
    m = manifest()
    for signature, item in m['hooks'].items():
        row = _row(cur, signature)
        if row[0] != state['definitions'][signature] or row[2:] != state['originals'][signature][2:] \
                or sha256(row[1].encode()).hexdigest() != item['after_body_sha256']:
            raise ValueError('OW10_REORDER_CALLER_HOOK_OR_AUTHORITY_CHANGED: '+signature)
    bodies = {}
    for filename in ('evaluate.sql', 'state.sql'):
        bodies.update(re.findall(r'create function (cp7_reorder_caller\.[a-z_]+)\([^;]*?\).*?as \$\$(.*?)\$\$;',
                                 (ROOT/filename).read_text(), re.S))
    if set(bodies) != {sig.split('(')[0] for sig in FUNCTIONS}:
        raise ValueError('OW10_REORDER_CALLER_PRIVATE_SET_CHANGED')
    for signature in FUNCTIONS:
        row = _row(cur, signature)
        if row[1] != bodies[signature.split('(')[0]] or row[2:6] != ['cp7_capture', False, FUNCTIONS[signature], ['search_path=""', 'TimeZone=UTC']]:
            raise ValueError('OW10_REORDER_CALLER_PRIVATE_BODY_OR_AUTHORITY_CHANGED: '+signature)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0]:
                raise ValueError('OW10_REORDER_CALLER_PRIVATE_EXECUTE_EXPOSED: '+signature+':'+role)
    actual = own_catalog(_catalog_rows(cur))
    if actual != state['new_catalog'] or set(actual['schemas']) != {SCHEMA} or set(actual['functions']) != set(FUNCTIONS):
        raise ValueError('OW10_REORDER_CALLER_PRIVATE_CATALOG_CHANGED')
    indexes = {SCHEMA+'.evaluations_pkey', SCHEMA+'.evaluations_root_id_key', SCHEMA+'.use_marks_pkey'}
    if set(actual['relations']) != TABLES | indexes or set(actual['indexes']) != indexes \
            or set(actual['policies']) != {SCHEMA+'.evaluations:reorder_evaluation_no_access', SCHEMA+'.use_marks:reorder_caller_use_no_access'} \
            or set(actual['triggers']) != {SCHEMA+'.use_marks:reorder_caller_use_immutable'} or len(actual['types']) != 4:
        raise ValueError('OW10_REORDER_CALLER_PRIVATE_OBJECT_SET_CHANGED')
    for table in TABLES:
        owner, rls = cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass', (table,)).fetchone()
        if owner != 'cp7_capture' or rls is not True:
            raise ValueError('OW10_REORDER_CALLER_PRIVATE_TABLE_AUTHORITY_CHANGED: '+table)
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')", (role, table)).fetchone()[0]:
                raise ValueError('OW10_REORDER_CALLER_PRIVATE_TABLE_EXPOSED: '+table+':'+role)
            if cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (role, SCHEMA)).fetchone()[0]:
                raise ValueError('OW10_REORDER_CALLER_SCHEMA_EXPOSED: '+role)
    if actual['schemas'][SCHEMA][0] != 'cp7_capture':
        raise ValueError('OW10_REORDER_CALLER_SCHEMA_OWNER_CHANGED')
    for group in ('schemas', 'functions', 'relations'):
        for key, row in actual[group].items():
            for grant in row[-1]:
                if grant[0] != 'cp7_capture' or grant[1] != 'cp7_capture' or grant[3] is not False:
                    raise ValueError('OW10_REORDER_CALLER_UNDECLARED_GRANT: '+key)
    return dict(stage='cp7.reorder-caller-stage.v1', hook_bodies=8, private_functions=2, private_tables=2,
                Native_DML=False, live_ROP_caller_changed=True, new_public_RPCS=0,
                full_A_chain_qualified=False, production_go=False)


def install_delta(cur):
    pins = verify_sources()
    if cur.execute('select to_regnamespace(%s)is not null', (SCHEMA,)).fetchone()[0]:
        raise ValueError('OW10_REORDER_CALLER_ALREADY_INSTALLED')
    before = _catalog_rows(cur)
    input_state = dict(sources=inputs.verify_sources(), new_catalog=inputs.own_catalog(before))
    reader_state = dict(sources=reader.verify_sources(), inputs=input_state, new_catalog=reader.own_catalog(before))
    reader.verify(cur, reader_state)
    verify_dependencies(cur)
    originals = {signature: _row(cur, signature) for signature in manifest()['hooks']}
    for signature, item in manifest()['hooks'].items():
        if sha256(originals[signature][1].encode()).hexdigest() != item['before_body_sha256']:
            raise ValueError('OW10_REORDER_CALLER_PREDECESSOR_BODY_CHANGED: '+signature)
    for filename in ('evaluate.sql', 'state.sql'):
        cur.execute((ROOT/filename).read_text(), prepare=False)
    installed = set()
    for item in manifest()['hooks'].values():
        if item['forward'] not in installed:
            cur.execute((ROOT/item['forward']).read_text(), prepare=False)
            installed.add(item['forward'])
    state = dict(sources=pins, reader=reader_state, originals=originals,
                 definitions={signature: _row(cur, signature)[0] for signature in originals},
                 new_catalog=own_catalog(_catalog_rows(cur)))
    verify(cur, state)
    return state


def admit_catalog(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('OW10_REORDER_CALLER_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if group == 'functions' and key in state['originals'] and old is not None and new is not None \
                    and old[0] == state['originals'][key][0] and new[0] == state['definitions'][key] and old[1:] == new[1:]:
                continue
            if old is None and new is not None and declared(group, key) and new == state['new_catalog'][group].get(key):
                continue
            raise ValueError('OW10_REORDER_CALLER_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur, state):
    verify(cur, state)
    if cur.execute('select exists(select 1 from cp7_reorder_caller.use_marks)or exists(select 1 from cp7_reorder_caller.evaluations)').fetchone()[0]:
        raise ValueError('OW10_REORDER_CALLER_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    # Restore every original body and its unchanged authority before dropping
    # the private layer. Do not clear a marker/cache to make rollback pass.
    for signature in reversed(tuple(state['originals'])):
        cur.execute(state['originals'][signature][0], prepare=False)
    cur.execute('drop schema cp7_reorder_caller cascade', prepare=False)
    for signature, original in state['originals'].items():
        if _row(cur, signature) != original:
            raise ValueError('OW10_REORDER_CALLER_ORIGINAL_NOT_RESTORED: '+signature)
