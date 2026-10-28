"""Full verified versioned/selected-return chain, then exact B path optimization.

The prior composer and all of its source proofs remain unchanged. Every old
function is verified on the real database before the two late replacements.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_versioned_target_installation as predecessor
import cp7_current_versioned_performance as performance

CONTRACT='cp7.current-AB-finance-versioned-performance.v1'
USED_ERROR='CURRENT_VERSIONED_PERFORMANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=predecessor.catalog,predecessor.atomic


def sources():
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor=predecessor.sources(),performance=performance.sources())


def binding(prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],actual_verification=proof))


def verify(cur,state):
    catalog._authority(cur)
    prior,proof=state['predecessor'],state['predecessor_verified_before_delta']
    if(state['sources']!=sources()or prior['sources']!=predecessor.sources()or state['before']!=prior['before']
       or state['predecessor_binding_sha256']!=binding(prior,proof)
       or proof.get('contract')!=predecessor.CONTRACT or proof.get('status')!='EXACT_CURRENT_VERSIONED_TARGET_ALL22'
       or proof.get('predecessor_verified_before_actual_delta')is not True or proof.get('all22_transition_chain_verified')is not True
       or proof.get('substituted_catalog_or_definitions')is not False or proof.get('selected_customer_refusal_preserved')is not True):
        raise ValueError('CURRENT_VERSIONED_PERFORMANCE_PREDECESSOR_BINDING_CHANGED')
    delta=state['performance']
    if(delta['before']!=prior['after']or delta['after']!=state['after']
       or delta['preuse_data_and_sequences']!=state['preuse_data_and_sequences']
       or state['preuse_data_and_sequences']!=prior['preuse_data_and_sequences']
       or state['preinstall_data_and_sequences']!=prior['preinstall_data_and_sequences']):
        raise ValueError('CURRENT_VERSIONED_PERFORMANCE_TRANSITION_CHANGED')
    performance.verify(cur,delta)
    return dict(contract=CONTRACT,status='EXACT_CURRENT_VERSIONED_PERFORMANCE_ALL22',
        predecessor_verified_before_actual_delta=True,all22_transition_chain_verified=True,
        substituted_catalog_or_definitions=False,two_late_B_function_replacements=True,
        every_old_row_and_sequence_preserved=True,selected_customer_refusal_preserved=True,
        unchanged_authority_and_all_business_predicates=True,production_go=False,independent_acceptance=False)


def install(cur):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        catalog._lock_tables(cur)
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        prior=predecessor.install(cur);proof=predecessor.verify(cur,prior)
        delta=performance.install_delta(cur,lambda c:predecessor.verify(c,prior))
        after_data=catalog._data(cur)
        if after_data!=prior['preuse_data_and_sequences']:raise ValueError('CURRENT_VERSIONED_PERFORMANCE_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
        state=dict(sources=sources(),before=before,preinstall_data_and_sequences=data,predecessor=prior,
            predecessor_verified_before_delta=proof,predecessor_binding_sha256=binding(prior,proof),
            performance=delta,after=catalog._catalog_rows(cur),preuse_data_and_sequences=after_data)
        verify(cur,state);return state


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        performance.rollback_preuse(cur,state['performance']);predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_VERSIONED_PERFORMANCE_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_CURRENT_VERSIONED_PERFORMANCE_PREUSE_INVERSE',predecessor=removed,
            all22_preinstall_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_any_DDL=True,production_go=False)
