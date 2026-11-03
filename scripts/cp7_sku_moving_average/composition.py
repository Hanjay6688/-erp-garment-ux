"""Append-only SKU moving-average successor over the qualified SKU parent.

This composition is deliberately isolated. Integration into a later unified
candidate requires its own exact parent pin and actual Native qualification.
"""
from hashlib import sha256
from pathlib import Path
from contextlib import contextmanager
from psycopg import sql
from psycopg.pq import TransactionStatus
from cp7_laundry_unknown_wash.composition import as_owner
import cp7_sku_pair_conversion.composition as sku_parent
from . import private_delta,consumer_delta,reader_delta,catalog_additions

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SCHEMA='cp7_sku_conversion'
CONTRACT='cp7.sku-moving-average.v2'
USED_ERROR='SKU_MOVAVG_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
TABLES=tuple(SCHEMA+'.'+x for x in(
 'valuation_quotes_v2','valuation_contributors_v2','valuation_postings_v2','valuation_attributions_v2',
 'sale_allocation_values_v2','sale_allocation_attributions_v2','sale_allocation_components_v2',
 'sales_return_values_v2','sales_return_attributions_v2','sales_return_components_v2',
 'valuation_events_v2','component_events_v2'))
INDEXES={SCHEMA+'.'+x for x in(
 'valuation_events_original_v2','valuation_events_recost_v2',
 'component_events_original_v2','component_events_reverse_v2')}
FUNCTIONS=tuple(SCHEMA+'.'+x for x in(
 'status_component_reverse_v2()',
 'pool_components_v2(uuid,uuid,text)','pool_attribution_v2(uuid,uuid,text)','pool_quote_v2(uuid,uuid,text)',
 'position_value_v2(uuid,uuid,text,numeric)','prepare_sale_values_v2(uuid)','sale_allocation_unit_v2(uuid,uuid)',
 'prepare_return_values_v2(uuid)','return_item_unit_v2(uuid,uuid,numeric)','prepare_valuation_v2(uuid,jsonb)',
 'finalize_valuation_v2(uuid)','reverse_valuation_v2(uuid)'))
VOLATILE={SCHEMA+'.'+x for x in('prepare_sale_values_v2(uuid)','prepare_return_values_v2(uuid)',
 'prepare_valuation_v2(uuid,jsonb)','finalize_valuation_v2(uuid)','reverse_valuation_v2(uuid)','status_component_reverse_v2()')}
EXISTING_TRIGGERS={'erp.sales_headers:sku_component_sale_reverse_v2','erp.sales_returns:sku_component_return_reverse_v2'}
READER_OWNERS={sig:'cp7_fg_read'for sig in reader_delta.SIGNATURES}

@contextmanager
def reader_handover(cur):
    """Give postgres SET on only the verified reader owner for this transaction."""
    granted=[]
    for role in sorted(set(READER_OWNERS.values())):
        if cur.execute("select pg_has_role('postgres',%s,'SET')and pg_has_role('postgres',%s,'USAGE')",(role,role)).fetchone()[0]:continue
        if not cur.execute('select rolsuper from pg_roles where rolname=current_user').fetchone()[0]:
            raise ValueError('SKU_MOVAVG_READER_HANDOVER_DENIED:'+role)
        cur.execute(sql.SQL('grant {} to postgres with inherit true, set true').format(sql.Identifier(role)));granted.append(role)
    try:yield
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            for role in granted:cur.execute(sql.SQL('revoke {} from postgres').format(sql.Identifier(role)))

@contextmanager
def reader_function_ddl(cur,signature):
    """Replace a private FG reader as its existing function and schema owner."""
    if signature not in READER_OWNERS:raise ValueError('SKU_MOVAVG_UNTRUSTED_READER_DDL')
    owner=READER_OWNERS[signature]
    actual,schema,schema_owner,create=cur.execute("""select pg_get_userbyid(p.proowner),n.nspname,pg_get_userbyid(n.nspowner),
        has_schema_privilege(%s,n.oid,'CREATE')from pg_proc p join pg_namespace n on n.oid=p.pronamespace
        where p.oid=%s::regprocedure""",(owner,signature)).fetchone()
    if actual!=owner or schema_owner!=owner:raise ValueError('SKU_MOVAVG_READER_OWNER_CHANGED:'+signature)
    previous=cur.execute('select current_user').fetchone()[0]
    if previous!='postgres':raise ValueError('SKU_MOVAVG_UNTRUSTED_READER_INSTALLER')
    cur.execute(sql.SQL('set local role {}').format(sql.Identifier(owner)))
    if not create:cur.execute(sql.SQL('grant create on schema {} to {}').format(sql.Identifier(schema),sql.Identifier(owner)))
    try:yield
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            if not create:cur.execute(sql.SQL('revoke create on schema {} from {}').format(sql.Identifier(schema),sql.Identifier(owner)))
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(previous)))

