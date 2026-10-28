"""Measured initial-worker delta over the exact 4ac installed composition."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CONTRACT='cp7.current-factory-initial-stage.v1'
USED_ERROR='FACTORY_INITIAL_STAGE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
CATALOG_ERROR='FACTORY_INITIAL_STAGE_ACTUAL_ALL22_CHANGED'
_BASE=None
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def base():
    global _BASE
    if _BASE is None:_BASE=load('initial_stage_exact_4ac_product',ROOT/'scripts/current-finance-factory-progress-followup-qualification/composition.py')
    return _BASE
def worker():return load('measured_initial_stage_worker',HERE/'worker.py')
def runtime():return base().runtime()
def sources():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['contract']==CONTRACT and source['production_go']is source['independent_acceptance']is False
    for path,digest in source['files'].items():assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    return dict(contract=CONTRACT,predecessor=base().sources(),source=source,
        new_public_RPC=0,initial_statement_limit_ms=16000,ordinary_statement_limit_ms=8000,qualification_only=True)
def binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],rows=prior['rows'],
        preinstall=prior['preinstall_data_and_sequences'],preuse=prior['preuse_data_and_sequences'],proof=proof))
def verify(cur,state):
    pins=sources();_,_,_,_,catalog=runtime();catalog._authority(cur);delta=worker()
    prior=state['predecessor'];proof=state['predecessor_verified_before_delta']
    assert state['sources']==pins and prior['sources']==base().sources()
    assert state['predecessor_binding_sha256']==binding(catalog,prior,proof)
    assert state['initial_worker']['before']==prior['after']
    assert state['initial_worker']['after']==state['after']
    assert proof['status']=='EXACT_COMBINED_CONSISTENT_READERS_ALL22'
    assert proof['all22_transition_chain_verified']is True and proof['substituted_catalog_or_definitions']is False
    for key in ('before','preinstall_data_and_sequences','preuse_data_and_sequences'):assert state[key]==prior[key]
    assert catalog._catalog_rows(cur)==state['after'],CATALOG_ERROR
    delta.transition(prior['after'],state['after'])
    for signature,old in prior['rows'].items():
        assert signature not in delta.REPLACED|delta.ADDED,'INITIAL_WORKER_OVERLAPS_PRIOR_DELTA'
        assert delta.row(cur,signature)==old
    assert state['original_rows']==prior['original_rows'],'OFFICIAL_REPORT_BASELINE_CHANGED'
    assert state['rows']==prior['rows']|state['initial_worker']['rows']
    observed=delta.verify(cur,state['initial_worker'],catalog)
    return dict(contract=CONTRACT,status='EXACT_FACTORY_INITIAL_STAGE_ALL22',actual_predecessor_verified=True,
        all22_transition_chain_verified=True,substituted_catalog_or_definitions=False,worker=observed,
        new_private_functions=2,replaced_private_functions=3,new_public_rpcs=0,
        Native_money_stock_HPP_definitions_unchanged=True,existing_four_schedules_unchanged=True,
        additional_bounded_initial_schedule=True,ordinary_statement_timeout_changed=False,
        qualification_only=True,default_adopted=False,production_go=False)
def install_delta(cur,readonly_prior):
    pins=sources();parent,_,_,predecessor,catalog=runtime();parent.disposable(cur);delta=worker()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        prior=base().install_delta(cur,readonly_prior);proof=base().verify(cur,prior)
        assert catalog._data(cur)==prior['preuse_data_and_sequences']
        applied=delta.install(cur,catalog)
        assert catalog._data(cur)==prior['preuse_data_and_sequences']
        state=dict(sources=pins,predecessor=prior,predecessor_verified_before_delta=proof,
            predecessor_binding_sha256=binding(catalog,prior,proof),before=prior['before'],
            preinstall_data_and_sequences=prior['preinstall_data_and_sequences'],preuse_data_and_sequences=prior['preuse_data_and_sequences'],
            initial_worker=applied,original_rows=prior['original_rows'],rows=prior['rows']|applied['rows'],after=catalog._catalog_rows(cur))
        verify(cur,state);return state
def install(cur):
    sources();parent,_,_,predecessor,_=runtime();parent.disposable(cur)
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        return install_delta(cur,parent.install(cur))
def rollback_delta_preuse(cur,state):
    _,_,_,predecessor,catalog=runtime();delta=worker()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        delta.restore(cur,state['initial_worker'],catalog)
        assert catalog._catalog_rows(cur)==state['predecessor']['after']
        base().verify(cur,state['predecessor'])
        removed=base().rollback_delta_preuse(cur,state['predecessor'])
        return dict(status='EXACT_INITIAL_STAGE_PREUSE_DELTA_INVERSE',worker_restored=True,predecessor=removed,
            all22_installed_parent_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_DDL=True,full_parent_inverse_repeated=False)
def rollback_preuse(cur,state):
    parent,_,_,predecessor,catalog=runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        delta=rollback_delta_preuse(cur,state)
        removed=parent.rollback_preuse(cur,state['predecessor']['predecessor']['predecessor'])
        assert catalog._catalog_rows(cur)==state['before']and catalog._data(cur)==state['preinstall_data_and_sequences']
        return dict(status='EXACT_INITIAL_STAGE_PREUSE_INVERSE',delta=delta,predecessor=removed,
            all22_preinstall_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_DDL=True)
