"""A-owned optional composition; actual predecessors verified before each delta.

No default installation or schedule registration. The final real catalog is
checked in full; earlier definitions are never substituted into a verifier.
"""
from hashlib import sha256
from pathlib import Path
import json
import cp7_current_analysis_progress.installation as predecessor
import cp7_frozen_analysis_readers_v2 as readers
import cp7_frozen_analysis_choice_v2 as choice
import cp7_frozen_choice_preparation as preparation
from . import hooks

ROOT=Path(__file__).resolve().parent
CONTRACT='cp7.current-AB-frozen-choice-preparation.v1'
USED_ERROR='CURRENT_CHOICE_PREPARATION_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=predecessor.catalog,predecessor.atomic
STAGES=(('READERS',readers),('CHOICE',choice),('PREPARATION',preparation),('SERVER_HOOKS',hooks))
PUBLIC={readers.render.PUBLIC+'('+readers.render.ARGS+')':'CANDIDATE_READ',
        choice.render.PUBLIC+'(jsonb,uuid)':'CHOICE_SAVE',
        **{sig:'PREPARATION_'+verb.upper()for sig,verb in preparation.render.PUBLIC.items()}}
EMPTY_WORK={preparation.SCHEMA+'.work':[0,sha256(b'[]').hexdigest()]}

def sources():
    pins=json.loads((ROOT/'B_SOURCE.json').read_bytes())
    for rel,digest in pins['files'].items():
        if sha256((ROOT.parents[1]/rel).read_bytes()).hexdigest()!=digest:
            raise ValueError('CURRENT_CHOICE_EXACT_B_SOURCE_CHANGED:'+rel)
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        B_source=pins,predecessor=predecessor.sources(),public_rpc_registry=PUBLIC,
        stages={name:module.verify_sources()for name,module in STAGES})

def binding(prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],actual_verification=proof))

def admit_delta(module,before,after,state):
    if set(before)!=set(after)or len(before)!=22 or module.own(after)!=state['catalog']:
        raise ValueError('CURRENT_CHOICE_FULL22_TRANSITION_REQUIRED')
    replacements=state.get('old_replacements',{})
    changed=set()
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            changed.add((group,key))
            if new!=state['catalog'][group].get(key):raise ValueError('CURRENT_CHOICE_UNDECLARED_DELTA:'+group+':'+key)
            if old is None:continue
            if (group=='functions'and key in replacements and old[1:]==new[1:]
                and old[0]==replacements[key][0]and new[0]==state['rows'][key][0]):continue
            raise ValueError('CURRENT_CHOICE_EXISTING_AUTHORITY_CHANGED:'+group+':'+key)
    expected={(g,k)for g,rows in state['catalog'].items()for k in rows}
    if changed!=expected:raise ValueError('CURRENT_CHOICE_INCOMPLETE_DELTA')

def _verify_prefix(cur,state,count):
    catalog._authority(cur)
    prior=state['predecessor'];proof=state['predecessor_verified_before_delta']
    if (state['sources']!=sources()or prior['sources']!=predecessor.sources()
        or binding(prior,proof)!=state['predecessor_binding_sha256']
        or proof.get('contract')!=predecessor.CONTRACT
        or proof.get('status')!='EXACT_CURRENT_FROZEN_PROGRESS_ALL22'
        or proof.get('all22_transition_chain_verified')is not True
        or proof.get('substituted_catalog_or_definitions')is not False
        or state['before']!=prior['before']
        or state['preinstall_data_and_sequences']!=prior['preinstall_data_and_sequences']):
        raise ValueError('CURRENT_CHOICE_PREDECESSOR_BINDING_CHANGED')
    if len(state['stages'])!=count or not 1<=count<=len(STAGES):raise ValueError('CURRENT_CHOICE_STAGE_COUNT_CHANGED')
    left=prior['after']
    for row,(name,module)in zip(state['stages'],STAGES[:count]):
        if (row['name']!=name or row['before']!=left or row['state']['sources']!=module.verify_sources()
            or row['verified_state_sha256']!=catalog.digest(row['state'])
            or row['verification_binding']!=catalog.digest(dict(state=row['state'],proof=row['verified_on_actual_database']))):
            raise ValueError('CURRENT_CHOICE_BOUND_STAGE_CHANGED:'+name)
        admit_delta(module,left,row['after'],row['state']);left=row['after']
    if catalog._catalog_rows(cur)!=left:raise ValueError('CURRENT_CHOICE_ACTUAL_FULL22_CHANGED')
    STAGES[count-1][1].verify(cur,state['stages'][-1]['state'])
    return dict(contract=CONTRACT,status='EXACT_CURRENT_CHOICE_PREFIX',stage_count=count,
        predecessor_verified_on_actual_database=True,substituted_catalog_or_definitions=False)

