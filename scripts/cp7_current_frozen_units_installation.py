"""A-owned, opt-in full composition of the exact qualified private B v2 units.

No public facade, default adoption, financial-v2 request or production grant.
Every predecessor is checked on the actual database before its next delta.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_versioned_performance_installation as predecessor
import cp7_current_frozen_units as inputs
from cp7_current_frozen_units import binary
import cp7_frozen_analysis_v2 as capsule
import cp7_frozen_analysis_units_v2 as units

CONTRACT = 'cp7.current-AB-finance-private-frozen-units.v1'
USED_ERROR = 'CURRENT_FROZEN_UNITS_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog, atomic = predecessor.catalog, predecessor.atomic


def sources():
    return dict(contract=CONTRACT,
                entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                predecessor=predecessor.sources(), inputs=inputs.sources())


def binding(prior, proof):
    return catalog.digest(dict(sources=prior['sources'], before=prior['before'],
                               after=prior['after'], actual_verification=proof))


def _admit_units(before, after, state):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('CURRENT_FROZEN_UNITS_FULL22_REQUIRED')
    originals = units.render.originals()
    if (set(state['old_rows']) != set(originals)
            or set(state['new_rows']) != set(originals) | set(units.FUNCTIONS)):
        raise ValueError('CURRENT_FROZEN_UNITS_PREDECESSOR_FUNCTION_SET_CHANGED')
    changed = set()
    for group in before:
        for key in set(before[group]) | set(after[group]):
            left, right = before[group].get(key), after[group].get(key)
            if left == right:
                continue
            changed.add((group, key))
            if not units.declared(group, key) or right != state['catalog'][group].get(key):
                raise ValueError('CURRENT_FROZEN_UNITS_UNDECLARED_DELTA:'+group+':'+key)
            if left is not None:
                if (group != 'functions' or key not in originals
                        or left[1:] != right[1:]
                        or left[0] != state['old_rows'][key][0]
                        or right[0] != state['new_rows'][key][0]):
                    raise ValueError('CURRENT_FROZEN_UNITS_EXISTING_AUTHORITY_CHANGED:'+key)
    expected = {('schemas', units.SCHEMA)} | {
        ('functions', key) for key in set(originals) | set(units.FUNCTIONS)}
    if changed != expected:
        raise ValueError('CURRENT_FROZEN_UNITS_INCOMPLETE_DECLARED_DELTA')


def _verify_binding(state):
    prior, proof = state['predecessor'], state['predecessor_verified_before_delta']
    if (state['sources'] != sources() or prior['sources'] != predecessor.sources()
            or state['before'] != prior['before']
            or state['predecessor_binding_sha256'] != binding(prior, proof)
            or proof.get('contract') != predecessor.CONTRACT
            or proof.get('status') != 'EXACT_CURRENT_VERSIONED_PERFORMANCE_ALL22'
            or proof.get('predecessor_verified_before_actual_delta') is not True
            or proof.get('all22_transition_chain_verified') is not True
            or proof.get('substituted_catalog_or_definitions') is not False
            or proof.get('every_old_row_and_sequence_preserved') is not True
            or proof.get('selected_customer_refusal_preserved') is not True
            or state['preuse_data_and_sequences'] != prior['preuse_data_and_sequences']
            or state['preinstall_data_and_sequences'] != prior['preinstall_data_and_sequences']):
        raise ValueError('CURRENT_FROZEN_UNITS_PREDECESSOR_BINDING_CHANGED')


def _verify_prefix(cur, state):
    """Verify actual additive binary/capsule state immediately before units."""
    catalog._authority(cur)
    _verify_binding(state)
    prior = state['predecessor']
    binary.admit_catalog(prior['after'], state['after_binary'], state['binary'])
    capsule.admit_catalog(state['after_binary'], state['after_capsule'], state['capsule'])
    binary.verify(cur, state['binary'])
    capsule.verify(cur, state['capsule'])
    if catalog._catalog_rows(cur) != state['after_capsule']:
        raise ValueError('CURRENT_FROZEN_UNITS_ACTUAL_PREFIX_CATALOG_CHANGED')
    return dict(contract=CONTRACT, status='EXACT_CURRENT_FROZEN_PREFIX_ALL22',
                actual_full_predecessor_verified=True, substituted_catalog_or_definitions=False)


def verify(cur, state):
    catalog._authority(cur)
    _verify_binding(state)
    binary.admit_catalog(state['predecessor']['after'], state['after_binary'], state['binary'])
    capsule.admit_catalog(state['after_binary'], state['after_capsule'], state['capsule'])
    _admit_units(state['after_capsule'], state['after'], state['units'])
    binary.verify(cur, state['binary'])
    capsule.verify(cur, state['capsule'])
    units.verify(cur, state['units'])
    if catalog._catalog_rows(cur) != state['after']:
        raise ValueError('CURRENT_FROZEN_UNITS_ACTUAL_FULL22_CHANGED')
    return dict(contract=CONTRACT, status='EXACT_CURRENT_FROZEN_UNITS_ALL22',
                predecessor_verified_before_actual_delta=True,
                all22_transition_chain_verified=True,
                substituted_catalog_or_definitions=False,
                exact_B_private_functions=20, existing_unit_replacements=8,
                new_tables=0, new_public_rpcs=0, old_v1_reference_unchanged=True,
                finance_v2_request_qualified=False, default_request_adopted=False,
                production_go=False, independent_acceptance=False)


def _locks(cur):
    catalog._authority(cur)
    cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
    cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
    catalog._lock_tables(cur)


def _unchanged_data(cur, expected):
    if catalog._data(cur) != expected:
        raise ValueError('CURRENT_FROZEN_UNITS_INSTALL_CHANGED_ROWS_OR_SEQUENCES')


def install(cur):
    with atomic(cur):
        _locks(cur)
        before, data = catalog._catalog_rows(cur), catalog._data(cur)
        prior = predecessor.install(cur)
        proof = predecessor.verify(cur, prior)
        if catalog._catalog_rows(cur) != prior['after']:
            raise ValueError('CURRENT_FROZEN_UNITS_ACTUAL_PREDECESSOR_CHANGED')
        used = prior['preuse_data_and_sequences']
        _unchanged_data(cur, used)
        state = dict(sources=sources(), before=before, preinstall_data_and_sequences=data,
                     predecessor=prior, predecessor_verified_before_delta=proof,
                     predecessor_binding_sha256=binding(prior, proof),
                     preuse_data_and_sequences=used)
        state['binary'] = binary.install_delta(cur)
        state['after_binary'] = catalog._catalog_rows(cur)
        binary.admit_catalog(prior['after'], state['after_binary'], state['binary'])
        binary.verify(cur, state['binary'])
        _unchanged_data(cur, used)
        state['capsule'] = capsule.install_delta(cur)
        state['after_capsule'] = catalog._catalog_rows(cur)
        _verify_prefix(cur, state)
        _unchanged_data(cur, used)
        state['units'] = units.install_delta(cur, lambda c: _verify_prefix(c, state))
        state['after'] = catalog._catalog_rows(cur)
        _unchanged_data(cur, used)
        verify(cur, state)
        return state


def rollback_preuse(cur, state):
    with atomic(cur):
        _locks(cur)
        verify(cur, state)
        # All rows and all sequences, before the first inverse DDL of any stage.
        if catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        units.rollback_preuse(cur, state['units'])
        _verify_prefix(cur, state)
        capsule.rollback_preuse(cur, state['capsule'])
        binary.verify(cur, state['binary'])
        if catalog._catalog_rows(cur) != state['after_binary']:
            raise ValueError('CURRENT_FROZEN_UNITS_CAPSULE_INVERSE_NOT_EXACT')
        binary.rollback_preuse(cur, state['binary'])
        predecessor.verify(cur, state['predecessor'])
        removed = predecessor.rollback_preuse(cur, state['predecessor'])
        if (catalog._catalog_rows(cur) != state['before']
                or catalog._data(cur) != state['preinstall_data_and_sequences']):
            raise ValueError('CURRENT_FROZEN_UNITS_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT, status='EXACT_CURRENT_FROZEN_UNITS_PREUSE_INVERSE',
                    predecessor=removed, all22_preinstall_equal=True,
                    all_rows_and_sequences_equal=True, global_used_guard_before_any_DDL=True,
                    production_go=False)
