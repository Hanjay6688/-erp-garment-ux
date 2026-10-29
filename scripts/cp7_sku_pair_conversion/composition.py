"""Owner 29 October pair/master and manual conversion delta over qualified vendor composition.

Parent is verified on its actual catalog before changing the six declared
functions. After use, only a full backup restore may remove this installation.
"""
from pathlib import Path
from hashlib import sha256
from . import native_delta,ri_catalog
from cp7_laundry_unknown_wash.composition import as_owner
import cp7_vendor_receivable.composition as vendor_parent
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SCHEMA=native_delta.SCHEMA
CONTRACT='cp7.sku-pair-conversion.v1'
USED_ERROR='SKU_PAIR_CONVERSION_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
TABLES=tuple(SCHEMA+'.'+t for t in ('pairs_v1','pair_events_v1','groups_v1','members_v1','execution_v1'))
FUNCTIONS=tuple(SCHEMA+'.'+f for f in (
 'immutable_v1()','guard_pair_v1()','partner_v1(uuid)','pair_revision_v1()','group_v1(uuid)',
 'save_pair_v1(jsonb,uuid)','sku_workspace_v1(jsonb)','sku_action_v1(text,jsonb,uuid)',
 'manual_allocation_v1(uuid,uuid,uuid,integer,timestamp with time zone)','assert_group_reverse_v1(uuid)',
 'stock_v1(uuid,uuid)','revision_v1(uuid,uuid,uuid)','preview_v1(jsonb)',
 'action_v1(text,jsonb,uuid)','workspace_v1(jsonb)'))
VOLATILE={SCHEMA+'.'+f for f in ('immutable_v1()','guard_pair_v1()','save_pair_v1(jsonb,uuid)','sku_action_v1(text,jsonb,uuid)',
 'preview_v1(jsonb)','action_v1(text,jsonb,uuid)','workspace_v1(jsonb)')}
CAPTURED={}

def parent():return vendor_parent

def runtime():return parent().runtime()

def sources():
    return dict(contract=CONTRACT,predecessor=parent().sources(),
        files={str((HERE/f).relative_to(ROOT)):sha256((HERE/f).read_bytes()).hexdigest()
               for f in ('pairs.sql','conversion.sql','native_delta.py','composition.py','ri_catalog.py')},
        new_public_RPC=0,production_go=False,independent_acceptance=False)

def transition(before,after,definitions):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('SKU_PAIR_CONVERSION_ALL22_REQUIRED')
    parent_ri=ri_catalog.expected_parent_triggers(after['constraints'])
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and old is not None and new is not None and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and new is not None:
                if group=='schemas'and key==SCHEMA:continue
                if group=='functions'and key in FUNCTIONS:continue
                if group=='triggers'and ri_catalog.permitted_parent_trigger(key,new,parent_ri):continue
                if group in ('relations','columns','constraints','indexes','triggers','types','type_implementation','policies')and key.startswith(SCHEMA+'.'):continue
            raise ValueError('SKU_PAIR_CONVERSION_UNDECLARED_CATALOG_DELTA:'+group+':'+key)
    if set(after['functions'])-set(before['functions'])!=set(FUNCTIONS):raise ValueError('SKU_PAIR_CONVERSION_FUNCTION_SET_CHANGED')
    added_parent_triggers={key:row for key,row in after['triggers'].items()if key not in before['triggers']and not key.startswith(SCHEMA+'.')}
    if added_parent_triggers!=parent_ri:raise ValueError('SKU_PAIR_CONVERSION_EXACT_SIX_PARENT_RI_TRIGGERS_REQUIRED')

def binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],parent_binding=prior['parent_binding'],definitions=prior['definitions'],originals=prior['originals'],
        preinstall=prior['preinstall_data_and_sequences'],preuse=prior['preuse_data_and_sequences'],proof=proof))