def _data_transition(name,before,after):
    expected={**before,**EMPTY_WORK}if name=='PREPARATION'else before
    if name=='PREPARATION'and any(k in before for k in EMPTY_WORK):raise ValueError('CURRENT_CHOICE_WORK_ALREADY_EXISTS')
    if after!=expected:raise ValueError('CURRENT_CHOICE_INSTALL_CHANGED_ROWS_OR_SEQUENCES:'+name)

def install(cur):
    with atomic(cur):
        predecessor.predecessor._locks(cur)
        before,data=catalog._catalog_rows(cur),catalog._data(cur)
        prior=predecessor.install(cur);proof=predecessor.verify(cur,prior)
        state=dict(sources=sources(),before=before,preinstall_data_and_sequences=data,predecessor=prior,
            predecessor_verified_before_delta=proof,predecessor_binding_sha256=binding(prior,proof),stages=[])
        for index,(name,module)in enumerate(STAGES):
            left,rows=catalog._catalog_rows(cur),catalog._data(cur)
            checker=(lambda c:predecessor.verify(c,prior))if index==0 else(lambda c:_verify_prefix(c,state,index))
            delta=module.install_delta(cur,checker);right=catalog._catalog_rows(cur)
            admit_delta(module,left,right,delta);actual=module.verify(cur,delta)
            _data_transition(name,rows,catalog._data(cur))
            state['stages'].append(dict(name=name,state=delta,before=left,after=right,
                verified_on_actual_database=actual,verified_state_sha256=catalog.digest(delta),
                verification_binding=catalog.digest(dict(state=delta,proof=actual))))
            _verify_prefix(cur,state,index+1)
        state['after']=catalog._catalog_rows(cur);state['preuse_data_and_sequences']=catalog._data(cur)
        verify(cur,state);return state

def verify(cur,state):
    _verify_prefix(cur,state,len(STAGES))
    if state['after']!=state['stages'][-1]['after']or state['preuse_data_and_sequences']!={**state['predecessor']['preuse_data_and_sequences'],**EMPTY_WORK}:
        raise ValueError('CURRENT_CHOICE_FINAL_BINDING_CHANGED')
    added_public={k for k in state['after']['functions']if k.startswith('public.')and k not in state['predecessor']['after']['functions']}
    if added_public!=set(PUBLIC):raise ValueError('CURRENT_CHOICE_PUBLIC_REGISTRY_CHANGED')
    for sig in PUBLIC:
        for role in ('anon','authenticated','service_role','cp7_alert'):
            if cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,sig)).fetchone()[0]is not(role=='authenticated'):
                raise ValueError('CURRENT_CHOICE_RPC_EXECUTE_CHANGED:'+sig+':'+role)
    return dict(contract=CONTRACT,status='EXACT_CURRENT_FROZEN_CHOICE_PREPARATION_ALL22',
        predecessor_verified_before_actual_delta=True,all22_transition_chain_verified=True,
        substituted_catalog_or_definitions=False,new_public_rpcs=5,new_tables=1,
        official_finance_source_reused=True,existing_K4_dispatch_composed=True,
        existing_retention_composed=True,schedules_registered=False,unit_timeouts_changed=False,
        default_adopted=False,full_final_acceptance=False,production_go=False)

def rollback_preuse(cur,state):
    with atomic(cur):
        predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        for row,(name,module)in reversed(list(zip(state['stages'],STAGES))):
            module.verify(cur,row['state']);module.rollback_preuse(cur,row['state'])
            if catalog._catalog_rows(cur)!=row['before']:raise ValueError('CURRENT_CHOICE_STAGE_INVERSE_NOT_EXACT:'+name)
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_CHOICE_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_CURRENT_CHOICE_PREUSE_INVERSE',predecessor=removed,
            all22_preinstall_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_any_DDL=True,production_go=False)
