#!/usr/bin/env python3
"""Before/after money oracles against the fixed disposable native endpoint."""
import hashlib
import json
import os
import re
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
import cp6_v2620e_counterexample_regression as base
import cp6_v2620k_runtime as k_runtime
import cp6_v2620l_runtime as l_runtime
import cp6_preuse_rollback_maintenance as maintenance

SOURCE = Path('supabase/tests/cp6_exact_ledger_conservation.sql')
BEFORE_CASES = ('SPLIT_HALF_CENT','CACHE_CENT','CLAIM_OVERDRAW')
CASES = ('CENT_CONTROL','NORMALIZED_CONTROL','SPLIT_HALF_CENT','NONFINITE',
    'NEGATIVE_INPUT','MALFORMED_LINES','CACHE_CENT','JOURNAL_WASH','EMPTY_JOURNAL',
    'NONFINITE_CACHE','NEGATIVE_AP_FAULT','AP_OVERDRAW','AP_ZERO_CONTROL',
    'CLAIM_OVERDRAW','CLAIM_ZERO_CONTROL')

def run():
    params=conninfo_to_dict(os.environ.get('PGURL',''))
    if params != dict(user='postgres',password='postgres',host='127.0.0.1',port='54322',dbname='postgres'):
        raise AssertionError('L_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_L_DISPOSABLE_CONFIRM')!='postgres':
        raise AssertionError('L_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    phase=os.environ.get('CP6_L_PHASE','AFTER_L')
    if phase not in ('BEFORE_L','AFTER_L'): raise AssertionError('L_UNKNOWN_PHASE')
    fixed=phase=='AFTER_L'
    result={'head':os.environ.get('GITHUB_SHA','LOCAL_UNBOUND'),'production_go':False,
      'classification':'DISPOSABLE_NATIVE_'+phase,'phase':phase,
      'oracle_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'cases':{}}
    with psycopg.connect(**params,autocommit=False) as conn,conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        if len(k_runtime.verified_successor(cur))!=4:raise AssertionError('K_REQUIRED')
        successor=l_runtime.verified_successor(cur)
        if len(successor)!=(3 if fixed else 0):raise AssertionError('L_PHASE_RUNTIME_MISMATCH')
        expected=maintenance.TRUSTED_FUNCTIONS['L']
        if not fixed: maintenance._function_snapshot(conn,expected)
        result['runtime']={'verified_k_functions':4,'verified_l_functions':len(successor),
          'l_predecessor_source_pins_exact':not fixed,'engine':base.one(cur,'select version()')}
        cur.execute("select set_config('request.jwt.claims',%s,true)",
          (json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),))
        cur.execute("select set_config('app.change_reason','CP6 L money conservation oracles',true)")
        base.load_fixture_foundation(cur)
        cur.execute(SOURCE.read_text(),prepare=False)
        for name in (CASES if fixed else BEFORE_CASES):
            cur.execute('savepoint l_case')
            stage='FIXTURE'
            try:
                delivery=None
                if name.startswith('CLAIM_'):
                    fixture=base.fresh(cur,'a')
                    if name=='CLAIM_OVERDRAW':
                        stage='CLAIM_PHYSICAL_TIME_FORMAT_CONTROL'
                        boundary=base.one(cur,'select pg_temp.l_boundary()')
                        base.expect_error(cur,
                            lambda:base.post_delivery(cur,fixture,base.BASE_PROCESS,'2026-09-01 11:00+00'),
                            'An explicit timezone-qualified physical_at is required')
                        if base.one(cur,'select pg_temp.l_boundary()')!=boundary:
                            raise AssertionError('L_INVALID_DELIVERY_MUTATED_BOUNDARY')
                        result['claim_fixture_control']={
                            'noncanonical_physical_at_rejected_atomically':True,
                            'accepted_physical_at':'2026-09-01T11:00:00Z'}
                    stage='CLAIM_DELIVERY_AFTER_SEWING'
                    delivery=base.post_delivery(cur,fixture,base.BASE_PROCESS,'2026-09-01T11:00:00Z')['delivery_id']
                stage='BUSINESS_ORACLE'
                result['cases'][name]=base.one(cur,'select pg_temp.l_case(%s,%s,%s,%s)',
                    (name,fixed,base.VENDOR,delivery))
                if not fixed:
                    stage='UNSAFE_HISTORY_UPGRADE_REFUSAL'
                    boundary=base.one(cur,'select pg_temp.l_boundary()')
                    cur.execute('savepoint l_upgrade_guard')
                    rejection=None
                    try:
                        body=re.sub(r'^(begin|commit);$', '',l_runtime.MIGRATION.read_text(),flags=re.M|re.I)
                        cur.execute(body,prepare=False)
                    except psycopg.Error as exc:
                        if exc.sqlstate!='P0001' or 'L_PREEXISTING_LEDGER_REVIEW_REQUIRED' not in str(exc):raise
                        rejection=exc.sqlstate
                    finally:
                        cur.execute('rollback to savepoint l_upgrade_guard')
                        cur.execute('release savepoint l_upgrade_guard')
                    if rejection!='P0001':raise AssertionError('L_UNSAFE_UPGRADE_ACCEPTED')
                    if base.one(cur,'select pg_temp.l_boundary()')!=boundary:raise AssertionError('L_REJECTED_UPGRADE_MUTATED_BOOKS')
                    maintenance._function_snapshot(conn,expected)
                    if l_runtime.verified_successor(cur):raise AssertionError('L_REJECTED_UPGRADE_RESIDUE')
                    result['cases'][name]['upgrade_refused_atomically']=True
            except Exception as exc:
                result['cases'][name]={'status':'FAIL','stage':stage,'code':getattr(exc,'sqlstate',None) or 'ORACLE_FAILED'}
            finally:
                cur.execute('rollback to savepoint l_case');cur.execute('release savepoint l_case')
            if base.one(cur,'select pg_temp.l_report()')!='READY':raise AssertionError('L_RESTORE_NOT_READY')
            result['cases'][name]['rolled_back_to_ready']=True
        conn.rollback()
    expected_status='PASS' if fixed else 'KNOWN_K_BUG_REPRODUCED'
    result['all_case_effects_rolled_back']=True
    result['status']=expected_status if all(c['status']==expected_status for c in result['cases'].values()) else 'FAIL'
    return result

def main():
    phase=os.environ.get('CP6_L_PHASE','AFTER_L')
    report=Path('cp6-proof/CP6_V2620L_'+('K_COUNTEREXAMPLES' if phase=='BEFORE_L' else 'LEDGER_REGRESSION')+'.json')
    try:result=run()
    except Exception as exc:result={'status':'FAIL','code':getattr(exc,'sqlstate',None) or 'L_PREFLIGHT_FAILED',
      'head':os.environ.get('GITHUB_SHA','LOCAL_UNBOUND'),'production_go':False}
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({'status':result['status'],'case_count':len(result.get('cases',{})),'production_go':False}))
    if result['status']=='FAIL':raise SystemExit(1)

if __name__=='__main__':main()
