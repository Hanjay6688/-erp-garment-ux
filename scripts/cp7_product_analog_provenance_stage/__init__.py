"""Opt-in provenance overlay. No default install, connection, commit or ERP DML."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_product_analog_consumer_stage as consumer
from . import render

ROOT=Path(__file__).resolve().parent
FUNCTION='cp7_product_analog_consumer.provenance(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)'


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())if p.is_file()and p.suffix in('.sql','.py','.json')}


def verify_sources():
    consumer.verify_sources()
    if (ROOT/'hooks.sql').read_text()!=render.render()or json.loads((ROOT/'MANIFEST.json').read_text())!=render.manifest():
        raise ValueError('ANALOG_PROVENANCE_SOURCE_CHANGED')
    return sources()


def own_catalog(catalog):
    allowed=set(render.originals())|{FUNCTION}
    return {g:{k:v for k,v in rows.items()if g=='functions'and k in allowed}for g,rows in catalog.items()}


def verify(cur,state):
    if verify_sources()!=state['sources']or own_catalog(_catalog_rows(cur))!=state['catalog']:
        raise ValueError('ANALOG_PROVENANCE_SOURCE_OR_CATALOG_CHANGED')
    for sig,row in state['new_rows'].items():
        if _row(cur,sig)!=row:raise ValueError('ANALOG_PROVENANCE_FUNCTION_CHANGED: '+sig)
        if sig in state['old_rows']and row[2:]!=state['old_rows'][sig][2:]:
            raise ValueError('ANALOG_PROVENANCE_AUTHORITY_CHANGED: '+sig)
    for sig,row in state['dependencies'].items():
        if _row(cur,sig)!=row:raise ValueError('ANALOG_PROVENANCE_DEPENDENCY_CHANGED: '+sig)
    if state['new_rows'][FUNCTION][2:6]!=['cp7_capture',False,'i',['search_path=""','TimeZone=UTC']]:
        raise ValueError('ANALOG_PROVENANCE_HELPER_AUTHORITY')
    for role in('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,FUNCTION)).fetchone()[0]:
            raise ValueError('ANALOG_PROVENANCE_HELPER_EXPOSED')
    return dict(stage='cp7.product-analog-provenance-stage.v1',new_private_functions=1,
      existing_replacements=4,new_public_rpcs=0,new_tables=0,Native_ERP_DML=False,
      actual_Auth_HTTP_credit=False,full_OW11_acceptance=False,production_go=False)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('ANALOG_PROVENANCE_PREDECESSOR_REQUIRED')
    predecessor_checker(cur)
    if cur.execute('select to_regprocedure(%s)is not null',(FUNCTION,)).fetchone()[0]:raise ValueError('ANALOG_PROVENANCE_ALREADY_INSTALLED')
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')").fetchone()[0]:raise ValueError('ANALOG_PROVENANCE_QUIET_INSTALL_REQUIRED')
    before=_catalog_rows(cur);originals=render.originals();old={sig:_row(cur,sig)for sig in originals}
    for sig,definition in originals.items():
        if old[sig][1]!=_body(definition)or old[sig][2]!='cp7_capture':raise ValueError('ANALOG_PROVENANCE_PREDECESSOR_CHANGED: '+sig)
    signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
    dependencies={sig:_row(cur,sig)for(sig,)in signatures if sig not in old}
    used=consumer.usage_state(cur)
    helper=(ROOT/'provenance.sql').read_text();cur.execute(helper,prepare=False);cur.execute((ROOT/'hooks.sql').read_text(),prepare=False)
    new={sig:_row(cur,sig)for sig in(*old,FUNCTION)}
    for sig,definition in render.replacements().items():
        if new[sig][1]!=_body(definition):raise ValueError('ANALOG_PROVENANCE_BODY_CHANGED: '+sig)
    if new[FUNCTION][1]!=_body(helper[:helper.index('end $$;')+7]):raise ValueError('ANALOG_PROVENANCE_HELPER_BODY_CHANGED')
    after=_catalog_rows(cur);catalog=own_catalog(after)
    if set(before)!=set(after)or len(before)!=22:raise ValueError('ANALOG_PROVENANCE_CATALOG_GROUPS')
    for group in before:
        for key in set(before[group])|set(after[group]):
            a,b=before[group].get(key),after[group].get(key)
            if a==b:continue
            if group=='functions'and key in new and b==catalog[group].get(key)and(key in old or a is None):continue
            raise ValueError('ANALOG_PROVENANCE_UNDECLARED_DELTA: '+group+':'+key)
    state=dict(sources=pins,old_rows=old,new_rows=new,dependencies=dependencies,usage_before=used,catalog=catalog)
    verify(cur,state);return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if consumer.usage_state(cur)!=state['usage_before']:raise ValueError('ANALOG_PROVENANCE_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p where not(p.oid=any(%s::regprocedure[]))and case when p.prokind in('f','p')then position('cp7_product_analog_consumer.provenance('in pg_get_functiondef(p.oid))>0 else false end",([*state['old_rows'],FUNCTION],)).fetchall()
    if external:raise ValueError('ANALOG_PROVENANCE_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint analog_provenance_inverse')
    try:
        for row in state['old_rows'].values():cur.execute(row[0],prepare=False)
        cur.execute('drop function '+FUNCTION+' restrict')
    except Exception:
        cur.execute('rollback to savepoint analog_provenance_inverse');raise
    finally:cur.execute('release savepoint analog_provenance_inverse')
