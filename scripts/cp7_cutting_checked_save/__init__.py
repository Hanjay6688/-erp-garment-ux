"""OW13c stricter SAVE only; A composes transaction/envelope and shared registry."""
from hashlib import sha256
from pathlib import Path
import json
from cp7_production_stage import _row
from cp7_ow04_restore_bundle import _catalog_rows

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_cutting_checked'
PUBLIC = 'public.erp_cp7_save_cutting_suggestion_v1(jsonb,uuid)'
FUNCTIONS = {SCHEMA+'.source_now(uuid,text)': ('cp7_capture', True),
             SCHEMA+'.save(jsonb,uuid)': ('cp7_plan_writer', False), PUBLIC: ('cp7_plan_writer', True)}


def manifest():
    return json.loads((ROOT/'MANIFEST.json').read_text())


def sources():
    return {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
            if p.is_file() and p.suffix in ('.sql', '.json', '.py')}


def verify_sources():
    for name, digest in manifest()['sql_sha256'].items():
        if sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError('OW13C_CHECKED_SAVE_SOURCE_CHANGED: '+name)
    return sources()


def dependencies(cur):
    for signature, expected in manifest()['dependencies'].items():
        row = _row(cur, signature)
        if sha256(row[1].encode()).hexdigest() != expected['body_sha256'] or row[2] != expected['owner']:
            raise ValueError('OW13C_CHECKED_SAVE_PREDECESSOR_CHANGED: '+signature)


def declared(group, key):
    return (group == 'schemas' and key == SCHEMA) or (group == 'functions' and key == PUBLIC) or (
        group in ('relations', 'columns', 'constraints', 'indexes', 'triggers', 'functions', 'types',
                  'type_implementation', 'policies') and key.startswith(SCHEMA+'.'))


def own_catalog(catalog):
    return {group: {k: v for k, v in values.items() if declared(group, k)} for group, values in catalog.items()}


def verify(cur, state):
    if verify_sources() != state['sources']:
        raise ValueError('OW13C_CHECKED_SAVE_SOURCE_CHANGED')
    dependencies(cur)
    if own_catalog(_catalog_rows(cur)) != state['catalog']:
        raise ValueError('OW13C_CHECKED_SAVE_CATALOG_CHANGED')
    for signature, (owner, definer) in FUNCTIONS.items():
        row = _row(cur, signature)
        if row[0] != state['definitions'][signature] or row[2:6] != [owner, definer, 'v', ['search_path=""', 'TimeZone=UTC']]:
            raise ValueError('OW13C_CHECKED_SAVE_AUTHORITY_CHANGED: '+signature)
        for role in ('anon', 'service_role', 'authenticated', 'cp7_capture'):
            allowed = role == owner or (signature == PUBLIC and role == 'authenticated')
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role, signature)).fetchone()[0] != allowed:
                raise ValueError('OW13C_CHECKED_SAVE_EXPOSED: '+signature+':'+role)
    if set(state['catalog']['functions']) != set(FUNCTIONS):
        raise ValueError('OW13C_CHECKED_SAVE_FUNCTION_SET_CHANGED')
    for role in ('anon', 'authenticated', 'service_role'):
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')", (role, SCHEMA)).fetchone()[0]:
            raise ValueError('OW13C_CHECKED_SAVE_SCHEMA_EXPOSED: '+role)
        if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                       (role, SCHEMA+'.receipts')).fetchone()[0]:
            raise ValueError('OW13C_CHECKED_SAVE_RECEIPTS_EXPOSED: '+role)
    for signature, row in state['dependency_rows'].items():
        if _row(cur, signature) != row:
            raise ValueError('OW13C_CHECKED_SAVE_DEPENDENCY_AUTHORITY_CHANGED: '+signature)
    owner, rls = cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',
                             (SCHEMA+'.receipts',)).fetchone()
    if owner != 'cp7_plan_writer' or rls is not True:
        raise ValueError('OW13C_CHECKED_SAVE_RECEIPT_AUTHORITY_CHANGED')
    return dict(stage='cp7.cutting-checked-save-stage.v1', public_rpcs=1, new_private_tables=1,
                old_plan_save_changed=False, Native_qualified=False, full_A_chain_qualified=False, production_go=False)


def install_delta(cur):
    pins = verify_sources()
    dependencies(cur)
    if cur.execute("select has_schema_privilege('cp7_plan_writer','public','CREATE')").fetchone()[0]:
        raise ValueError('OW13C_CHECKED_SAVE_PUBLIC_CREATE_PREEXISTS')
    for name in ('schema.sql', 'save.sql'):
        cur.execute((ROOT/name).read_text(), prepare=False)
    state = dict(sources=pins, catalog=own_catalog(_catalog_rows(cur)),
                 dependency_rows={s: _row(cur, s) for s in manifest()['dependencies']},
                 definitions={s: _row(cur, s)[0] for s in FUNCTIONS})
    verify(cur, state)
    return state


def admit_catalog(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('OW13C_CHECKED_SAVE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if old is None and new is not None and declared(group, key) and new == state['catalog'][group].get(key):
                continue
            raise ValueError('OW13C_CHECKED_SAVE_UNDECLARED_DELTA: '+group+':'+key)


def rollback_preuse(cur, state):
    verify(cur, state)
    if cur.execute('select exists(select 1 from cp7_cutting_checked.receipts)').fetchone()[0]:
        raise ValueError('OW13C_CHECKED_SAVE_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    cur.execute('drop function '+PUBLIC, prepare=False)
    cur.execute('drop function cp7_cutting_checked.save(jsonb,uuid)', prepare=False)
    cur.execute('drop function cp7_cutting_checked.source_now(uuid,text)', prepare=False)
    cur.execute('drop table cp7_cutting_checked.receipts', prepare=False)
    cur.execute('drop schema cp7_cutting_checked', prepare=False)
