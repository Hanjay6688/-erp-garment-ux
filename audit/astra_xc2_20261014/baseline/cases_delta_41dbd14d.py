"""Independent delta oracles. Writer helpers supply valid staged fixtures only, never verdicts."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import uuid,json,time,subprocess,os
import psycopg
from psycopg import sql
import cp7_p19_staged_cases as staged
import cp7_p19_report_v2_cases as fixture
import cp7_nightly_backup as backup
import cp6_auditor_runner as native

TABLES=['outputs','target_rows','pair_rows','pair_lists','fragments']
def counts(cur,job):
    native.api.admin(cur)
    return {t:cur.execute(sql.SQL('select count(*) from cp7_analysis_stage.{} where job_id=%s').format(sql.Identifier(t)),(job,)).fetchone()[0] for t in TABLES}
def digest(cur,run):
    native.api.admin(cur)
    return {t:cur.execute(sql.SQL("select md5(coalesce(string_agg(x::text,chr(10) order by x::text),'')),count(*) from cp7_analysis_stage.{} x where run_id=%s").format(sql.Identifier(t)),(run,)).fetchone() for t in ['headers','pages','page_sets']}
def blocked(cur,operation,code):
    cur.execute('savepoint asra_expected_refusal')
    try:operation();got=None
    except psycopg.Error as e:got=dict(sqlstate=e.sqlstate,message=e.diag.message_primary)
    finally:cur.execute('rollback to savepoint asra_expected_refusal');cur.execute('release savepoint asra_expected_refusal');native.api.admin(cur)
    assert got and got['sqlstate']==code,dict(expected=code,observed=got)
    return got

def cases(cur,today):
    def scoped_clean():
        a=fixture.staged_run(cur,today);b=fixture.staged_run(cur,today)
        ca,cb=counts(cur,a['job']),counts(cur,b['job']);da,db=digest(cur,a['run']),digest(cur,b['run'])
        assert sum(ca.values())>0 and sum(cb.values())>0
        out=cur.execute('select cp7_analysis_stage.clean_done(%s)',(a['job'],)).fetchone()[0]
        assert out['state']=='CLEANED' and out['removed']==ca
        assert sum(counts(cur,a['job']).values())==0 and counts(cur,b['job'])==cb
        assert digest(cur,a['run'])==da and digest(cur,b['run'])==db
        assert cur.execute("select coalesce(current_setting('cp7.analysis_work_delete',true),'')").fetchone()[0]==''
        again=cur.execute('select cp7_analysis_stage.clean_done(%s)',(a['job'],)).fetchone()[0]
        assert again['state']=='ALREADY_CLEANED'
        original,_,_=staged.fetch(cur,a['run']);assert original==a['original']
        return dict(status='PASS',removed=ca,other_job_unchanged=True,final_tables_unchanged=True,reopened_original_equal=True,idempotent=True)
    def guard_controls():
        a=fixture.staged_run(cur,today);before=counts(cur,a['job']);results=[]
        assert before['outputs']>0
        results.append(blocked(cur,lambda:cur.execute('delete from cp7_analysis_stage.outputs where job_id=%s',(a['job'],)),'55000'))
        cur.execute("select set_config('cp7.analysis_work_delete',%s,true)",(str(uuid.uuid4()),))
        results.append(blocked(cur,lambda:cur.execute('delete from cp7_analysis_stage.outputs where job_id=%s',(a['job'],)),'55000'))
        cur.execute("select set_config('cp7.analysis_work_delete',%s,true)",(a['job'],))
        results.append(blocked(cur,lambda:cur.execute('update cp7_analysis_stage.outputs set output=output where job_id=%s',(a['job'],)),'55000'))
        for role in ['anon','authenticated','service_role']:
            def denied(role=role):
                cur.execute(sql.SQL('set local role {}').format(sql.Identifier(role)))
                cur.execute("select set_config('cp7.analysis_work_delete',%s,true)",(a['job'],))
                cur.execute('delete from cp7_analysis_stage.outputs where job_id=%s',(a['job'],))
            results.append(blocked(cur,denied,'42501'))
        cur.execute("select set_config('cp7.analysis_work_delete','',true)")
        assert counts(cur,a['job'])==before
        return dict(status='PASS',refusals=results,rows_unchanged=True)
    def schedule_boundary():
        script=Path(staged.__file__).parent/'cp7_schedule.py'
        results=[]
        for action in ['install','verify','uninstall']:
            args=['python',str(script),action,'--erp-url',native.boundary.ADMIN,'--cron-url',native.boundary.PRIMARY_ADMIN,'--database','astra_wrong_disposable_name']
            p=subprocess.run(args,capture_output=True,text=True)
            assert p.returncode!=0 and 'CP7_SCHEDULE_DATABASE_MISMATCH' in p.stderr,(action,p.returncode,p.stderr[-500:])
            results.append(dict(action=action,exit=p.returncode,code='CP7_SCHEDULE_DATABASE_MISMATCH'))
        for action,code in [('install','CP7_SCHEDULE_INSTALL_NOT_APPROVED'),('uninstall','CP7_SCHEDULE_UNINSTALL_NOT_APPROVED')]:
            p=subprocess.run(['python',str(script),action,'--erp-url',native.boundary.ADMIN,'--cron-url',native.boundary.PRIMARY_ADMIN,'--database','cp6_rollback'],capture_output=True,text=True)
            assert p.returncode!=0 and code in p.stderr,(action,p.returncode,p.stderr[-500:])
            results.append(dict(action=action,exit=p.returncode,code=code))
        return dict(status='PASS',observations=results,no_schedule_installed=True)
    return [('ASD-N01-CLEANUP-SCOPED-AND-REOPEN',scoped_clean),('ASD-N02-IMMUTABILITY-AND-GUC-SPOOF',guard_controls),('ASD-N03-SCHEDULE-CLI-BOUNDARY',schedule_boundary)]

def races(tools,today):
    def nightly_case(kind):
        # Each backup source is a tiny, audit-owned database created from template0 in this disposable cluster.
        tag=uuid.uuid4().hex[:12];source='astra_backup_source_'+tag;scratch='astra_backup_scratch_'+tag
        admin=tools.admin;source_url=backup.db_url(admin,source);scratch_url=backup.db_url(admin,scratch)
        evidence=Path(native.r1.AUDITOR if hasattr(native.r1,'AUDITOR') else Path(staged.__file__).resolve().parents[1])/'cp6-proof/t3'/('ASD_BACKUP_'+kind)
        original_dump=backup.Tools.dump;observed={}
        def create(name,marker):
            with psycopg.connect(backup.db_url(admin,'postgres'),autocommit=True) as conn:
                conn.execute(sql.SQL('create database {} template template0').format(sql.Identifier(name)))
            with psycopg.connect(backup.db_url(admin,name)) as conn:
                conn.execute('create table public.astra_canary(k integer primary key,v text not null)')
                conn.execute('insert into public.astra_canary values(1,%s)',(marker,));conn.commit()
        def drop(name):
            assert name.startswith('astra_backup_')
            with psycopg.connect(backup.db_url(admin,'postgres'),autocommit=True) as conn:conn.execute(sql.SQL('drop database if exists {} with(force)').format(sql.Identifier(name)))
        def witness():
            if backup.scratch_state(admin,scratch) is None:return None
            with psycopg.connect(scratch_url) as conn:return conn.execute('select v from public.astra_canary where k=1').fetchone()[0]
        try:
            create(source,'SOURCE_ORIGINAL')
            if kind=='FOREIGN_BEFORE':create(scratch,'FOREIGN_PROTECTED')
            elif kind in ('OWNED_LEFTOVER','REPLACED_LEFTOVER'):
                create(scratch,'OWNED_OLD');backup.mark_scratch(admin,scratch)
            def dump(self,src,target,snapshot):
                result=original_dump(self,src,target,snapshot)
                if kind=='FOREIGN_APPEARS':create(scratch,'FOREIGN_PROTECTED')
                elif kind=='LIVE_WRITE':
                    with psycopg.connect(source_url) as conn:conn.execute("insert into public.astra_canary values(2,'AFTER_EXPORTED_SNAPSHOT')");conn.commit()
                elif kind=='REPLACED_LEFTOVER':
                    drop(scratch);create(scratch,'FOREIGN_REPLACEMENT')
                    observed['replacement_before_resume']=dict(state=backup.scratch_state(admin,scratch),canary=witness())
                return result
            backup.Tools.dump=dump
            result=backup.backup(admin,source,scratch,evidence,container=os.environ['CP6_DATABASE_CONTAINER'])
            final=witness();observed.update(receipt=result,foreign_canary_after=final)
            with psycopg.connect(source_url) as conn:observed['source_rows']=conn.execute('select k,v from public.astra_canary order by k').fetchall()
            if kind in ('FOREIGN_BEFORE','FOREIGN_APPEARS','REPLACED_LEFTOVER'):
                expected='FOREIGN_REPLACEMENT' if kind=='REPLACED_LEFTOVER' else 'FOREIGN_PROTECTED'
                ok=final==expected and result['restore_verified'] is False and bool(result.get('error')) and result['retention']['removed']==[]
            else:
                ok=result['restore_verified'] is True and final is None and result['data']['rows']==1 and not result['data']['differ']
                if kind=='LIVE_WRITE':ok=ok and len(observed['source_rows'])==2
            return dict(status='PASS' if ok else 'COUNTEREXAMPLE',fixture='Audit-owned PostgreSQL source and scratch, deterministic pause at completed real pg_dump; no product code changed',**observed)
        finally:backup.Tools.dump=original_dump;drop(scratch);drop(source)
    def clean_vs_step():
        with tools.connect() as conn,conn.cursor() as cur:
            a=fixture.staged_run(cur,today);key=uuid.uuid4();out=staged.request(cur,today,key);assert out['state']=='RUNNING';staged.step(cur,key);native.api.admin(cur);conn.commit()
        with tools.connect() as held,held.cursor() as hcur:
            native.api.admin(hcur);clean=hcur.execute('select cp7_analysis_stage.clean_done(%s)',(a['job'],)).fetchone()[0]
            assert clean['state']=='CLEANED'
            with tools.connect() as active,active.cursor() as acur:
                t=time.monotonic();out=staged.step(acur,key,timeout='8s');elapsed=time.monotonic()-t;active.commit()
                assert out['state'] in ('RUNNING','DONE') and elapsed<8,out
            held.commit()
        return dict(status='PASS',elapsed_seconds=elapsed,other_job_state=out['state'],cleanup_transaction_held_during_step=True)
    return [(f'ASD-B{i+1:02d}-{kind}',lambda kind=kind:nightly_case(kind)) for i,kind in enumerate(['FOREIGN_BEFORE','FOREIGN_APPEARS','LIVE_WRITE','OWNED_LEFTOVER','REPLACED_LEFTOVER'])]+[('ASD-R01-CLEANUP-DOES-NOT-BLOCK-OTHER-STEP',clean_vs_step)]

def http_cases(http,today):
    def owner_only_replay():
        owner=http.login('OWNER','astra-pl5-owner');admin=http.login('ADMIN','astra-pl5-admin')
        reader='erp_cp7_get_history_yield_policy_v1';writer='erp_cp7_save_history_yield_policy_v1'
        ow=owner.rpc(reader);ad=admin.rpc(reader)
        assert ow['status']==ad['status']==200 and ow['body']['manage_allowed'] is True and ad['body']['manage_allowed'] is False
        revision=ow['body']['current']['revision'] if ow['body']['current'] else '0'
        args=dict(p_payload=dict(expected_revision=revision,state='ACTIVE',reason='Astra independent owner-role boundary',window_days='180',min_groups='5',min_cut_pcs='200',confidence='0.90'),p_request=str(uuid.uuid4()))
        reject=admin.rpc(writer,args);assert reject['status']==403 and reject['body']['message']=='CP7_YIELD_POLICY_OWNER_REQUIRED',reject
        first=owner.rpc(writer,args);assert first['status']==200 and first['body']['policy']['actor_role']=='OWNER',first
        assert owner.rpc(writer,args)==first
        with http.connect() as conn:
            before=conn.execute('select count(*) from cp7_yield_policy.policies').fetchone()[0]
            conn.execute("update erp.app_users set role='ADMIN',role_id=(select id from erp.app_roles where role_code='ADMIN') where auth_user_id=%s",(owner.auth_user_id,));conn.commit()
        replay=owner.rpc(writer,args)
        fresh=owner.rpc(writer,dict(args,p_request=str(uuid.uuid4())))
        assert replay['status']==fresh['status']==403 and replay['body']['message']=='CP7_YIELD_POLICY_OWNER_REQUIRED',(replay,fresh)
        after_read=owner.rpc(reader);assert after_read['status']==200 and after_read['body']['manage_allowed'] is False
        with http.connect() as conn:after=conn.execute('select count(*) from cp7_yield_policy.policies').fetchone()[0]
        assert before==after
        return dict(status='PASS',admin_write=reject['status'],owner_save=first['status'],same_uuid_after_downgrade=replay['status'],new_uuid_after_downgrade=fresh['status'],rows_before=before,rows_after=after)
    return [('ASD-H01-PL5-OWNER-ONLY-REPLAY-REVOKED',owner_only_replay)]
