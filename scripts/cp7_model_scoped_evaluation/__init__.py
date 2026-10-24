"""Opt-in immutable scoped-model evaluation v3; old models/default callers unchanged."""
from pathlib import Path
from hashlib import sha256
import json
import re
import cp7_model_scoped_dataset as scope
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_model_scoped_evaluation'
TABLE=SCHEMA+'.runs'
FK_TRIGGERS={
 f'{parent}:cp7_model_scoped_evaluation.runs:{constraint}:"RI_FKey_noaction_{event}"():{kind}'
 for parent,constraint in(('cp7_model_history_runtime.runs','runs_history_run_id_fkey'),
                           ('cp7_model_native.registry','runs_registry_id_fkey'))
 for event,kind in(('del',9),('upd',17))}
PUBLIC=('public.erp_cp7_capture_model_evaluation_v3(jsonb,uuid)','public.erp_cp7_read_model_evaluation_v3(uuid)')
FUNCTIONS={SCHEMA+'.engine()':('s',False),SCHEMA+'.dataset(jsonb,uuid)':('v',False),
 SCHEMA+'.serve(uuid)':('v',False),SCHEMA+'.capture(jsonb,uuid)':('v',False),
 PUBLIC[0]:('v',True),PUBLIC[1]:('v',True)}
DEPENDENCIES=(*scope.FUNCTIONS,'cp7_model_history_runtime.serve(uuid)',
 'cp7_model_registry_adapter.current_guard(jsonb,jsonb,jsonb,jsonb,text,timestamp with time zone)',
 'cp7_model_registry_adapter.assess(jsonb,jsonb,jsonb)','cp7_model_policy.source_at(timestamp with time zone)',
 'cp7_model_native.query(jsonb)','cp7_private.access_now()','cp7_private.immutable_run()',
 'cp7_planning.utc(timestamp with time zone)')


def sources():
    return {str(p.relative_to(ROOT.parent)):sha256(p.read_bytes()).hexdigest()
            for folder in(ROOT,scope.ROOT)for p in sorted(folder.iterdir())
            if p.is_file()and p.suffix in('.py','.sql','.json')}


def manifest():
    return dict(contract='cp7.model-scoped-evaluation-stage.v1',private_functions=4,new_public_rpcs=2,new_tables=1,
      existing_replacements=0,sql_sha256=sha256((ROOT/'runtime.sql').read_bytes()).hexdigest(),
      functions=list(FUNCTIONS),dependencies=list(DEPENDENCIES),parent_fk_triggers=sorted(FK_TRIGGERS),requires_scoped_dataset_and_model_parent_checker=True,
      old_global_history_and_models_unchanged=True,default_installation=False,model_caller_integrated=False,production_go=False)


def verify_sources():
    scope.verify_sources()
    if json.loads((ROOT/'MANIFEST.json').read_text())!=manifest():
        raise ValueError('MODEL_SCOPED_EVALUATION_SOURCE_CHANGED')
    return sources()