def verify(cur,state):
    _,_,_,predecessor,catalog=runtime();catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('SKU_PAIR_CONVERSION_SOURCE_CHANGED')
    prior=state['predecessor']
    if prior['sources']!=parent().sources()or state['parent_binding']!=binding(catalog,prior,state['parent_proof']):
        raise ValueError('SKU_PAIR_CONVERSION_PARENT_CHANGED')
    actual=catalog._catalog_rows(cur)
    if actual!=state['after']:raise ValueError('SKU_PAIR_CONVERSION_ACTUAL_ALL22_CHANGED')
    transition(prior['after'],actual,state['definitions'])
    for sig in FUNCTIONS:
        owner,definer,volatility,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if owner!='postgres'or definer!=(sig!=SCHEMA+'.immutable_v1()')or volatility!=('v'if sig in VOLATILE else's')or 'search_path=""'not in(config or()):
            raise ValueError('SKU_PAIR_CONVERSION_PRIVATE_AUTHORITY_CHANGED:'+sig)
    roles=[r[0]for r in cur.execute("select rolname from pg_roles where rolname in('anon','authenticated','service_role')or rolname like 'cp7_%'")]
    for role in roles:
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:raise ValueError('SKU_PAIR_CONVERSION_SCHEMA_EXPOSED:'+role)
        for table in TABLES:
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,table)).fetchone()[0]:raise ValueError('SKU_PAIR_CONVERSION_TABLE_EXPOSED:'+role)
        for sig in FUNCTIONS:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:raise ValueError('SKU_PAIR_CONVERSION_FUNCTION_EXPOSED:'+role)
    for table in TABLES:
        owner,rls=cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()
        if owner!='postgres'or not rls:raise ValueError('SKU_PAIR_CONVERSION_RLS_REQUIRED:'+table)
    return dict(status='SKU_PAIR_CONVERSION_EXACT_SOURCE_AND_ALL22',contract=CONTRACT,
        actual_parent_verified_before_delta=True,projected_catalog=False,Native_changed_functions=list(native_delta.SIGNATURES),
        new_private_functions=len(FUNCTIONS),new_public_rpcs=0,Native_money_stock_HPP_engine_unchanged=True,Native_cross_dimension_only_exact_private_manual_allocation=True,
        formal_acceptance_unchanged=True,production_go=False,independent_acceptance=False)

def install_delta(cur,prior):
    _,_,_,predecessor,catalog=runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        proof=parent().verify(cur,prior)
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        if SCHEMA in before['schemas']:raise ValueError('SKU_PAIR_CONVERSION_ALREADY_INSTALLED')
        originals={sig:before['functions'][sig][0]for sig in native_delta.SIGNATURES}
        if any(before['functions'][sig][1]!='postgres'for sig in originals):raise ValueError('SKU_PAIR_CONVERSION_NATIVE_OWNER_CHANGED')
        CAPTURED.clear();CAPTURED.update(originals)
        definitions=native_delta.patched(originals)
        with as_owner(cur,'postgres'):
            cur.execute((HERE/'pairs.sql').read_text(),prepare=False)
            cur.execute((HERE/'conversion.sql').read_text(),prepare=False)
            for table in TABLES:
                cur.execute('alter table '+table+' owner to postgres');cur.execute('revoke all on '+table+' from public,anon,authenticated,service_role')
            for sig in FUNCTIONS:
                cur.execute('alter function '+sig+' owner to postgres');cur.execute('revoke all on function '+sig+' from public,anon,authenticated,service_role')
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
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['before_data']:raise ValueError('SKU_PAIR_CONVERSION_PREDECESSOR_NOT_RESTORED')
        proof=parent().verify(cur,state['predecessor'])
        return dict(status='SKU_PAIR_CONVERSION_EXACT_PREUSE_DELTA_RESTORE',parent_verified=proof,used_guard_before_DDL=True)

def rollback_preuse(cur,state):
    _,_,_,predecessor,_=runtime()
    with predecessor.atomic(cur):
        delta=rollback_delta_preuse(cur,state)
        return dict(status='SKU_PAIR_CONVERSION_FULL_PREUSE_RESTORE',delta=delta,parent=parent().rollback_preuse(cur,state['predecessor']))
