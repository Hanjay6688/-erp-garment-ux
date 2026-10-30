"""Actual PostgreSQL17 concurrency on a disposable synthetic model only."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from queue import Queue
import json
import os
import subprocess
import time
import traceback
import psycopg
import matrix

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='a6ded9cd4ce23a6d59cd32e42ca9bb33d793f8cc'
SCHEMA='cp7_lock_mechanics_model'
DATABASE='cp7_lock_mechanics'
CONNECT=dict(host='127.0.0.1',port=54329,dbname=DATABASE,user='postgres',password='disposable-lock-model')


def require(ok,message):
    if not ok:raise AssertionError(message)


def source():
    cfg=json.loads((HERE/'SOURCE.json').read_bytes())
    require(cfg['base']==BASE and cfg['actual_ERP_Native_cases']==0,'EXACT_SOURCE_CONTRACT_REQUIRED')
    for name,pin in cfg['files'].items():
        p=ROOT/name
        require(not any(x.is_symlink()for x in(p,*p.parents)if x.is_relative_to(ROOT)),'SOURCE_LINK_REFUSED')
        raw=p.read_bytes();require({'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==pin,'SOURCE_BYTES_CHANGED:'+name)
    changed=set(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',BASE,'HEAD'],text=True).splitlines())
    require(changed==set(cfg['files'])|{str((HERE/'SOURCE.json').relative_to(ROOT))},'EXACT_PREPARED_SOURCE_DELTA_REQUIRED')
    require(not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=no']).strip(),'DIRTY_TRACKED_SOURCE')
    return dict(head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        manifest_sha256=sha256((HERE/'SOURCE.json').read_bytes()).hexdigest(),files=len(cfg['files']),base=BASE)


def connect():
    c=psycopg.connect(**CONNECT)
    try:
        require(c.execute('select current_database()').fetchone()==(DATABASE,),'EXACT_MODEL_DATABASE_REQUIRED')
        require(170000<=int(c.execute('show server_version_num').fetchone()[0])<180000,'POSTGRESQL17_REQUIRED')
        c.rollback();return c
    except BaseException:
        c.close();raise


def snapshot():
    with connect()as c:
        rows={table:c.execute('select *from '+SCHEMA+'.'+table+' order by 1').fetchall()
              for table in('root','child','effects')}
        seq={name:c.execute('select last_value,is_called from '+SCHEMA+'.'+name).fetchone()
             for name in('effects_id_seq','before_effect_seq')}
        return dict(rows=rows,sequences=seq)


def pair(held,requested):
    with connect()as holder,connect()as worker:
        hp=holder.execute('select pg_backend_pid()').fetchone()[0]
        wp=worker.execute('select pg_backend_pid()').fetchone()[0]
        holder.execute('lock table '+SCHEMA+'.root in '+held+' mode')
        observed=holder.execute("select count(*)from pg_locks where pid=pg_backend_pid()and relation=%s::regclass and mode=%s and granted",
            (SCHEMA+'.root',held.title().replace(' ','')+'Lock')).fetchone()[0]==1
        try:worker.execute('lock table '+SCHEMA+'.root in '+requested+' mode nowait');state=None
        except psycopg.Error as error:state=error.sqlstate
        worker.rollback();holder.rollback()
        return dict(held=held,requested=requested,refused=state is not None,sqlstate=state,
            two_actual_backends=hp!=wp,holder_lock_observed=observed)


def fk_holder(requested):
    with connect()as holder,connect()as worker:
        holder.execute('insert into '+SCHEMA+'.child values(11,1)')
        locks=[r[0]for r in holder.execute("select mode from pg_locks where pid=pg_backend_pid()and relation=%s::regclass and granted order by mode",(SCHEMA+'.root',))]
        require('RowShareLock'in locks,'REAL_FK_ROW_SHARE_NOT_OBSERVED')
        try:worker.execute('lock table '+SCHEMA+'.root in '+requested+' mode nowait');state=None
        except psycopg.Error as error:state=error.sqlstate
        worker.rollback();holder.rollback()
        expected='55P03'if requested=='EXCLUSIVE'else None
        require(state==expected,dict(error='FK_HOLDER_CONFLICT_MISMATCH',requested=requested,sqlstate=state))
        return dict(requested=requested,actual_FK_parent_locks=locks,sqlstate=state,
            classification='ACTUAL_FK_LOCK_MECHANICS_NOT_ERP_FK_CLOSURE')


def before_effect():
    before=snapshot()
    with connect()as holder,connect()as worker:
        holder.execute('select *from '+SCHEMA+'.root for key share')
        try:worker.execute('select '+SCHEMA+'.command()');state=None
        except psycopg.Error as error:state=error.sqlstate
        require(state=='55P03','MODEL_COMMAND_MUST_REFUSE_BEFORE_SEQUENCE_OR_ROW_EFFECT')
        worker.rollback();holder.rollback()
    after=snapshot();require(after==before,'MODEL_ROWS_OR_SEQUENCES_CHANGED_ON_BUSY')
    return dict(sqlstate=state,model_before=before,model_after=after,complete_model_noeffect=True,
        actual_ERP_Native_cases=0)


def reader():
    with connect()as holder,connect()as worker:
        holder.execute('lock table '+SCHEMA+'.root in exclusive mode nowait')
        worker.execute("set local statement_timeout='2s'")
        rows=worker.execute('select *from '+SCHEMA+'.root order by id').fetchall()
        require(rows==[(1,'unchanged')],'ORDINARY_READER_MUST_REMAIN_AVAILABLE')
        worker.rollback();holder.rollback()
    return dict(plain_SELECT_while_EXCLUSIVE_held=True,rows=rows)


def blocked_writer(sql,release):
    before=snapshot();ready=Queue()
    def send():
        with connect()as c:
            c.execute("set local lock_timeout='8s';set local statement_timeout='10s'")
            ready.put(c.execute('select pg_backend_pid()').fetchone()[0])
            c.execute(sql)
            c.rollback();return dict(completed_after_release=True,worker_changes_rolled_back=True)
    with connect()as holder,connect()as observer,ThreadPoolExecutor(max_workers=1)as pool:
        hp=holder.execute('select pg_backend_pid()').fetchone()[0]
        holder.execute('lock table '+SCHEMA+'.root in exclusive mode nowait')
        job=pool.submit(send);wp=ready.get(timeout=5)
        try:
            deadline=time.monotonic()+4;blocked=False
            while time.monotonic()<deadline:
                observer.execute('select pg_stat_clear_snapshot()')
                blocked=observer.execute('select %s=any(pg_blocking_pids(%s))',(hp,wp)).fetchone()[0]
                observer.rollback()
                if blocked:break
                require(not job.done(),'WRITER_UNEXPECTEDLY_COMPLETED_BEFORE_RELEASE')
                time.sleep(.01)
            require(blocked and hp!=wp,'ACTUAL_HOLDER_BLOCKING_WRITER_REQUIRED')
            getattr(holder,release)();result=job.result(timeout=10)
        finally:holder.rollback()
    after=snapshot();require(after==before,'SYNTHETIC_WORKER_ROLLBACK_MODEL_NOT_EXACT')
    return dict(actual_holder_blocks_worker=True,holder_pid=hp,worker_pid=wp,
        release=release,sql=sql,worker=result,all_model_rows_sequences_restored=True)


def run():
    proof=source();report=dict(status='INCOMPLETE',source=proof,classification='ACTUAL_POSTGRESQL17_SYNTHETIC_LOCK_MODEL',
        actual_ERP_Native_cases=0,ERP_writer_trigger_FK_census_closed=False,ERP_lock_profile_qualified=False,
        production_go=False,independent_acceptance=False)
    created=False
    try:
        with connect()as c:
            report['server_version']=c.execute('select version()').fetchone()[0]
            require(c.execute('select count(*)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()==(0,),
                    'MODEL_SCHEMA_ALREADY_EXISTS_REFUSED')
            c.execute('create schema '+SCHEMA)
            c.execute('create table '+SCHEMA+'.root(id integer primary key,payload text not null)')
            c.execute('create table '+SCHEMA+'.child(id integer primary key,root_id integer not null references '+SCHEMA+'.root(id))')
            c.execute('create table '+SCHEMA+'.effects(id bigserial primary key,payload text not null)')
            c.execute('create sequence '+SCHEMA+'.before_effect_seq')
            c.execute('insert into '+SCHEMA+'.root values(1,\'unchanged\')')
            c.execute('create function '+SCHEMA+".command()returns void language plpgsql as $$begin lock table "+SCHEMA+
                '.root in exclusive mode nowait;perform nextval(\''+SCHEMA+'.before_effect_seq\');insert into '+SCHEMA+".effects(payload)values('effect');end$$")
            c.commit();created=True
        baseline=snapshot()
        report['pairs']=[pair(h,r)for h in matrix.MODES for r in('SHARE','SHARE ROW EXCLUSIVE','EXCLUSIVE')]
        report['matrix_gate']=matrix.complete(report['pairs'])
        report['foreign_key_holders']=[fk_holder(m)for m in('SHARE ROW EXCLUSIVE','EXCLUSIVE')]
        report['before_effect_busy']=before_effect()
        report['ordinary_reader']=reader()
        report['real_blocking']=[blocked_writer(sql,release)for release in('commit','rollback')for sql in(
            'insert into '+SCHEMA+'.root values(99,\'phantom\')',
            'insert into '+SCHEMA+'.child values(22,1)')]
        require(snapshot()==baseline,'COMPLETE_MODEL_NOT_RESTORED')
        report['complete_model_rows_sequences_equal']=True
        report['status']='PASS'
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if created:
            try:
                with connect()as c:c.execute('drop schema '+SCHEMA+' cascade')
                with connect()as c:
                    require(c.execute('select count(*)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()==(0,),'MODEL_SCHEMA_RESIDUE')
                    remaining=c.execute("select count(*)from pg_stat_activity where datname=current_database()and backend_type='client backend'and pid<>pg_backend_pid()").fetchone()[0]
                    require(remaining==0,'MODEL_SESSION_LEAKS')
                report['model_removed_and_no_session_leaks']=True
            except Exception as error:report.update(status='INCOMPLETE',cleanup_error=str(error))
        (ROOT/'LOCK_MECHANICS_REPORT.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in('status','classification','actual_ERP_Native_cases','error','cleanup_error','model_removed_and_no_session_leaks')}))
    require(report['status']=='PASS','LOCK_MECHANICS_NOT_PASS')


if __name__=='__main__':run()
