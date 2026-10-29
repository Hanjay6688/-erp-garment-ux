"""D1 owning correction delta over the actual qualified vendor composition.

Not the default installer. Root integrator owns publication and admission after
actual Native/restore/oracle qualification. No database calls occur on import.
"""
from hashlib import sha256
from pathlib import Path
import re
from cp7_vendor_receivable import composition as predecessor
from cp7_laundry_unknown_wash.composition import as_owner
from . import native_delta
HERE=Path(__file__).resolve().parent
SCHEMA=native_delta.SCHEMA
CONTRACT='cp7.credit-correction-de.v1'
SQL=('review.sql','facts.sql','owning.sql','proof.sql','posting.sql','materialize.sql','closure.sql')
TABLES=tuple(SCHEMA+'.'+n for n in ('work_v1','operations_v1','plans_v1','parts_v1','posting_v1'))
USED_ERROR='CREDIT_DE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
CAPTURED={}

def runtime():return predecessor.runtime()

def sql_functions():
    result={}
    for file in SQL:
        source=(HERE/file).read_text()
        for name,args,lang,vol,security in re.findall(r'create function ([a-z0-9_.]+)\(([^)]*)\)returns [\w ]+\nlanguage (\w+)(?: (immutable|stable|volatile))? security (invoker|definer)',source):
            sig=name+'('+','.join(a.strip().split()[1]for a in args.split(',')if a.strip())+')'
            result[sig]=(security=='definer',{'immutable':'i','stable':'s','volatile':'v','':'v'}[vol])
    actual=set(re.findall(r'create function ([a-z0-9_.]+)\(', '\n'.join((HERE/f).read_text()for f in SQL)))
    if actual!={s.split('(')[0]for s in result}:raise ValueError('CREDIT_DE_DECLARED_FUNCTION_PARSER_CHANGED')
    return result

def sources():return dict(contract=CONTRACT,predecessor=predecessor.sources(),
    files={f:sha256((HERE/f).read_bytes()).hexdigest()for f in SQL+('native_delta.py','composition.py')},
    admitted_slice='D1_FINANCIAL_INCREASE_IDENTICAL_PHYSICAL_AND_STATIC_NONPO_HPP',D_complete=False,E_complete=False,
    new_public_RPCS=0,production_go=False,independent_acceptance=False)

def functions():return set(sql_functions())|set(native_delta.COPIES.values())

def transition(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('CREDIT_DE_ALL22_CATALOG_GROUPS_REQUIRED')
    new_functions=functions()
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in native_delta.CHANGED and old is not None and new is not None and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None:
                if group=='schemas'and key==SCHEMA:continue
                if group=='functions'and key in new_functions:continue
                if group in('relations','columns','constraints','indexes','triggers','types','type_implementation','policies')and key.startswith(SCHEMA+'.'):continue
            raise ValueError('CREDIT_DE_UNDECLARED_CATALOG_DELTA:'+group+':'+key)
    if set(after['functions'])-set(before['functions'])!=new_functions:raise ValueError('CREDIT_DE_EXACT_NEW_FUNCTION_SET_CHANGED')

def binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],proof=proof,
        preuse=prior['preuse_data_and_sequences'],preinstall=prior['preinstall_data_and_sequences']))

