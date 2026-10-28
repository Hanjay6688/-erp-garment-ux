"""Private batched target-source composition; default target callers remain unchanged."""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows
ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_model_target_source_v2'
SCHEMAS = (SCHEMA, 'cp7_model_target_source')
FILES = ('stock.sql','non-stock.sql','physical.sql','source.sql','reorder.sql')
FUNCTIONS = {
 'cp7_model_target_source.engine()':'s',
 'cp7_model_target_source.selection(text[],uuid,timestamp with time zone)':'s',
 'cp7_model_target_source.capture(text[],timestamp with time zone)':'v',
 'cp7_model_target_source.capture_for_reorder(text[],timestamp with time zone)':'v',
 SCHEMA+'.stock_digests(jsonb,timestamp with time zone)':'s',
 SCHEMA+'.non_stock_rows(jsonb,integer)':'i',
 SCHEMA+'.physical_rows(jsonb,integer,jsonb,text)':'i',
 SCHEMA+'.producer()':'s',SCHEMA+'.engine()':'s',
 SCHEMA+'.capture(jsonb,integer)':'v',SCHEMA+'.capture_for_reorder(jsonb,integer)':'v'}


def sql_text():
    return (ROOT.parent/'cp7_model_target_source/source.sql').read_text()+'\n'+'\n'.join((ROOT/f).read_text() for f in FILES)



def verify_sources():
    m = json.loads((ROOT / 'MANIFEST.json').read_text())
    for name,digest in m['source_files_sha256'].items():
        assert sha256((ROOT/name).read_bytes()).hexdigest()==digest, 'MODEL_TARGET_SOURCE_V2_SQL_CHANGED: '+name
    for name, digest in m['dependencies_sha256'].items():
        assert sha256((ROOT.parent / name).read_bytes()).hexdigest() == digest, 'MODEL_TARGET_SOURCE_V2_DEPENDENCY_CHANGED: ' + name
    return sources()


def sources():
    return {str(p.relative_to(ROOT.parent)):sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.iterdir()) if p.is_file() and p.suffix in ('.py','.sql','.json')}


def declared(group,key):
    return (group=='schemas' and key in SCHEMAS) or (group=='functions' and key in FUNCTIONS)


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items() if declared(g,k)} for g,rows in catalog.items()}


def verify(cur,state):
    if verify_sources()!=state['sources'] or own_catalog(_catalog_rows(cur))!=state['catalog']:
        raise ValueError('MODEL_TARGET_SOURCE_V2_CATALOG_OR_SOURCE_CHANGED')
    for signature,row in state['dependencies'].items():
        if _row(cur,signature)!=row:
            raise ValueError('MODEL_TARGET_SOURCE_V2_DEPENDENCY_CHANGED: '+signature)
    sql=sql_text()
    for signature,volatility in FUNCTIONS.items():
        row=_row(cur,signature)
        definition=re.search(r'create function '+re.escape(signature.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if row!=state['rows'][signature] or row[1]!=_body(definition) or row[2:6]!=[
                'cp7_capture',False,volatility,(['search_path=""'] if signature=='cp7_model_target_source.engine()' else ['search_path=""','TimeZone=UTC'])]:
            raise ValueError('MODEL_TARGET_SOURCE_V2_FUNCTION_AUTHORITY_CHANGED: '+signature)
        for role in ('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,signature)).fetchone()[0]:
                raise ValueError('MODEL_TARGET_SOURCE_V2_EXECUTE_EXPOSED: '+signature)
    for schema_name in SCHEMAS:
        if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(schema_name,)).fetchone()!=('cp7_capture',):
            raise ValueError('MODEL_TARGET_SOURCE_V2_OWNER_CHANGED')
        for role in ('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,schema_name)).fetchone()[0]:
                raise ValueError('MODEL_TARGET_SOURCE_V2_SCHEMA_EXPOSED: '+role)
    for group in ('schemas','functions'):
        for key,row in state['catalog'][group].items():
            for grant in row[-1]:
                if grant[0]!='cp7_capture' or grant[1]!='cp7_capture' or grant[3] is not False:
                    raise ValueError('MODEL_TARGET_SOURCE_V2_UNDECLARED_GRANT: '+key)
    return dict(stage='cp7.model-target-source-stage.v2',private_functions=11,new_tables=0,
                public_rpcs=0,existing_replacements=0,Native_ERP_DML=False,
                actual_Native=False,target_caller_integrated=False,production_go=False)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):
        raise ValueError('MODEL_TARGET_SOURCE_V2_COMPOSED_PARENT_REQUIRED')
    predecessor_checker(cur)
    if any(cur.execute('select to_regnamespace(%s)is not null',(name,)).fetchone()[0] for name in SCHEMAS):
        raise ValueError('MODEL_TARGET_SOURCE_V2_ALREADY_INSTALLED')
    before=_catalog_rows(cur)
    signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                           "where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
    dependencies={sig:_row(cur,sig) for (sig,) in signatures}
    cur.execute(sql_text(),prepare=False)
    after=_catalog_rows(cur)
    state=dict(sources=pins,dependencies=dependencies,catalog=own_catalog(after),
               rows={sig:_row(cur,sig) for sig in FUNCTIONS})
    if set(before)!=set(after) or len(before)!=22:
        raise ValueError('MODEL_TARGET_SOURCE_V2_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            a,b=before[group].get(key),after[group].get(key)
            if a==b:continue
            if a is None and b is not None and declared(group,key) and b==state['catalog'][group].get(key):continue
            raise ValueError('MODEL_TARGET_SOURCE_V2_UNDECLARED_DELTA: '+group+':'+key)
    verify(cur,state)
    return state


def rollback_preuse(cur,state):
    # There is no table or retained usage in this source component. Once an
    # immutable runtime depends on it, removal must be part of that runtime's
    # composed restoration. Views and other catalog dependencies use RESTRICT.
    verify(cur,state)
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where not(n.nspname=any(%s)) and case when p.prokind in('f','p')then exists(select 1 from unnest(%s::text[])ns where position(ns||'.' in pg_get_functiondef(p.oid))>0)else false end",
        (list(SCHEMAS),list(SCHEMAS))).fetchall()
    if external:raise ValueError('MODEL_TARGET_SOURCE_V2_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint model_target_source_v2_inverse')
    try:
        for signature in reversed(FUNCTIONS):cur.execute('drop function '+signature+' restrict')
        for name in SCHEMAS:cur.execute('drop schema '+name+' restrict')
    except Exception:
        cur.execute('rollback to savepoint model_target_source_v2_inverse')
        raise
    finally:cur.execute('release savepoint model_target_source_v2_inverse')
