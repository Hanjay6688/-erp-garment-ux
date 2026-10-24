"""Opt-in backend overlay. No connection, commit, default install or admission.

The predecessor callback owns the complete B stack plus advisory and choices.
Public provenance/client integration and composed after-use restore remain open.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_product_analog_consumer as prototype
from . import render

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_product_analog_consumer'
FUNCTIONS={SCHEMA+'.capture(jsonb)':'s',SCHEMA+'.refs(jsonb)':'i',
 SCHEMA+'.prepare(jsonb,jsonb,jsonb)':'i',SCHEMA+'.resolve(jsonb,text,jsonb)':'i',
 SCHEMA+'.baseline_rows(jsonb,jsonb,jsonb,text,jsonb)':'i',
 SCHEMA+'.normalize_confirmed_delta(jsonb,jsonb,jsonb)':'i',SCHEMA+'.engine_hash()':'s'}
USAGE_SCHEMAS=('cp7_analysis_stage','cp7_baseline_native','cp7_schedule_native',
 'cp7_product_analog_choice','cp7_reorder_reader','cp7_reorder_caller')
DEPENDENCY_SCHEMAS=(*USAGE_SCHEMAS,'cp7_product_analog_stage','cp7_bounded_analysis_stage',
 'cp7_history_bounded','cp7_history_reference','cp7_reorder_inputs','cp7_reorder_supply',
 'cp7_planning','cp7_profile','cp7_supply_native','cp7_netting_native','cp7_analysis_native',
 'cp7_demand','cp7_wip','cp7_baseline','cp7_private','cp7_identity')


def sources():
    files=[*ROOT.glob('*.py'),*ROOT.glob('*.sql'),*ROOT.glob('*.json'),
           *prototype.ROOT.glob('*.py'),*prototype.ROOT.glob('*.sql'),*prototype.ROOT.glob('*.json')]
    return {str(p.relative_to(ROOT.parent)):sha256(p.read_bytes()).hexdigest()for p in sorted(files)}


def verify_sources():
    prototype.verify_sources()
    if json.loads((ROOT/'MANIFEST.json').read_text())!=render.manifest()or (ROOT/'hooks.sql').read_text()!=render.render():
        raise ValueError('ANALOG_CONSUMER_OVERLAY_SOURCE_CHANGED')
    return sources()


def declared(group,key):
    return (group=='schemas'and key==SCHEMA)or(group=='functions'and key in set(FUNCTIONS)|set(render.originals()))


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def usage_state(cur):
    # Used immutable receipts and mutated staged jobs are both after-use.
    # Do not infer pre-use from an empty new schema: this overlay adds no table.
    names=cur.execute("select quote_ident(n.nspname)||'.'||quote_ident(c.relname)from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=any(%s)and c.relkind='r'order by 1",(list(USAGE_SCHEMAS),)).fetchall()
    return {name:cur.execute("select count(*),md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]')::text)from "+name+' x').fetchone()for(name,)in names}


def verify(cur,state):
    if verify_sources()!=state['sources']or own_catalog(_catalog_rows(cur))!=state['catalog']:
        raise ValueError('ANALOG_CONSUMER_SOURCE_OR_CATALOG_CHANGED')
    for sig,old in state['original_rows'].items():
        row=_row(cur,sig)
        if row!=state['new_rows'][sig]or row[2:]!=old[2:]:
            raise ValueError('ANALOG_CONSUMER_EXISTING_AUTHORITY_CHANGED: '+sig)
    for sig,row in state['dependencies'].items():
        if _row(cur,sig)!=row:raise ValueError('ANALOG_CONSUMER_DEPENDENCY_CHANGED: '+sig)
    for sig,volatility in FUNCTIONS.items():
        row=_row(cur,sig)
        if row!=state['new_rows'][sig]or row[2:6]!=['cp7_capture',False,volatility,['search_path=""','TimeZone=UTC']]:
            raise ValueError('ANALOG_CONSUMER_PRIVATE_AUTHORITY_CHANGED: '+sig)
        for role in('anon','authenticated','service_role','cp7_alert'):
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('ANALOG_CONSUMER_PRIVATE_EXECUTE_EXPOSED: '+sig)
    for role in('anon','authenticated','service_role','cp7_alert'):
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
            raise ValueError('ANALOG_CONSUMER_SCHEMA_EXPOSED: '+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('ANALOG_CONSUMER_PUBLIC_CREATE_OPEN')
    return dict(stage='cp7.product-analog-consumer-stage.v1',private_functions=7,new_tables=0,
                new_public_rpcs=0,existing_replacements=18,Native_ERP_DML=False,
                frontend_provenance_integrated=False,full_OW11_acceptance=False,production_go=False)


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('ANALOG_CONSUMER_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if declared(group,key)and new==state['catalog'][group].get(key)and(old is None or group=='functions'and key in state['original_rows']):continue
            raise ValueError('ANALOG_CONSUMER_UNDECLARED_DELTA: '+group+':'+key)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('ANALOG_CONSUMER_PREDECESSOR_CHECKER_REQUIRED')
    predecessor_checker(cur)
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:raise ValueError('ANALOG_CONSUMER_ALREADY_INSTALLED')
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')").fetchone()[0]:raise ValueError('ANALOG_CONSUMER_RUNNING_JOB_REQUIRES_QUIET_INSTALL')
    before=_catalog_rows(cur);old=render.originals();rows={sig:_row(cur,sig)for sig in old}
    for sig,definition in old.items():
        if rows[sig][1]!=_body(definition)or rows[sig][2]!='cp7_capture':raise ValueError('ANALOG_CONSUMER_PREDECESSOR_CHANGED: '+sig)
    keys=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=any(%s)and p.prokind='f'order by 1",(list(DEPENDENCY_SCHEMAS),)).fetchall()
    dependencies={sig:_row(cur,sig)for(sig,)in keys if sig not in old}
    used=usage_state(cur)
    sql='\n'.join((p.read_text()for p in [prototype.ROOT/'kernel.sql',prototype.ROOT/'baseline.sql',ROOT/'confirmation.sql']))
    cur.execute(sql,prepare=False);cur.execute((ROOT/'hooks.sql').read_text(),prepare=False)
    new_rows={sig:_row(cur,sig)for sig in(*old,*FUNCTIONS)}
    for sig,definition in render.replacements().items():
        if new_rows[sig][1]!=_body(definition):raise ValueError('ANALOG_CONSUMER_REPLACEMENT_BODY_CHANGED: '+sig)
    for sig in FUNCTIONS:
        definition=re.search(r'create function '+re.escape(sig.split('(')[0])+r'\(.*?\$\$;',sql,re.S)[0]
        if new_rows[sig][1]!=_body(definition):raise ValueError('ANALOG_CONSUMER_ADDITION_BODY_CHANGED: '+sig)
    state=dict(sources=pins,original_rows=rows,new_rows=new_rows,dependencies=dependencies,
               usage_before=used,catalog=own_catalog(_catalog_rows(cur)))
    admit_catalog(before,_catalog_rows(cur),state);verify(cur,state)
    return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if usage_state(cur)!=state['usage_before']:raise ValueError('ANALOG_CONSUMER_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
    allowed=list(state['original_rows'])+list(FUNCTIONS)
    external=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname<>%s and not(p.oid=any(%s::regprocedure[]))and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 else false end",(SCHEMA,allowed,SCHEMA+'.')).fetchall()
    if external:raise ValueError('ANALOG_CONSUMER_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
    cur.execute('savepoint analog_consumer_inverse')
    try:
        for row in state['original_rows'].values():cur.execute(row[0],prepare=False)
        for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
        cur.execute('drop schema '+SCHEMA+' restrict')
    except Exception:
        cur.execute('rollback to savepoint analog_consumer_inverse');raise
    finally:cur.execute('release savepoint analog_consumer_inverse')
