"""Keep the additive S05 reader installed over the actual S03/SKU parent.

No connection, commit, default-installer change or qualification is supplied.
The caller owns source/Original admission and the complete restore boundary.
"""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTRACT='cp7.current-s03-sku-s05.v1'
USED_ERROR='CURRENT_S03_SKU_S05_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'

def parts():
    from cp7_s03_sku_composition import composition as financial
    from cp7_s05_s03_sku_composition import stage as reader
    if reader.parent()is not financial:raise ValueError('CURRENT_COMPOSITE_REAL_PARENT_IDENTITY_REQUIRED')
    return financial,reader

def parent():return parts()[0]
def runtime():return parent().runtime()

def sources():
    financial,reader=parts();manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    if(manifest['contract']!=CONTRACT or manifest['production_go']is not False
       or manifest['independent_acceptance']is not False):
        raise ValueError('CURRENT_COMPOSITE_EXACT_SOURCE_CONTRACT_REQUIRED')
    for name,digest in manifest['files'].items():
        path=ROOT/name
        if path.is_symlink()or sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('CURRENT_COMPOSITE_SOURCE_CHANGED:'+name)
    return dict(contract=CONTRACT,financial_parent=financial.sources(),reader=reader.sources(),
        source=manifest,reader_remains_installed=True,new_financial_functions=0,
        production_go=False,independent_acceptance=False)

def binding(catalog,state):
    financial=state['financial_parent'];reader=state['reader']
    return catalog.digest(dict(sources=state['sources'],financial_sources=financial['sources'],
        financial_parent_binding=financial['parent_binding'],financial_catalog=financial['after'],
        reader_sources=reader['sources'],reader_parent_binding=reader['parent_binding'],reader_catalog=reader['after'],
        reader_data_and_sequences=reader['data'],preuse_data_and_sequences=state['preuse_data_and_sequences'],
        preinstall_data_and_sequences=state['preinstall_data_and_sequences'],
        financial_preuse_data_and_sequences=financial['preuse_data_and_sequences'],
        financial_preinstall_data_and_sequences=financial['preinstall_data_and_sequences']))

def verify(cur,state):
    financial,reader=parts();_,_,_,_,catalog=runtime()
    if state['sources']!=sources()or state['financial_parent']['sources']!=financial.sources():
        raise ValueError('CURRENT_COMPOSITE_ACTUAL_SOURCE_CHANGED')
    if(state['reader']['before']!=state['financial_parent']['after']
       or state['reader']['parent_sources']!=state['financial_parent']['sources']
       or state['before']!=state['reader']['before']or state['after']!=state['reader']['after']
       or state['preuse_data_and_sequences']!=state['reader']['data']
       or state['preinstall_data_and_sequences']!=state['financial_parent']['preinstall_data_and_sequences']):
        raise ValueError('CURRENT_COMPOSITE_STATE_CHAIN_CHANGED')
    if state['component_binding']!=binding(catalog,state):
        raise ValueError('CURRENT_COMPOSITE_COMPONENT_BINDING_CHANGED')
    actual=reader.verify(cur,state['reader'])
    return dict(status='CURRENT_S03_SKU_S05_EXACT_INSTALLED_ALL22',
        reader=actual,financial_parent_verified_before_reader=True,
        all_financial_definitions_and_grants_preserved=True,reader_remains_installed=True,
        source_or_catalog_projection=False,production_go=False,independent_acceptance=False)

def install_delta(cur,qualified_financial_parent):
    financial,reader=parts();_,_,_,base,_=runtime()
    with base.atomic(cur):
        financial.verify(cur,qualified_financial_parent)
        installed=reader.install_delta(cur,qualified_financial_parent)
        state=dict(sources=sources(),financial_parent=qualified_financial_parent,reader=installed,
            before=installed['before'],after=installed['after'],
            preuse_data_and_sequences=installed['data'],
            preinstall_data_and_sequences=qualified_financial_parent['preinstall_data_and_sequences'])
        state['component_binding']=binding(runtime()[4],state)
        verify(cur,state)
        return state

def install(cur):
    _,_,_,base,_=runtime()
    with base.atomic(cur):return install_delta(cur,parent().install(cur))

def rollback_delta_preuse(cur,state):
    financial,reader=parts();_,_,_,base,catalog=runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur)
        verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        restored=reader.uninstall_delta(cur,state['reader'],state['financial_parent'])
        return dict(status='CURRENT_COMPOSITE_READER_PREUSE_INVERSE',financial_parent=restored,
            used_guard_before_DDL=True)

def rollback_preuse(cur,state):
    _,_,_,base,_=runtime()
    with base.atomic(cur):
        reader=rollback_delta_preuse(cur,state)
        return dict(reader=reader,parent=parent().rollback_preuse(cur,state['financial_parent']))
