"""Full current target plus exact selected-return customer refusal.

All prior definitions are verified before the one declared delta. Full22 and
all rows/sequences remain bound; no projected catalog or patched predecessor.
"""
from pathlib import Path
from hashlib import sha256
import cp7_current_model_target_installation as predecessor
import cp7_selected_return_customer_delta as delta

CONTRACT = 'cp7.current-selected-return-customer.v1'
USED_ERROR = 'CURRENT_SELECTED_RETURN_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog, atomic = predecessor.catalog, predecessor.atomic


def sources():
    return dict(contract=CONTRACT, entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                predecessor=predecessor.sources(), delta=delta.sources())


def binding(prior, proof):
    return catalog.digest(dict(sources=prior['sources'], before=prior['before'],
                               after=prior['after'], actual_verification=proof))


def install(cur):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        catalog._lock_tables(cur)
        before, rows = catalog._catalog_rows(cur), catalog._data(cur)
        prior = predecessor.install(cur)
        proof = predecessor.verify(cur, prior)
        stage = delta.install_delta(cur)
        state = dict(sources=sources(), before=before, preinstall_data_and_sequences=rows,
                     predecessor=prior, predecessor_verified_before_delta=proof,
                     predecessor_binding_sha256=binding(prior, proof), delta=stage,
                     after=stage['after'], preuse_data_and_sequences=stage['preuse_data_and_sequences'])
        verify(cur, state)
        return state


def verify(cur, state):
    catalog._authority(cur)
    prior, proof, stage = state['predecessor'], state['predecessor_verified_before_delta'], state['delta']
    if (state['sources'] != sources() or prior['sources'] != predecessor.sources()
            or state['before'] != prior['before'] or stage['before'] != prior['after']
            or state['preinstall_data_and_sequences'] != prior['preinstall_data_and_sequences']
            or stage['preuse_data_and_sequences'] != prior['preuse_data_and_sequences']
            or state['preuse_data_and_sequences'] != stage['preuse_data_and_sequences']
            or state['predecessor_binding_sha256'] != binding(prior, proof)
            or proof.get('contract') != predecessor.CONTRACT
            or proof.get('status') != 'EXACT_CURRENT_MODEL_TARGET_ALL22'
            or proof.get('predecessor_verified_before_actual_delta') is not True
            or proof.get('all22_transition_chain_verified') is not True
            or proof.get('substituted_catalog_or_definitions') is not False
            or state['after'] != stage['after']):
        raise ValueError('CURRENT_SELECTED_RETURN_TRANSITION_BINDING_CHANGED')
    delta.verify(cur, stage)
    return dict(contract=CONTRACT, status='EXACT_CURRENT_SELECTED_RETURN_ALL22',
                predecessor_verified_before_actual_delta=True, all22_transition_chain_verified=True,
                substituted_catalog_or_definitions=False, replaced_functions=[delta.SIGNATURE],
                every_old_row_and_sequence_preserved=True, production_go=False, independent_acceptance=False)


def rollback_preuse(cur, state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        verify(cur, state)
        catalog._lock_tables(cur)
        if catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        removed_delta = delta.rollback_preuse(cur, state['delta'])
        predecessor.verify(cur, state['predecessor'])
        removed_prior = predecessor.rollback_preuse(cur, state['predecessor'])
        if catalog._catalog_rows(cur) != state['before'] or catalog._data(cur) != state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_SELECTED_RETURN_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT, status='EXACT_CURRENT_SELECTED_RETURN_PREUSE_INVERSE',
                    delta=removed_delta, predecessor=removed_prior, all22_preinstall_equal=True,
                    all_rows_and_sequences_equal=True, global_used_guard_before_any_DDL=True,
                    production_go=False, independent_acceptance=False)