def parent():return sku_parent
def runtime():return parent().runtime()

def sources():
    names=('README.md','COMPONENT_LEDGER_DESIGN.md','component_oracle.py','valuation.sql','private_delta.py','consumer_delta.py','reader_delta.py','qualification_cases.py','composition.py','catalog_additions.py','CATALOG_ADDITIONS.json','test_component_contract.py','test_private_delta.py','test_consumer_delta.py','test_reader_delta.py','test_qualification_cases.py')
    return dict(contract=CONTRACT,predecessor=parent().sources(),
        files={str((HERE/n).relative_to(ROOT)):sha256((HERE/n).read_bytes()).hexdigest()for n in names},
        physical_FIFO_preserved=True,economic_valuation='SKU_LOCATION_GRADE_MOVING_AVERAGE',
        actual_SQL=0,production_go=False,independent_acceptance=False)

def binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],
        parent_binding=prior['parent_binding'],definitions=prior['definitions'],originals=prior['originals'],
        preinstall=prior['preinstall_data_and_sequences'],preuse=prior['preuse_data_and_sequences'],proof=proof))

def transition(before,after,definitions):
    additions=catalog_additions.expected()
    if set(before)!=set(after)or set(before)!=set(additions):raise ValueError('SKU_MOVAVG_ALL22_REQUIRED')
    if set(additions['functions'])!=set(FUNCTIONS):raise ValueError('SKU_MOVAVG_FUNCTION_SET_CHANGED')
    if {key for key,row in additions['relations'].items()if row[1]=='r'}!=set(TABLES):
        raise ValueError('SKU_MOVAVG_TABLE_SET_CHANGED')
    for group in before:
        added=set(after[group])-set(before[group]);expected=set(additions[group])
        if added-expected:raise ValueError('SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:'+group+':'+sorted(added-expected)[0])
        if expected-added:raise ValueError('SKU_MOVAVG_MISSING_CATALOG_ADDITION:'+group+':'+sorted(expected-added)[0])
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key in definitions and old is not None and new is not None and new[0]==definitions[key]and old[1:]==new[1:]:continue
            if old is None and key in additions[group]and new==additions[group][key]:continue
            raise ValueError('SKU_MOVAVG_UNDECLARED_CATALOG_DELTA:'+group+':'+key)
    if set(after['functions'])-set(before['functions'])!=set(FUNCTIONS):raise ValueError('SKU_MOVAVG_FUNCTION_SET_CHANGED')

def verify(cur,state):
    _,_,_,predecessor,catalog=runtime();catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('SKU_MOVAVG_SOURCE_CHANGED')
    prior=state['predecessor']
    if prior['sources']!=parent().sources()or state['parent_binding']!=binding(catalog,prior,state['parent_proof']):
        raise ValueError('SKU_MOVAVG_PARENT_CHANGED')
    actual=catalog._catalog_rows(cur)
    if actual!=state['after']:raise ValueError('SKU_MOVAVG_ACTUAL_ALL22_CHANGED')
    transition(prior['after'],actual,state['definitions'])
    for sig in FUNCTIONS:
        owner,definer,volatility,config=cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()
        if owner!='postgres'or not definer or volatility!=('v'if sig in VOLATILE else's')or 'search_path=""'not in(config or()):
            raise ValueError('SKU_MOVAVG_PRIVATE_AUTHORITY_CHANGED:'+sig)
    roles=[r[0]for r in cur.execute("select rolname from pg_roles where rolname in('anon','authenticated','service_role')or rolname like 'cp7_%'")]
    for role in roles:
        for table in TABLES:
            if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(role,table)).fetchone()[0]:
                raise ValueError('SKU_MOVAVG_TABLE_EXPOSED:'+role+':'+table)
        for sig in FUNCTIONS:
            if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
                raise ValueError('SKU_MOVAVG_FUNCTION_EXPOSED:'+role+':'+sig)
    for table in TABLES:
        owner,rls=cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()
        if owner!='postgres'or not rls:raise ValueError('SKU_MOVAVG_RLS_REQUIRED:'+table)
    return dict(status='SKU_MOVAVG_CONVERSION_CORE_EXACT_SOURCE_ALL22',physical_FIFO_preserved=True,
        Native_private_changed_functions=list(private_delta.SIGNATURES),Native_financial_changed_functions=list(consumer_delta.SIGNATURES),Native_reader_changed_functions=list(reader_delta.SIGNATURES),new_private_functions=len(FUNCTIONS),
        actual_SQL=0,financial_consumers_complete=False,formal_acceptance_unchanged=True,
        production_go=False,independent_acceptance=False)

