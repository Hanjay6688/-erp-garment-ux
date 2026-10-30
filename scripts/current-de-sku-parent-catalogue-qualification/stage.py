"""Qualification-only D1→E→SKU installation over the actual vendor parent.

No command or final runtime is opened. Each original verifier runs against
its actual catalogue before the next child's DDL and after child removal.
While children are installed, the top verifier binds the immutable lower
proof/state chain without projecting a catalogue into an older verifier.
"""
from hashlib import sha256
from pathlib import Path
import json
from cp7_vendor_receivable import composition as vendor
from cp7_credit_correction_de import composition as d1
from cp7_credit_correction_de import e_composition as e
from cp7_sku_pair_conversion import composition as sku

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CONTRACT='cp7.de-sku.parent-catalogue-only.v1'
USED_ERROR='DE_SKU_PARENT_CATALOGUE_CHANGED_DATA_REQUIRES_FULL_BACKUP_RESTORE'


def parent():return vendor
def runtime():return sku.runtime()


def sources():
    cfg=json.loads((HERE/'SOURCE.json').read_bytes())
    return dict(contract=CONTRACT,predecessor=sku.sources(),
        files={name:sha256((ROOT/name).read_bytes()).hexdigest()for name in cfg['files']},
        manifest_sha256=sha256((HERE/'SOURCE.json').read_bytes()).hexdigest(),
        business_runtime_entry=None,qualification_only=True,production_go=False,independent_acceptance=False)


def binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],
        preinstall=prior['preinstall_data_and_sequences'],preuse=prior['preuse_data_and_sequences'],proof=proof))


def verify(cur,state):
    *_,catalog=runtime();catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('DE_SKU_CATALOGUE_SOURCE_CHANGED')
    if state['parent_binding']!=binding(catalog,state['predecessor'],state['parent_proof']):
        raise ValueError('DE_SKU_CATALOGUE_PARENT_PROOF_CHANGED')
    top=state['top'];prior=state['predecessor']
    if top['predecessor']['predecessor']['predecessor']!=prior:
        raise ValueError('DE_SKU_CATALOGUE_NATURAL_PARENT_CHAIN_CHANGED')
    if state['after']!=top['after']or state['before']!=prior['after']:
        raise ValueError('DE_SKU_CATALOGUE_ACTUAL_TRANSITION_CHANGED')
    proof=sku.verify(cur,top)
    return dict(status='EXACT_D1_E_SKU_INSTALLED_CATALOGUE_ONLY',top=proof,
        older_verifiers_called_on_projected_catalogue=False,business_commands_executed=0,
        business_runtime_entry=None,production_go=False,independent_acceptance=False)


def install_delta(cur,prior):
    *_,base,catalog=runtime()
    with base.atomic(cur):
        proof=vendor.verify(cur,prior)
        d=d1.install_delta(cur,prior);dproof=d1.verify(cur,d)
        carried=e.install_delta(cur,d);eproof=e.verify(cur,carried)
        top=sku.install_delta(cur,carried);sproof=sku.verify(cur,top)
        state=dict(sources=sources(),predecessor=prior,parent_proof=proof,
            parent_binding=binding(catalog,prior,proof),top=top,before=prior['after'],after=top['after'],
            installed_layer_catalogues=dict(D1=d['after'],E=carried['after'],SKU=top['after']),
            actual_layer_proofs=dict(D1=dproof,E=eproof,SKU=sproof),
            preinstall_data_and_sequences=prior['preinstall_data_and_sequences'],
            preuse_data_and_sequences=top['preuse_data_and_sequences'])
        verify(cur,state);return state


def rollback_delta_preuse(cur,state):
    *_,base,catalog=runtime()
    with base.atomic(cur):
        verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        top=state['top'];carried=top['predecessor'];d=carried['predecessor']
        removed=dict(SKU=sku.rollback_delta_preuse(cur,top),E=e.rollback_delta_preuse(cur,carried),
                     D1=d1.rollback_delta_preuse(cur,d))
        proof=vendor.verify(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']:raise ValueError('DE_SKU_CATALOGUE_PARENT_NOT_RESTORED')
        if catalog._data(cur)!=state['predecessor']['preuse_data_and_sequences']:
            raise ValueError('DE_SKU_CATALOGUE_PARENT_ROWS_SEQUENCES_NOT_RESTORED')
        return dict(status='EXACT_D1_E_SKU_PREUSE_DELTA_RESTORE',removed=removed,parent_verified=proof,
            used_guard_before_DDL=True,used_guard_business_witness_executed=False,
            actual_business_cases=0,production_go=False)