def declared(group,key):
    if group=='schemas':return key==SCHEMA
    if group=='functions':return key in FUNCTIONS
    if group=='triggers'and key in FK_TRIGGERS:return True
    return group in('relations','columns','constraints','indexes','triggers','types','type_implementation','policies')and key.startswith(SCHEMA+'.')


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def verify(cur,state):
    catalog=own_catalog(_catalog_rows(cur))
    if verify_sources()!=state['sources']or catalog!=state['catalog']:
        raise ValueError('MODEL_SCOPED_EVALUATION_SOURCE_OR_CATALOG_CHANGED')
    if set(catalog['functions'])!=set(FUNCTIONS)or set(catalog['schemas'])!={SCHEMA}:
        raise ValueError('MODEL_SCOPED_EVALUATION_OBJECTS_CHANGED')
    indexes={SCHEMA+'.'+name for name in('runs_pkey','runs_actor_request_id_key')}
    if set(catalog['relations'])!={TABLE}|indexes or set(catalog['indexes'])!=indexes:
        raise ValueError('MODEL_SCOPED_EVALUATION_TABLES_CHANGED')
    if set(catalog['policies'])!={TABLE+':no_access'}or len(catalog['types'])!=2:
        raise ValueError('MODEL_SCOPED_EVALUATION_POLICY_OR_TYPES_CHANGED')
    if {k for k in catalog['triggers']if not k.startswith(SCHEMA+'.')}!=FK_TRIGGERS:
        raise ValueError('MODEL_SCOPED_EVALUATION_PARENT_FK_TRIGGERS_CHANGED')
    for sig,row in state['dependencies'].items():
        if _row(cur,sig)!=row:raise ValueError('MODEL_SCOPED_EVALUATION_DEPENDENCY_CHANGED: '+sig)
    for sig,(volatility,definer)in FUNCTIONS.items():
        row=_row(cur,sig);settings=['search_path=""','TimeZone=UTC']+(['statement_timeout=8s']if sig in PUBLIC else[])
        if row!=state['rows'][sig]or row[2:6]!=['cp7_capture',definer,volatility,settings]:
            raise ValueError('MODEL_SCOPED_EVALUATION_FUNCTION_AUTHORITY_CHANGED: '+sig)
        for role in('anon','authenticated','service_role','cp7_alert','cp7_capture'):
            allowed=role=='cp7_capture'or(role=='authenticated'and sig in PUBLIC)
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]!=allowed:
                raise ValueError('MODEL_SCOPED_EVALUATION_EXECUTE_CHANGED: '+sig+':'+role)
    if cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(TABLE,)).fetchone()!=('cp7_capture',True):
        raise ValueError('MODEL_SCOPED_EVALUATION_TABLE_AUTHORITY_CHANGED')
    if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()!=('cp7_capture',):
        raise ValueError('MODEL_SCOPED_EVALUATION_SCHEMA_OWNER_CHANGED')
    for role in('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,TABLE)).fetchone()[0]:
            raise ValueError('MODEL_SCOPED_EVALUATION_TABLE_EXPOSED: '+role)
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('MODEL_SCOPED_EVALUATION_SCHEMA_EXPOSED: '+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('MODEL_SCOPED_EVALUATION_PUBLIC_CREATE_OPEN')
    return dict(stage='cp7.model-scoped-evaluation-stage.v1',private_functions=4,public_rpcs=2,new_tables=1,
                existing_replacements=0,old_global_history_and_models_unchanged=True,
                Native_ERP_DML=False,model_caller_integrated=False,production_go=False)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('MODEL_SCOPED_EVALUATION_PARENT_CHECKER_REQUIRED')
    predecessor_checker(cur)
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
        raise ValueError('MODEL_SCOPED_EVALUATION_ALREADY_INSTALLED')
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('MODEL_SCOPED_EVALUATION_PUBLIC_CREATE_PREEXISTS')
    for sig in DEPENDENCIES:
        if cur.execute('select to_regprocedure(%s)is not null',(sig,)).fetchone()[0]is not True:
            raise ValueError('MODEL_SCOPED_EVALUATION_PARENT_MISSING: '+sig)
    before=_catalog_rows(cur)
    signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                           "where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
    dependencies={sig:_row(cur,sig)for(sig,)in signatures}
    sql=(ROOT/'runtime.sql').read_text();cur.execute(sql,prepare=False)
    rows={sig:_row(cur,sig)for sig in FUNCTIONS}
    for sig,row in rows.items():
        definition=re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if row[1]!=_body(definition):raise ValueError('MODEL_SCOPED_EVALUATION_WRONG_BODY: '+sig)
    after=_catalog_rows(cur);state=dict(sources=pins,dependencies=dependencies,rows=rows,catalog=own_catalog(after))
    if set(before)!=set(after)or len(before)!=22:raise ValueError('MODEL_SCOPED_EVALUATION_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if old is None and declared(group,key)and new==state['catalog'][group].get(key):continue
            raise ValueError('MODEL_SCOPED_EVALUATION_UNDECLARED_DELTA: '+group+':'+key)
    verify(cur,state)
    return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if cur.execute('select exists(select 1 from '+TABLE+')').fetchone()[0]:
        raise ValueError('MODEL_SCOPED_EVALUATION_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname<>%s and not(p.oid=any(%s::regprocedure[]))and case when p.prokind in('f','p') "
        "then position(%s in pg_get_functiondef(p.oid))>0 else false end",(SCHEMA,list(FUNCTIONS),SCHEMA+'.')).fetchall()
    if external:raise ValueError('MODEL_SCOPED_EVALUATION_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint model_scoped_evaluation_inverse')
    try:
        for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
        cur.execute('drop table '+TABLE+' restrict');cur.execute('drop schema '+SCHEMA+' restrict')
    except Exception:
        cur.execute('rollback to savepoint model_scoped_evaluation_inverse');raise
    finally:cur.execute('release savepoint model_scoped_evaluation_inverse')
