"""New real PostgreSQL17 catalog-barrier controls; no ERP or retained reruns."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
import argparse,json,os,subprocess,time,uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp7-proof'
NATIVE=dict(actual_ERP_cases=0,actual_Native_cases=0,global_writer_closure=False,
    production_go=False,independent_acceptance=False)
CASE_IDS=(
    'PG_PROC_SHARE_BLOCKS_CREATE_OR_REPLACE_FUNCTION',
    'PG_PROC_SHARE_BLOCKS_FUNCTION_EXECUTE_GRANT',
    'PG_AUTHID_SHARE_BLOCKS_ROLE_CAPABILITY_CHANGE',
    'PG_AUTH_MEMBERS_SHARE_BLOCKS_ROLE_MEMBERSHIP_GRANT',
    'INFLIGHT_FUNCTION_DDL_REFUSES_NOWAIT_CATALOG_BARRIER_BEFORE_EFFECT',
    'ALL_ACTUAL_CATALOG_TABLES_SHARE_ALLOW_FUNCTION_READ_AND_ORDINARY_DML',
    'SQL_EMPTY_IDENTIFIER_AND_EMPTY_SEARCH_PATH_HAVE_DISTINCT_ACTUAL_SETTINGS',
)


def require(value,message):
    if not value:raise ValueError(message)


def source():
    raw=(HERE/'SOURCE.json').read_bytes();manifest=json.loads(raw)
    require(manifest['classification']=='ISOLATED_REAL_PG17_CATALOG_BARRIER_CONTROLS_NOT_ERP','CATALOG_MODEL_SOURCE_SCOPE')
    for name,expected in manifest['files'].items():
        data=(ROOT/name).read_bytes()
        require(dict(bytes=len(data),sha256=sha256(data).hexdigest())==expected,'CATALOG_MODEL_SOURCE_CHANGED:'+name)
    return dict(head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD^{tree}'],text=True).strip(),
        manifest=dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),**NATIVE)


def run():
    import psycopg
    from psycopg import sql
    require(os.environ.get('CATALOG_LOCK_CONFIRM')=='cp7_catalog_locks','CATALOG_MODEL_EXPLICIT_CONFIRMATION')
    url=os.environ['CATALOG_LOCK_URL'];parts=urlsplit(url)
    require(parts.hostname in('127.0.0.1','localhost')and parts.port==55441
        and parts.path=='/cp7_catalog_locks','CATALOG_MODEL_LOCAL_ISOLATED_ONLY')
    identity=source();OUT.mkdir(exist_ok=True)
    report=dict(status='INCOMPLETE',classification='ACTUAL_REAL_PG17_CATALOG_BARRIER_MODEL_ONLY',
        source=identity,retained_primitive9_NOT_rerun=True,cases=[],**NATIVE)
    suffix=uuid.uuid4().hex[:12];schema='cp7_catalog_model_'+suffix
    group='catalog_group_'+suffix;member='catalog_member_'+suffix
    admin=psycopg.connect(url,autocommit=True);watch=psycopg.connect(url,autocommit=True)
    def connection():return psycopg.connect(url)
    q=lambda name:sql.Identifier(name)
    def locks(conn,names):
        conn.execute(sql.SQL('lock table {} in share mode nowait').format(
            sql.SQL(',').join(sql.Identifier('pg_catalog',x)for x in names)))
    def snapshot():
        return dict(rows=admin.execute(sql.SQL('select *from {}.effects order by id').format(q(schema))).fetchall(),
            sequence=admin.execute(sql.SQL('select last_value::text,is_called from {}.effect_seq').format(q(schema))).fetchone(),
            function=admin.execute('select pg_get_functiondef(p.oid),p.proacl::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s',(schema,'value')).fetchall(),
            member=admin.execute('select rolcanlogin,rolsuper,rolcreatedb from pg_roles where rolname=%s',(member,)).fetchone(),
            memberships=admin.execute('select r.rolname,m.rolname from pg_auth_members a join pg_roles r on r.oid=a.roleid join pg_roles m on m.oid=a.member where r.rolname=%s or m.rolname=%s order by 1,2',(group,member)).fetchall())
    def conflicts(label,names,statement):
        before=snapshot()
        with connection()as holder,connection()as worker:
            holder_pid=holder.info.backend_pid;worker_pid=worker.info.backend_pid
            require(holder_pid!=worker_pid,'CATALOG_MODEL_DISTINCT_REAL_BACKENDS')
            locks(holder,names)
            held=watch.execute('select c.relname,l.mode,l.granted from pg_locks l join pg_class c on c.oid=l.relation where l.pid=%s and c.relname=any(%s)order by 1,2',(holder_pid,list(names))).fetchall()
            require(all((name,'ShareLock',True)in held for name in names),'CATALOG_MODEL_ACTUAL_SHARE_LOCKS')
            worker.execute("set local lock_timeout='1800ms'")
            def attempt():
                try:worker.execute(statement);return dict(sqlstate=None)
                except psycopg.Error as error:return dict(sqlstate=error.sqlstate,error_type=type(error).__name__)
            blocked=None
            with ThreadPoolExecutor(max_workers=1)as pool:
                future=pool.submit(attempt);deadline=time.monotonic()+1.5
                while not future.done()and time.monotonic()<deadline:
                    row=watch.execute('select pg_blocking_pids(%s)',(worker_pid,)).fetchone()[0]
                    if holder_pid in row:blocked=dict(worker_pid=worker_pid,holder_pid=holder_pid,blockers=row);break
                    time.sleep(.02)
                result=future.result(timeout=5)
            worker.rollback()
            require(result['sqlstate']=='55P03','CATALOG_MODEL_EXPECTED_REAL_LOCK_TIMEOUT:'+label+':'+str(result))
            require(blocked is not None,'CATALOG_MODEL_REAL_BLOCKING_PIDS_REQUIRED:'+label)
            require(snapshot()==before,'CATALOG_MODEL_REFUSAL_CHANGED_MODEL:'+label)
            holder.commit()
            remaining=watch.execute("select count(*)from pg_locks l join pg_class c on c.oid=l.relation where l.pid=%s and c.relname=any(%s)and l.mode='ShareLock'",(holder_pid,list(names))).fetchone()[0]
            require(remaining==0,'CATALOG_MODEL_COMMIT_MUST_RELEASE_ALL_LOCKS')
            worker.execute(statement);worker.rollback()
            require(snapshot()==before,'CATALOG_MODEL_POST_RELEASE_PROBE_NOT_RESTORED:'+label)
            report['cases'].append(dict(id=label,status='PASS',actual_held_locks=held,blocked=blocked,
                lock_timeout_sqlstate=result['sqlstate'],refused_before_model_effect=True,
                same_statement_succeeded_after_commit=True,worker_probe_rolled_back=True,
                model_rows_sequence_function_ACL_role_membership_equal=True))
    created=False
    try:
        server=admin.execute('select version(),current_database(),current_user,current_setting(\'server_version_num\')').fetchone()
        require(server[1:3]==('cp7_catalog_locks','postgres')and 170000<=int(server[3])<180000,'CATALOG_MODEL_ACTUAL_PG17_CONTEXT')
        report['server']=server
        admin.execute(sql.SQL('create schema {}').format(q(schema)));created=True
        admin.execute(sql.SQL('create table {}.effects(id int primary key,value text);create sequence {}.effect_seq;create function {}.value()returns int language sql as $$select 1$$').format(q(schema),q(schema),q(schema)),prepare=False)
        admin.execute(sql.SQL('create role {} nologin;create role {} nologin').format(q(group),q(member)),prepare=False)
        baseline=snapshot()
        replace=sql.SQL('create or replace function {}.value()returns int language sql as $$select 22$$').format(q(schema))
        conflicts('PG_PROC_SHARE_BLOCKS_CREATE_OR_REPLACE_FUNCTION',('pg_proc',),replace)
        conflicts('PG_PROC_SHARE_BLOCKS_FUNCTION_EXECUTE_GRANT',('pg_proc',),
            sql.SQL('grant execute on function {}.value()to {}').format(q(schema),q(member)))
        conflicts('PG_AUTHID_SHARE_BLOCKS_ROLE_CAPABILITY_CHANGE',('pg_authid',),
            sql.SQL('alter role {} login').format(q(member)))
        conflicts('PG_AUTH_MEMBERS_SHARE_BLOCKS_ROLE_MEMBERSHIP_GRANT',('pg_auth_members',),
            sql.SQL('grant {} to {}').format(q(group),q(member)))
        # The reverse schedule proves a writer already in flight refuses the
        # owning NOWAIT barrier before its model sequence or row is consumed.
        with connection()as writer,connection()as guarded:
            writer.execute(replace)
            seen=watch.execute("select mode,granted from pg_locks where pid=%s and relation='pg_catalog.pg_proc'::regclass",(writer.info.backend_pid,)).fetchall()
            require(('RowExclusiveLock',True)in seen,'CATALOG_MODEL_ACTUAL_PRIOR_PG_PROC_WRITER')
            error=None
            try:locks(guarded,('pg_proc',))
            except psycopg.Error as failed:error=failed.sqlstate
            guarded.rollback();writer.rollback()
            require(error=='55P03'and snapshot()==baseline,'CATALOG_MODEL_PRIOR_DDL_MUST_REFUSE_BEFORE_EFFECT')
            report['cases'].append(dict(id='INFLIGHT_FUNCTION_DDL_REFUSES_NOWAIT_CATALOG_BARRIER_BEFORE_EFFECT',
                status='PASS',sqlstate=error,actual_prior_writer_locks=seen,model_baseline_equal=True))
        # Test the full actual catalog-table set, rather than assuming the
        # three demonstrated catalogs cover operators, casts, RLS and types.
        catalogs=[x[0]for x in admin.execute("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='pg_catalog'and c.relkind in('r','p')order by c.relname").fetchall()]
        require({'pg_proc','pg_authid','pg_auth_members','pg_cast','pg_operator','pg_type','pg_policy','pg_event_trigger'}<=set(catalogs),'CATALOG_MODEL_ACTUAL_COMPLETE_CATALOG_TABLE_SET')
        with connection()as holder,connection()as worker:
            locks(holder,catalogs)
            actual=watch.execute("select c.relname from pg_locks l join pg_class c on c.oid=l.relation join pg_namespace n on n.oid=c.relnamespace where n.nspname='pg_catalog'and l.pid=%s and l.mode='ShareLock'and l.granted order by c.relname",(holder.info.backend_pid,)).fetchall()
            require([x[0]for x in actual]==catalogs,'CATALOG_MODEL_EVERY_CATALOG_LOCK_ACTUALLY_HELD')
            value=worker.execute(sql.SQL('select {}.value()').format(q(schema))).fetchone()[0]
            require(value==1,'CATALOG_MODEL_EXISTING_FUNCTION_EXECUTION_ALLOWED')
            worker.execute(sql.SQL("insert into {}.effects values(1,'ordinary DML while catalogs frozen')").format(q(schema)))
            require(worker.execute(sql.SQL('select count(*)from {}.effects').format(q(schema))).fetchone()[0]==1,'CATALOG_MODEL_ORDINARY_DML_MUST_RUN')
            worker.rollback();holder.rollback()
            require(snapshot()==baseline,'CATALOG_MODEL_CATALOG_BARRIER_DML_PROBE_FULLY_RESTORED')
            report['cases'].append(dict(id='ALL_ACTUAL_CATALOG_TABLES_SHARE_ALLOW_FUNCTION_READ_AND_ORDINARY_DML',
                status='PASS',catalog_tables=catalogs,actual_catalog_count=len(catalogs),
                distinct_backends=True,executed_function_result=value,ordinary_model_DML_completed=True,
                holder_rollback_and_worker_rollback=True,model_baseline_equal=True))
        # Diagnose the exact optional metadata caller path without repeating a
        # financial case or pretending the first run retained an error string.
        with connection()as conn:
            conn.execute("set local search_path=''");quoted=conn.execute("select current_setting('search_path')").fetchone()[0]
            conn.execute("select pg_catalog.set_config('search_path','',true)");empty=conn.execute("select current_setting('search_path')").fetchone()[0]
            require(quoted=='""'and empty=='','CATALOG_MODEL_EXACT_EMPTY_PATH_RENDERING')
            report['cases'].append(dict(id='SQL_EMPTY_IDENTIFIER_AND_EMPTY_SEARCH_PATH_HAVE_DISTINCT_ACTUAL_SETTINGS',
                status='PASS',SET_empty_identifier_actual=quoted,set_config_empty_path_actual=empty,
                historical_error_cause_not_claimed_proven=True))
        require(snapshot()==baseline,'CATALOG_MODEL_FINAL_COMPLETE_BASELINE')
        require(tuple(row['id']for row in report['cases'])==CASE_IDS,'CATALOG_MODEL_EXACT_SEVEN_NEW_PREDECLARED_CASES')
        report.update(status='PASS',actual_new_primitive_cases=len(report['cases']),
            all_model_rows_sequences_function_ACL_roles_memberships_equal=True)
    except BaseException as error:
        report.update(status='FAIL',error_type=type(error).__name__,error=str(error)[:1000],
            sqlstate=getattr(error,'sqlstate',None))
        raise
    finally:
        cleanup=[]
        for conn in(admin,watch):
            if not conn.closed:conn.rollback()
        if created:
            for statement in[sql.SQL('drop schema {} cascade').format(q(schema)),
                    sql.SQL('drop role if exists {}').format(q(member)),sql.SQL('drop role if exists {}').format(q(group))]:
                try:admin.execute(statement)
                except Exception as error:cleanup.append(type(error).__name__)
        report['cleanup_errors']=cleanup;watch.close();admin.close()
        report['all_opened_connections_closed']=True
        with(OUT/'CATALOG_LOCK_BARRIER_NEW7.json').open('x')as stream:json.dump(report,stream,indent=2);stream.write('\n')
        print(json.dumps(dict(status=report['status'],completed_new_cases=len(report['cases']),cleanup_errors=cleanup,**NATIVE)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
    require(a.run!=a.check,'CATALOG_MODEL_ONE_MODE_REQUIRED')
    if a.check:print(json.dumps(dict(status='SOURCE_COMPILE_AND_MANIFEST_ONLY',source=source(),**NATIVE)))
    else:run()
