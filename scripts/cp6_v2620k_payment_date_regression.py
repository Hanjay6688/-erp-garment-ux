#!/usr/bin/env python3
"""Native K business oracles; exclusively allowlisted disposable PostgreSQL."""
import hashlib
import json
import os
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
import cp6_v2620e_counterexample_regression as base
import cp6_v2620h_adversarial_regression as h
import cp6_v2620k_runtime as runtime

REPORT = Path('cp6-proof/CP6_V2620K_PAYMENT_DATE_REGRESSION.json')
CASES = ('LATE_ALLOCATION','MULTI_HOP','COHERENT_DATE_FAULT','ATOMIC_INVALID','CLOSED_PERIOD','TIMEZONE')
SOURCE = Path('supabase/tests/cp6_payment_date_conservation.sql')

def run():
    params = conninfo_to_dict(os.environ.get('PGURL',''))
    if params != dict(user='postgres',password='postgres',host='127.0.0.1',port='54322',dbname='postgres'):
        raise AssertionError('K_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_K_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('K_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    result={'head':os.environ.get('GITHUB_SHA','LOCAL_UNBOUND'),'production_go':False,
      'classification':'DISPOSABLE_NATIVE_POSTGRESQL_AFTER_E_F_G_H_I_J_K',
      'oracle_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'cases':{}}
    with psycopg.connect(**params,autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC'; set local statement_timeout='180s'; set local lock_timeout='8s'")
        observed=runtime.verified_successor(cur)
        if len(observed)!=4: raise AssertionError('K_RUNTIME_NOT_INSTALLED')
        result['runtime']={'function_count':4,'all_source_pins_owner_acl_exact':True,
          'migration_sha256':hashlib.sha256(runtime.MIGRATION.read_bytes()).hexdigest(),
          'engine':base.one(cur,'select version()')}
        # Diagnose the original fault-harness permission mismatch without
        # logging raw exceptions or granting any additional privilege.
        role_before=base.one(cur,"select jsonb_build_object('role',current_user,'superuser',rolsuper) from pg_roles where rolname=current_user")
        control={'set_config_accepted':False,'set_config_sqlstate':None}
        cur.execute('savepoint k_replication_control')
        try:
            cur.execute("select set_config('session_replication_role','replica',true)")
            control['set_config_accepted']=True
        except psycopg.Error as exc:
            if exc.sqlstate!='42501': raise
            control['set_config_sqlstate']=exc.sqlstate
        finally:
            cur.execute('rollback to savepoint k_replication_control')
            cur.execute('release savepoint k_replication_control')
        cur.execute("set local session_replication_role='replica'")
        if base.one(cur,"select current_setting('session_replication_role')")!='replica':
            raise AssertionError('K_FAULT_UTILITY_CONTROL_FAILED')
        cur.execute("set local session_replication_role='origin'")
        role_after=base.one(cur,"select jsonb_build_object('role',current_user,'superuser',rolsuper) from pg_roles where rolname=current_user")
        if role_before!=role_after: raise AssertionError('K_FAULT_CONTROL_CHANGED_ROLE')
        result['fault_harness_permission_control']={**control,**role_after,
          'utility_set_accepted':True,'origin_restored':True,'role_privileges_unchanged':True}
        cur.execute("select set_config('request.jwt.claims',%s,true)",
          (json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),))
        cur.execute("select set_config('app.change_reason','CP6 K competition oracles',true)")
        base.load_fixture_foundation(cur)
        cur.execute(SOURCE.read_text(),prepare=False)
        for name in CASES:
            cur.execute('savepoint k_case')
            try:
                customer=base.create_customer(cur,'K-'+name)
                first=h.opening_sale(cur,'K-A',customer)
                second=h.opening_sale(cur,'K-B',customer)
                foreign=h.opening_sale(cur,'K-C')
                result['cases'][name]=base.one(cur,'select pg_temp.k_case(%s,%s,%s,%s,%s)',
                  (name,first['sale'],second['sale'],foreign['sale'],customer))
            except Exception as exc:
                result['cases'][name]={'status':'FAIL','code':getattr(exc,'sqlstate',None) or 'ORACLE_FAILED'}
            finally:
                cur.execute('rollback to savepoint k_case');cur.execute('release savepoint k_case')
        conn.rollback()
    result['all_case_effects_rolled_back']=True
    result['status']='PASS' if len(result['cases'])==len(CASES) and all(c['status']=='PASS' for c in result['cases'].values()) else 'FAIL'
    return result

def main():
    try: result=run()
    except Exception as exc:
        result={'status':'FAIL','code':getattr(exc,'sqlstate',None) or 'K_PREFLIGHT_FAILED',
          'head':os.environ.get('GITHUB_SHA','LOCAL_UNBOUND'),'production_go':False}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({'status':result['status'],'case_count':len(result.get('cases',{})),
      'production_go':False}))
    if result['status']!='PASS': raise SystemExit(1)

if __name__=='__main__': main()
