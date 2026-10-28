"""Opt-in private model dataset from immutable single-product history."""
from pathlib import Path
from hashlib import sha256
import json
import re
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows
from . import render

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_model_scoped_dataset'
FUNCTIONS = {SCHEMA+'.'+sig:volatility for sig,volatility in (
    ('native_dataset(jsonb,uuid)','s'), ('engine()','s'), ('dataset(jsonb,uuid)','v'))}


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())
            if p.is_file()and p.suffix in('.py','.sql','.json')}


def verify_sources():
    if (ROOT/'dataset.sql').read_text()!=render.render() or json.loads((ROOT/'MANIFEST.json').read_text())!=render.manifest():
        raise ValueError('MODEL_SCOPED_DATASET_SOURCE_CHANGED')
    return sources()


def declared(group,key):
    return (group=='schemas' and key==SCHEMA) or (group=='functions' and key in FUNCTIONS)


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items() if declared(g,k)} for g,rows in catalog.items()}


def verify(cur,state):
    if verify_sources()!=state['sources'] or own_catalog(_catalog_rows(cur))!=state['catalog']:
        raise ValueError('MODEL_SCOPED_DATASET_CATALOG_OR_SOURCE_CHANGED')
    for signature,row in state['dependencies'].items():
        if _row(cur,signature)!=row:
            raise ValueError('MODEL_SCOPED_DATASET_DEPENDENCY_CHANGED: '+signature)
    sql=(ROOT/'dataset.sql').read_text()
    for signature,volatility in FUNCTIONS.items():
        row=_row(cur,signature)
        definition=re.search(r'create function '+re.escape(signature.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if row!=state['rows'][signature] or row[1]!=_body(definition) or row[2:6]!=[
                'cp7_capture',False,volatility,['search_path=""','TimeZone=UTC']]:
            raise ValueError('MODEL_SCOPED_DATASET_FUNCTION_AUTHORITY_CHANGED: '+signature)
        for role in ('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,signature)).fetchone()[0]:
                raise ValueError('MODEL_SCOPED_DATASET_EXECUTE_EXPOSED: '+signature)
    if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()!=('cp7_capture',):
        raise ValueError('MODEL_SCOPED_DATASET_OWNER_CHANGED')
    for role in ('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('MODEL_SCOPED_DATASET_SCHEMA_EXPOSED: '+role)
    for group in ('schemas','functions'):
        for key,row in state['catalog'][group].items():
            for grant in row[-1]:
                if grant[0]!='cp7_capture' or grant[1]!='cp7_capture' or grant[3] is not False:
                    raise ValueError('MODEL_SCOPED_DATASET_UNDECLARED_GRANT: '+key)
    return dict(stage='cp7.model-scoped-dataset-stage.v1',private_functions=3,new_tables=0,
                public_rpcs=0,existing_replacements=0,Native_ERP_DML=False,
                model_evaluation_runtime_qualified=False,model_caller_integrated=False,production_go=False)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):
        raise ValueError('MODEL_SCOPED_DATASET_COMPOSED_PARENT_REQUIRED')
    predecessor_checker(cur)
    for sig in ('cp7_model_history_runtime.serve(uuid)','cp7_model_registry_adapter.bind(jsonb,jsonb,jsonb,text)','cp7_model_registry_adapter.assess(jsonb,jsonb,jsonb)'):
        if cur.execute('select to_regprocedure(%s)is not null',(sig,)).fetchone()[0] is not True:
            raise ValueError('MODEL_SCOPED_DATASET_COMPOSED_PARENT_MISSING: '+sig)
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
        raise ValueError('MODEL_SCOPED_DATASET_ALREADY_INSTALLED')
    before=_catalog_rows(cur)
    signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                           "where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
    dependencies={sig:_row(cur,sig) for (sig,) in signatures}
    cur.execute((ROOT/'dataset.sql').read_text(),prepare=False)
    after=_catalog_rows(cur)
    state=dict(sources=pins,dependencies=dependencies,catalog=own_catalog(after),
               rows={sig:_row(cur,sig) for sig in FUNCTIONS})
    if set(before)!=set(after) or len(before)!=22:
        raise ValueError('MODEL_SCOPED_DATASET_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            a,b=before[group].get(key),after[group].get(key)
            if a==b:continue
            if a is None and b is not None and declared(group,key) and b==state['catalog'][group].get(key):continue
            raise ValueError('MODEL_SCOPED_DATASET_UNDECLARED_DELTA: '+group+':'+key)
    verify(cur,state)
    return state


def rollback_preuse(cur,state):
    # There is no table or retained usage in this source component. Once an
    # immutable runtime depends on it, removal must be part of that runtime's
    # composed restoration. Views and other catalog dependencies use RESTRICT.
    verify(cur,state)
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname<>%s and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 else false end",
        (SCHEMA,SCHEMA+'.')).fetchall()
    if external:raise ValueError('MODEL_SCOPED_DATASET_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint model_scoped_dataset_inverse')
    try:
        for signature in reversed(FUNCTIONS):cur.execute('drop function '+signature+' restrict')
        cur.execute('drop schema '+SCHEMA+' restrict')
    except Exception:
        cur.execute('rollback to savepoint model_scoped_dataset_inverse')
        raise
    finally:cur.execute('release savepoint model_scoped_dataset_inverse')
