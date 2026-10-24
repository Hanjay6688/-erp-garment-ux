"""Current A/B installation with the qualified sibling-return draft correction.

The preceding current entrypoint and all qualified SQL stay source-frozen.
Its verifier runs on the actual predecessor before the one declared delta,
and again after the exact inverse. No projected catalog is passed to it.
The caller owns the transaction; no connection, commit or production GO.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_installation as predecessor
import cp7_draft_return_isolation as delta

CONTRACT='cp7.current-AB-with-draft-return-isolation.v1'
catalog=delta.catalog
atomic=predecessor.product.atomic
USED_ERROR=delta.USED_ERROR


def sources():
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor=predecessor.sources(),draft_return_delta=delta.sources())


def install(cur):
    with atomic(cur):
        authority=catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        patch=delta.install_delta(cur)
        state=dict(sources=sources(),authority=authority,predecessor=previous,
            predecessor_verification_before_delta=proof,delta=patch,
            before=before,preinstall_data_and_sequences=data,after=patch['after'])
        verify(cur,state)
        return state


def verify(cur,state):
    if state.get('sources')!=sources():raise ValueError('CURRENT_RETURN_INSTALLATION_SOURCE_CHANGED')
    previous=state['predecessor'];patch=state['delta']
    admission=previous.get('current_installation_admission',{})
    receipt=admission.get('receipt',{})
    proof=state.get('predecessor_verification_before_delta',{})
    if(previous.get('sources')!=predecessor.product.sources()
       or admission.get('sha256')!=predecessor.inventory.digest(receipt)
       or receipt.get('sources')!=predecessor.sources()
       or receipt.get('before')!=receipt.get('after')
       or proof.get('contract')!=predecessor.CONTRACT
       or proof.get('installation_inventory_sha256')!=admission['sha256']
       or proof.get('legacy_inventory_checked')is not True):
        raise ValueError('CURRENT_RETURN_INSTALLATION_PREDECESSOR_RECEIPT_CHANGED')
    if(state['before']!=previous['p21_preinstall_catalog']
       or patch['before']!=previous['after']
       or previous['installed_catalog']!=previous['after']
       or state['after']!=patch['after']):
        raise ValueError('CURRENT_RETURN_INSTALLATION_BROKEN_CATALOG_TRANSITION')
    exact=delta.verify(cur,patch)
    return dict(contract=CONTRACT,status='CURRENT_AB_DRAFT_RETURN_EXACT_ALL22',
        predecessor_verified_before_actual_delta=True,delta=exact,
        installation_inventory_sha256=admission['sha256'],
        legacy_inventory_checked=True,substituted_catalog_or_definitions=False,
        installed_schedules=False,hosted_installation=False,production_go=False,
        independent_acceptance=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        verify(cur,state)
        # The stricter complete data+sequence guard runs before ANY inverse
        # DDL. Legitimate business use requires complete backup restoration.
        corrected=delta.rollback_preuse(cur,state['delta'])
        predecessor.verify(cur,state['predecessor'])
        previous=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']:
            raise ValueError('CURRENT_RETURN_INSTALLATION_PREUSE_CATALOG_NOT_EXACT')
        if catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_RETURN_INSTALLATION_PREUSE_DATA_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_FULL_PREUSE_INVERSE',
            delta=corrected,predecessor=previous,full22_preinstall_equal=True,
            all_rows_and_sequences_preinstall_equal=True,used_guard_before_DDL=True,
            production_go=False,independent_acceptance=False)
