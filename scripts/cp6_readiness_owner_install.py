"""Pinned CP6 installer from hosted v2.6.20 using its database owner.

Default CLI mode only reads metadata. --apply requires an approved maintenance
reference and a restored backup receipt. This file is never called on hosted by
CI. The full path prepends 28 frozen predecessor files to the accepted 30-file
package. No SQL bytes or guards change. An AB-only suffix is explicitly separate.
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
PREFIX_SHA='390171162cc897445278b2abcdda6f1e68fd447c3585c45f9b3b27147eb4efe3'
FULL_SHA=hashlib.sha256((PREFIX_SHA+':'+MANIFEST_SHA).encode()).hexdigest()
FULL='FULL_FROM_V2620'
SUFFIX='AC_BF_FROM_AB'
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
        expected_c={'host':'127.0.0.1','port':'54322','user':'postgres','dbname':'template1'}
    elif profile=='ERP_ENTENG':
        expected_t={'host':f'db.{PROJECT}.supabase.co','port':'5432','user':'postgres','dbname':'postgres'}
        expected_c={**expected_t,'dbname':'template1'}
    else:raise Refused('PROFILE_NOT_ALLOWED')
    if any(t.get(k)!=v for k,v in expected_t.items()) or any(c.get(k)!=v for k,v in expected_c.items()):raise Refused('ENDPOINT_NOT_ALLOWED')
    return t['dbname']

def files(mode):
    if mode not in (FULL,SUFFIX):raise Refused('INSTALL_MODE_NOT_ALLOWED')
    raw=(ROOT/'supabase/release/cp6-t3/MANIFEST.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise Refused('MANIFEST_DRIFT')
    rows=json.loads(raw)['files']
    if [r['key'] for r in rows]!=[k.upper() for k in package.KEYS]:raise Refused('PACKAGE_ORDER_DRIFT')
    result=[]
    if mode==FULL:
        prefix=(ROOT/'docs/cp6-readiness/PREDECESSOR_MANIFEST.json').read_bytes()
        if hashlib.sha256(prefix).hexdigest()!=PREFIX_SHA:raise Refused('PREDECESSOR_MANIFEST_DRIFT')
        prior=json.loads(prefix)['files']
        if [r['key'] for r in prior]!=list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')+['AA','AB']:raise Refused('PREDECESSOR_ORDER_DRIFT')
        for row in prior:
            if not row['file'].startswith('supabase/migrations/') or '..' in Path(row['file']).parts:raise Refused('PREDECESSOR_PATH')
            text=(ROOT/row['file']).read_text()
            if hashlib.sha256(text.encode()).hexdigest()!=row['sha256']:raise Refused('PREDECESSOR_FILE_DRIFT')
            transaction_body(text)
            result.append(({**row,'package_sha256':row['sha256']},text))
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

def capability(work,control,database,mode,rows):
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
        versions={row[0] for row in work.execute('select version from erp.schema_migrations').fetchall()}
        applied=[row['key'] for row,_ in rows if 'v2.6.20'+row['key'].lower() in versions]
        baseline='v2.6.20' if mode==FULL else 'v2.6.20ab'
        baseline_differ=[]
        if mode==FULL and baseline in versions and not applied:
            import cp6_g01_fingerprint as fingerprint
            pinned=json.loads((ROOT/'docs/evidence/cp6-g01/hosted_summary.json').read_text())['summary']
            live=core._scalar(work,fingerprint.SUMMARY)
            baseline_differ=sorted(k for k in set(pinned)|set(live) if k!='platform_ledger' and pinned.get(k)!=live.get(k))
        return dict(same_cluster=True,target_database=database,control_database='template1',control_owns_target=True,
          control_is_superuser=core._scalar(control,'select rolsuper from pg_roles where rolname=current_user'),
          work_is_superuser=core._scalar(work,'select rolsuper from pg_roles where rolname=current_user'),
          required_baseline=baseline,baseline_present=baseline in versions,baseline_differ=baseline_differ,already_applied_target_keys=applied,
          other_sessions=core._scalar(control,'select count(*) from pg_stat_activity where datname=%s and pid<>%s',(database,core._scalar(work,'select pg_backend_pid()'))))

def approval(profile,window,backup,mode):
    if profile=='DISPOSABLE' and window=='DISPOSABLE_CI_ONLY':return
    if profile!='ERP_ENTENG' or not window or not backup:raise Refused('APPROVED_WINDOW_AND_RESTORED_BACKUP_REQUIRED')
    record=json.loads(Path(backup).read_text())
    if record.get('project_ref')!=PROJECT or record.get('database')!='postgres' or record.get('restore_verified') is not True or record.get('manifest_sha256')!=(FULL_SHA if mode==FULL else MANIFEST_SHA) or record.get('install_mode')!=mode:raise Refused('BACKUP_RECEIPT_NOT_FOR_THIS_INSTALL')
    checked=datetime.fromisoformat(record['verified_at'])
    if checked.tzinfo is None or not 0<= (datetime.now(timezone.utc)-checked).total_seconds()<=3600:raise Refused('BACKUP_VERIFICATION_NOT_FRESH')

def owner_verified(cur):
    """Keep every Native catalog/body/RLS/coverage check with the actual owner.

    The existing probe's q()/one() reset a superuser fixture session before
    reading. A real postgres owner cannot perform that fixture reset. Replace
    only the Python fixture reset, for this metadata call, with an assertion
    that the unchanged current/session user is postgres. No SQL grant, role,
    guard, business function or expected body is changed or skipped.
    """
    import cp6_bf_probe as native
    fixture_api=native.be.bdp.api
    previous=fixture_api.admin
    def keep_owner(cursor):
        if cursor.execute('select current_user,session_user').fetchone()!=('postgres','postgres'):
            raise Refused('NATIVE_OWNER_IDENTITY_CHANGED')
    keep_owner(cur)
    try:
        fixture_api.admin=keep_owner
        return native.verified(cur)
    finally:fixture_api.admin=previous

def run(target,control,*,profile,report_path,mode=FULL,apply=False,window=None,backup=None,certificate=None,drain_seconds=15):
    report=dict(label='CP6_OWNER_MAINTENANCE',status='INCOMPLETE',profile=profile,mode='APPLY' if apply else 'READ_ONLY_PLAN',
      install_mode=mode,manifest_sha256=FULL_SHA if mode==FULL else MANIFEST_SHA,release_manifest_sha256=MANIFEST_SHA,
      predecessor_manifest_sha256=PREFIX_SHA if mode==FULL else None,files=[],admission_change_attempted=False,install_attempted=False,admission_closed=False,
      admission_reopened=False,admission_left_closed=False,production_go=False)
    work=authority=None;locked=False;database=None
    def save():
        Path(report_path).parent.mkdir(parents=True,exist_ok=True);Path(report_path).write_text(json.dumps(report,indent=2)+'\n')
    try:
        database=endpoints(target,control,profile);rows=files(mode)
        kwargs={'connect_timeout':15,'application_name':'cp6-owner-maintenance'}
        if profile=='ERP_ENTENG':
            if not certificate or not Path(certificate).is_file():raise Refused('SERVER_CERTIFICATE_REQUIRED')
            kwargs.update(sslmode='verify-full',sslrootcert=certificate)
        if apply:approval(profile,window,backup,mode)
        work=psycopg.connect(target,autocommit=True,**kwargs);authority=psycopg.connect(control,autocommit=True,**kwargs)
        report['capability']=capability(work,authority,database,mode,rows)
        if not report['capability']['baseline_present']:raise Refused('LIVE_REQUIRED_BASELINE_MISSING')
        if report['capability']['already_applied_target_keys']:raise Refused('LIVE_TARGET_ALREADY_APPLIED_OR_PARTIAL')
        if report['capability']['baseline_differ']:raise Refused('LIVE_G01_BASELINE_DRIFT')
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
                ledger_text=text[:-1] if row.get('ledger_omit_final_newline') else text
                cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',(row['stamp'],row['name'],[ledger_text]))
            report['files'].append(dict(key=row['key'],status='PASS',sha256=row['package_sha256']));save()
        # The retained target session can still read the closed database. Bind
        # the receipt to exact Native bodies/RLS and a catalog/config snapshot
        # before closing that session; a new target login is then impossible
        # until the separately reviewed admission reopen.
        import cp6_g01_fingerprint as fingerprint
        with work.transaction(),work.cursor() as cur:
            cur.execute('set transaction read only')
            result=owner_verified(cur)
            cur.execute(fingerprint.SUMMARY);snapshot=cur.fetchone()[0]
        report.update(native_stage_verified=result['stage'],native_sql_sha256=result['bf_sql_sha256'],
          installed_catalog_sha256=hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        report.update(status='ALL_FILES_INSTALLED',package_files=len(rows))
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
    parser.add_argument('--install-mode',choices=(FULL,SUFFIX),default=FULL)
    args=parser.parse_args()
    report=run(os.environ['CP6_OWNER_TARGET_PGURL'],os.environ['CP6_OWNER_CONTROL_PGURL'],profile='ERP_ENTENG',report_path=args.report,
      mode=args.install_mode,apply=args.apply,window=os.environ.get('CP6_APPROVED_MAINTENANCE_WINDOW'),backup=os.environ.get('CP6_VERIFIED_BACKUP_RECEIPT'),certificate=os.environ.get('CP6_DATABASE_CA_CERT'))
    print(json.dumps({k:report[k] for k in ('label','status','mode','admission_closed','admission_left_closed','production_go')}))
    raise SystemExit(0 if report['status'] in ('READ_ONLY_PLAN_COMPLETE','ALL_FILES_INSTALLED') else 1)
if __name__=='__main__':main()
