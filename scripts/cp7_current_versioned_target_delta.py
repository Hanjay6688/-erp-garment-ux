"""A-owned transition from installed target v1 to exact B versioned hooks.

Retain all legacy source/projection/consumer objects and every business row.
Only two new private namespaces, nine functions are added; 14 of 21 named hook bodies change.
This adapter never calls the fresh-only B installer over an existing target.
"""
from hashlib import sha256
from pathlib import Path
import re
import cp7_model_target_consumer_stage as previous
import cp7_model_target_source_v2 as source
import cp7_model_target_consumer_v2_stage as target
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows

CONTRACT = 'cp7.current-versioned-target-delta.v1'
HOOK_SIGNATURES = frozenset(previous.render.originals())
SCHEMAS = (source.SCHEMA, 'cp7_model_target_consumer_v2')
FUNCTIONS = {sig:(v,True) for sig,v in source.FUNCTIONS.items() if sig.startswith(source.SCHEMA+'.')}
FUNCTIONS.update({sig:flags for sig,flags in target.FUNCTIONS.items() if sig.startswith('cp7_model_target_consumer_v2.')})


def verify_sources():
    assert len(FUNCTIONS) == 9 and len(SCHEMAS) == 2
    return dict(contract=CONTRACT, entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                predecessor=previous.verify_sources(), source=source.verify_sources(), target=target.verify_sources())


def definitions():
    sql = '\n'.join((source.ROOT/name).read_text() for name in source.FILES)
    sql += '\n'+'\n'.join((target.consumer.ROOT/name).read_text() for name in ('consumer.sql','timeline.sql'))
    new = {sig:re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0] for sig in FUNCTIONS}
    old, replaced = previous.render.replacements(), target.render.replacements()
    assert set(old) == set(replaced) == HOOK_SIGNATURES and len(old) == 21
    assert sum(_body(old[sig]) != _body(replaced[sig]) for sig in old) == 14
    return sql, new, old, replaced


def declared(group, key):
    return (group == 'schemas' and key in SCHEMAS) or (group == 'functions' and key in set(FUNCTIONS)|HOOK_SIGNATURES)


def own_catalog(catalog):
    return {group:{key:row for key,row in rows.items() if declared(group,key)} for group,rows in catalog.items()}


def admit_catalog(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_CATALOG_GROUPS_CHANGED')
    _, _, old, new = definitions()
    replacements = {sig for sig in old if _body(old[sig]) != _body(new[sig])}
    expected = {('functions',sig) for sig in replacements|set(FUNCTIONS)}|{('schemas',name) for name in SCHEMAS}
    if own_catalog(after) != state['catalog']:
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_OWN_CATALOG_CHANGED')
    observed = set()
    for group in before:
        for key in set(before[group])|set(after[group]):
            left, right = before[group].get(key), after[group].get(key)
            if left == right:
                continue
            if ((group,key) not in expected or right is None
                    or ((group == 'functions' and key in replacements) != (left is not None))):
                raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_UNDECLARED: '+group+':'+key)
            observed.add((group,key))
    if observed != expected:
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_INCOMPLETE')


def verify(cur, state):
    if verify_sources() != state['sources'] or own_catalog(_catalog_rows(cur)) != state['catalog']:
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_SOURCE_OR_CATALOG_CHANGED')
    _, new, old, replacements = definitions()
    if set(state['old_rows']) != set(old) or set(state['new_rows']) != set(new)|set(old):
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_SIGNATURES_CHANGED')
    for sig, row in state['new_rows'].items():
        if _row(cur,sig) != row or row[1] != _body((new|replacements)[sig]):
            raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_FUNCTION_CHANGED: '+sig)
        if sig in old and (state['old_rows'][sig][1] != _body(old[sig]) or row[2:] != state['old_rows'][sig][2:]):
            raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_OLD_BODY_OR_AUTHORITY_CHANGED: '+sig)
    for sig, row in state['dependencies'].items():
        if _row(cur,sig) != row:
            raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_DEPENDENCY_CHANGED: '+sig)
    for sig,(volatility,utc) in FUNCTIONS.items():
        settings = ['search_path=""']+(['TimeZone=UTC'] if utc else [])
        if state['new_rows'][sig][2:6] != ['cp7_capture',False,volatility,settings]:
            raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_PRIVATE_AUTHORITY_CHANGED: '+sig)
        for role in ('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_PRIVATE_EXECUTE_EXPOSED: '+sig)
    for name in SCHEMAS:
        if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(name,)).fetchone() != ('cp7_capture',):
            raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_SCHEMA_OWNER_CHANGED')
        for role in ('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,name)).fetchone()[0]:
                raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_SCHEMA_EXPOSED')
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_PUBLIC_CREATE_OPEN')
    return dict(stage=CONTRACT,new_private_functions=9,new_schemas=2,existing_replacements=14,named_hooks_verified=21,unchanged_hooks_retained=7,
                legacy_target_objects_retained=True,new_public_rpcs=0,new_tables=0,production_go=False)


def install_delta(cur, predecessor_checker):
    pins = verify_sources()
    if not callable(predecessor_checker):
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_COMPOSED_PARENT_REQUIRED')
    predecessor_checker(cur)
    if any(cur.execute('select to_regnamespace(%s)is not null',(name,)).fetchone()[0] for name in SCHEMAS):
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_ALREADY_INSTALLED')
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')or exists(select 1 from cp7_analysis_jobs.jobs where state='WAITING')").fetchone()[0]:
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_QUIET_INSTALL_REQUIRED')
    sql, new, originals, replacements = definitions()
    before = _catalog_rows(cur)
    old = {sig:_row(cur,sig) for sig in originals}
    for sig,definition in originals.items():
        if old[sig][1] != _body(definition) or old[sig][2] != 'cp7_capture':
            raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_PREDECESSOR_CHANGED: '+sig)
    signatures = cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
    dependencies = {sig:_row(cur,sig) for (sig,) in signatures if sig not in old}
    used = target.usage_state(cur)
    cur.execute(sql,prepare=False)
    cur.execute((target.ROOT/'hooks.sql').read_text(),prepare=False)
    state = dict(sources=pins,old_rows=old,new_rows={sig:_row(cur,sig) for sig in (*old,*new)},
                 dependencies=dependencies,usage_before=used,catalog=own_catalog(_catalog_rows(cur)))
    admit_catalog(before,_catalog_rows(cur),state)
    verify(cur,state)
    return state


def rollback_preuse(cur, state):
    verify(cur,state)
    if target.usage_state(cur) != state['usage_before']:
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE')
    external = cur.execute("select p.oid::regprocedure::text from pg_proc p where not(p.oid=any(%s::regprocedure[]))and case when p.prokind in('f','p')then exists(select 1 from unnest(%s::text[])ns where position(ns||'.'in pg_get_functiondef(p.oid))>0)else false end",(list(state['new_rows']),list(SCHEMAS))).fetchall()
    if external:
        raise ValueError('CURRENT_VERSIONED_TARGET_DELTA_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint current_versioned_target_inverse')
    try:
        for row in state['old_rows'].values():
            cur.execute(row[0],prepare=False)
        for sig in reversed(FUNCTIONS):
            cur.execute('drop function '+sig+' restrict')
        for name in reversed(SCHEMAS):
            cur.execute('drop schema '+name+' restrict')
    except Exception:
        cur.execute('rollback to savepoint current_versioned_target_inverse')
        raise
    finally:
        cur.execute('release savepoint current_versioned_target_inverse')