def verify(cur,state):
    *_,catalog=runtime();catalog._authority(cur)
    if state['sources']!=sources()or state['parent_binding']!=binding(catalog,state['predecessor'],state['parent_proof']):raise ValueError('CREDIT_DE_SOURCE_OR_PARENT_CHANGED')
    if state['before']!=state['predecessor']['after']:raise ValueError('CREDIT_DE_ACTUAL_PARENT_CATALOG_BINDING_CHANGED')
    actual=catalog._catalog_rows(cur)
    if actual!=state['after']:raise ValueError('CREDIT_DE_ACTUAL_ALL22_CHANGED')
    transition(state['before'],actual,state['definitions'])
    roles=[r[0]for r in cur.execute("select rolname from pg_roles where rolname in('anon','authenticated','service_role')or rolname like 'cp7_%'")]
    allowed={SCHEMA+'.workspace_v1(jsonb)':'cp7_sales_read',SCHEMA+'.dispatch_v1(jsonb,uuid,text)':'cp7_sales_write'}
    for sig in functions():
        owner,definer,vol,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if owner!='postgres':raise ValueError('CREDIT_DE_PRIVATE_OWNER_CHANGED:'+sig)
        if sig in sql_functions()and((definer,vol)!=sql_functions()[sig]or 'search_path=""'not in(config or())):raise ValueError('CREDIT_DE_FUNCTION_AUTHORITY_CHANGED:'+sig)
        for role in roles:
            exposed=cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]
            if exposed!=(allowed.get(sig)==role):raise ValueError('CREDIT_DE_FUNCTION_EXPOSURE_CHANGED:'+sig+':'+role)
    for role in roles:
        exposed=cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]
        if exposed!=(role in('cp7_sales_read','cp7_sales_write')):raise ValueError('CREDIT_DE_SCHEMA_EXPOSURE_CHANGED:'+role)
        for table in TABLES:
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,table)).fetchone()[0]:raise ValueError('CREDIT_DE_TABLE_EXPOSED:'+role+':'+table)
    for table in TABLES:
        if cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()!=('postgres',True):raise ValueError('CREDIT_DE_TABLE_AUTHORITY_CHANGED:'+table)
    return dict(status='CREDIT_DE_EXACT_SOURCE_AND_ALL22',actual_parent_verified_before_delta=True,projected_catalog=False,
        changed_functions=list(native_delta.CHANGED),private_Native_copies=native_delta.COPIES,Native_money_HPP_engine_unchanged=True,
        formal_acceptance_unchanged=True,D_complete=False,E_complete=False,production_go=False,independent_acceptance=False)

def install_delta(cur,prior):
    _,_,_,base,catalog=runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        proof=predecessor.verify(cur,prior);before=catalog._catalog_rows(cur);data=catalog._data(cur)
        if SCHEMA in before['schemas']:raise ValueError('CREDIT_DE_ALREADY_INSTALLED')
        originals={sig:before['functions'][sig][0]for sig in native_delta.CAPTURES}
        if any(before['functions'][sig][1]!='postgres'for sig in native_delta.CAPTURES if sig not in(native_delta.PUBLIC_COMMAND,native_delta.PUBLIC_WORKSPACE)):raise ValueError('CREDIT_DE_NATIVE_OWNER_CHANGED')
        CAPTURED.clear();CAPTURED.update(originals);definitions=native_delta.derive(originals)
        with as_owner(cur,'postgres'):
            for file in SQL:cur.execute((HERE/file).read_text(),prepare=False)
            for definition in definitions.values():cur.execute(definition,prepare=False)
            cur.execute('revoke all on all functions in schema '+SCHEMA+' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write')
            cur.execute('grant usage on schema '+SCHEMA+' to cp7_sales_read,cp7_sales_write')
            cur.execute('grant execute on function '+SCHEMA+'.workspace_v1(jsonb)to cp7_sales_read')
            cur.execute('grant execute on function '+SCHEMA+'.dispatch_v1(jsonb,uuid,text)to cp7_sales_write')
        # pg_get_functiondef normalizes declarations. Verify normalized actuals,
        # while binding each derivation to the verified exact source above.
        installed={sig:cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]for sig in definitions}
        state=dict(sources=sources(),predecessor=prior,parent_proof=proof,parent_binding=binding(catalog,prior,proof),before=before,before_data=data,
            originals={sig:originals[sig]for sig in native_delta.CHANGED},derivations=definitions,definitions=installed,
            after=catalog._catalog_rows(cur),preuse_data_and_sequences=catalog._data(cur),preinstall_data_and_sequences=prior['preinstall_data_and_sequences'])
        transition(before,state['after'],installed);verify(cur,state);return state

def install(cur):
    _,_,_,base,_=runtime()
    with base.atomic(cur):return install_delta(cur,predecessor.install(cur))

def rollback_delta_preuse(cur,state):
    _,_,_,base,catalog=runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        with as_owner(cur,'postgres'):
            for original in state['originals'].values():cur.execute(original,prepare=False)
            cur.execute('drop schema '+SCHEMA+' cascade')
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['before_data']:raise ValueError('CREDIT_DE_PREDECESSOR_NOT_EXACTLY_RESTORED')
        return dict(status='CREDIT_DE_EXACT_PREUSE_DELTA_RESTORE',parent_verified=predecessor.verify(cur,state['predecessor']),used_guard_before_DDL=True)

def rollback_preuse(cur,state):
    _,_,_,base,_=runtime()
    with base.atomic(cur):return dict(status='CREDIT_DE_FULL_PREUSE_RESTORE',delta=rollback_delta_preuse(cur,state),parent=predecessor.rollback_preuse(cur,state['predecessor']))
