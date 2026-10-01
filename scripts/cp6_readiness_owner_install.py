"""Pinned CP6 installer using a database owner, not a superuser controller.

Default CLI mode only reads metadata. --apply requires an approved maintenance
reference and a restored backup receipt. This file is never called on hosted by
CI. SQL bytes/guards remain those of the accepted 30-file package.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,time
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
import cp6_t3_release_package as package
import cp6_preuse_rollback_maintenance as core

ROOT=Path(__file__).resolve().parents[1]
MANIFEST_SHA='40795c3fce619c5795b427e9aa31836777b687f82eba4ab5654264d57564879f'
PROJECT='siimvrusnzxexizpyoib'
LOCK="select pg_advisory_lock(hashtextextended('CP6_PREUSE_ROLLBACK_MAINTENANCE',0))"

class Refused(RuntimeError):pass

def endpoints(target,control,profile):
    for label,value in [('target',target),('control',control)]:
        core._reject_ambiguous_conninfo(value,label)
    t,c=conninfo_to_dict(target),conninfo_to_dict(control)
    if not t.get('password') or not c.get('password'):raise Refused('PASSWORD_REQUIRED')
    if profile=='DISPOSABLE':
        expected_t={'host':'127.0.0.1','port':'54322','user':'postgres','dbname':'cp6_rollback'}
        expected_c={'host':'127.0.0.1','port':'54322','user':'cp6_readiness_owner','dbname':'template1'}
    elif profile=='ERP_ENTENG':
        expected_t={'host':f'db.{PROJECT}.supabase.co','port':'5432','user':'postgres','dbname':'postgres'}
        expected_c={**expected_t,'dbname':'template1'}
    else:raise Refused('PROFILE_NOT_ALLOWED')
    if any(t.get(k)!=v for k,v in expected_t.items()) or any(c.get(k)!=v for k,v in expected_c.items()):raise Refused('ENDPOINT_NOT_ALLOWED')
    return t['dbname']

def files():
    raw=(ROOT/'supabase/release/cp6-t3/MANIFEST.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise Refused('MANIFEST_DRIFT')
    rows=json.loads(raw)['files']
    if [r['key'] for r in rows]!=[k.upper() for k in package.KEYS]:raise Refused('PACKAGE_ORDER_DRIFT')
    result=[]
    for row in rows:
        if not row['file'].startswith('supabase/release/cp6-t3/') or '..' in Path(row['file']).parts:raise Refused('PACKAGE_PATH')
        text=(ROOT/row['file']).read_text()
        if hashlib.sha256(text.encode()).hexdigest()!=row['package_sha256']:raise Refused('PACKAGE_FILE_DRIFT')
        transaction_body(text)  # exact pinned transaction wrapper, not a rewrite
        result.append((row,text))
    return result

def transaction_body(text):
    lines=text.splitlines(keepends=True)
    first=next((i for i,line in enumerate(lines) if line.strip() and not line.lstrip().startswith('--')),None)
    if first is None or lines[first]!='begin;\n' or lines[-1]!='commit;\n':raise Refused('UNREVIEWED_TRANSACTION_WRAPPER')
    return ''.join(lines[first+1:-1])

def capability(work,control,database):
    # Metadata reads happen inside explicitly read-only transactions.
    with work.transaction(),control.transaction():
        work.execute('set transaction read only');control.execute('set transaction read only')
        a,b=core._endpoint_snapshot(work),core._endpoint_snapshot(control)
        if a['database']!=database or b['database']!='template1' or a['user']!='postgres':raise Refused('LIVE_ENDPOINT_IDENTITY')
        if not all(a[k] and a[k]==b[k] for k in ('server_address','server_port','system_identifier')):raise Refused('CLUSTER_IDENTITY')
        owner=core._scalar(control,'select datdba=(select oid from pg_roles where rolname=current_user) from pg_database where datname=%s',(database,))
        if not owner:raise Refused('CONTROL_NOT_DATABASE_OWNER')
        if not core._scalar(control,"select pg_has_role(current_user,'pg_read_all_stats','MEMBER')"):raise Refused('SESSION_VISIBILITY_REQUIRED')
        if not core._scalar(control,'select datallowconn from pg_database where datname=%s',(database,)):raise Refused('ENTRY_ADMISSION_ALREADY_CLOSED')
        return dict(same_cluster=True,target_database=database,control_database='template1',control_owns_target=True,
          control_is_superuser=core._scalar(control,'select rolsuper from pg_roles where rolname=current_user'),
          work_is_superuser=core._scalar(work,'select rolsuper from pg_roles where rolname=current_user'),
          other_sessions=core._scalar(control,'select count(*) from pg_stat_activity where datname=%s and pid<>%s',(database,core._scalar(work,'select pg_backend_pid()'))))

def approval(profile,window,backup):
    if profile=='DISPOSABLE' and window=='DISPOSABLE_CI_ONLY':return
    if profile!='ERP_ENTENG' or not window or not backup:raise Refused('APPROVED_WINDOW_AND_RESTORED_BACKUP_REQUIRED')
    record=json.loads(Path(backup).read_text())
    if record.get('project_ref')!=PROJECT or record.get('database')!='postgres' or record.get('restore_verified') is not True or record.get('manifest_sha256')!=MANIFEST_SHA:raise Refused('BACKUP_RECEIPT_NOT_FOR_THIS_INSTALL')
    checked=datetime.fromisoformat(record['verified_at'])
    if checked.tzinfo is None or not 0<= (datetime.now(timezone.utc)-checked).total_seconds()<=3600:raise Refused('BACKUP_VERIFICATION_NOT_FRESH')

def run(target,control,*,profile,report_path,apply=False,window=None,backup=None,certificate=None,drain_seconds=15):
    report=dict(label='CP6_OWNER_MAINTENANCE',status='INCOMPLETE',profile=profile,mode='APPLY' if apply else 'READ_ONLY_PLAN',
      manifest_sha256=MANIFEST_SHA,files=[],admission_change_attempted=False,install_attempted=False,admission_closed=False,
      admission_reopened=False,admission_left_closed=False,production_go=False)
    work=authority=None;locked=False;database=None
    def save():
        Path(report_path).parent.mkdir(parents=True,exist_ok=True);Path(report_path).write_text(json.dumps(report,indent=2)+'\n')
    try:
        database=endpoints(target,control,profile);rows=files()
        kwargs={'connect_timeout':15,'application_name':'cp6-owner-maintenance'}
        if profile=='ERP_ENTENG':
            if not certificate or not Path(certificate).is_file():raise Refused('SERVER_CERTIFICATE_REQUIRED')
            kwargs.update(sslmode='verify-full',sslrootcert=certificate)
        if apply:approval(profile,window,backup)
        work=psycopg.connect(target,autocommit=True,**kwargs);authority=psycopg.connect(control,autocommit=True,**kwargs)
        report['capability']=capability(work,authority,database)
        if not apply:
            report.update(status='READ_ONLY_PLAN_COMPLETE',package_files=len(rows));return report
        report['approved_window_reference']=window
        if not core._scalar(authority,LOCK.replace('pg_advisory_lock','pg_try_advisory_lock')):
            raise Refused('MAINTENANCE_LOCK_BUSY_NO_INSTALL')
        locked=True
        report['admission_change_attempted']=True;save()
        authority.execute(sql.SQL('alter database {} with allow_connections false').format(sql.Identifier(database)))
        report['admission_closed']=True;save()
        pid=core._scalar(work,'select pg_backend_pid()');deadline=time.monotonic()+drain_seconds
        while core._scalar(authority,'select count(*) from pg_stat_activity where datname=%s and pid<>%s',(database,pid)):
            if time.monotonic()>=deadline:raise Refused('DRAIN_TIMEOUT_NO_INSTALL_STARTED')
            time.sleep(.05)
        # One retained work session for the entire package; no reconnect between
        # files, no admission gap, no termination of other sessions.
        for row,text in rows:
            if core._scalar(authority,'select datallowconn from pg_database where datname=%s',(database,)):raise Refused('ADMISSION_REOPENED_BEFORE_FILE')
            # A lost COMMIT acknowledgement is not evidence of rollback. Once
            # any file is attempted, a failure must retain closed admission.
            report.update(install_attempted=True,current_file_key=row['key']);save()
            with work.transaction(),work.cursor() as cur:
                cur.execute(transaction_body(text),prepare=False)
                cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(row['stamp'],row['name'],[text]))
            report['files'].append(dict(key=row['key'],status='PASS',sha256=row['package_sha256']));save()
        report.update(status='ALL_FILES_INSTALLED',package_files=30)
        # Even a successful package remains closed for installation review.
        # Owner configuration and canaries need a separately reviewed reopen
        # while application maintenance still blocks ordinary transactions.
        return report
    except Exception as exc:
        report.update(status='REFUSED' if isinstance(exc,Refused) or getattr(exc,'sqlstate',None)=='P0001' else 'INCOMPLETE',
          error_type=type(exc).__name__,sqlstate=getattr(exc,'sqlstate',None),
          error_code=str(exc) if isinstance(exc,Refused) else core._public_failure_code(exc))
        return report
    finally:
        try:
            if authority is not None and report['admission_change_attempted']:
                if not report['install_attempted']:
                    authority.execute(sql.SQL('alter database {} with allow_connections true').format(sql.Identifier(database)))
                    report['admission_reopened']=True
                report['admission_left_closed']=not core._scalar(authority,'select datallowconn from pg_database where datname=%s',(database,))
            if authority is not None and locked:authority.execute(LOCK.replace('pg_advisory_lock','pg_advisory_unlock'))
        except Exception as cleanup:
            report.update(status='INCOMPLETE',admission_state='UNKNOWN',cleanup_error_code=core._public_failure_code(cleanup))
        finally:
            if work is not None:work.close()
            if authority is not None:authority.close()
            save()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--report',required=True)
    args=parser.parse_args()
    report=run(os.environ['CP6_OWNER_TARGET_PGURL'],os.environ['CP6_OWNER_CONTROL_PGURL'],profile='ERP_ENTENG',report_path=args.report,
      apply=args.apply,window=os.environ.get('CP6_APPROVED_MAINTENANCE_WINDOW'),backup=os.environ.get('CP6_VERIFIED_BACKUP_RECEIPT'),certificate=os.environ.get('CP6_DATABASE_CA_CERT'))
    print(json.dumps({k:report[k] for k in ('label','status','mode','admission_closed','admission_left_closed','production_go')}))
    raise SystemExit(0 if report['status'] in ('READ_ONLY_PLAN_COMPLETE','ALL_FILES_INSTALLED') else 1)
if __name__=='__main__':main()
