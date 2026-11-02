"""Only the three missing catalog/quiescence controls; retain the actual four.

The failed original remains failed. Its four completed source-pinned cases are
not executed here. Permanent transaction-ID locks, not the snapshot xip sublist,
must expose a preexisting uncommitted catalog writer before model effects.
"""
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlsplit
import argparse,importlib.util,json,os,uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp7-proof'
IDS=('PREEXISTING_CATALOG_WRITER_REFUSED_BY_FRESH_XID_QUIESCENCE_BEFORE_EFFECT',
     'ALL_CATALOG_SHARE_LOCKS_ALLOW_EXISTING_FUNCTION_AND_ORDINARY_DML',
     'ACTUAL_EMPTY_IDENTIFIER_AND_EMPTY_SEARCH_PATH_SETTINGS_DIFFER')
NO_CREDIT=dict(actual_ERP_cases=0,actual_Native_cases=0,global_writer_closure=False,
    production_go=False,independent_acceptance=False)


def require(value,message):
    if not value:raise ValueError(message)


def source():
    raw=(HERE/'probe.py').read_bytes()
    manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    origin=json.loads((HERE/'FOCUSED3_TXLOCK_REPAIR_ORIGIN.json').read_bytes())
    current=Path(__file__).read_text()
    for route in reversed(origin['routes']):
        require(current.count(route['after'])==route['count'],'CATALOG_FOCUSED3_EXACT_REPAIR_REVERSE')
        current=current.replace(route['after'],route['before'],route['count'])
    recovered=current.encode()
    require(dict(bytes=len(recovered),sha256=sha256(recovered).hexdigest())==origin['before'],
        'CATALOG_FOCUSED3_ORIGINAL_209_SOURCE_MUST_BE_RECOVERED')
    require(manifest['retained_original_probe']==dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),
        'CATALOG_FOCUSED3_ORIGINAL_PROBE_MUST_STAY_EXACT')
    spec=importlib.util.spec_from_file_location('catalog_original_source_check_ONLY',HERE/'probe.py')
    prototype=importlib.util.module_from_spec(spec);spec.loader.exec_module(prototype)
    return prototype.source()  # Never prototype.run().


