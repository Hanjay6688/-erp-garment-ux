"""Current A/B installation entry point, owned by the integrator.

An administrative cursor is required. The caller owns the transaction;
this module never connects, commits, schedules work or enables production.
Historical P21 entry points remain source-frozen for their actual receipts.
"""
from hashlib import sha256
from pathlib import Path
from cp7_ab_bounded_chain import composition as product
import cp7_install_legacy_inventory as inventory

CONTRACT='cp7.current-AB-installation-with-legacy-inventory.v1'


def sources():
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        inventory_sha256=inventory.source_hash(),product=product.sources())


def install(cur):
    with product.atomic(cur):
        before=inventory.capture(cur)
        state=product.install(cur)
        after=inventory.assert_preserved(cur,before)
        preview=inventory.preview_active_rules(cur,before)
        admission=dict(sources=sources(),before=before,after=after,official_active_rules=preview)
        state['current_installation_admission']=dict(receipt=admission,sha256=inventory.digest(admission))
        verify(cur,state)
        return state


def verify(cur,state):
    admission=state.get('current_installation_admission',{})
    receipt=admission.get('receipt',{})
    if admission.get('sha256')!=inventory.digest(receipt) or receipt.get('sources')!=sources():
        raise ValueError('CURRENT_INSTALLATION_SOURCE_OR_INVENTORY_RECEIPT_CHANGED')
    if receipt['before']!=receipt['after']:
        raise ValueError('CURRENT_INSTALLATION_NATIVE_REFERENCES_CHANGED')
    # A legitimate later business command may change a configuration. The
    # immutable installation receipt describes installation time, not "now".
    return dict(contract=CONTRACT,product=product.verify(cur,state),
        installation_inventory_sha256=admission['sha256'],legacy_inventory_checked=True,
        official_active_rules_observed=True,legacy_selection_made=False,
        installed_schedules=False,hosted_installation=False,production_go=False)


def rollback_preuse(cur,state):
    with product.atomic(cur):
        verify(cur,state)
        references=inventory.capture(cur)
        result=product.rollback_preuse(cur,state)
        inventory.assert_preserved(cur,references)
        return dict(product=result,legacy_native_references_preserved=True,production_go=False)
