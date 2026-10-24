"""Opt-in v2 immutable model evaluation; requires the qualified policy parent.

Seven private functions, two public facades, one private schema/table. No old
replacement or default installer mutation. After-use restore is composed.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
import cp7_model_registry_adapter as adapter
import cp7_model_policy_stage as policy
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows

ROOT=Path(__file__).resolve().parent
SCHEMAS=('cp7_model_registry_adapter',)
TABLES=('cp7_model_registry_adapter.runs',)
FK_TRIGGERS={
 f'{parent}:cp7_model_registry_adapter.runs:{constraint}:"RI_FKey_noaction_{event}"():{kind}'
 for parent,constraint in(('cp7_planning.history_runs','runs_history_run_id_fkey'),
                           ('cp7_model_native.registry','runs_registry_id_fkey'))
 for event,kind in(('del',9),('upd',17))}
PUBLIC=('public.erp_cp7_capture_model_evaluation_v2(jsonb,uuid)',
        'public.erp_cp7_read_model_evaluation_v2(uuid)')
FUNCTIONS={'cp7_model_registry_adapter.engine()':('s',False),
 'cp7_model_registry_adapter.bind(jsonb,jsonb,jsonb,text)':('i',False),
 'cp7_model_registry_adapter.dataset(jsonb,uuid)':('s',False),
 'cp7_model_registry_adapter.assess(jsonb,jsonb,jsonb)':('i',False),
 'cp7_model_registry_adapter.current_guard(jsonb,jsonb,jsonb,jsonb,text,timestamp with time zone)':('i',False),
 'cp7_model_registry_adapter.serve(uuid)':('v',False),
 'cp7_model_registry_adapter.capture(jsonb,uuid)':('v',False),
 PUBLIC[0]:('v',True),PUBLIC[1]:('v',True)}
DEPENDENCIES=('cp7_private.access_now()','cp7_private.immutable_run()',
 'cp7_planning.utc(timestamp with time zone)','cp7_planning.serve_history(uuid)',
 'cp7_model_native.query(jsonb)','cp7_model_native.dataset(jsonb,uuid)','cp7_model_native.build(jsonb)',
 'cp7_model_policy.source_at(timestamp with time zone)',
 'cp7_model_activation_gate.policy(jsonb)','cp7_model_activation_gate.decide(jsonb,jsonb,jsonb,jsonb)',
 'cp7_wip.fields(jsonb,text[])','cp7_demand.instant(jsonb)','cp7_demand.day(jsonb)')


def sources():
    return {str(p.relative_to(ROOT.parent)):sha256(p.read_bytes()).hexdigest()
            for folder in(ROOT,adapter.ROOT)for p in sorted(folder.iterdir())
            if p.is_file()and p.suffix in('.py','.sql','.json')}


def verify_sources():
    adapter.verify_sources();policy.verify_sources()
    m=json.loads((ROOT/'MANIFEST.json').read_text())
    if sha256((ROOT/'runtime.sql').read_bytes()).hexdigest()!=m['sql_sha256']:
        raise ValueError('MODEL_V2_SQL_CHANGED')
    if list(FUNCTIONS)!=m['functions']or list(DEPENDENCIES)!=m['dependencies']or sorted(FK_TRIGGERS)!=m['parent_fk_triggers']:
        raise ValueError('MODEL_V2_DECLARATION_CHANGED')
    return sources()


def declared(group,key):
    if group=='schemas':return key in SCHEMAS
    if group=='functions':return key in FUNCTIONS
    if group=='triggers'and key in FK_TRIGGERS:return True
    return group in('relations','columns','constraints','indexes','triggers','types','type_implementation','policies')and key.startswith('cp7_model_registry_adapter.')


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def verify(cur,state):
    catalog=own_catalog(_catalog_rows(cur))
    if verify_sources()!=state['sources']or catalog!=state['catalog']:
        raise ValueError('MODEL_V2_SOURCE_OR_CATALOG_CHANGED')
    if set(catalog['functions'])!=set(FUNCTIONS)or set(catalog['schemas'])!=set(SCHEMAS):
        raise ValueError('MODEL_V2_OBJECTS_CHANGED')
    indexes={'cp7_model_registry_adapter.'+name for name in('runs_pkey','runs_actor_request_id_key')}
    if set(catalog['relations'])!=set(TABLES)|indexes or set(catalog['indexes'])!=indexes:
        raise ValueError('MODEL_V2_TABLES_CHANGED')
    if set(catalog['policies'])!={'cp7_model_registry_adapter.runs:no_access'}or len(catalog['types'])!=2:
        raise ValueError('MODEL_V2_POLICY_OR_TYPES_CHANGED')
    if {k for k in catalog['triggers']if not k.startswith('cp7_model_registry_adapter.')}!=FK_TRIGGERS:
        raise ValueError('MODEL_V2_PARENT_FK_TRIGGERS_CHANGED')
    for sig,expected in state['dependencies'].items():
        if _row(cur,sig)!=expected:raise ValueError('MODEL_V2_DEPENDENCY_CHANGED: '+sig)
    for sig,(volatility,definer)in FUNCTIONS.items():
        row=_row(cur,sig);settings=['search_path=""','TimeZone=UTC']+(['statement_timeout=8s']if sig in PUBLIC else[])
        if row!=state['rows'][sig]or row[2:6]!=['cp7_capture',definer,volatility,settings]:
            raise ValueError('MODEL_V2_FUNCTION_AUTHORITY_CHANGED: '+sig)
        for role in('anon','authenticated','service_role','cp7_alert','cp7_capture'):
            allowed=role=='cp7_capture'or(role=='authenticated'and sig in PUBLIC)
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]!=allowed:
                raise ValueError('MODEL_V2_EXECUTE_CHANGED: '+sig+':'+role)
    if cur.execute("select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid='cp7_model_registry_adapter.runs'::regclass").fetchone()!=('cp7_capture',True):
        raise ValueError('MODEL_V2_TABLE_AUTHORITY_CHANGED')
    for role in('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_table_privilege(%s,'cp7_model_registry_adapter.runs','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,)).fetchone()[0]:
            raise ValueError('MODEL_V2_TABLE_EXPOSED: '+role)
        if cur.execute("select has_schema_privilege(%s,'cp7_model_registry_adapter','USAGE')",(role,)).fetchone()[0]:
            raise ValueError('MODEL_V2_SCHEMA_EXPOSED: '+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('MODEL_V2_PUBLIC_CREATE_OPEN')
    return dict(stage='cp7.model-evaluation-v2-stage.v1',private_functions=7,public_rpcs=2,new_tables=1,
                old_replacements=0,legacy_v1_unchanged=True,Native_ERP_DML=False,
                forecast_applied=False,production_go=False)


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('MODEL_V2_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if old is None and declared(group,key)and new==state['catalog'][group].get(key):continue
            raise ValueError('MODEL_V2_UNDECLARED_DELTA: '+group+':'+key)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('MODEL_V2_PARENT_CHECKER_REQUIRED')
    predecessor_checker(cur)
    if cur.execute("select to_regnamespace('cp7_model_registry_adapter')is not null").fetchone()[0]:
        raise ValueError('MODEL_V2_ALREADY_INSTALLED')
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('MODEL_V2_PUBLIC_CREATE_PREEXISTS')
    before=_catalog_rows(cur);dependencies={sig:_row(cur,sig)for sig in DEPENDENCIES}
    sql=(adapter.ROOT/'adapter.sql').read_text()+'\n'+(ROOT/'runtime.sql').read_text();cur.execute(sql,prepare=False)
    rows={sig:_row(cur,sig)for sig in FUNCTIONS}
    for sig,row in rows.items():
        definition=re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if row[1]!=_body(definition):raise ValueError('MODEL_V2_WRONG_BODY: '+sig)
    state=dict(sources=pins,dependencies=dependencies,rows=rows,catalog=own_catalog(_catalog_rows(cur)))
    admit_catalog(before,_catalog_rows(cur),state);verify(cur,state)
    return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if cur.execute('select exists(select 1 from cp7_model_registry_adapter.runs)').fetchone()[0]:
        raise ValueError('MODEL_V2_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname<>'cp7_model_registry_adapter'and not(p.oid=any(%s::regprocedure[])) "
        "and case when p.prokind in('f','p')then position('cp7_model_registry_adapter.'in pg_get_functiondef(p.oid))>0 else false end",
        (list(FUNCTIONS),)).fetchall()
    if external:raise ValueError('MODEL_V2_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint model_v2_inverse')
    try:
        for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
        cur.execute('drop table cp7_model_registry_adapter.runs restrict')
        cur.execute('drop schema cp7_model_registry_adapter restrict')
    except Exception:
        cur.execute('rollback to savepoint model_v2_inverse');raise
    finally:cur.execute('release savepoint model_v2_inverse')