def run():
    import psycopg
    from psycopg import sql
    require(os.environ.get('CATALOG_LOCK_CONFIRM')=='cp7_catalog_locks','CATALOG_FOCUSED3_CONFIRMATION')
    url=os.environ['CATALOG_LOCK_URL'];parts=urlsplit(url)
    require(parts.hostname in('127.0.0.1','localhost')and parts.port==55441
        and parts.path=='/cp7_catalog_locks','CATALOG_FOCUSED3_ISOLATED_LOCAL_ONLY')
    identity=source();OUT.mkdir(exist_ok=True)
    report=dict(status='INCOMPLETE',classification='ACTUAL_REAL_PG17_CATALOG_QUIESCENCE_FOCUSED3_ONLY',
        source=identity,retained_original_run=41371274977,retained_original_completed_cases=4,
        original_run_relabelled_PASS=False,retained_catalog4_NOT_rerun=True,
        retained_relation_primitive9_NOT_rerun=True,cases=[],**NO_CREDIT)
    schema='catalog_quiet_'+uuid.uuid4().hex[:12];created=False;admin=None;watch=None
    q=lambda:sql.Identifier(schema)
    def connect():return psycopg.connect(url)
    def lock(conn,names):
        conn.execute(sql.SQL('lock table {} in share mode nowait').format(
            sql.SQL(',').join(sql.Identifier('pg_catalog',name)for name in names)))
    def snapshot():
        return dict(rows=[list(r)for r in admin.execute(sql.SQL('select *from {}.effects order by id').format(q())).fetchall()],
            sequence=list(admin.execute(sql.SQL('select last_value::text,is_called from {}.effect_seq').format(q())).fetchone()),
            function=[list(r)for r in admin.execute('select p.oid::text,pg_get_functiondef(p.oid),p.proacl::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s',(schema,'value')).fetchall()])
    try:
        admin=psycopg.connect(url,autocommit=True);watch=psycopg.connect(url,autocommit=True)
        server=admin.execute("select version(),current_database(),current_user,current_setting('server_version_num')").fetchone()
        require(server[1:3]==('cp7_catalog_locks','postgres')and 170000<=int(server[3])<180000,
            'CATALOG_FOCUSED3_ACTUAL_PG17_IDENTITY');report['server']=list(server)
        admin.execute(sql.SQL('create schema {}').format(q()));created=True
        admin.execute(sql.SQL('create table {}.effects(id int primary key,value text);create sequence {}.effect_seq;create function {}.value()returns int language sql as $$select 1$$').format(q(),q(),q()),prepare=False)
        baseline=snapshot();report['model_baseline']=baseline
        with connect()as writer,connect()as guarded:
            require(writer.info.backend_pid!=guarded.info.backend_pid,'CATALOG_FOCUSED3_DISTINCT_REAL_BACKENDS')
            writer.execute(sql.SQL('create or replace function {}.value()returns int language sql as $$select 22$$').format(q()))
            xid=writer.execute('select pg_current_xact_id()::text').fetchone()[0]
            relation_locks=[list(r)for r in watch.execute("select c.relname,l.mode,l.granted from pg_locks l join pg_class c on c.oid=l.relation where l.pid=%s and c.relname='pg_proc'order by 1,2",(writer.info.backend_pid,)).fetchall()]
            # This is the PostgreSQL17 behavior the original guessed mode
            # assertion failed to observe: table_close releases that lock.
            lock(guarded,('pg_proc',))
            visible=guarded.execute(sql.SQL('select {}.value()').format(q())).fetchone()[0]
            require(visible==1,'CATALOG_FOCUSED3_UNCOMMITTED_FUNCTION_MUST_STILL_BE_INVISIBLE')
            actual_snapshot=guarded.execute('select pg_current_snapshot()::text').fetchone()[0]
            xips=[r[0]for r in guarded.execute('select pg_snapshot_xip(pg_current_snapshot())::text order by 1').fetchall()]
            txlocks=[list(r)for r in guarded.execute("select pid,transactionid::text,mode,granted,fastpath from pg_catalog.pg_locks where locktype='transactionid'and mode='ExclusiveLock'and granted and pid is distinct from pg_backend_pid()order by pid nulls first,transactionid::text").fetchall()]
            report['preexisting_writer_observation']=dict(writer_pid=writer.info.backend_pid,
                guarded_pid=guarded.info.backend_pid,writer_xid=xid,actual_snapshot=actual_snapshot,
                snapshot_xip_sublist=xips,actual_other_granted_transaction_ID_locks=txlocks,
                actual_pg_proc_relation_locks=relation_locks,
                catalog_SHARE_alone_admitted=True,visible_function_result=visible)
            require(any(row[0]==writer.info.backend_pid and int(row[1])==int(xid)%4294967296
                and row[2:]==['ExclusiveLock',True,False]for row in txlocks),
                'CATALOG_FOCUSED3_ACTUAL_PERMANENT_TRANSACTION_ID_LOCK_REQUIRED')
            before_refusal=snapshot();error=None
            try:
                guarded.execute("""do $$begin
                  if exists(select 1 from pg_catalog.pg_locks
                    where locktype='transactionid'and mode='ExclusiveLock'and granted
                     and pid is distinct from pg_backend_pid())then
                    raise exception using errcode='55P03',message='CATALOG_PREEXISTING_TRANSACTION_REVIEW_AGAIN';
                  end if;
                  raise exception 'CATALOG_FOCUSED3_UNSAFE_NO_QUIESCENCE_REFUSAL';
                end$$""")
            except psycopg.Error as failed:error=dict(sqlstate=failed.sqlstate,message=failed.diag.message_primary)
            require(error==dict(sqlstate='55P03',message='CATALOG_PREEXISTING_TRANSACTION_REVIEW_AGAIN'),
                'CATALOG_FOCUSED3_QUIESCENCE_MUST_REFUSE_BEFORE_MODEL_EFFECT')
            guarded.rollback();writer.rollback();after=snapshot()
            require(before_refusal==baseline==after,'CATALOG_FOCUSED3_WRITER_AND_GUARD_MUST_FULLY_RESTORE')
            report['cases'].append(dict(id=IDS[0],status='PASS',writer_pid=writer.info.backend_pid,
                guarded_pid=guarded.info.backend_pid,writer_xid=xid,actual_pg_proc_relation_locks=relation_locks,
                catalog_SHARE_alone_admitted=True,uncommitted_function_result_not_visible=visible,
                actual_snapshot=actual_snapshot,snapshot_xip_sublist=xips,
                actual_other_granted_transaction_ID_locks=txlocks,quiescence_refusal=error,
                actual_model_before_refusal=before_refusal,actual_model_after_rollback=after))
        catalogs=[r[0]for r in admin.execute("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='pg_catalog'and c.relkind in('r','p')order by c.relname").fetchall()]
        require({'pg_proc','pg_authid','pg_auth_members','pg_cast','pg_operator','pg_type','pg_policy','pg_event_trigger'}<=set(catalogs),'CATALOG_FOCUSED3_REQUIRED_DISPATCH_AND_AUTHORITY_CATALOGS')
        with connect()as holder,connect()as worker:
            lock(holder,catalogs)
            held=[r[0]for r in watch.execute("select c.relname from pg_locks l join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace where n.nspname='pg_catalog'and l.pid=%s and l.mode='ShareLock'and l.granted order by c.relname",(holder.info.backend_pid,)).fetchall()]
            require(held==catalogs,'CATALOG_FOCUSED3_ALL_CATALOG_LOCKS_MUST_ACTUALLY_BE_HELD')
            before_txlocks=[list(r)for r in holder.execute("select pid,transactionid::text,mode,granted,fastpath from pg_catalog.pg_locks where locktype='transactionid'and mode='ExclusiveLock'and granted and pid is distinct from pg_backend_pid()order by pid nulls first,transactionid::text").fetchall()]
            report['all_catalog_barrier_observation']=dict(holder_pid=holder.info.backend_pid,
                worker_pid=worker.info.backend_pid,expected_catalog_tables=catalogs,
                actual_held_catalog_tables=held,actual_preexisting_transaction_ID_locks=before_txlocks)
            require(not before_txlocks,'CATALOG_FOCUSED3_NO_OTHER_PERMANENT_TRANSACTION_ID_LOCKS')
            value=worker.execute(sql.SQL('select {}.value()').format(q())).fetchone()[0]
            worker.execute(sql.SQL("insert into {}.effects values(1,'allowed ordinary model DML')").format(q()))
            own_rows=[list(r)for r in worker.execute(sql.SQL('select *from {}.effects order by id').format(q())).fetchall()]
            require(value==1 and own_rows==[[1,'allowed ordinary model DML']],'CATALOG_FOCUSED3_EXISTING_READ_AND_DML_MUST_RUN')
            worker.rollback();holder.rollback();after=snapshot()
            require(after==baseline,'CATALOG_FOCUSED3_COMPLETE_BARRIER_PROBE_RESTORATION')
            report['cases'].append(dict(id=IDS[1],status='PASS',holder_pid=holder.info.backend_pid,
                worker_pid=worker.info.backend_pid,catalog_tables=catalogs,actual_held_catalog_tables=held,
                actual_preexisting_transaction_ID_locks=before_txlocks,existing_function_result=value,actual_uncommitted_worker_rows=own_rows,
                actual_model_after_rollback=after))
        with connect()as conn:
            conn.execute("set local search_path=''");quoted=conn.execute("select current_setting('search_path')").fetchone()[0]
            conn.execute("select pg_catalog.set_config('search_path','',true)");empty=conn.execute("select current_setting('search_path')").fetchone()[0]
            require(quoted=='""'and empty=='','CATALOG_FOCUSED3_EMPTY_PATH_SETTINGS')
            report['cases'].append(dict(id=IDS[2],status='PASS',actual_SET_empty_identifier=quoted,
                actual_set_config_empty_path=empty,original_metadata_error_cause_not_claimed_proven=True))
        final=snapshot();require(final==baseline,'CATALOG_FOCUSED3_FINAL_FULL_MODEL_BASELINE')
        require(tuple(r['id']for r in report['cases'])==IDS,'CATALOG_FOCUSED3_EXACT_NEW_THREE_IDS')
        report.update(status='PASS',actual_new_primitive_cases=3,model_final=final,
            global_barrier_requires_no_other_permanent_transaction_ID_locks_in_addition_to_catalog_locks=True,
            catalog_SHARE_alone_does_NOT_close_preexisting_catalog_writer=True)
    except BaseException as error:
        report.update(status='FAIL',error_type=type(error).__name__,error=str(error)[:1000],
            sqlstate=getattr(error,'sqlstate',None));raise
    finally:
        cleanup=[]
        if admin is not None and not admin.closed:
            if created:
                try:admin.execute(sql.SQL('drop schema {} cascade').format(q()))
                except Exception as error:cleanup.append(type(error).__name__)
            admin.close()
        if watch is not None and not watch.closed:watch.close()
        report['cleanup_errors']=cleanup;report['all_opened_connections_closed']=True
        with(OUT/'CATALOG_QUIESCENCE_FOCUSED3.json').open('x')as stream:json.dump(report,stream,indent=2);stream.write('\n')
        print(json.dumps(dict(status=report['status'],fresh_cases=len(report['cases']),retained4_NOT_rerun=True,**NO_CREDIT)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
    require(a.run!=a.check,'CATALOG_FOCUSED3_ONE_MODE')
    if a.check:print(json.dumps(dict(status='FOCUSED3_SEALED_SOURCE_ONLY',source=source(),**NO_CREDIT)))
    else:run()