def install_delta(cur,prior):
    _,_,_,predecessor,catalog=runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        proof=parent().verify(cur,prior)
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        capture=private_delta.SIGNATURES+consumer_delta.SIGNATURES+reader_delta.SIGNATURES
        originals={sig:before['functions'][sig][0]for sig in capture}
        definitions=private_delta.patched({sig:originals[sig]for sig in private_delta.SIGNATURES})
        definitions.update(consumer_delta.patched({sig:originals[sig]for sig in consumer_delta.SIGNATURES}))
        definitions.update(reader_delta.patched({sig:originals[sig]for sig in reader_delta.SIGNATURES}))
        with reader_handover(cur),as_owner(cur,'postgres'):
            cur.execute((HERE/'valuation.sql').read_text(),prepare=False)
            for table in TABLES:
                cur.execute('alter table '+table+' owner to postgres')
                cur.execute('revoke all on '+table+' from public,anon,authenticated,service_role')
            for sig in FUNCTIONS:
                cur.execute('alter function '+sig+' owner to postgres')
                cur.execute('revoke all on function '+sig+' from public,anon,authenticated,service_role')
            for signature,definition in definitions.items():
                if signature in READER_OWNERS:
                    with reader_function_ddl(cur,signature):cur.execute(definition,prepare=False)
                else:cur.execute(definition,prepare=False)
        state=dict(sources=sources(),predecessor=prior,parent_proof=proof,parent_binding=binding(catalog,prior,proof),
            before=before,before_data=data,originals=originals,definitions=definitions,after=catalog._catalog_rows(cur),
            preuse_data_and_sequences=catalog._data(cur),preinstall_data_and_sequences=prior['preinstall_data_and_sequences'])
        transition(before,state['after'],definitions);verify(cur,state);return state

def install(cur):
    _,_,_,predecessor,_=runtime()
    with predecessor.atomic(cur):return install_delta(cur,parent().install(cur))

def rollback_delta_preuse(cur,state):
    _,_,_,predecessor,catalog=runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        with reader_handover(cur),as_owner(cur,'postgres'):
            for signature,original in state['originals'].items():
                if signature in READER_OWNERS:
                    with reader_function_ddl(cur,signature):cur.execute(original,prepare=False)
                else:cur.execute(original,prepare=False)
            cur.execute('drop trigger sku_component_return_reverse_v2 on erp.sales_returns')
            cur.execute('drop trigger sku_component_sale_reverse_v2 on erp.sales_headers')
            for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig)
            for table in reversed(TABLES):cur.execute('drop table '+table+' cascade')
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['before_data']:
            raise ValueError('SKU_MOVAVG_PREDECESSOR_NOT_RESTORED')
        return dict(status='SKU_MOVAVG_EXACT_PREUSE_DELTA_RESTORE',parent_verified=parent().verify(cur,state['predecessor']))

def rollback_preuse(cur,state):
    _,_,_,predecessor,_=runtime()
    with predecessor.atomic(cur):
        delta=rollback_delta_preuse(cur,state)
        return dict(status='SKU_MOVAVG_FULL_PREUSE_RESTORE',delta=delta,parent=parent().rollback_preuse(cur,state['predecessor']))

