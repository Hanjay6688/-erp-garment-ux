"""Small admitted delta over the exact backend3194 composition.

Parent is verified on its actual catalog before changing the seven declared
functions. After use, only a full backup restore may remove this installation.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,re
from . import native_delta
from cp7_laundry_unknown_wash.composition import as_owner
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SCHEMA=native_delta.SCHEMA
CONTRACT='cp7.vendor-receivable.v1'
USED_ERROR='VENDOR_RECEIVABLE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
TABLES=tuple(SCHEMA+'.'+t for t in ('sources_v1','refunds_v1','reversals_v1'))
FUNCTIONS=tuple(SCHEMA+'.'+f for f in (
 'immutable_v1()','eligible_v1(uuid)','accounts_v1()','register_v1(uuid,uuid)',
 'refunded_v1(text,uuid)','application_lines_v1(text,uuid,uuid,numeric)',
 'opening_lines_v1(uuid,jsonb)','prove_v1(uuid)','check_dates_v1(uuid)','refund_v1(jsonb,uuid)',
 'reverse_refund_v1(jsonb,uuid)','augment_v1(uuid,jsonb)'))
VOLATILE={SCHEMA+'.'+f for f in ('immutable_v1()','register_v1(uuid,uuid)','refund_v1(jsonb,uuid)','reverse_refund_v1(jsonb,uuid)')}
_PARENT=None
CAPTURED={}

def parent():
    global _PARENT
    if _PARENT is None:
        spec=importlib.util.spec_from_file_location('vendor_receivable_exact_backend3194',ROOT/'scripts/current-factory-initial-stage/composition.py')
        _PARENT=importlib.util.module_from_spec(spec);spec.loader.exec_module(_PARENT)
    return _PARENT

def runtime():return parent().runtime()

def sources():
    return dict(contract=CONTRACT,predecessor=parent().sources(),
        files={str((HERE/f).relative_to(ROOT)):sha256((HERE/f).read_bytes()).hexdigest()
               for f in ('receivable.sql','native_delta.py','composition.py')},
        new_public_RPC=0,production_go=False,independent_acceptance=False)

def transition(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('VENDOR_RECEIVABLE_ALL22_REQUIRED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and old is not None and new is not None and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None:
                if group=='schemas'and key==SCHEMA:continue
                if group=='functions'and key in FUNCTIONS:continue
                if group in ('relations','columns','constraints','indexes','triggers','types','type_implementation','policies')and key.startswith(SCHEMA+'.'):continue
            raise ValueError('VENDOR_RECEIVABLE_UNDECLARED_CATALOG_DELTA:'+group+':'+key)
    if set(after['functions'])-set(before['functions'])!=set(FUNCTIONS):raise ValueError('VENDOR_RECEIVABLE_FUNCTION_SET_CHANGED')

def binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],rows=prior['rows'],
        preinstall=prior['preinstall_data_and_sequences'],preuse=prior['preuse_data_and_sequences'],proof=proof))

def verify(cur,state):
    _,_,_,predecessor,catalog=runtime();catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('VENDOR_RECEIVABLE_SOURCE_CHANGED')
    prior=state['predecessor']
    if prior['sources']!=parent().sources()or state['parent_binding']!=binding(catalog,prior,state['parent_proof']):
        raise ValueError('VENDOR_RECEIVABLE_PARENT_CHANGED')
    actual=catalog._catalog_rows(cur)
    if actual!=state['after']:raise ValueError('VENDOR_RECEIVABLE_ACTUAL_ALL22_CHANGED')
    transition(prior['after'],actual,state['definitions'])
    for sig in FUNCTIONS:
        owner,definer,volatility,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if owner!='postgres'or definer!=(sig!=SCHEMA+'.immutable_v1()')or volatility!=('v'if sig in VOLATILE else's')or 'search_path=""'not in(config or()):
            raise ValueError('VENDOR_RECEIVABLE_PRIVATE_AUTHORITY_CHANGED:'+sig)
    roles=[r[0]for r in cur.execute("select rolname from pg_roles where rolname in('anon','authenticated','service_role')or rolname like 'cp7_%'")]
    for role in roles:
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:raise ValueError('VENDOR_RECEIVABLE_SCHEMA_EXPOSED:'+role)
        for table in TABLES:
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,table)).fetchone()[0]:raise ValueError('VENDOR_RECEIVABLE_TABLE_EXPOSED:'+role)
        for sig in FUNCTIONS:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:raise ValueError('VENDOR_RECEIVABLE_FUNCTION_EXPOSED:'+role)
    for table in TABLES:
        owner,rls=cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()
        if owner!='postgres'or not rls:raise ValueError('VENDOR_RECEIVABLE_RLS_REQUIRED:'+table)
    return dict(status='VENDOR_RECEIVABLE_EXACT_SOURCE_AND_ALL22',contract=CONTRACT,
        actual_parent_verified_before_delta=True,projected_catalog=False,Native_changed_functions=list(native_delta.SIGNATURES),
        new_private_functions=len(FUNCTIONS),new_public_rpcs=0,Native_money_stock_HPP_engine_unchanged=True,
        formal_acceptance_unchanged=True,production_go=False,independent_acceptance=False)

def install_delta(cur,prior):
    _,_,_,predecessor,catalog=runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        proof=parent().verify(cur,prior)
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        if SCHEMA in before['schemas']:raise ValueError('VENDOR_RECEIVABLE_ALREADY_INSTALLED')
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        if any(before['functions'][sig][1]!='postgres'for sig in originals):raise ValueError('VENDOR_RECEIVABLE_NATIVE_OWNER_CHANGED')
        CAPTURED.clear();CAPTURED.update(originals)
        definitions=native_delta.patched(originals)
        with as_owner(cur,'postgres'):
            cur.execute((HERE/'receivable.sql').read_text(),prepare=False)
            for definition in definitions.values():cur.execute(definition,prepare=False)
        state=dict(sources=sources(),predecessor=prior,parent_proof=proof,parent_binding=binding(catalog,prior,proof),
            before=before,before_data=data,originals=originals,definitions=definitions,after=catalog._catalog_rows(cur),
            preuse_data_and_sequences=catalog._data(cur),preinstall_data_and_sequences=prior['preinstall_data_and_sequences'])
        transition(before,state['after'],definitions);verify(cur,state)
        return state

def install(cur):
    _,_,_,predecessor,_=runtime()
    with predecessor.atomic(cur):return install_delta(cur,parent().install(cur))

def rollback_delta_preuse(cur,state):
    _,_,_,predecessor,catalog=runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        # Before any inverse DDL; never discard business evidence after use.
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        with as_owner(cur,'postgres'):
            for original in state['originals'].values():cur.execute(original,prepare=False)
            cur.execute('drop schema '+SCHEMA+' cascade')
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['before_data']:raise ValueError('VENDOR_RECEIVABLE_PREDECESSOR_NOT_RESTORED')
        proof=parent().verify(cur,state['predecessor'])
        return dict(status='VENDOR_RECEIVABLE_EXACT_PREUSE_DELTA_RESTORE',parent_verified=proof,used_guard_before_DDL=True)

def rollback_preuse(cur,state):
    _,_,_,predecessor,_=runtime()
    with predecessor.atomic(cur):
        delta=rollback_delta_preuse(cur,state)
        return dict(status='VENDOR_RECEIVABLE_FULL_PREUSE_RESTORE',delta=delta,parent=parent().rollback_preuse(cur,state['predecessor']))
