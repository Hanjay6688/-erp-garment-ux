"""Opt-in exact model-target overlay; no default installer or ERP DML.

Requires analog provenance + reader correction + immutable model-v2 parents.
After-use restoration is composed; pre-use inverse is savepoint-atomic.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_model_target_source as source
import cp7_model_target_projection as projection
import cp7_model_target_consumer as consumer
import cp7_product_analog_consumer_stage as analog
from . import render

ROOT=Path(__file__).resolve().parent
SCHEMAS=('cp7_model_target_source','cp7_model_target_projection','cp7_model_target_consumer')
FUNCTIONS={
 'cp7_model_target_source.engine()':('s',False),
 'cp7_model_target_source.selection(text[],uuid,timestamp with time zone)':('s',True),
 'cp7_model_target_source.capture(text[],timestamp with time zone)':('v',True),
 'cp7_model_target_source.capture_for_reorder(text[],timestamp with time zone)':('v',True),
 'cp7_model_target_projection.sum_window(jsonb,numeric,numeric)':('i',False),
 'cp7_model_target_projection.project(jsonb,jsonb,date)':('i',True),
 'cp7_model_target_consumer.rows(jsonb,jsonb,jsonb,text,jsonb)':('i',True),
 'cp7_model_target_consumer.timeline(jsonb)':('i',False)}


def sources():
    return {str(p.relative_to(ROOT.parent)):sha256(p.read_bytes()).hexdigest()
            for folder in(ROOT,source.ROOT,projection.ROOT,consumer.ROOT)
            for p in sorted(folder.iterdir())if p.is_file()and p.suffix in('.py','.sql','.json')}


def verify_sources():
    if (ROOT/'hooks.sql').read_text()!=render.render()or json.loads((ROOT/'MANIFEST.json').read_text())!=render.manifest():
        raise ValueError('MODEL_TARGET_HOOK_SOURCE_CHANGED')
    return sources()


def declared(group,key):
    return(group=='schemas'and key in SCHEMAS)or(group=='functions'and key in set(FUNCTIONS)|set(render.originals()))


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def usage_state(cur):
    state=analog.usage_state(cur)
    names=cur.execute("select quote_ident(n.nspname)||'.'||quote_ident(c.relname)from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=any(%s)and c.relkind='r'order by 1",
       (['cp7_model_registry_adapter','cp7_model_policy','cp7_model_native','cp7_planning'],)).fetchall()
    for(name,)in names:
        state[name]=cur.execute("select count(*),md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]')::text)from "+name+' x').fetchone()
    return state


def verify(cur,state):
    if verify_sources()!=state['sources']or own_catalog(_catalog_rows(cur))!=state['catalog']:
        raise ValueError('MODEL_TARGET_SOURCE_OR_CATALOG_CHANGED')
    for sig,row in state['new_rows'].items():
        if _row(cur,sig)!=row:raise ValueError('MODEL_TARGET_FUNCTION_CHANGED: '+sig)
        if sig in state['old_rows']and row[2:]!=state['old_rows'][sig][2:]:
            raise ValueError('MODEL_TARGET_EXISTING_AUTHORITY_CHANGED: '+sig)
    for sig,row in state['dependencies'].items():
        if _row(cur,sig)!=row:raise ValueError('MODEL_TARGET_DEPENDENCY_CHANGED: '+sig)
    for sig,(volatility,utc)in FUNCTIONS.items():
        settings=['search_path=""']+(['TimeZone=UTC']if utc else[])
        if state['new_rows'][sig][2:6]!=['cp7_capture',False,volatility,settings]:
            raise ValueError('MODEL_TARGET_PRIVATE_AUTHORITY_CHANGED: '+sig)
        for role in('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('MODEL_TARGET_PRIVATE_EXECUTE_EXPOSED: '+sig)
    for schema in SCHEMAS:
        if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(schema,)).fetchone()!=('cp7_capture',):
            raise ValueError('MODEL_TARGET_SCHEMA_OWNER_CHANGED')
        for role in('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,schema)).fetchone()[0]:
                raise ValueError('MODEL_TARGET_SCHEMA_EXPOSED: '+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('MODEL_TARGET_PUBLIC_CREATE_OPEN')
    return dict(stage='cp7.model-target-consumer-stage.v1',new_private_functions=8,
      existing_replacements=20,new_public_rpcs=0,new_tables=0,Native_ERP_DML=False,
      actual_Auth_HTTP_credit=False,full_OW11_acceptance=False,production_go=False)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('MODEL_TARGET_COMPOSED_PARENT_REQUIRED')
    predecessor_checker(cur)
    if cur.execute('select exists(select 1 from pg_namespace where nspname=any(%s))',(list(SCHEMAS),)).fetchone()[0]:
        raise ValueError('MODEL_TARGET_ALREADY_INSTALLED')
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')").fetchone()[0]:
        raise ValueError('MODEL_TARGET_QUIET_INSTALL_REQUIRED')
    before=_catalog_rows(cur);originals=render.originals();old={sig:_row(cur,sig)for sig in originals}
    for sig,definition in originals.items():
        if old[sig][1]!=_body(definition)or old[sig][2]!='cp7_capture':raise ValueError('MODEL_TARGET_PREDECESSOR_CHANGED: '+sig)
    signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
    dependencies={sig:_row(cur,sig)for(sig,)in signatures if sig not in old}
    used=usage_state(cur)
    sql='\n'.join(p.read_text()for p in(source.ROOT/'source.sql',projection.ROOT/'projection.sql',consumer.ROOT/'consumer.sql',consumer.ROOT/'timeline.sql'))
    cur.execute(sql,prepare=False);cur.execute((ROOT/'hooks.sql').read_text(),prepare=False)
    new={sig:_row(cur,sig)for sig in(*old,*FUNCTIONS)}
    definitions=render.replacements()
    for sig in FUNCTIONS:
        definitions[sig]=re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
    for sig,definition in definitions.items():
        if new[sig][1]!=_body(definition):raise ValueError('MODEL_TARGET_WRONG_BODY: '+sig)
    after=_catalog_rows(cur);catalog=own_catalog(after)
    if set(before)!=set(after)or len(before)!=22:raise ValueError('MODEL_TARGET_CATALOG_GROUPS')
    for group in before:
        for key in set(before[group])|set(after[group]):
            a,b=before[group].get(key),after[group].get(key)
            if a==b:continue
            if declared(group,key)and b==catalog[group].get(key)and(a is None or group=='functions'and key in old):continue
            raise ValueError('MODEL_TARGET_UNDECLARED_DELTA: '+group+':'+key)
    state=dict(sources=pins,old_rows=old,new_rows=new,dependencies=dependencies,usage_before=used,catalog=catalog)
    verify(cur,state);return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if usage_state(cur)!=state['usage_before']:raise ValueError('MODEL_TARGET_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p where not(p.oid=any(%s::regprocedure[]))and case when p.prokind in('f','p')then "
      "position('cp7_model_target_source.'in pg_get_functiondef(p.oid))>0 or position('cp7_model_target_projection.'in pg_get_functiondef(p.oid))>0 or position('cp7_model_target_consumer.'in pg_get_functiondef(p.oid))>0 else false end",(list(state['new_rows']),)).fetchall()
    if external:raise ValueError('MODEL_TARGET_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint model_target_inverse')
    try:
        for row in state['old_rows'].values():cur.execute(row[0],prepare=False)
        for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
        for schema in reversed(SCHEMAS):cur.execute('drop schema '+schema+' restrict')
    except Exception:
        cur.execute('rollback to savepoint model_target_inverse');raise
    finally:cur.execute('release savepoint model_target_inverse')
