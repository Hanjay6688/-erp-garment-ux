"""A-owned full scoped-model chain plus exact versioned target transition.

Each predecessor is verified on the actual database before the next replacement.
The complete22 catalog and every data/sequence key remain bound across stages.
No default install, owner policy, financial writer, connection or commit.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_scoped_model_installation as predecessor
import cp7_model_evaluation_selection as selection
import cp7_model_target_binding as physical
import cp7_current_versioned_target_delta as target

CONTRACT='cp7.current-AB-finance-scoped-versioned-target.v1'
USED_ERROR='CURRENT_VERSIONED_TARGET_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=predecessor.catalog,predecessor.atomic
STAGES=(('MODEL_SELECTION',selection),('PHYSICAL_BINDING',physical),('VERSIONED_TARGET',target))
STAGE_CONTRACTS=('cp7.model-evaluation-selection-stage.v1','cp7.model-target-physical-binding-stage.v1',target.CONTRACT)


def sources():
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor=predecessor.sources(),stages={name:module.verify_sources()for name,module in STAGES})


def binding(prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],
        actual_verification=proof))


def admit_catalog(before,after,state,name):
    if name == 'VERSIONED_TARGET':
        return target.admit_catalog(before,after,state)
    modules = {'MODEL_SELECTION':selection,'PHYSICAL_BINDING':physical}
    if name not in modules:
        raise ValueError('CURRENT_VERSIONED_TARGET_UNDECLARED_STAGE')
    module = modules[name]
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('CURRENT_VERSIONED_TARGET_CATALOG_GROUPS_CHANGED')
    if module.own_catalog(after) != state['catalog']:
        raise ValueError('CURRENT_VERSIONED_TARGET_STAGE_CATALOG_CHANGED')
    expected = {('functions',key) for key in module.FUNCTIONS}|{('schemas',module.SCHEMA)}
    observed = set()
    for group in before:
        for key in set(before[group])|set(after[group]):
            left,right = before[group].get(key),after[group].get(key)
            if left == right:
                continue
            if (group,key) not in expected or left is not None or right is None:
                raise ValueError('CURRENT_VERSIONED_TARGET_UNDECLARED_CATALOG_DELTA: '+group+':'+key)
            observed.add((group,key))
    if observed != expected:
        raise ValueError('CURRENT_VERSIONED_TARGET_INCOMPLETE_CATALOG_DELTA')


def admit_data(before,after):
    if before!=after:
        raise ValueError('CURRENT_VERSIONED_TARGET_INSTALL_CHANGED_ROWS_OR_SEQUENCES')


def _verify_prefix(cur,state,count):
    catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('CURRENT_VERSIONED_TARGET_SOURCE_CHANGED')
    prior=state['predecessor'];proof=state['predecessor_verified_before_delta']
    if(prior['sources']!=predecessor.sources()or state['before']!=prior['before']
       or state['predecessor_binding_sha256']!=binding(prior,proof)
       or proof.get('contract')!=predecessor.CONTRACT
       or proof.get('status')!='EXACT_CURRENT_SCOPED_MODEL_ALL22'
       or proof.get('predecessor_verified_before_actual_delta')is not True
       or proof.get('all22_transition_chain_verified')is not True
       or proof.get('substituted_catalog_or_definitions')is not False
       or proof.get('scoped_model_tables')!=1 or proof.get('scoped_model_public_rpcs')!=2
       or proof.get('scoped_model_old_replacements')!=0
       or proof.get('exact_parent_FK_trigger_additions')!=sorted(predecessor.runtime.FK_TRIGGERS)):
        raise ValueError('CURRENT_VERSIONED_TARGET_PREDECESSOR_BINDING_CHANGED')
    if len(state['stages'])!=count or not 1<=count<=len(STAGES):
        raise ValueError('CURRENT_VERSIONED_TARGET_STAGE_COUNT_CHANGED')
    left=prior['after'];data=prior['preuse_data_and_sequences']
    for index,(row,(name,module))in enumerate(zip(state['stages'],STAGES[:count])):
        if(row['name']!=name or row['before']!=left or row['data_before']!=data
           or row['state']['sources']!=module.verify_sources()
           or row['verified_state_sha256']!=catalog.digest(row['state'])
           or row['verified_on_actual_database'].get('stage')!=STAGE_CONTRACTS[index]):
            raise ValueError('CURRENT_VERSIONED_TARGET_TRANSITION_CHANGED: '+name)
        admit_catalog(left,row['after'],row['state'],name)
        admit_data(data,row['data_after'])
        left,data=row['after'],row['data_after']
    actual=catalog._catalog_rows(cur)
    if len(actual)!=22 or actual!=left:raise ValueError('CURRENT_VERSIONED_TARGET_LIVE_FULL22_CHANGED')
    # A later replacement supersedes earlier exact dependencies. Each earlier
    # verifier ran before that replacement and its receipt is bound above.
    # The final stage checks its real objects and every unmodified dependency.
    STAGES[count-1][1].verify(cur,state['stages'][-1]['state'])
    return dict(contract=CONTRACT,status='EXACT_CURRENT_VERSIONED_TARGET_PREFIX',stage_count=count,
        predecessor_verified_on_actual_database=True,substituted_catalog_or_definitions=False)


def install(cur):
    with atomic(cur):
        authority=catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        catalog._lock_tables(cur)
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        prior=predecessor.install(cur);proof=predecessor.verify(cur,prior)
        state=dict(sources=sources(),authority=authority,before=before,preinstall_data_and_sequences=data,
            predecessor=prior,predecessor_verified_before_delta=proof,
            predecessor_binding_sha256=binding(prior,proof),stages=[])
        for index,(name,module)in enumerate(STAGES):
            left=catalog._catalog_rows(cur);rows=catalog._data(cur)
            checker=(lambda c:predecessor.verify(c,prior))if index==0 else(lambda c:_verify_prefix(c,state,index))
            stage=module.install_delta(cur,checker)
            right=catalog._catalog_rows(cur);after_rows=catalog._data(cur)
            admit_catalog(left,right,stage,name);admit_data(rows,after_rows)
            verified=module.verify(cur,stage)
            state['stages'].append(dict(name=name,state=stage,before=left,after=right,
                data_before=rows,data_after=after_rows,verified_on_actual_database=verified,
                verified_state_sha256=catalog.digest(stage)))
            _verify_prefix(cur,state,index+1)
        state['after']=catalog._catalog_rows(cur);state['preuse_data_and_sequences']=catalog._data(cur)
        verify(cur,state);return state


def verify(cur,state):
    _verify_prefix(cur,state,len(STAGES))
    if(state['after']!=state['stages'][-1]['after']or state['preuse_data_and_sequences']!=state['stages'][-1]['data_after']):
        raise ValueError('CURRENT_VERSIONED_TARGET_FINAL_BINDING_CHANGED')
    return dict(contract=CONTRACT,status='EXACT_CURRENT_VERSIONED_TARGET_ALL22',
        predecessor_verified_before_actual_delta=True,all22_transition_chain_verified=True,
        substituted_catalog_or_definitions=False,target_replacements=14,named_hooks_verified=21,unchanged_hooks_retained=7,
        new_private_functions=len(selection.FUNCTIONS)+len(physical.FUNCTIONS)+len(target.FUNCTIONS),
        new_schemas=4,new_tables=0,new_public_rpcs=0,legacy_target_objects_retained=True,
        every_old_row_and_sequence_preserved=True,default_owner_policy_created=False,
        installed_schedules=False,full_OW11_acceptance=False,production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        for row,(name,module)in reversed(list(zip(state['stages'],STAGES))):
            module.rollback_preuse(cur,row['state'])
            if catalog._catalog_rows(cur)!=row['before']or catalog._data(cur)!=row['data_before']:
                raise ValueError('CURRENT_VERSIONED_TARGET_STAGE_INVERSE_NOT_EXACT: '+name)
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_VERSIONED_TARGET_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_CURRENT_VERSIONED_TARGET_PREUSE_INVERSE',predecessor=removed,
            all22_preinstall_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_any_DDL=True,
            production_go=False,independent_acceptance=False)
