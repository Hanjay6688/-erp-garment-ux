"""Full A frozen-unit chain plus explicit private official finance-v2 requests."""
from hashlib import sha256
from pathlib import Path
import cp7_current_frozen_units_installation as predecessor
import cp7_current_frozen_finance as finance

CONTRACT = 'cp7.current-AB-private-frozen-finance.v1'
USED_ERROR = 'CURRENT_FROZEN_FINANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog, atomic = predecessor.catalog, predecessor.atomic


def sources():
    return dict(contract=CONTRACT, entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                predecessor=predecessor.sources(), finance=finance.verify_sources())


def binding(prior, proof):
    return catalog.digest(dict(sources=prior['sources'], before=prior['before'],
                               after=prior['after'], actual_verification=proof))


def verify(cur,state):
    catalog._authority(cur)
    prior, proof = state['predecessor'], state['predecessor_verified_before_delta']
    if (state['sources'] != sources() or prior['sources'] != predecessor.sources()
            or state['before'] != prior['before']
            or state['predecessor_binding_sha256'] != binding(prior,proof)
            or proof.get('contract') != predecessor.CONTRACT
            or proof.get('status') != 'EXACT_CURRENT_FROZEN_UNITS_ALL22'
            or proof.get('predecessor_verified_before_actual_delta') is not True
            or proof.get('all22_transition_chain_verified') is not True
            or proof.get('substituted_catalog_or_definitions') is not False
            or proof.get('old_v1_reference_unchanged') is not True):
        raise ValueError('CURRENT_FROZEN_FINANCE_PREDECESSOR_BINDING_CHANGED')
    delta = state['finance']
    if (delta['before'] != prior['after'] or delta['after'] != state['after']
            or delta['preuse_data_and_sequences'] != prior['preuse_data_and_sequences']
            or state['preuse_data_and_sequences'] != prior['preuse_data_and_sequences']
            or state['preinstall_data_and_sequences'] != prior['preinstall_data_and_sequences']):
        raise ValueError('CURRENT_FROZEN_FINANCE_TRANSITION_CHANGED')
    finance.verify(cur,delta)
    return dict(contract=CONTRACT, status='EXACT_CURRENT_FROZEN_FINANCE_ALL22',
                predecessor_verified_before_actual_delta=True, all22_transition_chain_verified=True,
                substituted_catalog_or_definitions=False, official_finance_source_reused=True,
                finance_mode_bound_before_first_seal=True, new_public_rpcs=0,
                factory_finance_qualified=False, default_adopted=False,
                production_go=False, independent_acceptance=False)


def _locks(cur):
    catalog._authority(cur)
    cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
    cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
    catalog._lock_tables(cur)


def install(cur):
    with atomic(cur):
        _locks(cur)
        before, data = catalog._catalog_rows(cur), catalog._data(cur)
        prior = predecessor.install(cur)
        proof = predecessor.verify(cur,prior)
        delta = finance.install_delta(cur,lambda c:predecessor.verify(c,prior))
        if catalog._data(cur) != prior['preuse_data_and_sequences']:
            raise ValueError('CURRENT_FROZEN_FINANCE_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
        state = dict(sources=sources(), before=before, preinstall_data_and_sequences=data,
                     predecessor=prior, predecessor_verified_before_delta=proof,
                     predecessor_binding_sha256=binding(prior,proof), finance=delta,
                     after=catalog._catalog_rows(cur), preuse_data_and_sequences=prior['preuse_data_and_sequences'])
        verify(cur,state)
        return state


def rollback_preuse(cur,state):
    with atomic(cur):
        _locks(cur)
        verify(cur,state)
        if catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        finance.rollback_preuse(cur,state['finance'])
        predecessor.verify(cur,state['predecessor'])
        removed = predecessor.rollback_preuse(cur,state['predecessor'])
        if (catalog._catalog_rows(cur) != state['before']
                or catalog._data(cur) != state['preinstall_data_and_sequences']):
            raise ValueError('CURRENT_FROZEN_FINANCE_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT, status='EXACT_CURRENT_FROZEN_FINANCE_PREUSE_INVERSE',
                    predecessor=removed, all22_preinstall_equal=True,
                    all_rows_and_sequences_equal=True, global_used_guard_before_any_DDL=True,
                    production_go=False)
