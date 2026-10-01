"""Actual owner-only 58-file install on a disposable hosted-aligned v2.6.20 copy."""
from pathlib import Path
import json,os
import psycopg
import cp6_readiness_owner_install as installer
import cp6_t3_package_run as runtime
import cp6_bf_probe as bf

OUT=Path(__file__).resolve().parents[1]/'cp6-proof/t3'
TARGET='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
PRIMARY='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
ADMIN=os.environ['CP6_ADMISSION_CONTROL_PGURL']

def main():
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    installer.core._validate_connections(TARGET,ADMIN)
    OUT.mkdir(parents=True,exist_ok=True)
    control='postgresql://postgres:postgres@127.0.0.1:54322/template1'
    report=dict(label='CP6_OWNER_CONTROLLER_DISPOSABLE',status='INCOMPLETE',hosted_executed=False,production_go=False,cases={})
    before=runtime.fingerprint(PRIMARY)
    with psycopg.connect(ADMIN,autocommit=True) as conn:
        conn.execute('create role cp6_readiness_other_owner nologin nosuperuser nocreatedb nocreaterole noreplication')
    def run(name,**kwargs):
        result=installer.run(TARGET,control,profile='DISPOSABLE',report_path=OUT/('OWNER_'+name+'.json'),**kwargs)
        return result
    try:
        plan=run('READ_ONLY_PLAN')
        assert plan['status']=='READ_ONLY_PLAN_COMPLETE' and plan['capability']['control_is_superuser'] is False and plan['capability']['work_is_superuser'] is False and not plan['admission_closed'],plan
        report['cases']['READ_ONLY_OWNER_PLAN']='PASS'
        report['capability']=plan['capability']
        suffix=run('MISSING_AB',mode=installer.SUFFIX)
        assert suffix['error_code']=='LIVE_REQUIRED_BASELINE_MISSING' and not suffix['admission_change_attempted'],suffix
        report['cases']['V2620_REFUSES_SUFFIX_WITHOUT_AB_BEFORE_ADMISSION_CHANGE']='PASS'
        # Validate a wrong database and a non-owner without DDL or file install.
        wrong=installer.run(TARGET.replace('/cp6_rollback','/postgres'),control,profile='DISPOSABLE',report_path=OUT/'OWNER_WRONG_ENDPOINT.json')
        assert wrong['error_code']=='ENDPOINT_NOT_ALLOWED' and not wrong['admission_closed'],wrong
        report['cases']['WRONG_ENDPOINT_REFUSED_BEFORE_CONNECTION']='PASS'
        with psycopg.connect(ADMIN,autocommit=True) as conn:conn.execute('alter database cp6_rollback owner to cp6_readiness_other_owner')
        nonowner=run('NOT_OWNER',apply=True,window='DISPOSABLE_CI_ONLY')
        assert nonowner['error_code']=='CONTROL_NOT_DATABASE_OWNER' and not nonowner['admission_closed'],nonowner
        with psycopg.connect(ADMIN,autocommit=True) as conn:conn.execute('alter database cp6_rollback owner to postgres')
        report['cases']['NONOWNER_REFUSED_BEFORE_ADMISSION_CHANGE']='PASS'
        with psycopg.connect(TARGET,autocommit=True) as conn:
            conn.execute('create function erp.readiness_unreviewed_catalog_marker() returns integer language sql as $$ select 1 $$')
            try:drift=run('BASELINE_DRIFT')
            finally:conn.execute('drop function erp.readiness_unreviewed_catalog_marker()')
        assert drift['error_code']=='LIVE_G01_BASELINE_DRIFT' and not drift['admission_change_attempted'],drift
        report['cases']['G01_CATALOG_DRIFT_REFUSED_BEFORE_ADMISSION_CHANGE']='PASS'
        with psycopg.connect(control,autocommit=True) as held:
            held.execute(installer.LOCK)
            locked=run('LOCK_BUSY',apply=True,window='DISPOSABLE_CI_ONLY')
            held.execute(installer.LOCK.replace('pg_advisory_lock','pg_advisory_unlock'))
        assert locked['error_code']=='MAINTENANCE_LOCK_BUSY_NO_INSTALL' and not locked['admission_change_attempted'] and locked['files']==[],locked
        report['cases']['COMPETING_MAINTENANCE_REFUSED_WITHOUT_ADMISSION_CHANGE']='PASS'
        with psycopg.connect(TARGET,autocommit=True) as held:
            held.execute('select 1')
            busy=run('BUSY',apply=True,window='DISPOSABLE_CI_ONLY',drain_seconds=.2)
        assert busy['error_code']=='DRAIN_TIMEOUT_NO_INSTALL_STARTED' and busy['files']==[] and busy['admission_reopened'] and not busy['admission_left_closed'],busy
        report['cases']['BUSY_REFUSES_WITHOUT_KILL_OR_INSTALL_AND_REOPENS']='PASS'
        installed=run('INSTALL',apply=True,window='DISPOSABLE_CI_ONLY')
        assert installed['status']=='ALL_FILES_INSTALLED' and len(installed['files'])==58 and installed['admission_left_closed'] and not installed['admission_reopened'],installed
        assert installed['native_stage_verified']=='BE_PLUS_BF_T1' and len(installed['installed_catalog_sha256'])==64,installed
        report['cases']['ALL_58_PINNED_FILES_WITH_NONSUPERUSER_OWNER_AND_WORK']='PASS'
        report['install_file_count']=len(installed['files']);report['manifest_sha256']=installed['manifest_sha256']
        # This test's explicit reopen happens from the surviving control DB,
        # after reviewing the complete install receipt, then verifies Native.
        with psycopg.connect(control,autocommit=True) as conn:
            assert conn.execute('select rolsuper from pg_roles where rolname=current_user').fetchone()[0] is False
            conn.execute('alter database cp6_rollback with allow_connections true')
        with psycopg.connect(TARGET) as conn,conn.cursor() as cur:
            result=bf.verified(cur);conn.rollback()
        report['native_stage']=result['stage'];assert result['stage']=='BE_PLUS_BF_T1'
        report['cases']['OWNER_REOPEN_AND_EXACT_NATIVE_BF_VERIFY']='PASS'
        again=run('ALREADY_INSTALLED')
        assert again['error_code']=='LIVE_TARGET_ALREADY_APPLIED_OR_PARTIAL' and not again['admission_change_attempted'],again
        report['cases']['ALREADY_INSTALLED_REFUSED_BEFORE_ADMISSION_CHANGE']='PASS'
        report['primary_unchanged']=runtime.fingerprint(PRIMARY)==before;assert report['primary_unchanged']
        report['status']='PASS'
    except Exception as exc:
        report.update(error_type=type(exc).__name__,error_code=installer.core._public_failure_code(exc))
        raise
    finally:
        # Only the disposable CI cluster is cleaned up; no hosted role exists
        # or is created by this test. Failure evidence is kept unchanged.
        with psycopg.connect(ADMIN,autocommit=True) as conn:
            conn.execute('alter database cp6_rollback with allow_connections true')
            conn.execute('alter database cp6_rollback owner to postgres')
            conn.execute('drop role cp6_readiness_other_owner')
        (OUT/'OWNER_CONTROLLER_QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
if __name__=='__main__':main()
