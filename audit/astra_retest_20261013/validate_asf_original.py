"""Strict validation of retained first-run evidence; does not execute or retry any product case.

ASRA-T01: the outer classifier in probe_asf_modes.py used bool(session_leaks).
Native mode returns an object with three empty fields, while other modes return a list.
The runtime's original rows, restoration gates and first failure are preserved byte-for-byte.
"""
from pathlib import Path
from copy import deepcopy
import json,hashlib,sys
SOURCE=Path(sys.argv[1]);OUT=Path(sys.argv[2])
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='bb77504ca0a27ce9ee035844e681be6c550313cd565f450eb31e255a6028d3f0'
original=json.loads(raw)
MODES=['savepoint','race','http','browser']
def validate(d):
    assert d['product_sha']=='7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2'
    assert not d.get('error') and not d.get('restore_error')
    assert d['restore']=={'boundary':True,'public':True,'functions':True}
    expected=['ASF-MODE-'+m.upper()+'-'+k.upper() for m in MODES for k in ('negative','positive')]
    assert [r['id'] for r in d['cases']]==expected
    verdicts=[]
    for record in d['cases']:
        _,_,mode,kind=record['id'].split('-');mode=mode.lower();kind=kind.lower()
        key='races' if mode=='race' else 'cases'
        expected_states=['FAIL','COUNTEREXAMPLE','INCOMPLETE','PASS'] if kind=='negative' else ['PASS']
        ids=[f'ASFM_{mode}_{kind}_{s}' for s in expected_states]
        def check_group(g,rolled):
            assert isinstance(g,dict) and key in g
            assert not any(g.get(k) for k in ['error','missing','database_remaining','cleanup_failures','auth_cleanup_failures','session_leaks','host_error'])
            assert list(g[key])==ids
            assert g['planned_race_ids' if mode=='race' else 'planned_case_ids']==ids
            if mode=='savepoint':assert g['complete_boundary_restored'] is True
            else:assert g['database_remaining']==0
            if mode in ('http','browser'):
                assert g['real_auth'] is True and g['jwt_signed_by_runtime'] is False
                assert g['auth_counts']['restored'] is True and g['auth_counts']['before']==g['auth_counts']['after']
                assert not g['cleanup']['cleanup_failures'] and not g['cleanup']['rest_remaining']
            if mode=='browser':assert g['host_status']=='RUN_COMPLETE' and g['host_exit']==0 and g['console_errors']==0
            for cid in ids:
                row=g[key][cid];input_status=cid.rsplit('_',1)[1]
                # COUNTEREXAMPLE contains no underscore, so this extracts all four declared statuses exactly.
                assert not row.get('harness_check_failed') and 'status_outside_vocabulary' not in row
                if mode=='savepoint':
                    assert row['full_boundary_restored'] is True and row['public_schema_unchanged'] is True
                    assert row['session_leaks']=={'advisory_locks':0,'advisory_lock_keys':[],'other_sessions':[]}
                    assert row['transport']['sql_executed'] is True
                elif mode in ('race','http'):assert row['session_leaks']==[]
                if mode=='race':assert len(set(row['transport']['concurrent_backend_pids']))==2
                if mode=='http':assert row['transport']['real_auth'] is True and row['transport']['http_status']==200
                if mode=='browser':assert row['transport']['real_auth'] is True and row['transport']['rpc_status']==200
                dates=row['business_day'];actual_roll=len(set(dates.values()))>1
                assert actual_roll==rolled and bool(row.get('business_day_rollover'))==rolled
                if input_status!='PASS':
                    assert row['status']==input_status and row['error']=='ASTRA_INJECTED_DATE_INDEPENDENT_'+input_status
                    assert row['synthetic_failure'] is True and row['expected_total_cents']==10000 and row['observed_total_cents']==10001
                else:
                    assert row['synthetic_failure'] is False and row['observed_total_cents']==row['expected_total_cents']==10000
                    assert row['status']==('INCOMPLETE' if rolled else 'PASS')
                    if rolled:assert row['status_before_rollover']=='PASS' and row['error']=='AUDITOR_BUSINESS_DAY_ROLLOVER'
                    else:assert not row.get('error')
        if kind=='negative':
            assert record['attempts']==1 and not record['result'].get('business_day_retried')
            assert 'business_day_first_attempt' not in record['result'];check_group(record['result'],True)
        else:
            assert record['attempts']==2 and record['result']['business_day_retried'] is True
            check_group(record['result'],False);check_group(record['result']['business_day_first_attempt'],True)
        verdicts.append(dict(id=record['id'],status='PASS',original_outer_status=record['status'],attempts=record['attempts']))
    return verdicts
verdicts=validate(original)
negative_controls=[]
def rejects(label,alter):
    copied=deepcopy(original);alter(copied)
    try:validate(copied)
    except AssertionError:negative_controls.append(dict(id=label,status='PASS',invalid_evidence_rejected=True));return
    raise AssertionError('VALIDATOR_INSENSITIVE_'+label)
rejects('real_leaked_session',lambda d:d['cases'][0]['result']['cases']['ASFM_savepoint_negative_FAIL']['session_leaks']['other_sessions'].append('INJECTED'))
rejects('real_advisory_lock',lambda d:d['cases'][0]['result']['cases']['ASFM_savepoint_negative_FAIL']['session_leaks'].__setitem__('advisory_locks',1))
rejects('boundary_not_restored',lambda d:d['cases'][0]['result'].__setitem__('complete_boundary_restored',False))
rejects('unrelated_failure_hidden',lambda d:d['cases'][0]['result']['cases']['ASFM_savepoint_negative_FAIL'].__setitem__('status','PASS'))
rejects('third_attempt',lambda d:d['cases'][1].__setitem__('attempts',3))
rejects('first_attempt_missing',lambda d:d['cases'][1]['result'].__setitem__('business_day_first_attempt',{}))
result=dict(status='PASS',product_sha=original['product_sha'],source_sha256=hashlib.sha256(raw).hexdigest(),source_runtime_run=38354144743,source_runtime_job=115153016591,
    classification='AUDITOR_TOOL_ERROR_ASRA_T01',no_product_case_rerun=True,original_report_unchanged=True,
    correction='Require the native session_leaks object to contain exactly 0 advisory locks, zero lock keys and zero other sessions. Do not interpret object existence as a leak.',
    evidence_origin='INDEPENDENT_RUNTIME_ORIGINAL_WITH_CORRECTED_AUDITOR_CLASSIFICATION',cases=verdicts,negative_controls=negative_controls,counts={'PASS':len(verdicts)},production_go=False)
assert SOURCE.read_bytes()==raw
OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
