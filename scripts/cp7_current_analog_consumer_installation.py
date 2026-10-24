"""A-owned full current ERP plus reviewed analog consumer and provenance.

Each predecessor verifier runs on its actual database before the declared
replacement. Later verification checks the complete real 22-group catalog;
it never substitutes an old definition or projects a catalog for an old check.
No default installation, connection, commit, schedule or production admission.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_analog_installation as predecessor
import cp7_product_analog_consumer_stage as consumer
import cp7_product_analog_provenance_stage as provenance

CONTRACT='cp7.current-AB-return-analog-consumer.v1'
USED_ERROR='CURRENT_ANALOG_CONSUMER_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=predecessor.catalog,predecessor.atomic
choice=predecessor.choice
STAGES=(('ANALOG_CONSUMER',consumer),('ANALOG_PROVENANCE',provenance))


def sources():
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor=predecessor.sources(),stages={name:module.verify_sources()for name,module in STAGES})


def _predecessor_binding(prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],
        after=prior['after'],actual_verification=proof))


def _admit_provenance(before,after,state):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('CURRENT_CONSUMER_PROVENANCE_FULL22_REQUIRED')
    if provenance.own_catalog(after)!=state['catalog']:
        raise ValueError('CURRENT_CONSUMER_PROVENANCE_CATALOG_BINDING_CHANGED')
    allowed=set(provenance.render.originals())|{provenance.FUNCTION}
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if(group=='functions'and key in allowed and new==state['catalog'][group].get(key)
               and(key in state['old_rows']or old is None)):
                continue
            raise ValueError('CURRENT_CONSUMER_PROVENANCE_UNDECLARED_DELTA: '+group+':'+key)


def _verify_prefix(cur,state,count):
    catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('CURRENT_CONSUMER_SOURCE_CHANGED')
    prior=state['predecessor'];proof=state['predecessor_verified_before_delta']
    if(prior['sources']!=predecessor.sources()
       or _predecessor_binding(prior,proof)!=state['predecessor_binding_sha256']
       or proof.get('contract')!=predecessor.CONTRACT
       or proof.get('status')!='EXACT_CURRENT_AB_RETURN_ANALOG_ALL22'
       or proof.get('predecessor_verified_before_actual_delta')is not True
       or proof.get('all22_transition_chain_verified')is not True
       or proof.get('substituted_catalog_or_definitions')is not False
       or state['before']!=prior['before']):
        raise ValueError('CURRENT_CONSUMER_PREDECESSOR_BINDING_CHANGED')
    if len(state['stages'])!=count or not 1<=count<=len(STAGES):
        raise ValueError('CURRENT_CONSUMER_STAGE_COUNT_CHANGED')
    left=prior['after']
    for row,(name,module)in zip(state['stages'],STAGES[:count]):
        if(row['name']!=name or row['before']!=left
           or row['state']['sources']!=module.verify_sources()
           or row['verified_state_sha256']!=catalog.digest(row['state'])):
            raise ValueError('CURRENT_CONSUMER_CATALOG_TRANSITION_CHANGED: '+name)
        if name=='ANALOG_CONSUMER':module.admit_catalog(left,row['after'],row['state'])
        else:_admit_provenance(left,row['after'],row['state'])
        left=row['after']
    actual=catalog._catalog_rows(cur)
    if len(actual)!=22 or actual!=left:
        raise ValueError('CURRENT_CONSUMER_LIVE_FULL22_CHANGED')
    # Earlier definitions are intentionally replaced. Only the latest verifier
    # is applicable to the current database, with every earlier transition bound
    # above and every untouched catalog member equal to the original observation.
    STAGES[count-1][1].verify(cur,state['stages'][-1]['state'])
    return dict(contract=CONTRACT,status='EXACT_CURRENT_CONSUMER_PREFIX',stage_count=count,
        predecessor_verified_on_actual_database=True,substituted_catalog_or_definitions=False)


def install(cur):
    with atomic(cur):
        authority=catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        prior=predecessor.install(cur)
        proof=predecessor.verify(cur,prior)
        state=dict(sources=sources(),authority=authority,before=before,
            preinstall_data_and_sequences=data,predecessor=prior,
            predecessor_binding_sha256=_predecessor_binding(prior,proof),
            predecessor_verified_before_delta=proof,stages=[])
        for index,(name,module)in enumerate(STAGES):
            left=catalog._catalog_rows(cur);rows=catalog._data(cur)
            checker=(lambda c:predecessor.verify(c,prior))if index==0 else(lambda c:_verify_prefix(c,state,index))
            installed=module.install_delta(cur,checker)
            right=catalog._catalog_rows(cur)
            if name=='ANALOG_CONSUMER':module.admit_catalog(left,right,installed)
            else:_admit_provenance(left,right,installed)
            actual_proof=module.verify(cur,installed)
            if catalog._data(cur)!=rows:raise ValueError('CURRENT_CONSUMER_OVERLAY_CHANGED_ROWS_OR_SEQUENCES: '+name)
            state['stages'].append(dict(name=name,state=installed,before=left,after=right,
                verified_on_actual_database=actual_proof,verified_state_sha256=catalog.digest(installed)))
            _verify_prefix(cur,state,index+1)
        state['after']=catalog._catalog_rows(cur)
        state['preuse_data_and_sequences']=catalog._data(cur)
        verify(cur,state)
        return state


def verify(cur,state):
    _verify_prefix(cur,state,len(STAGES))
    if state['after']!=state['stages'][-1]['after']:
        raise ValueError('CURRENT_CONSUMER_FINAL_CATALOG_CHANGED')
    return dict(contract=CONTRACT,status='EXACT_CURRENT_AB_ANALOG_CONSUMER_ALL22',
        consumer_private_functions=7,consumer_replacements=18,
        provenance_private_functions=1,provenance_replacements=4,
        overlay_new_tables=0,overlay_new_public_rpcs=0,
        predecessor_verified_before_actual_delta=True,all22_transition_chain_verified=True,
        substituted_catalog_or_definitions=False,reviewed_analog_used_in_fresh_captures=True,
        installed_schedules=False,hosted_installation=False,full_OW11_acceptance=False,
        production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        verify(cur,state)
        catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        for row,(name,module)in reversed(list(zip(state['stages'],STAGES))):
            module.verify(cur,row['state'])
            module.rollback_preuse(cur,row['state'])
            if catalog._catalog_rows(cur)!=row['before']:
                raise ValueError('CURRENT_CONSUMER_STAGE_INVERSE_NOT_EXACT: '+name)
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_CONSUMER_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_CURRENT_CONSUMER_PREUSE_INVERSE',predecessor=removed,
            all22_preinstall_equal=True,all_rows_and_sequences_equal=True,
            global_used_guard_before_any_DDL=True,production_go=False,independent_acceptance=False)
