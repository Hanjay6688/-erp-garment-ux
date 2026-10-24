"""Opt-in full current consumer composition plus explicit bounded finance.

Every predecessor is verified on its actual catalog before replacement.
No connection, commit, default installation, schedule or production admission.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_analog_consumer_installation as predecessor
import cp7_bounded_finance_bridge as finance

CONTRACT='cp7.current-AB-consumer-bounded-official-finance.v1'
USED_ERROR='CURRENT_BOUNDED_FINANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=predecessor.catalog,predecessor.atomic


def sources():
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor=predecessor.sources(),finance=finance.verify_sources())


def binding(prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],actual_verification=proof))


def verify(cur,state):
    catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('CURRENT_BOUNDED_FINANCE_SOURCE_CHANGED')
    prior=state['predecessor'];proof=state['predecessor_verified_before_delta'];stage=state['finance']
    if(prior['sources']!=predecessor.sources()
       or binding(prior,proof)!=state['predecessor_binding_sha256']
       or proof.get('contract')!=predecessor.CONTRACT
       or proof.get('status')!='EXACT_CURRENT_AB_ANALOG_CONSUMER_ALL22'
       or proof.get('all22_transition_chain_verified')is not True
       or proof.get('substituted_catalog_or_definitions')is not False
       or state['before']!=prior['before']or stage['before']!=prior['after']
       or stage['after']!=state['after']or catalog.digest(stage)!=state['finance_state_sha256']):
        raise ValueError('CURRENT_BOUNDED_FINANCE_PREDECESSOR_BINDING_CHANGED')
    finance.admit_catalog(prior['after'],state['after'],stage)
    finance.verify(cur,stage)
    return dict(contract=CONTRACT,status='EXACT_CURRENT_BOUNDED_FINANCE_ALL22',
        predecessor_verified_before_actual_delta=True,all22_transition_chain_verified=True,
        substituted_catalog_or_definitions=False,private_functions_added=1,public_rpcs_added=1,
        functions_replaced=1,new_tables=0,financial_math_added=False,
        full_factory3600_financial_parity=False,production_go=False,independent_acceptance=False)


def install(cur):
    with atomic(cur):
        authority=catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        prior=predecessor.install(cur);proof=predecessor.verify(cur,prior)
        stage=finance.install_delta(cur,lambda c:predecessor.verify(c,prior))
        state=dict(sources=sources(),authority=authority,before=before,
            preinstall_data_and_sequences=data,predecessor=prior,
            predecessor_verified_before_delta=proof,predecessor_binding_sha256=binding(prior,proof),
            finance=stage,finance_state_sha256=catalog.digest(stage),
            after=catalog._catalog_rows(cur),preuse_data_and_sequences=catalog._data(cur))
        verify(cur,state)
        return state


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        finance.rollback_preuse(cur,state['finance'])
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_BOUNDED_FINANCE_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_CURRENT_BOUNDED_FINANCE_PREUSE_INVERSE',
            predecessor=removed,all22_preinstall_equal=True,all_rows_and_sequences_equal=True,
            global_used_guard_before_any_DDL=True,production_go=False,independent_acceptance=False)
