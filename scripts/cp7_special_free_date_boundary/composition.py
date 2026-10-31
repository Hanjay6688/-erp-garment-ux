"""One actual Native FREE lookup predicate over the complete permanent parent.

The caller must admit its exact actual parent qualification and own the full
disposable restore boundary. No connection, commit, dispatch, default change,
new FREE category, GOOD policy, accrual or recost is supplied by this module.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SQL=ROOT/'scripts/current-special-free-date-boundary'
CONTRACT='cp7.special-free-wib-date.v1'
SIGNATURE='erp.bc_free_basis_v1(uuid,uuid,timestamp with time zone)'
USED_ERROR='SPECIAL_FREE_DATE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'


def parent():
    from cp7_current_s03_sku_s05 import composition
    return composition


def runtime():return parent().runtime()


def prepared():
    spec=importlib.util.spec_from_file_location('exact_actual_free_date_predicate',SQL/'derive.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    before=(SQL/'ORIGINAL.sql').read_bytes();after,proof=module.derive(before)
    if after.encode()!=(SQL/'PREPARED.sql').read_bytes():
        raise ValueError('SPECIAL_FREE_EXACT_PREPARED_STATEMENT_REQUIRED')
    return before.decode(),after,proof


def sources():
    manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    if(manifest['contract']!=CONTRACT or manifest['production_go']is not False
       or manifest['independent_acceptance']is not False):
        raise ValueError('SPECIAL_FREE_EXACT_SOURCE_CONTRACT_REQUIRED')
    for name,pin in manifest['files'].items():
        path=ROOT/name;raw=path.read_bytes()
        if path.is_symlink()or len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('SPECIAL_FREE_DATE_SOURCE_CHANGED:'+name)
    _,_,proof=prepared()
    return dict(contract=CONTRACT,parent=parent().sources(),source=manifest,predicate=proof,
        new_functions=0,new_roles=0,new_business_rows=0,GOOD_eligibility_policy_decided=False,
        production_go=False,independent_acceptance=False)


def transition(before,after):
    original,derived,_=prepared()
    if len(before)!=22 or set(before)!=set(after):
        raise ValueError('SPECIAL_FREE_DATE_COMPLETE_ALL22_REQUIRED')
    row=before['functions'].get(SIGNATURE)
    if not row or row[0]!=original or row[1]!='postgres':
        raise ValueError('SPECIAL_FREE_DATE_EXACT_ACTUAL_PREDECESSOR_AND_OWNER_REQUIRED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if(group=='functions'and key==SIGNATURE and old is not None and new is not None
               and new[0]==derived and old[1:]==new[1:]):continue
            raise ValueError('SPECIAL_FREE_DATE_UNDECLARED_CATALOG_CHANGE:'+group+':'+key)
    expected=after['functions'].get(SIGNATURE)
    if expected is None or expected[0]!=derived:
        raise ValueError('SPECIAL_FREE_DATE_EXACT_SINGLE_PREDICATE_REQUIRED')


def raw_authority(cur):
    row=cur.execute('select p.oid::text,pg_get_userbyid(p.proowner),p.proacl::text '
        'from pg_proc p where p.oid=%s::regprocedure',(SIGNATURE,)).fetchone()
    if row is None or row[1]!='postgres':raise ValueError('SPECIAL_FREE_DATE_ACTUAL_NATIVE_OWNER_REQUIRED')
    return list(row)


def binding(catalog,state):
    return catalog.digest(dict(sources=state['sources'],parent_sources=state['parent_sources'],
        parent_proof=state['parent_proof'],parent_binding=state['parent_binding'],before=state['before'],after=state['after'],
        raw_native_authority=state['raw_native_authority'],data=state['preuse_data_and_sequences']))


def verify(cur,state):
    _,_,_,_,catalog=runtime();catalog._authority(cur)
    if state['sources']!=sources()or state['parent_sources']!=parent().sources():
        raise ValueError('SPECIAL_FREE_DATE_PARENT_OR_SOURCE_CHANGED')
    if state['binding']!=binding(catalog,state):raise ValueError('SPECIAL_FREE_DATE_BINDING_CHANGED')
    actual=catalog._catalog_rows(cur)
    if actual!=state['after']:raise ValueError('SPECIAL_FREE_DATE_ACTUAL_ALL22_CHANGED')
    transition(state['before'],actual)
    if raw_authority(cur)!=state['raw_native_authority']:
        raise ValueError('SPECIAL_FREE_DATE_RAW_OWNER_OID_OR_ACL_CHANGED')
    return dict(status='SPECIAL_FREE_DATE_EXACT_SINGLE_PREDICATE_ALL22',
        raw_NULL_or_explicit_ACL_preserved=True,Native_OID_and_owner_preserved=True,
        no_business_row_or_sequence_rewrite=True,GOOD_eligibility_policy_decided=False,
        production_go=False,independent_acceptance=False)


def install_delta(cur,qualified_parent):
    p=parent();_,_,_,base,catalog=runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        proof=p.verify(cur,qualified_parent)
        before,data=catalog._catalog_rows(cur),catalog._data(cur)
        original,derived,route=prepared()
        if before['functions'].get(SIGNATURE,[None])[0]!=original:
            raise ValueError('SPECIAL_FREE_DATE_EXACT_ACTUAL_FUNCTION_REQUIRED_BEFORE_DDL')
        authority=raw_authority(cur)
        cur.execute(derived,prepare=False)
        after=catalog._catalog_rows(cur)
        transition(before,after)
        if catalog._data(cur)!=data:raise ValueError('SPECIAL_FREE_DATE_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
        if raw_authority(cur)!=authority:raise ValueError('SPECIAL_FREE_DATE_INSTALL_CHANGED_RAW_AUTHORITY')
        state=dict(sources=sources(),parent_sources=p.sources(),parent_proof=proof,parent_binding=qualified_parent['component_binding'],
            before=before,after=after,raw_native_authority=authority,predicate_derivation=route,
            preuse_data_and_sequences=data,
            preinstall_data_and_sequences=qualified_parent['preinstall_data_and_sequences'])
        state['binding']=binding(catalog,state);verify(cur,state);return state


def rollback_delta_preuse(cur,state,qualified_parent):
    _,_,_,base,catalog=runtime()
    with base.atomic(cur):
        if(qualified_parent['sources']!=state['parent_sources']or qualified_parent['after']!=state['before']
           or qualified_parent['component_binding']!=state['parent_binding']):
            raise ValueError('SPECIAL_FREE_DATE_EXACT_QUALIFIED_PARENT_STATE_REQUIRED')
        base.predecessor.predecessor._locks(cur)
        verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        cur.execute(prepared()[0],prepare=False)
        if(catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preuse_data_and_sequences']
           or raw_authority(cur)!=state['raw_native_authority']):
            raise ValueError('SPECIAL_FREE_DATE_EXACT_PREUSE_RESTORE_REQUIRED')
        return dict(status='SPECIAL_FREE_DATE_PREUSE_INVERSE',parent=parent().verify(cur,qualified_parent),
            used_guard_before_DDL=True)
