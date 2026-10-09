"""Independent restore, scheduling, race and real HTTP acceptance probes. Disposable only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlparse,urlunparse
import hashlib,json,os,subprocess,tempfile,threading,time,uuid
import psycopg
from psycopg import sql
import cp6_auditor_modes as modes
import cp7_schedule as schedule
import cp7_nightly_backup as backup
import cp7_p19_plan_v2_cases as fixture
from cases_stage import wrap,check,save,admin,new_run,read_pages,temporaries,retained,clean,tick,refusal,api,digest_rows


def disposable(tools):
    u=urlparse(tools.admin)
    check(u.hostname in ('127.0.0.1','localhost','::1'),'Disposable loopback only')
    return u,u.path.lstrip('/')

def own_hashes(url):
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        conn.read_only=True
        tables=cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p') and n.nspname not in('pg_catalog','information_schema','cron') and n.nspname not like 'pg\\_%' order by 1,2").fetchall()
        return {s+'.'+t:digest_rows(cur,s,t) for s,t in tables}

def races(tools,today):
    def two_cleaners():
        with tools.connect() as conn,conn.cursor() as cur:
            r=new_run(cur,today);proof=read_pages(cur,r);kept=retained(cur,r);conn.commit()
        barrier=threading.Barrier(2)
        def call():
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait(10);x=tick(cur);conn.commit();return x
        with ThreadPoolExecutor(max_workers=2) as pool:
            a,b=pool.submit(call),pool.submit(call);results=[a.result(60),b.result(60)]
        with tools.connect() as conn,conn.cursor() as cur:
            check(retained(cur,r)==kept,'Two cleaners retain complete final state')
            check(read_pages(cur,r)['identity']==proof['identity'],'Two cleaners preserve identity')
            n=cur.execute('select count(*) from cp7_analysis_stage.cleanups where job_id=%s',(r['job'],)).fetchone()[0]
            check(n==1,'Two concurrent cleaners create one receipt',count=n,results=results)
            check(all(v['rows']==0 for v in temporaries(cur,r).values()),'Complete temporary cleanup once')
        return results

    def cron_run():
        u,database=disposable(tools);cron_url=urlunparse(u._replace(path='/postgres'))
        with tools.connect() as conn,conn.cursor() as cur:
            r=new_run(cur,today);proof=read_pages(cur,r);conn.commit();defs=schedule.definitions(cur)
        expected=[('cp7-staged-cleanup','*/5 * * * *','select cp7_ops.cleanup_tick()'),('cp7-staged-retention','30 19 * * *','select cp7_ops.retention_tick()')]
        check([(x['name'],x['schedule'],x['command']) for x in defs]==expected,'Exact declared schedule and WIB UTC conversion')
        # CLI install denial is proved before pg_cron mutation; database is still a disposable copy.
        cmd=['python',str(Path(schedule.__file__)),'install','--erp-url',tools.admin,'--cron-url',cron_url,'--database',database]
        denied=subprocess.run(cmd,capture_output=True,text=True)
        check(denied.returncode!=0 and 'INSTALL_NOT_APPROVED' in denied.stderr,'Explicit install approval required')
        with psycopg.connect(cron_url,autocommit=True) as conn,conn.cursor() as cur:
            before=cur.execute('select jobid,jobname,schedule,command,database,username,active from cron.job order by jobid').fetchall()
            version=cur.execute("select extversion from pg_extension where extname='pg_cron'").fetchone()[0]
            every='10 seconds' if tuple(map(int,version.split('.')[:2]))>=(1,5) else '* * * * *'
            since=cur.execute('select clock_timestamp()').fetchone()[0]
            ids=schedule.install(cur,database,'postgres',defs,{x['name']:every for x in defs})
            seen={}
            try:
                deadline=time.monotonic()+145
                while time.monotonic()<deadline:
                    seen={n:schedule.runs(cur,i,since) for n,i in ids.items()}
                    if all(any(x['status']=='succeeded' for x in v) for v in seen.values()):break
                    time.sleep(2)
                save('AS20-43_cron_first_runs',seen)
                check(all(any(x['status']=='succeeded' for x in v) for v in seen.values()),'Both actual pg_cron jobs fire successfully',runs=seen)
            finally:
                schedule.uninstall(cur,database)
                cur.execute('delete from cron.job_run_details where jobid=any(%s)',(list(ids.values()),))
            after=cur.execute('select jobid,jobname,schedule,command,database,username,active from cron.job order by jobid').fetchall()
            check(after==before,'Uninstall restores pretest cron jobs exactly')
        with tools.connect() as conn,conn.cursor() as cur:
            check(read_pages(cur,r)['identity']==proof['identity'],'Result available after actual scheduled cleanup')
            check(all(v['rows']==0 for v in temporaries(cur,r).values()),'Actual scheduler removed intermediates')
        return dict(version=version,test_only_schedule_override=every,runs=seen,approval_denied=denied.returncode)

    def cron_isolation():
        u,database=disposable(tools);cron_url=urlunparse(u._replace(path='/postgres'))
        # An independent second disposable database, never the hosted/primary ERP.
        other='cp7_astra_cron_'+uuid.uuid4().hex[:8]
        helper=backup.Tools(tools.admin,os.environ['CP6_DATABASE_CONTAINER'])
        helper.recreate(other)
        with tools.connect() as conn,conn.cursor() as cur:defs=schedule.definitions(cur)
        seen={};ids=[]
        try:
            with psycopg.connect(cron_url,autocommit=True) as conn,conn.cursor() as cur:
                before=cur.execute('select jobid,jobname,schedule,command,database,username,active from cron.job order by jobid').fetchall()
                # Future schedule avoids execution in the blank second DB. Installing one target must not repoint another.
                a=schedule.install(cur,other,'postgres',defs,{x['name']:'0 0 1 1 *' for x in defs});ids+=list(a.values())
                a_rows=schedule.installed(cur,other)
                b=schedule.install(cur,database,'postgres',defs,{x['name']:'0 0 1 1 *' for x in defs});ids+=list(b.values())
                after_a=schedule.installed(cur,other);after_b=schedule.installed(cur,database)
                seen=dict(before_other=a_rows,after_other=after_a,after_target=after_b)
                save('AS20-43_cross_database',seen)
                # Restore before raising any counterexample.
                for ident in set(ids):cur.execute('select cron.unschedule(%s::bigint)',(ident,))
                cur.execute('delete from cron.job_run_details where jobid=any(%s)',(list(set(ids)),))
                check(cur.execute('select jobid,jobname,schedule,command,database,username,active from cron.job order by jobid').fetchall()==before,'Cron test cleanup restored all prior jobs')
                check(after_a==a_rows,'Installing schedules for databaseB must not delete/repoint databaseA jobs',observed=seen)
        finally:
            with psycopg.connect(cron_url,autocommit=True) as conn,conn.cursor() as cur:
                for db in (other,database):schedule.uninstall(cur,db)
                if ids:cur.execute('delete from cron.job_run_details where jobid=any(%s)',(list(set(ids)),))
            helper.drop(other)
        return seen

    def restore():
        u,database=disposable(tools);container=os.environ['CP6_DATABASE_CONTAINER'];scratch='cp7_astra_restore_'+uuid.uuid4().hex[:8]
        with tools.connect() as conn,conn.cursor() as cur:
            r=new_run(cur,today);clean(cur,r);conn.commit();identity=read_pages(cur,r)['identity']
        before=own_hashes(tools.admin)
        with tempfile.TemporaryDirectory(prefix='astra-backup-') as dest:
            receipt=backup.backup(tools.admin,database,scratch,dest,container=container)
            save('AS20-44_writer_backup_receipt_reexecuted',receipt)
            check(receipt['restore_verified'] is True,'Actual backup restore verified',receipt=receipt)
            path=Path(dest)/receipt['file'];check(hashlib.sha256(path.read_bytes()).hexdigest()==receipt['sha256'],'Independent dump file SHA256')
            helper=backup.Tools(tools.admin,container)
            try:
                helper.recreate(scratch)
                subprocess.run(['docker','cp',str(path),container+':/tmp/'+path.name],capture_output=True,check=True)
                result=helper.restore(scratch,path)
                restored=own_hashes(backup.db_url(tools.admin,scratch))
                diff={k:dict(source=before.get(k),restored=restored.get(k)) for k in set(before)|set(restored) if before.get(k)!=restored.get(k)}
                save('AS20-44_independent_all_table_sha256',dict(source=before,restored=restored,difference=diff,pg_restore_exit=result.returncode))
                check(not diff,'Every non-system table row counted and independently SHA256 hashed after second restore',diff=diff)
                with psycopg.connect(backup.db_url(tools.admin,scratch)) as conn,conn.cursor() as cur:
                    check(read_pages(cur,r)['identity']==identity,'Restored retained result still readable through public actor API')
            finally:helper.drop(scratch);helper.remove_inner(path)
        return dict(tables=len(before),independent_algorithm='SHA256 length-framed sorted to_jsonb rows',original_identity=identity)

    def retention15():
        _,_=disposable(tools);container=os.environ['CP6_DATABASE_CONTAINER'];source='cp7_astra_nights_'+uuid.uuid4().hex[:8];scratch='cp7_astra_night_restore_'+uuid.uuid4().hex[:8]
        helper=backup.Tools(tools.admin,container);helper.recreate(source)
        try:
            with psycopg.connect(backup.db_url(tools.admin,source)) as conn,conn.cursor() as cur:
                cur.execute('create table public.astra_receipt(id integer primary key,numeric_fact numeric(20,6),text_fact text)')
                cur.execute("insert into public.astra_receipt values(1,73.123457,'Verified night Ω 🧵')");conn.commit()
            with tempfile.TemporaryDirectory(prefix='astra-15-nights-') as dest:
                start=datetime(2026,9,15,18,tzinfo=timezone.utc);receipts=[]
                for i in range(15):
                    got=backup.backup(tools.admin,source,scratch,dest,keep=14,container=container,now=start+timedelta(days=i))
                    receipts.append(got);save('AS20-45_fifteen_actual_restore_receipts',receipts)
                    check(got['restore_verified'] is True,'Each synthetic night is an actual dump/restore',night=i,result=got)
                current={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(dest).iterdir()}
                check(len(list(Path(dest).glob('*.dump')))==14,'Retain14 actually verified backups after15nights',files=list(current))
                failed=backup.backup(tools.admin,'astra_missing_source_'+uuid.uuid4().hex[:8],scratch,dest,keep=14,container=container,now=start+timedelta(days=15))
                check(not failed['restore_verified'] and not failed['retention']['removed'],'Failed next night never prunes')
                check(all((Path(dest)/p).exists() and hashlib.sha256((Path(dest)/p).read_bytes()).hexdigest()==h for p,h in current.items()),'Every earlier verified dump and receipt unchanged after failed night')
                # Source==scratch refusal must happen before any creation/drop.
                try:backup.backup(tools.admin,source,source,dest,container=container)
                except AssertionError:separate_refused=True
                else:separate_refused=False
                check(separate_refused,'Source cannot be scratch')
                return dict(actual_restores=15,calendar_simulated=True,kept=14,failed_night=failed)
        finally:helper.drop(source);helper.drop(scratch)

    def collision():
        _,_=disposable(tools);container=os.environ['CP6_DATABASE_CONTAINER'];source='cp7_astra_retry_'+uuid.uuid4().hex[:8];scratch='cp7_astra_retry_restore_'+uuid.uuid4().hex[:8]
        helper=backup.Tools(tools.admin,container);helper.recreate(source)
        try:
            with psycopg.connect(backup.db_url(tools.admin,source)) as conn,conn.cursor() as cur:
                cur.execute('create table public.astra_backup_control(id integer primary key)');cur.execute('insert into public.astra_backup_control values(73)');conn.commit()
            with tempfile.TemporaryDirectory(prefix='astra-backup-collision-') as dest:
                now=datetime(2026,10,9,18,0,0,tzinfo=timezone.utc)
                good=backup.backup(tools.admin,source,scratch,dest,container=container,now=now)
                check(good['restore_verified'] is True,'Verified baseline backup required')
                before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(dest).iterdir()}
                bad=backup.backup(tools.admin,'astra_missing_retry_'+uuid.uuid4().hex[:8],scratch,dest,container=container,now=now)
                after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(dest).iterdir()}
                save('AS20-45_same_second_failure',dict(good=good,failed=bad,before=before,after=after,clock_simulated=True))
                check(not bad['restore_verified'],'Failure injection really failed')
                check(all(after.get(p)==h for p,h in before.items()),'Failed backup attempt cannot overwrite prior verified dump or receipt at same-second filename',before=before,after=after,failed=bad)
                return dict(before=before,after=after)
        finally:helper.drop(source);helper.drop(scratch)

    return [wrap('AS20-40_TWO_CLEANERS',two_cleaners),wrap('AS20-43_REAL_CRON',cron_run),wrap('AS20-43_CRON_DATABASE_ISOLATION',cron_isolation),
      wrap('AS20-44_RESTORE_ALL_TABLES',restore),wrap('AS20-45_FIFTEEN_VERIFIED_NIGHTS',retention15),wrap('AS20-45_FAILED_RETRY_COLLISION',collision)]


def http_cases(http,today):
    def access_replay():
        actor=http.login('OWNER','astra-p20-current-authority')
        with http.connect() as conn,conn.cursor() as cur:
            fixture.fixture(cur,today);q=fixture.staged.query(today);conn.commit()
        key=str(uuid.uuid4());args=dict(p_query=q,p_request=key)
        first=actor.rpc('erp_cp7_request_staged_analysis_v1',args)
        check(first['status']==200,'Real authenticated request accepted',response=first)
        s=first
        for _ in range(20000):
            if s['body']['state']!='RUNNING':break
            s=actor.rpc('erp_cp7_step_staged_analysis_v1',dict(p_request=key));check(s['status']==200,'Every real HTTP step succeeds',response=s)
        check(s['body']['state']=='DONE','Complete real HTTP job',response=s)
        run=s['body']['run_id'];pages=actor.rpc('erp_cp7_read_staged_analysis_pages_v1',dict(p_run=run))
        check(pages['status']==200,'Real HTTP completed page read',response=pages)
        requests=[('erp_cp7_request_staged_analysis_v1',args),('erp_cp7_get_staged_analysis_v1',dict(p_request=key)),
         ('erp_cp7_read_staged_analysis_pages_v1',dict(p_run=run)),('erp_cp7_get_staged_ai_brief_v1',dict(p_run=run,p_targets=[])),
         ('erp_cp7_staged_snapshot_freshness_v1',dict(p_run=run)),('erp_cp7_step_reminder_conditions_v2',dict(p_run=run))]
        positive={name:actor.rpc(name,arg) for name,arg in requests}
        check(all(v['status']==200 for v in positive.values()),'Every revocation probe has a working authorized control',responses=positive)
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor.auth_user_id,));conn.commit()
        observed={name:actor.rpc(name,arg) for name,arg in requests}
        check(all(v['status']>=400 for v in observed.values()),'Old valid JWT loses access on every replay/consumer',responses=observed)
        return dict(created=first,done=s,revoked=observed)

    def private():
        actor=http.login('OWNER','astra-p20-private-api')
        results=[]
        probes=[('cp7_ops','cleanup_tick',{}),('cp7_ops','retention_tick',{}),('cp7_analysis_stage','clean_done',dict(p_job=str(uuid.uuid4()))),('cp7_analysis_stage','clean_pending',dict(p_limit=1)),('cp7_analysis_stage','purge_expired',dict(p_limit=1))]
        for schema,name,args in probes:
            public=actor.rpc(name,args);anon=http.anon_rpc(name,args)
            direct=modes._call(modes.REST_URL+'/rpc/'+name,args,{'apikey':http._anon,'Authorization':'Bearer '+actor._token,'Content-Profile':schema,'Accept-Profile':schema})
            row=dict(schema=schema,name=name,owner_public=public,anon_public=anon,explicit_private_profile=direct);results.append(row)
        check(all(x[k]['status']>=400 for x in results for k in ('owner_public','anon_public','explicit_private_profile')),'Private scheduled helpers unreachable via public or explicit REST profile',responses=results)
        return results

    return [wrap('AS20-01_HTTP_REVOKED_REPLAY',access_replay),wrap('AS20-02_HTTP_PRIVATE',private)]
