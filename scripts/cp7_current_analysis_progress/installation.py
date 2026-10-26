"""Opt-in A telemetry composition on the actual full public finance predecessor."""
from pathlib import Path
from hashlib import sha256
import re
import cp7_current_frozen_public_installation as predecessor
from cp7_production_stage import _row,_body

ROOT=Path(__file__).resolve().parent
SIGNATURE='public.erp_cp7_get_frozen_analysis_progress_v1(uuid)'
CONTRACT='cp7.current-AB-public-frozen-progress.v1'
USED_ERROR='CURRENT_FROZEN_PROGRESS_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=predecessor.catalog,predecessor.atomic

def sources():
    # Explicit product source closure: generated test reports never enter it.
    return dict(contract=CONTRACT,policy_id='D17-18-20261026',predecessor=predecessor.sources(),
                files={n:sha256((ROOT/n).read_bytes()).hexdigest()for n in ('installation.py','progress.prepared.sql')})

def definition():
    matches=re.findall(r'create function public\.erp_cp7_get_frozen_analysis_progress_v1\(.*?\$\$;',
                       (ROOT/'progress.prepared.sql').read_text(),re.S)
    if len(matches)!=1:raise ValueError('CURRENT_PROGRESS_SINGLE_DEFINITION_REQUIRED')
    return matches[0]

def binding(prior,proof):
    return catalog.digest(dict(sources=prior['sources'],before=prior['before'],after=prior['after'],actual_verification=proof))

def exact_delta(before,after):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('CURRENT_PROGRESS_FULL22_REQUIRED')
    changed={(group,key)for group in before for key in set(before[group])|set(after[group])
             if before[group].get(key)!=after[group].get(key)}
    if changed!={('functions',SIGNATURE)}or before['functions'].get(SIGNATURE)is not None or after['functions'].get(SIGNATURE)is None:
        raise ValueError('CURRENT_PROGRESS_UNDECLARED_DELTA')

def verify(cur,state):
    catalog._authority(cur)
    prior,proof=state['predecessor'],state['predecessor_verified_before_delta']
    if (state['sources']!=sources()or prior['sources']!=predecessor.sources()
        or state['before']!=prior['before']or state['predecessor_binding_sha256']!=binding(prior,proof)
        or proof.get('contract')!=predecessor.CONTRACT
        or proof.get('status')!='EXACT_CURRENT_FROZEN_PUBLIC_FINANCE_ALL22'
        or proof.get('predecessor_verified_before_actual_delta')is not True
        or proof.get('all22_transition_chain_verified')is not True
        or proof.get('substituted_catalog_or_definitions')is not False
        or proof.get('official_finance_source_reused')is not True
        or proof.get('new_public_rpcs')!=2):
        raise ValueError('CURRENT_PROGRESS_PREDECESSOR_BINDING_CHANGED')
    if (state['preuse_data_and_sequences']!=prior['preuse_data_and_sequences']
        or state['preinstall_data_and_sequences']!=prior['preinstall_data_and_sequences']
        or catalog._catalog_rows(cur)!=state['after']):
        raise ValueError('CURRENT_PROGRESS_CURRENT_STATE_CHANGED')
    exact_delta(prior['after'],state['after'])
    row=_row(cur,SIGNATURE)
    if (row!=state['row']or row[1]!=_body(definition())or row[0]!=state['after']['functions'][SIGNATURE][0]
        or row[2:6]!=['cp7_capture',True,'v',['search_path=""','TimeZone=UTC']]):
        raise ValueError('CURRENT_PROGRESS_FUNCTION_OR_AUTHORITY_CHANGED')
    acl=state['after']['functions'][SIGNATURE][-1]
    grants={('cp7_capture','cp7_capture','EXECUTE',False),('authenticated','cp7_capture','EXECUTE',False)}
    if (not isinstance(acl,list)or len(acl)!=len(grants)
        or any(not isinstance(x,list)or len(x)!=4 or x[3]is not False for x in acl)
        or {tuple(x)for x in acl}!=grants):raise ValueError('CURRENT_PROGRESS_GRANTS_CHANGED')
    for role in ('anon','authenticated','service_role','cp7_alert'):
        if cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,SIGNATURE)).fetchone()[0]is not(role=='authenticated'):
            raise ValueError('CURRENT_PROGRESS_EXECUTE_CHANGED:'+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('CURRENT_PROGRESS_OWNER_CREATE_OPEN')
    return dict(contract=CONTRACT,status='EXACT_CURRENT_FROZEN_PROGRESS_ALL22',
                predecessor_verified_before_actual_delta=True,all22_transition_chain_verified=True,
                substituted_catalog_or_definitions=False,new_public_rpcs=1,new_tables=0,
                existing_functions_replaced=0,financial_math_added=False,timeout_changed=False,
                actual_Auth_HTTP_credit=False,default_adopted=False,production_go=False)

def install(cur):
    with atomic(cur):
        predecessor._locks(cur)
        if cur.execute('select to_regprocedure(%s)is not null',(SIGNATURE,)).fetchone()[0]:
            raise ValueError('CURRENT_PROGRESS_ALREADY_INSTALLED')
        before,data=catalog._catalog_rows(cur),catalog._data(cur)
        prior=predecessor.install(cur);proof=predecessor.verify(cur,prior)
        cur.execute((ROOT/'progress.prepared.sql').read_text(),prepare=False)
        if catalog._data(cur)!=prior['preuse_data_and_sequences']:
            raise ValueError('CURRENT_PROGRESS_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
        state=dict(sources=sources(),before=before,preinstall_data_and_sequences=data,
                   predecessor=prior,predecessor_verified_before_delta=proof,
                   predecessor_binding_sha256=binding(prior,proof),after=catalog._catalog_rows(cur),
                   preuse_data_and_sequences=prior['preuse_data_and_sequences'],row=_row(cur,SIGNATURE))
        verify(cur,state);return state

def rollback_preuse(cur,state):
    with atomic(cur):
        predecessor._locks(cur);verify(cur,state)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        cur.execute('drop function '+SIGNATURE+' restrict')
        predecessor.verify(cur,state['predecessor'])
        removed=predecessor.rollback_preuse(cur,state['predecessor'])
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preinstall_data_and_sequences']:
            raise ValueError('CURRENT_PROGRESS_FULL_INVERSE_NOT_EXACT')
        return dict(contract=CONTRACT,status='EXACT_CURRENT_FROZEN_PROGRESS_PREUSE_INVERSE',predecessor=removed,
                    all22_preinstall_equal=True,all_rows_and_sequences_equal=True,
                    global_used_guard_before_any_DDL=True,production_go=False)
