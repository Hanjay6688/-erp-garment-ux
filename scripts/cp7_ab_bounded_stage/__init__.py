"""A integrator adapter: exact B stage with the declared A finance predecessor."""
from pathlib import Path
from hashlib import sha256
import json
import re
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows
from . import render
from cp7_bounded_analysis_stage import source
import cp7_bounded_analysis_stage as bounded

ROOT = Path(__file__).resolve().parent
SCHEMA = render.SCHEMA
ADDITIONS = {SCHEMA+'.'+s: props for s,props in render.PRIVATE.items()}
ADDITIONS[render.PUBLIC] = ('v', True)


def sources():
    return dict(adapter={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
                if p.is_file() and p.suffix in('.py','.sql','.json')},
                qualified_B=bounded.sources(),composition=render.manifest())


def verify_sources():
    bounded.verify_sources()
    if json.loads((ROOT/'MANIFEST.json').read_text())!=render.manifest():
        raise ValueError('AB_BOUNDED_COMPOSITION_SOURCE_CHANGED')
    return sources()


def declared(group, key):
    return (group=='schemas' and key==SCHEMA) or (group=='functions' and (key in ADDITIONS or key in render.originals()))


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items() if declared(g,k)} for g,rows in catalog.items()}


def verify(cur, state):
    if verify_sources()!=state['sources']:
        raise ValueError('BOUNDED_ANALYSIS_SOURCE_CHANGED')
    if own_catalog(_catalog_rows(cur))!=state['catalog']:
        raise ValueError('BOUNDED_ANALYSIS_CATALOG_CHANGED')
    for sig, old in state['original_rows'].items():
        row=_row(cur,sig)
        if row!=state['new_rows'][sig] or row[2:]!=old[2:]:
            raise ValueError('BOUNDED_ANALYSIS_EXISTING_AUTHORITY_CHANGED: '+sig)
    # All unchanged Native dependencies are still exact. The one counted
    # fingerprint replacement is verified above with its existing authority.
    for sig, old in state['dependencies'].items():
        if _row(cur,sig)!=old:
            raise ValueError('BOUNDED_ANALYSIS_DEPENDENCY_CHANGED: '+sig)
    for sig,(volatility,definer) in ADDITIONS.items():
        row=_row(cur,sig)
        if row!=state['new_rows'][sig] or row[2:6]!=['cp7_capture',definer,volatility,['search_path=""','TimeZone=UTC']]:
            raise ValueError('BOUNDED_ANALYSIS_NEW_AUTHORITY_CHANGED: '+sig)
        for role in ('anon','authenticated','service_role','cp7_alert','cp7_capture'):
            allowed=role=='cp7_capture' or (sig==render.PUBLIC and role=='authenticated')
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]!=allowed:
                raise ValueError('BOUNDED_ANALYSIS_EXECUTE_EXPOSED: '+sig+':'+role)
    for role in ('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('BOUNDED_ANALYSIS_SCHEMA_EXPOSED: '+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('BOUNDED_ANALYSIS_PUBLIC_CREATE_LEFT_OPEN')
    return dict(stage='cp7.ab-bounded-finance-stage.v1',private_functions=len(render.PRIVATE),public_rpcs=1,
                new_tables=0,existing_function_replacements=len(render.originals()),Native_ERP_DML=False,
                real_Native_job_rows=True,raw_native_status_overridden=False,
                actual_checked_SAVE2000_qualified=False,full_A_chain_qualified=False,production_go=False)


def install_delta(cur):
    pins=verify_sources()
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
        raise ValueError('BOUNDED_ANALYSIS_ALREADY_INSTALLED')
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('BOUNDED_ANALYSIS_PUBLIC_CREATE_PREEXISTS')
    old=render.originals()
    rows={sig:_row(cur,sig) for sig in old}
    for sig,text in old.items():
        if rows[sig][1]!=_body(text) or rows[sig][2]!='cp7_capture':
            raise ValueError('BOUNDED_ANALYSIS_PREDECESSOR_CHANGED: '+sig+': '+json.dumps(dict(
                expected=sha256(_body(text).encode()).hexdigest(),actual=sha256(rows[sig][1].encode()).hexdigest(),owner=rows[sig][2])))
    dependencies={}
    for sig,pin in source.native_dependencies().items():
        if sig in old:
            continue
        row=_row(cur,sig)
        if sha256(row[1].encode()).hexdigest()!=pin['body_sha256'] or row[2]!=pin['owner']:
            raise ValueError('BOUNDED_ANALYSIS_SOURCE_DEPENDENCY_CHANGED: '+sig+': '+json.dumps(dict(
                expected=pin['body_sha256'],actual=sha256(row[1].encode()).hexdigest(),owner=row[2])))
        dependencies[sig]=row
    # The complete compiler and digest are separate qualified stages, not
    # copies with a relaxed guard. Bind their entire private function sets.
    for module in ('cp7_history_bounded','cp7_history_reference'):
        keys=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.prokind='f' order by 1",(module,)).fetchall()
        if len(keys)!=(2 if module=='cp7_history_bounded' else 1):
            raise ValueError('BOUNDED_ANALYSIS_INPUT_STAGE_MISSING: '+module)
        dependencies.update({sig:_row(cur,sig) for (sig,) in keys})
    cur.execute(render.render()[0],prepare=False)
    state=dict(sources=pins,original_rows=rows,dependencies=dependencies,
               new_rows={sig:_row(cur,sig) for sig in (*old,*ADDITIONS)},catalog=own_catalog(_catalog_rows(cur)))
    sql,new=render.render()
    for sig,text in new.items():
        if state['new_rows'][sig][1]!=_body(text):
            raise ValueError('BOUNDED_ANALYSIS_WRONG_REPLACEMENT: '+sig)
    for sig in ADDITIONS:
        expected=re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if state['new_rows'][sig][1]!=_body(expected):
            raise ValueError('BOUNDED_ANALYSIS_WRONG_ADDITION: '+sig)
    verify(cur,state)
    return state


def admit_catalog(before, after, state):
    if set(before)!=set(after) or len(before)!=22:
        raise ValueError('BOUNDED_ANALYSIS_CATALOG_GROUPS_CHANGED')
    original=set(state['original_rows'])
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:
                continue
            expected=state['catalog'][group].get(key)
            if declared(group,key) and new==expected and (old is None or group=='functions' and key in original):
                continue
            raise ValueError('BOUNDED_ANALYSIS_UNDECLARED_DELTA: '+group+':'+key)


def rollback_preuse(cur,state):
    verify(cur,state)
    # This check precedes every DDL. Used jobs or immutable work receipts need
    # the real composed after-use backup/restore, never a pre-use inverse.
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where reference->>'bounded_request_contract'=%s) "
                   "or exists(select 1 from cp7_schedule_native.commands where result->>'bounded_request_contract'=%s)",
                   (source.REQUEST,source.REQUEST)).fetchone()[0]:
        raise ValueError('BOUNDED_ANALYSIS_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    allowed=set(render.originals())|set(ADDITIONS)
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname<>%s and not(p.oid=any(%s::regprocedure[])) "
        "and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 else false end",
        (SCHEMA,sorted(allowed),SCHEMA+'.')).fetchall()
    if external:
        raise ValueError('BOUNDED_ANALYSIS_UNDECLARED_EXTERNAL_CALLER')
    for row in state['original_rows'].values():
        cur.execute(row[0],prepare=False)
    cur.execute('drop function '+render.PUBLIC+' restrict')
    # SQL functions have real dependency edges; reverse construction order.
    for sig in reversed(tuple(render.PRIVATE)):
        cur.execute('drop function '+SCHEMA+'.'+sig+' restrict')
    cur.execute('drop schema '+SCHEMA+' restrict')
