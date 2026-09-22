"""Disposable-only closed-admission package installer and existing rollback adapter."""
from pathlib import Path
import time
import psycopg
from psycopg import sql
import cp6_preuse_rollback_maintenance as core
import cp6_ao_ap_runtime as runtime

LOCK="select pg_advisory_lock(hashtextextended('CP6_PREUSE_ROLLBACK_MAINTENANCE',0))"
UNLOCK=LOCK.replace('pg_advisory_lock','pg_advisory_unlock')

def install(*,family,target_pgurl,maintenance_pgurl,report_path,drain_timeout=10,natural_grace=.1,terminate_after_grace=True):
    database,maintenance_database=core._validate_connections(target_pgurl,maintenance_pgurl)
    p=runtime.pins()['families'][family];source=(runtime.ROOT/p['migration']).read_text()
    report=dict(contract='CP6_AO_AP_CLOSED_INSTALL_V1',family=family,status='RUNNING',migration_sha256=p['migration_sha256'],admission_closed=False,install_started=False,install_committed=False,admission_reopened=False,production_go=False,independent_acceptance=False)
    core._phase(report_path,report,'PREFLIGHT')
    conn=control=None;locked=False
    try:
        conn=psycopg.connect(target_pgurl,autocommit=True,application_name='cp6-package-install-'+family.lower())
        control=psycopg.connect(maintenance_pgurl,autocommit=True,application_name='cp6-package-admission')
        target=core._endpoint_snapshot(conn);authority=core._endpoint_snapshot(control)
        assert target['database']==database and target['user']=='postgres','INSTALL_ENDPOINT_IDENTITY'
        assert authority['database']==maintenance_database and authority['user']=='cp6_maintenance_admission','INSTALL_CONTROL_IDENTITY'
        assert all(target[k] and target[k]==authority[k] for k in ('server_address','server_port','system_identifier')),'INSTALL_CLUSTER_IDENTITY'
        assert core._scalar(control,'select rolsuper from pg_roles where rolname=current_user'),'INSTALL_CONTROL_AUTHORITY'
        assert core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,)),'INSTALL_REQUIRES_OPEN_ADMISSION_AT_ENTRY'
        report.update(target_endpoint=target,admission_control_endpoint=authority)
        core._scalar(control,LOCK);locked=True
        pid=core._scalar(conn,'select pg_backend_pid()')
        with conn.transaction(),conn.cursor() as cur:
            cur.execute("set local statement_timeout='15s'")
            report['preflight']=runtime.verified(cur,p['previous'],pre_admission=True)
        control.execute(sql.SQL('alter database {} with allow_connections false').format(sql.Identifier(database)))
        assert not core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,))
        report['admission_closed']=True;core._phase(report_path,report,'ADMISSION_CLOSED')
        active=core._sessions(control,database,pid);report['sessions_at_close']=active
        deadline=time.monotonic()+natural_grace
        while active and time.monotonic()<deadline:
            time.sleep(.025);active=core._sessions(control,database,pid)
        terminated=[]
        if active and terminate_after_grace:
            for s in active:terminated.append(dict(pid=s['pid'],requested=core._scalar(control,'select pg_terminate_backend(%s)',(s['pid'],))))
        report['terminated_sessions']=terminated;deadline=time.monotonic()+drain_timeout
        while active and time.monotonic()<deadline:
            time.sleep(.025);active=core._sessions(control,database,pid)
        assert not active,'INSTALL_DRAIN_TIMEOUT'
        assert not core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,)),'INSTALL_ADMISSION_REOPENED'
        report['install_started']=True;core._phase(report_path,report,'INSTALL_STARTED')
        with conn.transaction(),conn.cursor() as cur:
            runtime.verified(cur,p['previous'])
            cur.execute(runtime.sql_body(source),prepare=False)
            cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(p['stamp'],p['name'],[source]))
            report['installed']=runtime.verified(cur,family)
        report['install_committed']=True;core._phase(report_path,report,'INSTALL_COMMITTED')
        with conn.transaction(),conn.cursor() as cur:report['committed_catalog']=runtime.verified(cur,family)
        control.execute(sql.SQL('alter database {} with allow_connections true').format(sql.Identifier(database)))
        assert core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,))
        report.update(status='PASS',admission_reopened=True);core._phase(report_path,report,'ADMISSION_REOPENED')
        return report
    except Exception as exc:
        report.update(status='FAIL',error_type=type(exc).__name__,error_code=core._public_failure_code(exc))
        if control is not None and report['admission_closed']:
            report['admission_still_closed']=not core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,))
        core._phase(report_path,report,'FAILED_CLOSED');raise
    finally:
        if control is not None and locked:
            try:core._scalar(control,UNLOCK)
            except psycopg.Error:pass
        if conn is not None:conn.close()
        if control is not None:control.close()

def rollback(*,family,target_pgurl,maintenance_pgurl,report_path,**kwargs):
    core._validate_connections(target_pgurl,maintenance_pgurl)
    p=runtime.pins()['families'][family]
    # Catalog deparsing waits until the existing controller has drained sessions.
    # The reviewed SQL repeats the full proof inside its restoration transaction.
    with psycopg.connect(target_pgurl) as conn,conn.cursor() as cur:
        cur.execute("set local statement_timeout='15s'");runtime.verified(cur,family,pre_admission=True)
    core.TARGETS[family]=dict(rollback=runtime.ROOT/p['rollback'],rollback_sha256=p['rollback_sha256'],marker=p['version'],platform=p['name'],predecessor='v2.6.20'+p['previous'].lower(),capsule=p['capsule'],capsule_count=len(p['functions']))
    core.TRUSTED_FUNCTIONS[family]=p['functions']
    return core.run_maintenance_rollback(target_name=family,target_pgurl=target_pgurl,maintenance_pgurl=maintenance_pgurl,report_path=report_path,**kwargs)
