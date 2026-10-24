"""Opt-in immutable confirmation metadata. A owns default/after-use admission.

No connection, commit, ERP DML, forecast hook or old function replacement.
The strict predecessor callback must include the advisory reader stage.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_product_analog_choice'
TABLES=(SCHEMA+'.choices',SCHEMA+'.commands')
PUBLIC=('public.erp_cp7_get_product_analog_choices_v1(text[])',
        'public.erp_cp7_save_product_analog_choice_v1(jsonb,uuid)')
FUNCTIONS={SCHEMA+'.material(jsonb,text,text)':('i',False),
           SCHEMA+'.source_at(text[],timestamp with time zone)':('s',False),
           SCHEMA+'.workspace(text[])':('v',False),
           SCHEMA+'.apply(jsonb,uuid)':('v',False),
           PUBLIC[0]:('v',True),PUBLIC[1]:('v',True)}
DEPENDENCIES=('cp7_product_analog_stage.candidates(jsonb,text,integer,integer)',
              'cp7_product_analog_stage.read_candidates(uuid,text,integer,integer,text)',
              'cp7_bounded_analysis_stage.require_inputs(jsonb,jsonb)',
              'cp7_bounded_analysis_stage.source_for(jsonb,jsonb)',
              'cp7_analysis_native.fingerprint(jsonb)',
              'cp7_schedule_native.access_now(boolean)','cp7_private.access_now()',
              'cp7_private.immutable_run()','cp7_demand.decimal(jsonb)',
              'cp7_wip.fields(jsonb,text[])','cp7_wip.key(jsonb)','cp7_wip.pcs(jsonb)')


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())
            if p.is_file()and p.suffix in('.py','.sql','.json')}


def verify_sources():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    if sha256((ROOT/'choice.sql').read_bytes()).hexdigest()!=manifest['sql_sha256']:
        raise ValueError('ANALOG_CHOICE_SQL_CHANGED')
    if list(FUNCTIONS)!=manifest['functions']or list(DEPENDENCIES)!=manifest['dependencies']:
        raise ValueError('ANALOG_CHOICE_DECLARATION_CHANGED')
    return sources()


def declared(group,key):
    if group=='schemas':return key==SCHEMA
    if group=='functions':return key in FUNCTIONS
    return group in('relations','columns','constraints','indexes','triggers','types',
                     'type_implementation','policies')and key.startswith(SCHEMA+'.')


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def verify(cur,state):
    catalog=own_catalog(_catalog_rows(cur))
    if verify_sources()!=state['sources']or catalog!=state['catalog']:
        raise ValueError('ANALOG_CHOICE_SOURCE_OR_CATALOG_CHANGED')
    if set(catalog['functions'])!=set(FUNCTIONS)or set(catalog['schemas'])!={SCHEMA}:
        raise ValueError('ANALOG_CHOICE_OBJECTS_CHANGED')
    indexes={SCHEMA+'.'+name for name in('choices_pkey','choices_target_key_revision_key','commands_pkey')}
    if set(catalog['relations'])!=set(TABLES)|indexes or set(catalog['indexes'])!=indexes:
        raise ValueError('ANALOG_CHOICE_TABLES_CHANGED')
    if set(catalog['policies'])!={t+':no_access'for t in TABLES}or len(catalog['types'])!=4:
        raise ValueError('ANALOG_CHOICE_POLICY_OR_TYPES_CHANGED')
    for sig,expected in state['dependencies'].items():
        if _row(cur,sig)!=expected:raise ValueError('ANALOG_CHOICE_NATIVE_DEPENDENCY_CHANGED: '+sig)
    for sig,(volatility,definer)in FUNCTIONS.items():
        row=_row(cur,sig)
        if row!=state['rows'][sig]or row[2:6]!=['cp7_capture',definer,volatility,['search_path=""','TimeZone=UTC']]:
            raise ValueError('ANALOG_CHOICE_FUNCTION_AUTHORITY_CHANGED: '+sig)
        for role in('anon','authenticated','service_role','cp7_alert','cp7_capture'):
            allowed=role=='cp7_capture'or(role=='authenticated'and sig in PUBLIC)
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]!=allowed:
                raise ValueError('ANALOG_CHOICE_EXECUTE_CHANGED: '+sig+':'+role)
    for table in TABLES:
        if cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()!=('cp7_capture',True):
            raise ValueError('ANALOG_CHOICE_TABLE_AUTHORITY_CHANGED: '+table)
        for role in('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,table)).fetchone()[0]:
                raise ValueError('ANALOG_CHOICE_TABLE_EXPOSED: '+role)
    for role in('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('ANALOG_CHOICE_SCHEMA_EXPOSED: '+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('ANALOG_CHOICE_PUBLIC_CREATE_OPEN')
    return dict(stage='cp7.product-analog-choice-stage.v1',private_functions=4,public_rpcs=2,
                new_tables=2,old_replacements=0,Native_ERP_DML=False,
                forecast_applied=False,production_go=False)


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('ANALOG_CHOICE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if old is None and declared(group,key)and new==state['catalog'][group].get(key):continue
            raise ValueError('ANALOG_CHOICE_UNDECLARED_DELTA: '+group+':'+key)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('ANALOG_CHOICE_PARENT_CHECKER_REQUIRED')
    predecessor_checker(cur)
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
        raise ValueError('ANALOG_CHOICE_ALREADY_INSTALLED')
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('ANALOG_CHOICE_PUBLIC_CREATE_PREEXISTS')
    before=_catalog_rows(cur);dependencies={sig:_row(cur,sig)for sig in DEPENDENCIES}
    sql=(ROOT/'choice.sql').read_text();cur.execute(sql,prepare=False)
    rows={sig:_row(cur,sig)for sig in FUNCTIONS}
    for sig,row in rows.items():
        definition=re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if row[1]!=_body(definition):raise ValueError('ANALOG_CHOICE_WRONG_BODY: '+sig)
    state=dict(sources=pins,dependencies=dependencies,rows=rows,catalog=own_catalog(_catalog_rows(cur)))
    admit_catalog(before,_catalog_rows(cur),state);verify(cur,state)
    return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if any(cur.execute('select exists(select 1 from '+table+')').fetchone()[0]for table in TABLES):
        raise ValueError('ANALOG_CHOICE_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname<>%s and not(p.oid=any(%s::regprocedure[])) "
        "and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 else false end",
        (SCHEMA,list(FUNCTIONS),SCHEMA+'.')).fetchall()
    if external:raise ValueError('ANALOG_CHOICE_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    # RESTRICT also catches catalog-bound callers/views/FKs. A failed inverse
    # restores its own partial DDL before returning control to the installer.
    cur.execute('savepoint analog_choice_inverse')
    try:
        for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
        for table in reversed(TABLES):cur.execute('drop table '+table+' restrict')
        cur.execute('drop schema '+SCHEMA+' restrict')
    except Exception:
        cur.execute('rollback to savepoint analog_choice_inverse')
        raise
    finally:cur.execute('release savepoint analog_choice_inverse')
