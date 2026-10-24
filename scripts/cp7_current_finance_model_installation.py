"""A-owned current finance plus explicit policy and immutable evaluation v2.

Each stage is installed only after its actual predecessor is verified. Final
verification observes the real full22 catalog; no projected old catalog or
substituted definition. No default installation, connection, commit or schedule.
"""
from hashlib import sha256
from pathlib import Path
from datetime import datetime,timezone
import cp7_current_bounded_finance_installation as predecessor
import cp7_model_policy_stage as policy
import cp7_model_evaluation_v2_stage as evaluation

CONTRACT='cp7.current-AB-finance-policy-model-v2.v1'
USED_ERROR='CURRENT_FINANCE_MODEL_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=predecessor.catalog,predecessor.atomic
STAGES=(('MODEL_POLICY',policy),('MODEL_EVALUATION_V2',evaluation))
EMPTY=[0,sha256(b'[]').hexdigest()]


def sources():
    return dict(contract=CONTRACT,entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor=predecessor.sources(),stages={name:module.verify_sources()for name,module in STAGES})


def binding(prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],
        after=prior['after'],actual_verification=proof))


def stage_digest(state):
    """Bind the actual typed registry snapshot without changing its Native state.

    B's registry reader returns PostgreSQL timestamptz as an aware datetime.
    Only that declared column is encoded here, at full microsecond precision.
    Strings, naive clocks and other unsupported values are refused rather than
    accepted by a generic string fallback. All other stage members stay exact.
    """
    value=dict(state)
    if 'registry'in state:
        rows=[]
        for row in state['registry']:
            if(len(row)!=3 or not isinstance(row[0],str)or not isinstance(row[1],datetime)
               or row[1].utcoffset()is None or not isinstance(row[2],dict)):
                raise ValueError('CURRENT_FINANCE_MODEL_NATIVE_REGISTRY_TYPES_CHANGED')
            rows.append([row[0],{'native_timestamptz_UTC':row[1].astimezone(timezone.utc).isoformat(timespec='microseconds')},row[2]])
        value['registry']=rows
    return catalog.digest(value)


def admit_empty_tables(before,after,tables):
    """The only allowed data-key delta is the declared set of empty new tables."""
    expected=set(tables)
    if(expected&set(before)or set(before)-set(after)or set(after)-set(before)!=expected
       or any(after[k]!=value for k,value in before.items())
       or any(after[k]!=EMPTY for k in expected)):
        raise ValueError('CURRENT_FINANCE_MODEL_INSTALL_CHANGED_ROWS_OR_SEQUENCES')


def _verify_prefix(cur,state,count):
    catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('CURRENT_FINANCE_MODEL_SOURCE_CHANGED')
    prior=state['predecessor'];proof=state['predecessor_verified_before_delta']
    if(prior['sources']!=predecessor.sources()or binding(prior,proof)!=state['predecessor_binding_sha256']
       or proof.get('contract')!=predecessor.CONTRACT
       or proof.get('status')!='EXACT_CURRENT_BOUNDED_FINANCE_ALL22'
       or proof.get('predecessor_verified_before_actual_delta')is not True
       or proof.get('all22_transition_chain_verified')is not True
       or proof.get('substituted_catalog_or_definitions')is not False
       or state['before']!=prior['before']):
        raise ValueError('CURRENT_FINANCE_MODEL_PREDECESSOR_BINDING_CHANGED')
    if len(state['stages'])!=count or not 1<=count<=len(STAGES):
        raise ValueError('CURRENT_FINANCE_MODEL_STAGE_COUNT_CHANGED')
    left=prior['after'];data=prior['preuse_data_and_sequences']
    for row,(name,module)in zip(state['stages'],STAGES[:count]):
        if(row['name']!=name or row['before']!=left or row['data_before']!=data
           or row['state']['sources']!=module.verify_sources()
           or row['verified_state_sha256']!=stage_digest(row['state'])
           or row['verified_on_actual_database'].get('stage')!=('cp7.model-policy-stage.v1'if name=='MODEL_POLICY'else'cp7.model-evaluation-v2-stage.v1')):
            raise ValueError('CURRENT_FINANCE_MODEL_TRANSITION_CHANGED: '+name)
        module.admit_catalog(left,row['after'],row['state'])
        admit_empty_tables(data,row['data_after'],module.TABLES)
        left,data=row['after'],row['data_after']
    actual=catalog._catalog_rows(cur)
    if len(actual)!=22 or actual!=left:raise ValueError('CURRENT_FINANCE_MODEL_LIVE_FULL22_CHANGED')
    # Both additive stages retain their own exact catalogs and dependencies.
    # The finance predecessor was checked before additions and is bound above.
    for row,(_,module)in zip(state['stages'],STAGES[:count]):module.verify(cur,row['state'])
    return dict(contract=CONTRACT,status='EXACT_CURRENT_FINANCE_MODEL_PREFIX',stage_count=count,
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
            module.admit_catalog(left,right,stage);admit_empty_tables(rows,after_rows,module.TABLES)
            verified=module.verify(cur,stage)
            state['stages'].append(dict(name=name,state=stage,before=left,after=right,
                data_before=rows,data_after=after_rows,verified_on_actual_database=verified,
                verified_state_sha256=stage_digest(stage)))
            _verify_prefix(cur,state,index+1)
        state['after']=catalog._catalog_rows(cur);state['preuse_data_and_sequences']=catalog._data(cur)
        verify(cur,state)
        return state


def verify(cur,state):
    _verify_prefix(cur,state,len(STAGES))
    if(state['after']!=state['stages'][-1]['after']
       or state['preuse_data_and_sequences']!=state['stages'][-1]['data_after']):
        raise ValueError('CURRENT_FINANCE_MODEL_FINAL_BINDING_CHANGED')
    return dict(contract=CONTRACT,status='EXACT_CURRENT_FINANCE_MODEL_ALL22',
        predecessor_verified_before_actual_delta=True,all22_transition_chain_verified=True,
        substituted_catalog_or_definitions=False,model_private_functions=14,model_public_rpcs=4,
        model_tables=3,model_old_replacements=0,model_install_preserved_every_old_row_and_sequence=True,
        default_owner_policy_created=False,forecast_applied=False,installed_schedules=False,
        full_OW11_acceptance=False,production_go=False,independent_acceptance=False)


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
                raise ValueError('CURRENT_FINANCE_MODEL_STAGE_INVERSE_NOT_EXACT: '+name)
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_FINANCE_MODEL_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_CURRENT_FINANCE_MODEL_PREUSE_INVERSE',predecessor=removed,
            all22_preinstall_equal=True,all_rows_and_sequences_equal=True,global_used_guard_before_any_DDL=True,
            production_go=False,independent_acceptance=False)
