"""Actual owner-only admission control on a disposable hosted-aligned AB copy."""
from pathlib import Path
from urllib.parse import quote
import json,os,secrets
import psycopg
from psycopg import sql
import cp6_readiness_owner_install as installer
import cp6_t3_package_run as runtime
import cp6_bf_probe as bf

OUT=Path(__file__).resolve().parents[1]/'cp6-proof/t3'
TARGET='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
PRIMARY='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
ADMIN='postgresql://postgres:postgres@127.0.0.1:54322/template1'

def main():
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    OUT.mkdir(parents=True,exist_ok=True);password=secrets.token_hex(32);print('::add-mask::'+password,flush=True)
    control=f'postgresql://cp6_readiness_owner:{quote(password)}@127.0.0.1:54322/template1'
    print('::add-mask::'+control,flush=True)
    report=dict(label='CP6_OWNER_CONTROLLER_DISPOSABLE',status='INCOMPLETE',hosted_executed=False,production_go=False,cases={})
    before=runtime.fingerprint(PRIMARY)
    with psycopg.connect(ADMIN,autocommit=True) as conn:
        conn.execute(sql.SQL('create role cp6_readiness_owner login nosuperuser nocreatedb nocreaterole noreplication password {}').format(sql.Literal(password)))
        conn.execute('grant pg_monitor to cp6_readiness_owner')
        conn.execute('alter database cp6_rollback owner to cp6_readiness_owner')
    def run(name,**kwargs):
        result=installer.run(TARGET,control,profile='DISPOSABLE',report_path=OUT/('OWNER_'+name+'.json'),**kwargs)
        return result
    try:
        plan=run('READ_ONLY_PLAN')
        assert plan['status']=='READ_ONLY_PLAN_COMPLETE' and plan['capability']['control_is_superuser'] is False and not plan['admission_closed'],plan
        report['cases']['READ_ONLY_OWNER_PLAN']='PASS'
        # Validate a wrong database and a non-owner without DDL or file install.
        wrong=installer.run(TARGET.replace('/cp6_rollback','/postgres'),control,profile='DISPOSABLE',report_path=OUT/'OWNER_WRONG_ENDPOINT.json')
        assert wrong['error_code']=='ENDPOINT_NOT_ALLOWED' and not wrong['admission_closed'],wrong
        report['cases']['WRONG_ENDPOINT_REFUSED_BEFORE_CONNECTION']='PASS'
        with psycopg.connect(ADMIN,autocommit=True) as conn:conn.execute('alter database cp6_rollback owner to postgres')
        nonowner=run('NOT_OWNER',apply=True,window='DISPOSABLE_CI_ONLY')
        assert nonowner['error_code']=='CONTROL_NOT_DATABASE_OWNER' and not nonowner['admission_closed'],nonowner
        with psycopg.connect(ADMIN,autocommit=True) as conn:conn.execute('alter database cp6_rollback owner to cp6_readiness_owner')
        report['cases']['NONOWNER_REFUSED_BEFORE_ADMISSION_CHANGE']='PASS'
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
        assert installed['status']=='ALL_FILES_INSTALLED' and len(installed['files'])==30 and installed['admission_left_closed'] and not installed['admission_reopened'],installed
        report['cases']['ALL_30_PINNED_FILES_WITH_NONSUPERUSER_OWNER_CONTROL']='PASS'
        # This test's explicit reopen happens from the surviving control DB,
        # after reviewing the complete install receipt, then verifies Native.
        with psycopg.connect(control,autocommit=True) as conn:
            assert conn.execute('select rolsuper from pg_roles where rolname=current_user').fetchone()[0] is False
            conn.execute('alter database cp6_rollback with allow_connections true')
        with psycopg.connect(TARGET) as conn,conn.cursor() as cur:
            result=bf.verified(cur);conn.rollback()
        report['native_stage']=result['stage'];assert result['stage']=='BE_PLUS_BF_T1'
        report['cases']['OWNER_REOPEN_AND_EXACT_NATIVE_BF_VERIFY']='PASS'
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
            conn.execute('drop role cp6_readiness_owner')
        (OUT/'OWNER_CONTROLLER_QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
if __name__=='__main__':main()
