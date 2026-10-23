"""Integrator-owned first B stage over the complete A chain (qualification only).

The B module owns its 18 SQL bodies and exact metadata admission. This module
owns atomic installation, the full catalogue boundary and a global before-DDL
used-state refusal. No connection, commit, cron, hosted target or default
installer is selected here. Further B stages are not implicitly installed.
"""
from hashlib import sha256
from pathlib import Path

import cp7_p21_chain_adapter as predecessor
import cp7_production_stage as stage

catalog=predecessor.catalog
atomic=predecessor.atomic
base=predecessor.base
USED_ERROR=predecessor.USED_ERROR


def sources():
    return dict(predecessor=predecessor.sources(),production=stage.verify_sources(),
        composition_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def install(cur):
    with atomic(cur):
        authority=catalog._authority(cur)
        before_A=catalog._catalog_rows(cur)
        previous=predecessor.install(cur)
        predecessor_proof=predecessor.verify(cur,previous)
        before=catalog._catalog_rows(cur)
        delta=stage.apply(cur)
        after=catalog._catalog_rows(cur)
        stage.admit_catalog(before,after,delta)
        state=dict(sources=sources(),predecessor=previous,
            predecessor_proof=predecessor_proof,authority=authority,
            p21_preinstall_catalog=before_A,before=before,after=after,
            installed_catalog=after,production=delta,
            p21_seeded_private_rows=base.private_rows(cur))
        verify(cur,state)
        return state


def verify(cur,state):
    if state['sources']!=sources():
        raise ValueError('OW15_PRODUCTION_CHAIN_SOURCE_CHANGED')
    if catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('OW15_PRODUCTION_CHAIN_COMPLETE22_CHANGED')
    if state['installed_catalog']!=state['after']:
        raise ValueError('OW15_PRODUCTION_CHAIN_CATALOG_ALIAS_CHANGED')
    result=stage.verify(cur,state['production'])
    return dict(status='OW15_PRODUCTION_CHAIN_EXACT_SOURCE_AND_ALL22_VERIFIED',
        production_stage=result,predecessor_installed_in_same_transaction=True,
        further_B_stages_installed=False,full_chain_qualified=False,
        production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    """Refuse any changed private facts before the first B or A DDL statement."""
    with atomic(cur):
        catalog._authority(cur)
        verify(cur,state)
        predecessor._lock_private_tables(cur,state)
        if base.private_rows(cur)!=state['p21_seeded_private_rows']:
            raise ValueError(USED_ERROR)
        stage.rollback_preuse(cur,state['production'])
        if catalog._catalog_rows(cur)!=state['before']:
            raise ValueError('OW15_PRODUCTION_CHAIN_A_NOT_EXACTLY_RESTORED')
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['p21_preinstall_catalog']:
            raise ValueError('OW15_PRODUCTION_CHAIN_PREINSTALL_NOT_EXACTLY_RESTORED')
        return dict(status='OW15_PRODUCTION_CHAIN_PREUSE_EXACT_RESTORE',
            predecessor_removed=removed,all22_preinstall_equal=True,
            used_guard_before_any_DDL=True,financial_facts_deleted=False,
            production_go=False)
