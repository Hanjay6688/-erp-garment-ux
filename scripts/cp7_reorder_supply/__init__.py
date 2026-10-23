"""Reversible B supply-budget producer; A composes the full release.

No connection/commit, cron, public RPC or live ROP caller. Reader integration
remains open. A supplies transaction/envelope and the global after-use guard.
"""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
from . import patches

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_reorder_supply'
FUNCTIONS=(SCHEMA+'.project(jsonb)',SCHEMA+'.budgets(jsonb,jsonb)')


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())
            if p.is_file()and p.suffix in('.sql','.py','.json')}


def verify_sources():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for filename,digest in manifest['sql_sha256'].items():
        if sha256((ROOT/filename).read_bytes()).hexdigest()!=digest:
            raise ValueError('OW10_SUPPLY_SOURCE_CHANGED: '+filename)
    return sources()


def declared(group,key):
    return (group=='schemas'and key==SCHEMA)or(group=='functions'and key in FUNCTIONS)


def new_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def verify(cur,state):
    if verify_sources()!=state['sources']:
        raise ValueError('OW10_SUPPLY_SOURCE_CHANGED')
    expected=patches.patched({sig:row[0]for sig,row in state['originals'].items()})
    for sig in patches.SIGNATURES:
        row=_row(cur,sig)
        if row[0]!=state['definitions'][sig]or row[0]!=expected[sig]or row[2:]!=state['originals'][sig][2:]:
            raise ValueError('OW10_SUPPLY_HOOK_OR_AUTHORITY_CHANGED: '+sig)
    bodies={}
    for file in ('projection.sql','capture.sql'):
        bodies.update(re.findall(r'create function (cp7_reorder_supply\.[a-z_]+)\([^;]*?\).*?as \$\$(.*?)\$\$;',
                                 (ROOT/file).read_text(),re.S))
    if set(bodies)!={sig.split('(')[0]for sig in FUNCTIONS}:
        raise ValueError('OW10_SUPPLY_PRIVATE_SET_CHANGED')
    for sig in FUNCTIONS:
        row=_row(cur,sig)
        if row[1]!=bodies[sig.split('(')[0]]or row[2:6]!=['cp7_capture',False,'i',['search_path=""','TimeZone=UTC']]:
            raise ValueError('OW10_SUPPLY_PRIVATE_BODY_OR_AUTHORITY_CHANGED: '+sig)
        for role in ('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('OW10_SUPPLY_PRIVATE_EXECUTE_EXPOSED: '+sig+':'+role)
    catalog=new_catalog(_catalog_rows(cur))
    if catalog!=state['new_catalog']or set(catalog['schemas'])!={SCHEMA}or set(catalog['functions'])!=set(FUNCTIONS):
        raise ValueError('OW10_SUPPLY_PRIVATE_CATALOG_CHANGED')
    for group,rows in catalog.items():
        if group not in('schemas','functions')and rows:
            raise ValueError('OW10_SUPPLY_UNDECLARED_PRIVATE_OBJECT: '+group)
    if catalog['schemas'][SCHEMA][0]!='cp7_capture':
        raise ValueError('OW10_SUPPLY_SCHEMA_OWNER_CHANGED')
    for group in ('schemas','functions'):
        for key,row in catalog[group].items():
            for grant in row[-1]:
                if grant[0]!='cp7_capture'or grant[1]!='cp7_capture'or grant[3]is not False:
                    raise ValueError('OW10_SUPPLY_UNDECLARED_PRIVATE_GRANT: '+key)
    return dict(stage='cp7.reorder-supply-producer.v1',private_functions=2,hook_bodies=2,
        new_public_rpcs=0,live_ROP_caller_changed=False,full_A_chain_qualified=False,production_go=False)


def install_delta(cur):
    pins=verify_sources()
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
        raise ValueError('OW10_SUPPLY_ALREADY_INSTALLED')
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')").fetchone()[0]:
        raise ValueError('OW10_SUPPLY_RUNNING_ANALYSIS_REQUIRES_QUIET_INSTALL')
    before=_catalog_rows(cur)
    originals={sig:_row(cur,sig)for sig in patches.SIGNATURES}
    definitions=patches.patched({sig:row[0]for sig,row in originals.items()})
    for file in ('projection.sql','capture.sql'):
        cur.execute((ROOT/file).read_text(),prepare=False)
    for definition in definitions.values():cur.execute(definition,prepare=False)
    state=dict(sources=pins,originals=originals,
        definitions={sig:_row(cur,sig)[0]for sig in patches.SIGNATURES},new_catalog=new_catalog(_catalog_rows(cur)))
    # pg_get_functiondef normalizes headers. Compare expected bodies, retaining
    # every original owner/ACL/config field. Body text itself stays byte exact.
    expected_bodies={sig:_body(definition)for sig,definition in definitions.items()}
    for sig in definitions:
        if _row(cur,sig)[1]!=expected_bodies[sig]:raise ValueError('OW10_SUPPLY_HOOK_BODY_CHANGED: '+sig)
    admit_catalog(before,_catalog_rows(cur),state);verify(cur,state)
    return state


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('OW10_SUPPLY_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in patches.SIGNATURES and old is not None and new is not None:
                if old[0]==state['originals'][key][0]and new[0]==state['definitions'][key]and old[1:]==new[1:]:continue
            if old is None and new is not None and declared(group,key)and new==state['new_catalog'][group].get(key):continue
            raise ValueError('OW10_SUPPLY_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur,state):
    verify(cur,state)
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where reference?'reorder_supply_engine')"
                   "or exists(select 1 from cp7_analysis_stage.plan_scope where scope?'reorder_supply_budget')").fetchone()[0]:
        raise ValueError('OW10_SUPPLY_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    for sig in reversed(patches.SIGNATURES):cur.execute(state['originals'][sig][0],prepare=False)
    cur.execute('drop schema cp7_reorder_supply cascade',prepare=False)
    for sig,row in state['originals'].items():
        if _row(cur,sig)!=row:raise ValueError('OW10_SUPPLY_HOOK_NOT_RESTORED: '+sig)
