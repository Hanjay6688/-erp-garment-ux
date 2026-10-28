"""Optional full-current composition of scoped source and immutable history.

No model caller/default install is changed. Every stage verifies its real
predecessor before additions. Exact22 catalog and all row/sequence keys bind the
transition; no projected old catalog or substituted definition is accepted.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_model_target_installation as predecessor
import cp7_model_history_scope as scope
import cp7_model_history_runtime as runtime

CONTRACT = 'cp7.current-AB-finance-target-scoped-history.v1'
USED_ERROR = 'CURRENT_MODEL_HISTORY_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog, atomic = predecessor.catalog, predecessor.atomic
STAGES = (('SCOPED_HISTORY_SOURCE', scope), ('IMMUTABLE_HISTORY_RUNTIME', runtime))
CONTRACTS = ('cp7.model-history-scope-stage.v1', 'cp7.model-history-runtime-stage.v1')
EMPTY = [0, sha256(b'[]').hexdigest()]


def sources():
    return dict(contract=CONTRACT, entrypoint_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                predecessor=predecessor.sources(), stages={name:module.verify_sources() for name,module in STAGES})


def binding(prior, proof):
    return catalog.digest(dict(sources=prior['sources'], before=prior['before'],
                               after=prior['after'], actual_verification=proof))


def admit_catalog(before, after, state, module):
    if set(before) != set(after) or len(before) != 22:
        raise ValueError('CURRENT_MODEL_HISTORY_CATALOG_GROUPS_CHANGED')
    if module.own_catalog(after) != state['catalog']:
        raise ValueError('CURRENT_MODEL_HISTORY_STAGE_CATALOG_CHANGED')
    expected = {(group,key) for group,rows in state['catalog'].items() for key in rows}
    observed = set()
    for group in before:
        for key in set(before[group]) | set(after[group]):
            old, new = before[group].get(key), after[group].get(key)
            if old == new:
                continue
            if old is not None or new is None or not module.declared(group,key) or (group,key) not in expected:
                raise ValueError('CURRENT_MODEL_HISTORY_UNDECLARED_CATALOG_DELTA: '+group+':'+key)
            observed.add((group,key))
    if observed != expected:
        raise ValueError('CURRENT_MODEL_HISTORY_INCOMPLETE_CATALOG_DELTA')


def admit_data(before, after, module):
    expected = {runtime.TABLE} if module is runtime else set()
    if (expected & set(before) or set(before) - set(after) or set(after) - set(before) != expected
            or any(after[key] != value for key,value in before.items())
            or any(after[key] != EMPTY for key in expected)):
        raise ValueError('CURRENT_MODEL_HISTORY_INSTALL_CHANGED_ROWS_OR_SEQUENCES')


def _verify_prefix(cur, state, count):
    catalog._authority(cur)
    if state['sources'] != sources():
        raise ValueError('CURRENT_MODEL_HISTORY_SOURCE_CHANGED')
    prior, proof = state['predecessor'], state['predecessor_verified_before_delta']
    if (prior['sources'] != predecessor.sources() or state['before'] != prior['before']
            or state['predecessor_binding_sha256'] != binding(prior,proof)
            or proof.get('contract') != predecessor.CONTRACT
            or proof.get('status') != 'EXACT_CURRENT_MODEL_TARGET_ALL22'
            or proof.get('predecessor_verified_before_actual_delta') is not True
            or proof.get('all22_transition_chain_verified') is not True
            or proof.get('substituted_catalog_or_definitions') is not False
            or proof.get('target_replacements') != 21):
        raise ValueError('CURRENT_MODEL_HISTORY_PREDECESSOR_BINDING_CHANGED')
    if len(state['stages']) != count or not 1 <= count <= len(STAGES):
        raise ValueError('CURRENT_MODEL_HISTORY_STAGE_COUNT_CHANGED')
    left, data = prior['after'], prior['preuse_data_and_sequences']
    for index,(row,(name,module)) in enumerate(zip(state['stages'],STAGES[:count])):
        if (row['name'] != name or row['before'] != left or row['data_before'] != data
                or row['state']['sources'] != module.verify_sources()
                or row['verified_state_sha256'] != catalog.digest(row['state'])
                or row['verified_on_actual_database'].get('stage') != CONTRACTS[index]):
            raise ValueError('CURRENT_MODEL_HISTORY_TRANSITION_CHANGED: '+name)
        admit_catalog(left,row['after'],row['state'],module)
        admit_data(data,row['data_after'],module)
        left, data = row['after'], row['data_after']
    actual = catalog._catalog_rows(cur)
    if len(actual) != 22 or actual != left:
        raise ValueError('CURRENT_MODEL_HISTORY_LIVE_FULL22_CHANGED')
    for row,(_,module) in zip(state['stages'],STAGES[:count]):
        module.verify(cur,row['state'])
    return dict(contract=CONTRACT, status='EXACT_CURRENT_MODEL_HISTORY_PREFIX', stage_count=count,
                predecessor_verified_on_actual_database=True, substituted_catalog_or_definitions=False)


def install(cur):
    with atomic(cur):
        authority = catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        catalog._lock_tables(cur)
        before, data = catalog._catalog_rows(cur), catalog._data(cur)
        prior = predecessor.install(cur)
        proof = predecessor.verify(cur,prior)
        state = dict(sources=sources(), authority=authority, before=before, preinstall_data_and_sequences=data,
                     predecessor=prior, predecessor_verified_before_delta=proof,
                     predecessor_binding_sha256=binding(prior,proof), stages=[])
        for index,(name,module) in enumerate(STAGES):
            left, rows = catalog._catalog_rows(cur), catalog._data(cur)
            checker = (lambda c:predecessor.verify(c,prior)) if index == 0 else (lambda c:_verify_prefix(c,state,index))
            stage = module.install_delta(cur,checker)
            right, after_rows = catalog._catalog_rows(cur), catalog._data(cur)
            admit_catalog(left,right,stage,module)
            admit_data(rows,after_rows,module)
            verified = module.verify(cur,stage)
            state['stages'].append(dict(name=name, state=stage, before=left, after=right,
                                       data_before=rows, data_after=after_rows,
                                       verified_on_actual_database=verified,
                                       verified_state_sha256=catalog.digest(stage)))
            _verify_prefix(cur,state,index+1)
        state['after'] = catalog._catalog_rows(cur)
        state['preuse_data_and_sequences'] = catalog._data(cur)
        verify(cur,state)
        return state


def verify(cur, state):
    _verify_prefix(cur,state,len(STAGES))
    if (state['after'] != state['stages'][-1]['after']
            or state['preuse_data_and_sequences'] != state['stages'][-1]['data_after']):
        raise ValueError('CURRENT_MODEL_HISTORY_FINAL_BINDING_CHANGED')
    return dict(contract=CONTRACT, status='EXACT_CURRENT_MODEL_HISTORY_ALL22',
                predecessor_verified_before_actual_delta=True, all22_transition_chain_verified=True,
                substituted_catalog_or_definitions=False,
                scoped_history_private_functions=len(scope.FUNCTIONS)+len(runtime.FUNCTIONS)-len(runtime.PUBLIC),
                scoped_history_public_rpcs=len(runtime.PUBLIC), scoped_history_tables=1, scoped_history_old_replacements=0,
                installation_preserved_every_old_row_and_sequence=True, default_owner_policy_created=False,
                model_caller_integrated=False, forecast_applied=False, installed_schedules=False,
                full_OW11_acceptance=False, production_go=False, independent_acceptance=False)


def rollback_preuse(cur, state):
    with atomic(cur):
        catalog._authority(cur)
        cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
        cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        verify(cur,state)
        catalog._lock_tables(cur)
        if catalog._data(cur) != state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        for row,(_,module) in reversed(list(zip(state['stages'],STAGES))):
            module.rollback_preuse(cur,row['state'])
            if catalog._catalog_rows(cur) != row['before'] or catalog._data(cur) != row['data_before']:
                raise ValueError('CURRENT_MODEL_HISTORY_STAGE_INVERSE_NOT_EXACT')
        predecessor.verify(cur,state['predecessor'])
        removed = predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur) != state['before'] or catalog._data(cur) != state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_MODEL_HISTORY_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT, status='EXACT_CURRENT_MODEL_HISTORY_PREUSE_INVERSE', predecessor=removed,
                    all22_preinstall_equal=True, all_rows_and_sequences_equal=True,
                    global_used_guard_before_any_DDL=True, production_go=False, independent_acceptance=False)
