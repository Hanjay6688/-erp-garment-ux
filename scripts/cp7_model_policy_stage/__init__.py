"""Opt-in prospective policy metadata; no default installer or model caller.

Seven private functions, two public wrappers, two schemas and two immutable
tables. New registry rows are business use and prohibit a pre-use inverse.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
import cp7_model_activation_gate as gate
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows

ROOT=Path(__file__).resolve().parent
SCHEMAS=('cp7_model_activation_gate','cp7_model_policy')
TABLES=('cp7_model_policy.policies','cp7_model_policy.commands')
PUBLIC=('public.erp_cp7_get_model_activation_policy_v1()',
        'public.erp_cp7_save_model_activation_policy_v1(jsonb,uuid)')
FUNCTIONS={'cp7_model_activation_gate.policy(jsonb)':('i',False),
 'cp7_model_activation_gate.decide(jsonb,jsonb,jsonb,jsonb)':('i',False),
 'cp7_model_policy.access_now(boolean)':('s',False),
 'cp7_model_policy.template()':('s',False),
 'cp7_model_policy.source_at(timestamp with time zone)':('s',False),
 'cp7_model_policy.workspace()':('v',False),
 'cp7_model_policy.apply(jsonb,uuid)':('v',False),
 PUBLIC[0]:('v',True),PUBLIC[1]:('v',True)}
DEPENDENCIES=('cp7_schedule_native.access_now(boolean)','cp7_private.access_now()',
 'cp7_private.immutable_run()','erp.has_permission(text)','cp7_planning.utc(timestamp with time zone)',
 'cp7_wip.fields(jsonb,text[])','cp7_wip.key(jsonb)','cp7_wip.pcs(jsonb)',
 'cp7_demand.instant(jsonb)','cp7_demand.items(jsonb,integer)',
 'cp7_models.promotion(jsonb,jsonb,jsonb)','cp7_model_native.build(jsonb)')


def sources():
    return {str(p.relative_to(ROOT.parent)):sha256(p.read_bytes()).hexdigest()
            for folder in(ROOT,gate.ROOT)for p in sorted(folder.iterdir())
            if p.is_file()and p.suffix in('.py','.sql','.json')}


def verify_sources():
    gate.verify_sources();m=json.loads((ROOT/'MANIFEST.json').read_text())
    if sha256((ROOT/'policy.sql').read_bytes()).hexdigest()!=m['sql_sha256']:
        raise ValueError('MODEL_POLICY_SQL_CHANGED')
    if list(FUNCTIONS)!=m['functions']or list(DEPENDENCIES)!=m['dependencies']:
        raise ValueError('MODEL_POLICY_DECLARATION_CHANGED')
    return sources()


def declared(group,key):
    if group=='schemas':return key in SCHEMAS
    if group=='functions':return key in FUNCTIONS
    return group in('relations','columns','constraints','indexes','triggers','types',
                     'type_implementation','policies')and key.startswith('cp7_model_policy.')


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def registry_rows(cur):
    return cur.execute('select id,registered_at,configuration from cp7_model_native.registry order by id').fetchall()


def verify(cur,state):
    catalog=own_catalog(_catalog_rows(cur))
    if verify_sources()!=state['sources']or catalog!=state['catalog']:
        raise ValueError('MODEL_POLICY_SOURCE_OR_CATALOG_CHANGED')
    if set(catalog['functions'])!=set(FUNCTIONS)or set(catalog['schemas'])!=set(SCHEMAS):
        raise ValueError('MODEL_POLICY_OBJECTS_CHANGED')
    indexes={'cp7_model_policy.'+name for name in('policies_pkey','policies_revision_key','policies_registry_id_key','commands_pkey')}
    if set(catalog['relations'])!=set(TABLES)|indexes or set(catalog['indexes'])!=indexes:
        raise ValueError('MODEL_POLICY_TABLES_CHANGED')
    if set(catalog['policies'])!={t+':no_access'for t in TABLES}or len(catalog['types'])!=4:
        raise ValueError('MODEL_POLICY_POLICY_OR_TYPES_CHANGED')
    for sig,expected in state['dependencies'].items():
        if _row(cur,sig)!=expected:raise ValueError('MODEL_POLICY_NATIVE_DEPENDENCY_CHANGED: '+sig)
    for sig,(volatility,definer)in FUNCTIONS.items():
        row=_row(cur,sig);settings=['search_path=""','TimeZone=UTC']+(['statement_timeout=8s']if sig in PUBLIC else[])
        if row!=state['rows'][sig]or row[2:6]!=['cp7_capture',definer,volatility,settings]:
            raise ValueError('MODEL_POLICY_FUNCTION_AUTHORITY_CHANGED: '+sig)
        for role in('anon','authenticated','service_role','cp7_alert','cp7_capture'):
            allowed=role=='cp7_capture'or(role=='authenticated'and sig in PUBLIC)
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]!=allowed:
                raise ValueError('MODEL_POLICY_EXECUTE_CHANGED: '+sig+':'+role)
    for table in TABLES:
        if cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()!=('cp7_capture',True):
            raise ValueError('MODEL_POLICY_TABLE_AUTHORITY_CHANGED: '+table)
        for role in('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,table)).fetchone()[0]:
                raise ValueError('MODEL_POLICY_TABLE_EXPOSED: '+role)
    for schema in SCHEMAS:
        for role in('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,schema)).fetchone()[0]:
                raise ValueError('MODEL_POLICY_SCHEMA_EXPOSED: '+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('MODEL_POLICY_PUBLIC_CREATE_OPEN')
    return dict(stage='cp7.model-policy-stage.v1',private_functions=7,public_rpcs=2,new_tables=2,
                old_replacements=0,default_policy_created=False,Native_ERP_DML=False,
                forecast_applied=False,production_go=False)


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('MODEL_POLICY_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if old is None and declared(group,key)and new==state['catalog'][group].get(key):continue
            raise ValueError('MODEL_POLICY_UNDECLARED_DELTA: '+group+':'+key)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('MODEL_POLICY_PARENT_CHECKER_REQUIRED')
    predecessor_checker(cur)
    if any(cur.execute('select to_regnamespace(%s)is not null',(s,)).fetchone()[0]for s in SCHEMAS):
        raise ValueError('MODEL_POLICY_ALREADY_INSTALLED')
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('MODEL_POLICY_PUBLIC_CREATE_PREEXISTS')
    before=_catalog_rows(cur);dependencies={sig:_row(cur,sig)for sig in DEPENDENCIES};registry=registry_rows(cur)
    sql=(gate.ROOT/'gate.sql').read_text()+'\n'+(ROOT/'policy.sql').read_text();cur.execute(sql,prepare=False)
    rows={sig:_row(cur,sig)for sig in FUNCTIONS}
    for sig,row in rows.items():
        definition=re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if row[1]!=_body(definition):raise ValueError('MODEL_POLICY_WRONG_BODY: '+sig)
    state=dict(sources=pins,dependencies=dependencies,rows=rows,catalog=own_catalog(_catalog_rows(cur)),registry=registry)
    if registry_rows(cur)!=registry:raise ValueError('MODEL_POLICY_INSTALL_WROTE_REGISTRY')
    admit_catalog(before,_catalog_rows(cur),state);verify(cur,state)
    return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if registry_rows(cur)!=state['registry']or any(cur.execute('select exists(select 1 from '+t+')').fetchone()[0]for t in TABLES):
        raise ValueError('MODEL_POLICY_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
    for schema in SCHEMAS:
        external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
            "where n.nspname<>all(%s) and not(p.oid=any(%s::regprocedure[])) "
            "and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 else false end",
            (list(SCHEMAS),list(FUNCTIONS),schema+'.')).fetchall()
        if external:raise ValueError('MODEL_POLICY_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint model_policy_inverse')
    try:
        for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
        for table in reversed(TABLES):cur.execute('drop table '+table+' restrict')
        for schema in reversed(SCHEMAS):cur.execute('drop schema '+schema+' restrict')
    except Exception:
        cur.execute('rollback to savepoint model_policy_inverse');raise
    finally:cur.execute('release savepoint model_policy_inverse')
