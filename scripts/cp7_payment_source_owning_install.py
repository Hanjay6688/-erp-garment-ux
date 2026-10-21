"""Complete atomic CP7 owner plus the isolated real payment-correction stage.

No connection, commit, hosted installation or production admission. Preserve
the actual qualified predecessor verification before deriving this extension.
"""
from hashlib import sha256
from pathlib import Path

import cp7_consumer_owning_install as predecessor
from cp7_customer_credit.payment_correction import composition as payment

catalog = predecessor.catalog
base = predecessor.base
atomic = predecessor.atomic


def sources():
    return dict(installer_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor=predecessor.sources(), payment=payment.sources())


def install(cur):
    with atomic(cur):
        previous = predecessor.install(cur)
        proof = predecessor.verify(cur,previous)
        extension = payment.install(cur,proof,catalog._catalog_rows)
        state = dict(sources=sources(), predecessor=previous, predecessor_proof_before_extension=proof,
            payment=extension, installed_catalog=catalog._catalog_rows(cur),seeded_private_rows=base.private_rows(cur))
        verify(cur,state)
        return state


def verify(cur,state):
    if sources() != state['sources'] or catalog._catalog_rows(cur) != state['installed_catalog']:
        raise ValueError('CP7_PAYMENT_SOURCE_COMPLETE_INSTALLED_SOURCE_OR_CATALOG_CHANGED')
    proof = payment.verify(cur,state['payment'],catalog._catalog_rows)
    return dict(classification='SOURCE_VALIDATED_COMPLETE_PAYMENT_CORRECTION_COMPOSITION_NOT_RAW_LEGACY_PASS',
        catalog_groups=22, catalog_members=sum(map(len,state['installed_catalog'].values())), payment=proof,
        predecessor_verified_before_source_derived_extension=True,legacy_definitions_projected=False,
        production_go=False,feature_complete=False,formal_CP7C_started=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        verify(cur,state)
        predecessor._lock_private_tables(cur,state)
        if base.private_rows(cur) != state['seeded_private_rows']:
            raise ValueError(predecessor.USED_ERROR)
        removed = payment.uninstall_preuse(cur,state['payment'],catalog._catalog_rows)
        restored = predecessor.verify(cur,state['predecessor'])
        previous_removed = predecessor.rollback_preuse(cur,state['predecessor'])
        return dict(status='COMPLETE_PAYMENT_SOURCE_PREUSE_REMOVED',payment=removed,
            predecessor_restored_verification=restored,predecessor_removed=previous_removed,
            used_guard_before_any_uninstall=True,financial_facts_deleted=False,production_go=False)
