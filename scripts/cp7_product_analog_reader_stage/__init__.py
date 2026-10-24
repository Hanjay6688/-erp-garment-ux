"""Opt-in advisory reader delta; A owns default/whole-chain admission.

No connection, commit, selection, table, existing replacement or ERP write.
A strict parent checker must admit the actual twelve-stage predecessor first.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
import cp7_product_analog_stage as kernel
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_product_analog_stage'
PUBLIC='public.erp_cp7_read_product_analog_candidates_v1(uuid,text,integer,integer,text)'
FUNCTIONS={SCHEMA+'.candidates(jsonb,text,integer,integer)':('i',False),
           SCHEMA+'.read_candidates(uuid,text,integer,integer,text)':('v',False),PUBLIC:('v',True)}
DEPENDENCIES=('cp7_analysis_stage.job_of(uuid,uuid)','cp7_analysis_stage.page_set(uuid)',
              'cp7_analysis_stage.require_kept(uuid)','cp7_schedule_native.access_now(boolean)',
              'cp7_private.access_now()','cp7_bounded_analysis_stage.producer_hash()',
              'cp7_bounded_analysis_stage.require_inputs(jsonb,jsonb)','cp7_wip.key(jsonb)',
              'cp7_wip.pcs(jsonb)')


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())
            if p.is_file()and p.suffix in('.py','.sql','.json')}


def verify_sources():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    if manifest['kernel_manifest']!=kernel.verify_sources():
        raise ValueError('PRODUCT_ANALOG_READER_KERNEL_CHANGED')
    if sha256((ROOT/'reader.sql').read_bytes()).hexdigest()!=manifest['reader_sql_sha256']:
        raise ValueError('PRODUCT_ANALOG_READER_SQL_CHANGED')
    if list(FUNCTIONS)!=manifest['functions']or list(DEPENDENCIES)!=manifest['dependencies']:
        raise ValueError('PRODUCT_ANALOG_READER_DECLARATION_CHANGED')
    return sources()


def declared(group,key):
    return(group=='schemas'and key==SCHEMA)or(group=='functions'and key in FUNCTIONS)


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def verify(cur,state):
    if verify_sources()!=state['sources']or own_catalog(_catalog_rows(cur))!=state['catalog']:
        raise ValueError('PRODUCT_ANALOG_READER_SOURCE_OR_CATALOG_CHANGED')
    for sig,expected in state['dependencies'].items():
        if _row(cur,sig)!=expected:
            raise ValueError('PRODUCT_ANALOG_READER_NATIVE_DEPENDENCY_CHANGED: '+sig)
    for sig,(volatility,definer)in FUNCTIONS.items():
        row=_row(cur,sig)
        if row!=state['rows'][sig]or row[2:6]!=['cp7_capture',definer,volatility,['search_path=""','TimeZone=UTC']]:
            raise ValueError('PRODUCT_ANALOG_READER_AUTHORITY_CHANGED: '+sig)
        for role in('anon','authenticated','service_role','cp7_alert','cp7_capture'):
            allowed=role=='cp7_capture'or(role=='authenticated'and sig==PUBLIC)
            if cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,sig)).fetchone()[0]!=allowed:
                raise ValueError('PRODUCT_ANALOG_READER_EXECUTE_CHANGED: '+sig+':'+role)
    for role in('anon','authenticated','service_role','cp7_alert'):
        if cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')',(role,SCHEMA)).fetchone()[0]:
            raise ValueError('PRODUCT_ANALOG_READER_SCHEMA_EXPOSED: '+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('PRODUCT_ANALOG_READER_PUBLIC_CREATE_OPEN')
    return dict(stage='cp7.product-analog-reader-stage.v1',private_functions=2,public_rpcs=1,
                new_tables=0,old_replacements=0,Native_ERP_DML=False,selected=False,reviewed=False,
                forecast_applied=False,production_go=False)


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('PRODUCT_ANALOG_READER_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if old is None and declared(group,key)and new==state['catalog'][group].get(key):continue
            raise ValueError('PRODUCT_ANALOG_READER_UNDECLARED_DELTA: '+group+':'+key)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('PRODUCT_ANALOG_READER_PARENT_CHECKER_REQUIRED')
    predecessor_checker(cur)
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
        raise ValueError('PRODUCT_ANALOG_READER_ALREADY_INSTALLED')
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('PRODUCT_ANALOG_READER_PUBLIC_CREATE_PREEXISTS')
    before=_catalog_rows(cur)
    dependencies={sig:_row(cur,sig)for sig in DEPENDENCIES}
    sql=(kernel.ROOT/'candidates.sql').read_text()+'\n'+(ROOT/'reader.sql').read_text()
    cur.execute(sql,prepare=False)
    rows={sig:_row(cur,sig)for sig in FUNCTIONS}
    for sig,row in rows.items():
        expected=re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if row[1]!=_body(expected):raise ValueError('PRODUCT_ANALOG_READER_WRONG_BODY: '+sig)
    state=dict(sources=pins,dependencies=dependencies,rows=rows,catalog=own_catalog(_catalog_rows(cur)))
    admit_catalog(before,_catalog_rows(cur),state)
    verify(cur,state)
    return state


def rollback_readonly(cur,state):
    verify(cur,state)
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname<>%s and not(p.oid=any(%s::regprocedure[])) "
        "and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 else false end",
        (SCHEMA,list(FUNCTIONS),SCHEMA+'.')).fetchall()
    if external:raise ValueError('PRODUCT_ANALOG_READER_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    # This stage owns no persistent receipt/configuration. Reads leave no data
    # to roll back. RESTRICT still protects real catalog dependencies.
    for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
    cur.execute('drop schema '+SCHEMA+' restrict')
