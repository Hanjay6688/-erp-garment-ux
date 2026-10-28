"""Private opening-reader correction on the exact AF combined installation."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CONTRACT='cp7.current-consistent-finance-private-opening.v2'
USED_ERROR='CONSISTENT_FINANCE_READER_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
_BASE=None


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def base():
    global _BASE
    if _BASE is None:_BASE=load('reader_stream_exact_AF_product',ROOT/'scripts/current-finance-combined-composition/composition.py')
    return _BASE


def opening():return load('reader_stream_private_opening',HERE/'opening.py')
def runtime():return base().runtime()


def qualification():
    config=json.loads((HERE/'CONFIG.json').read_bytes());evidence=load('reader_stream_AF_evidence',HERE/'evidence.py')
    proof=evidence.gate(config);binding=json.loads((HERE/'BINDING.json').read_bytes())
    assert proof==binding['actual_AF']
    directory=Path(os.environ[config['original_directory_variable']])
    source=json.loads((ROOT/'scripts/current-finance-combined-composition/QUALIFICATION_SOURCE.json').read_bytes())
    for path,digest in source['files'].items():assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    return evidence.retained(proof,(directory/proof['name']).read_bytes(),
        (directory/proof['package_name']).read_bytes(),source,base().sources(),binding)


def sources():
    _,accepted=qualification()
    return dict(contract=CONTRACT,predecessor=base().sources(),retained_AF=accepted,
        files={name:sha256((HERE/name).read_bytes()).hexdigest()for name in
            ('composition.py','opening.py','evidence.py','CONFIG.json','BINDING.json')},
        original_Native_opening_definition_unchanged=True,private_opening_body_copied_exactly=True)


def parent_binding(catalog,prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],
        rows=prior['rows'],preinstall=prior['preinstall_data_and_sequences'],preuse=prior['preuse_data_and_sequences'],proof=proof))


def verify(cur,state):
    pins=sources();parent,_,_,predecessor,catalog=runtime();catalog._authority(cur);delta=opening()
    prior=state['predecessor'];proof=state['predecessor_verified_before_delta']
    assert state['sources']==pins and prior['sources']==base().sources()
    assert state['predecessor_binding_sha256']==parent_binding(catalog,prior,proof)
    assert proof['status']=='EXACT_COMBINED_FINANCE_ALL22'and proof['all22_transition_chain_verified']is True
    assert proof['substituted_catalog_or_definitions']is False
    for key in ('before','preinstall_data_and_sequences','preuse_data_and_sequences'):assert state[key]==prior[key]
    assert catalog._catalog_rows(cur)==state['after'],'CONSISTENT_FINANCE_READER_ACTUAL_ALL22_CHANGED'
    changed={(group,key)for group in prior['after']for key in set(prior['after'][group])|set(state['after'][group])
        if prior['after'][group].get(key)!=state['after'][group].get(key)}
    assert changed=={('functions',delta.HPP),('functions',delta.PRIVATE)},'CONSISTENT_FINANCE_READER_UNDECLARED_DELTA'
    assert prior['after']['functions'][delta.HPP][1:]==state['after']['functions'][delta.HPP][1:]
    assert delta.PRIVATE not in prior['after']['functions']
    for signature,row in prior['rows'].items():assert delta.row(cur,signature)==row
    assert delta.row(cur,delta.HPP)==state['rows'][delta.HPP]
    assert delta.row(cur,delta.PRIVATE)==state['rows'][delta.PRIVATE]
    observed=delta.verify(cur,state['opening'],catalog)
    return dict(contract=CONTRACT,status='EXACT_COMBINED_CONSISTENT_READERS_ALL22',
        actual_predecessor_verified=True,all22_transition_chain_verified=True,substituted_catalog_or_definitions=False,
        new_private_functions=4,changed_private_functions=5,new_private_columns=1,internal_schema_usage_grants=1,
        new_public_rpcs=0,Native_money_stock_HPP_definitions_unchanged=True,opening=observed,
        schedules_changed=False,timeout_changed=False,qualification_only=True,default_adopted=False,production_go=False)


def install_delta(cur,readonly_prior):
    pins=sources();parent,_,_,predecessor,catalog=runtime();parent.disposable(cur);delta=opening()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        prior=base().install_delta(cur,readonly_prior);verified=base().verify(cur,prior)
        assert catalog._data(cur)==prior['preuse_data_and_sequences']
        applied=delta.install(cur,catalog)
        assert catalog._data(cur)==prior['preuse_data_and_sequences']
        state=dict(sources=pins,predecessor=prior,predecessor_verified_before_delta=verified,
            predecessor_binding_sha256=parent_binding(catalog,prior,verified),before=prior['before'],
            preinstall_data_and_sequences=prior['preinstall_data_and_sequences'],preuse_data_and_sequences=prior['preuse_data_and_sequences'],
            opening=applied,original_rows=prior['original_rows']|{delta.HPP:applied['hpp_before']},
            rows=prior['rows']|{delta.HPP:applied['hpp_after'],delta.PRIVATE:applied['helper']},after=catalog._catalog_rows(cur))
        verify(cur,state);return state


def install(cur):
    sources();parent,_,_,predecessor,_=runtime();parent.disposable(cur)
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        return install_delta(cur,parent.install(cur))


def rollback_delta_preuse(cur,state):
    parent,_,_,predecessor,catalog=runtime();delta=opening()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        delta.restore(cur,state['opening'])
        assert catalog._catalog_rows(cur)==state['predecessor']['after']
        base().verify(cur,state['predecessor'])
        removed=base().rollback_delta_preuse(cur,state['predecessor'])
        return dict(status='EXACT_CONSISTENT_READER_PREUSE_DELTA_INVERSE',opening_restored=True,predecessor=removed,
            all22_installed_parent_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_DDL=True,full_parent_inverse_repeated=False)


def rollback_preuse(cur,state):
    parent,_,_,predecessor,catalog=runtime()
    with predecessor.atomic(cur):
        predecessor.predecessor.predecessor._locks(cur)
        delta=rollback_delta_preuse(cur,state)
        removed=parent.rollback_preuse(cur,state['predecessor']['predecessor'])
        assert catalog._catalog_rows(cur)==state['before']and catalog._data(cur)==state['preinstall_data_and_sequences']
        return dict(status='EXACT_CONSISTENT_READER_PREUSE_INVERSE',delta=delta,predecessor=removed,
            all22_preinstall_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_DDL=True)
