"""Complete D1/E then the exact single Native WIB FREE predicate correction.

No connection, commit, workflow, public RPC or new economic policy is supplied.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTRACT='cp7.current-complete-de-free-date.v1'
USED_ERROR='SPECIAL_FREE_DATE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'


def qualification():
    spec=importlib.util.spec_from_file_location('free_date_complete_DE_actual_parent',
        ROOT/'scripts/current-de-free-date-preparation/admission.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.parent_receipt()


def parent():
    qualification()
    from cp7_complete_credit_de import composition
    return composition


def stage():
    qualification()
    from cp7_special_free_date_on_de import composition
    return composition


def runtime():return parent().runtime()


def qualified_parent_sources(receipt,value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    actual=dict(bytes=len(raw),sha256=sha256(raw).hexdigest());expected=receipt.get('qualified_complete_DE_sources')
    if(type(expected)is not dict or set(expected)!={'bytes','sha256'}
       or type(expected.get('bytes'))is not int or type(expected.get('sha256'))is not str or expected!=actual):
        raise ValueError('FREE_DATE_DE_ENTIRE_PARENT_SOURCE_MUST_EQUAL_ACTUAL_NATIVE30')
    return actual


def source_manifest():
    value=json.loads((HERE/'SOURCE.json').read_bytes())
    if(value['contract']!=CONTRACT or value['actual_Native_cases']!=0
       or value['production_go']is not False or value['independent_acceptance']is not False):
        raise ValueError('FREE_DATE_DE_EXACT_PREPARATION_SOURCE_REQUIRED')
    for name,pin in value['files'].items():
        path=ROOT/name;raw=path.read_bytes()
        if path.is_symlink()or len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('FREE_DATE_DE_OWN_SOURCE_CHANGED:'+name)
    return value


def sources():
    receipt=qualification()
    manifest=source_manifest();actual=parent().sources();accepted=qualified_parent_sources(receipt,actual)
    date=stage().sources()
    if date['parent']!=actual:raise ValueError('FREE_DATE_DE_NATURAL_STAGE_PARENT_CHANGED')
    return dict(contract=CONTRACT,parent=actual,date=date,source=manifest,qualified_parent_sources=accepted,
        new_functions=0,new_roles=0,new_business_rows=0,GOOD_eligibility_policy_decided=False,
        production_go=False,independent_acceptance=False)


def binding(catalog,state):
    p=state['predecessor'];date=state['date']
    return catalog.digest(dict(sources=state['sources'],before=state['before'],after=state['after'],
        qualified_parent_sources=state['qualified_parent_sources'],
        actual_parent_binding=p['component_binding'],parent_binding_recomputed=parent().binding(catalog,p),
        date_binding=date['binding'],date_binding_recomputed=stage().binding(catalog,date),
        preinstall=state['preinstall_data_and_sequences'],preuse=state['preuse_data_and_sequences']))


def verify(cur,state):
    receipt=qualification();p=parent();date=stage();_,_,_,_,catalog=runtime()
    actual=qualified_parent_sources(receipt,state['predecessor']['sources'])
    if state['qualified_parent_sources']!=actual or state['sources']!=sources():
        raise ValueError('FREE_DATE_DE_QUALIFIED_SOURCE_BINDING_CHANGED')
    if(date.parent()is not p or state['before']!=state['predecessor']['after']
       or state['before']!=state['date']['before']or state['after']!=state['date']['after']
       or state['preuse_data_and_sequences']!=state['date']['preuse_data_and_sequences']
       or state['preuse_data_and_sequences']!=state['predecessor']['preuse_data_and_sequences']
       or state['preinstall_data_and_sequences']!=state['predecessor']['preinstall_data_and_sequences']
       or state['preinstall_data_and_sequences']!=state['date']['preinstall_data_and_sequences']):
        raise ValueError('FREE_DATE_DE_ACTUAL_STATE_CHAIN_CHANGED')
    date.require_parent_state(catalog,state['date'],state['predecessor'])
    if state['component_binding']!=binding(catalog,state):raise ValueError('FREE_DATE_DE_COMPONENT_BINDING_CHANGED')
    result=date.verify(cur,state['date'])
    return dict(status='CURRENT_COMPLETE_DE_FREE_DATE_EXACT_INSTALLED_ALL22',date=result,
        parent_verifier_not_called_on_changed_catalogue=True,GOOD_eligibility_policy_decided=False,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)


def install_delta(cur,qualified_parent):
    receipt=qualification()
    accepted=qualified_parent_sources(receipt,qualified_parent['sources']);pins=sources()
    p=parent();date=stage();_,_,_,base,_=runtime()
    with base.atomic(cur):
        p.verify(cur,qualified_parent)
        installed=date.install_delta(cur,qualified_parent)
        state=dict(sources=pins,predecessor=qualified_parent,date=installed,qualified_parent_sources=accepted,
            before=qualified_parent['after'],after=installed['after'],
            preuse_data_and_sequences=installed['preuse_data_and_sequences'],
            preinstall_data_and_sequences=qualified_parent['preinstall_data_and_sequences'])
        state['component_binding']=binding(runtime()[4],state);verify(cur,state);return state


def install(cur):
    receipt=qualification();p=parent();qualified_parent_sources(receipt,p.sources());sources()
    _,_,_,base,_=runtime()
    with base.atomic(cur):return install_delta(cur,p.install(cur))


def rollback_delta_preuse(cur,state):
    qualification();p=parent();date=stage();_,_,_,base,_=runtime()
    with base.atomic(cur):
        verify(cur,state)
        restored=date.rollback_delta_preuse(cur,state['date'],state['predecessor'])
        return dict(status='CURRENT_COMPLETE_DE_FREE_DATE_PREUSE_DELTA_INVERSE',date=restored,
            parent=restored['parent'],used_guard_before_DDL=True)


def rollback_preuse(cur,state):
    qualification();p=parent();_,_,_,base,_=runtime()
    with base.atomic(cur):
        removed=rollback_delta_preuse(cur,state)
        return dict(status='CURRENT_COMPLETE_DE_FREE_DATE_FULL_PREUSE_RESTORE',date=removed,
            parent=p.rollback_preuse(cur,state['predecessor']))
