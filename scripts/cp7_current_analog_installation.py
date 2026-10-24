"""Explicit A-owned composition of corrected current ERP and B analog metadata.

All original stages stay source-frozen. Each preceding verifier executes on
the real database before the next delta. No connection, commit or schedule.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_return_installation as predecessor
import cp7_product_analog_reader_stage as reader
import cp7_product_analog_choice_stage as choice

CONTRACT='cp7.current-AB-return-with-analog-metadata.v1'
USED_ERROR='CURRENT_ANALOG_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=predecessor.catalog,predecessor.atomic
STAGES=(('ANALOG_READER',reader),('ANALOG_CHOICE',choice))


def sources():
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor=predecessor.sources(),stages={name:module.verify_sources()for name,module in STAGES})


def _verify_prefix(cur,state,count):
    if state['sources']!=sources():raise ValueError('CURRENT_ANALOG_SOURCE_CHANGED')
    previous=state['predecessor'];proof=state['predecessor_verified_before_delta']
    if(previous['sources']!=predecessor.sources()
       or proof.get('contract')!=predecessor.CONTRACT
       or proof.get('status')!='CURRENT_AB_DRAFT_RETURN_EXACT_ALL22'
       or proof.get('predecessor_verified_before_actual_delta')is not True
       or previous['delta']['after']!=predecessor.delta.expected(previous['delta']['before'])
       or previous['after']!=previous['delta']['after']
       or previous['delta']['before']!=previous['predecessor']['after']
       or state['before']!=previous['before']):
        raise ValueError('CURRENT_ANALOG_PREDECESSOR_BINDING_CHANGED')
    if len(state['stages'])!=count:raise ValueError('CURRENT_ANALOG_STAGE_COUNT_CHANGED')
    left=previous['after']
    for row,(name,module)in zip(state['stages'],STAGES[:count]):
        if row['name']!=name or row['before']!=left:
            raise ValueError('CURRENT_ANALOG_CATALOG_TRANSITION_CHANGED: '+name)
        module.admit_catalog(row['before'],row['after'],row['state'])
        module.verify(cur,row['state'])
        left=row['after']
    actual=catalog._catalog_rows(cur)
    if len(actual)!=22 or actual!=left:
        raise ValueError('CURRENT_ANALOG_LIVE_FULL22_CHANGED')
    return dict(contract=CONTRACT,status='EXACT_CURRENT_ANALOG_PREFIX',stage_count=count,
        predecessor_verifier_executed_before_actual_delta=True,substituted_catalog=False)


def install(cur):
    with atomic(cur):
        authority=catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        previous=predecessor.install(cur)
        proof=predecessor.verify(cur,previous)
        state=dict(sources=sources(),authority=authority,before=before,
            preinstall_data_and_sequences=data,predecessor=previous,
            predecessor_verified_before_delta=proof,stages=[])
        for index,(name,module)in enumerate(STAGES):
            left=catalog._catalog_rows(cur)
            check=(lambda c:predecessor.verify(c,previous))if index==0 else(lambda c:_verify_prefix(c,state,index))
            installed=module.install_delta(cur,check)
            right=catalog._catalog_rows(cur)
            module.admit_catalog(left,right,installed)
            actual_proof=module.verify(cur,installed)
            state['stages'].append(dict(name=name,state=installed,before=left,after=right,
                verified_on_actual_database=actual_proof))
            _verify_prefix(cur,state,index+1)
        state['after']=catalog._catalog_rows(cur)
        state['preuse_data_and_sequences']=catalog._data(cur)
        verify(cur,state)
        return state


def verify(cur,state):
    _verify_prefix(cur,state,len(STAGES))
    if state['after']!=state['stages'][-1]['after']:
        raise ValueError('CURRENT_ANALOG_FINAL_CATALOG_CHANGED')
    return dict(contract=CONTRACT,status='EXACT_CURRENT_AB_RETURN_ANALOG_ALL22',
        stages=[name for name,_ in STAGES],new_analog_tables=2,new_analog_public_rpcs=3,
        old_functions_replaced_by_analog=0,predecessor_verified_before_actual_delta=True,
        all22_transition_chain_verified=True,substituted_catalog_or_definitions=False,
        installed_schedules=False,forecast_applied=False,hosted_installation=False,
        production_go=False,independent_acceptance=False)


def rollback_preuse(cur,state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        verify(cur,state)
        # Check every actual row and sequence BEFORE dropping even one new
        # function or table. Empty analog tables do not make ERP use reversible.
        catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        for row,(name,module)in reversed(list(zip(state['stages'],STAGES))):
            module.verify(cur,row['state'])
            if name=='ANALOG_CHOICE':module.rollback_preuse(cur,row['state'])
            else:module.rollback_readonly(cur,row['state'])
            if catalog._catalog_rows(cur)!=row['before']:
                raise ValueError('CURRENT_ANALOG_STAGE_INVERSE_NOT_EXACT: '+name)
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_ANALOG_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_CURRENT_ANALOG_PREUSE_INVERSE',
            predecessor=removed,all22_preinstall_equal=True,all_rows_and_sequences_equal=True,
            global_used_guard_before_any_DDL=True,production_go=False,independent_acceptance=False)
