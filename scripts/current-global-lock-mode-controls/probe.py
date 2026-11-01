"""Real two-session PostgreSQL lock primitives, never ERP writer acceptance."""
from pathlib import Path
from urllib.parse import urlparse
from hashlib import sha256
import argparse,json,os,time,uuid

OUT=Path('cp7-proof/GLOBAL_LOCK_MODE_CONTROLS.json')


def target(url,confirmation):
    parsed=urlparse(url)
    if(confirmation!='cp7_lock_modes'or parsed.scheme not in('postgresql','postgres')
        or parsed.hostname not in('127.0.0.1','localhost')or parsed.port!=55439
        or parsed.path!='/cp7_lock_modes'or parsed.query or parsed.fragment):
        raise ValueError('DEDICATED_LOOPBACK_MODEL_DATABASE_55439_ONLY_NOT_ERP')
    return url


def run(url):
    # No PostgreSQL client import precedes the exact non-ERP target gate.
    target(url,os.environ.get('PGLOCK_MODEL_CONFIRM'))
    import psycopg
    report=dict(status='INCOMPLETE',classification='POSTGRES_TWO_SESSION_LOCK_PRIMITIVES_ONLY',
        actual_ERP_cases=0,actual_Native_cases=0,actual_Auth_or_browser_cases=0,
        global_writer_current_rights_or_phantom_closure=False,production_go=False,independent_acceptance=False,
        documentation='https://www.postgresql.org/docs/17/explicit-locking.html',cases={})
    schema='cp7_lock_mode_probe_'+uuid.uuid4().hex
    a=b=None;created=False
    try:
        a=psycopg.connect(url,connect_timeout=10);b=psycopg.connect(url,connect_timeout=10)
        identities=[]
        for conn in(a,b):
            row=conn.execute("select current_database(),current_setting('server_version_num'),pg_backend_pid(),"
                "exists(select 1 from pg_namespace where nspname='erp')").fetchone()
            if row[0]!='cp7_lock_modes'or row[1]!='170006'or row[3]is not False:
                raise ValueError('EXACT_POSTGRES_17_6_EMPTY_NON_ERP_MODEL_REQUIRED')
            identities.append(dict(database=row[0],server_version_num=row[1],backend_pid=row[2]))
            conn.execute("set statement_timeout='5s';set lock_timeout='250ms'");conn.commit()
        if identities[0]['backend_pid']==identities[1]['backend_pid']:
            raise ValueError('TWO_DISTINCT_ACTUAL_POSTGRES_BACKENDS_REQUIRED')
        report['sessions']=identities
        a.execute('create schema '+schema);created=True
        a.execute('create table '+schema+'.facts(id integer primary key,amount numeric(20,2)not null)')
        a.execute('insert into '+schema+'.facts values(1,100),(2,200)')
        a.execute('create table '+schema+'.children(id integer primary key,parent_id integer references '+schema+'.facts(id))')
        a.execute('create sequence '+schema+'.untouched_sequence start 11')
        a.execute('create function '+schema+'.code_v1()returns integer language sql as $$select 1$$')
        a.commit()
        def snapshot(conn):
            value=dict(facts=conn.execute('select id,amount::text from '+schema+'.facts order by id').fetchall(),
                children=conn.execute('select id,parent_id from '+schema+'.children order by id').fetchall(),
                sequence=conn.execute('select last_value::text,is_called from '+schema+'.untouched_sequence').fetchone())
            return json.loads(json.dumps(value))
        baseline=snapshot(a);a.rollback()
        report['baseline']=baseline
        def clean():a.rollback();b.rollback()
        def rejected(conn,sql):
            begin=time.monotonic()
            try:conn.execute(sql)
            except psycopg.Error as error:
                if error.sqlstate!='55P03':raise
                return dict(sqlstate=error.sqlstate,elapsed_ms=round((time.monotonic()-begin)*1000,3))
            raise AssertionError('MODEL_CONFLICT_MUST_REFUSE:'+sql)
        def save(name,**values):
            clean();after=snapshot(a);a.rollback()
            if after!=baseline:raise AssertionError('MODEL_REFUSAL_OR_LOCK_CHANGED_ROWS_OR_SEQUENCE:'+name)
            report['cases'][name]=dict(status='PASS',rows_and_sequence_unchanged=True,**values)

        # Existing row lockers remain compatible with SHARE ROW EXCLUSIVE;
        # the blueprint's separate NOWAIT tuple acquisition must not be omitted.
        b.execute('select*from '+schema+'.facts where id=1 for update')
        a.execute('lock table '+schema+'.facts in share row exclusive mode nowait')
        refusal=rejected(a,'select*from '+schema+'.facts where id=1 for update nowait')
        save('SHARE_ROW_EXCLUSIVE_DOES_NOT_EXCLUDE_EXISTING_ROW_LOCKER',
            table_barrier_acquired=True,separate_row_lock_refusal=refusal)

        b.execute('select*from '+schema+'.facts where id=1 for update')
        refusal=rejected(a,'lock table '+schema+'.facts in exclusive mode nowait')
        save('EXCLUSIVE_NOWAIT_REFUSES_EXISTING_ROW_SHARE',refusal=refusal)

        b.execute('update '+schema+'.facts set amount=amount+1 where id=1')
        refusal=rejected(a,'lock table '+schema+'.facts in exclusive mode nowait')
        save('EXCLUSIVE_NOWAIT_REFUSES_EXISTING_DML',refusal=refusal)

        a.execute('lock table '+schema+'.facts in exclusive mode nowait')
        read=b.execute('select id,amount::text from '+schema+'.facts order by id').fetchall()
        if json.loads(json.dumps(read))!=baseline['facts']:raise AssertionError('ORDINARY_READ_CHANGED')
        save('EXCLUSIVE_PRESERVES_CONCURRENT_ORDINARY_SELECT',reader_completed=True)

        a.execute('lock table '+schema+'.facts in exclusive mode nowait')
        refusal=rejected(b,'lock table '+schema+'.facts in exclusive mode nowait')
        save('SECOND_EXCLUSIVE_BARRIER_REFUSES_WITHOUT_UPGRADE_CYCLE',refusal=refusal)

        a.execute('lock table '+schema+'.facts in exclusive mode nowait')
        refusal=rejected(b,'insert into '+schema+'.children values(1,1)')
        save('EXCLUSIVE_BLOCKS_FOREIGN_KEY_PARENT_ROW_SHARE',refusal=refusal,
            bounded_model_lock_timeout_ms=250,Native_or_ERP_path_executed=False)

        a.execute('lock table '+schema+'.facts in exclusive mode nowait')
        refusal=rejected(b,'alter table '+schema+'.facts add column forbidden_concurrent_column integer')
        save('EXCLUSIVE_BLOCKS_RELATION_DDL',refusal=refusal,bounded_model_lock_timeout_ms=250)

        # Deliberately demonstrate the remaining catalog-authority gap.
        # A table lock cannot be relabelled as a function-DDL/writer census.
        a.execute('lock table '+schema+'.facts in exclusive mode nowait')
        signature=schema+'.code_v1()'
        before=a.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]
        b.execute('create or replace function '+signature+'returns integer language sql as $$select 2$$');b.commit()
        after=a.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]
        observed=a.execute('select '+signature).fetchone()[0]
        if before==after or observed!=2:raise AssertionError('FUNCTION_DDL_COUNTEREXAMPLE_NOT_OBSERVED')
        changed=dict(before_sha256=sha256(before.encode()).hexdigest(),after_sha256=sha256(after.encode()).hexdigest(),
            other_session_function_DDL_committed_while_table_barrier_held=True,actual_new_function_result=observed)
        clean();b.execute('create or replace function '+signature+'returns integer language sql as $$select 1$$');b.commit()
        restored=a.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]
        if restored!=before:raise AssertionError('MODEL_FUNCTION_ORIGINAL_NOT_RESTORED')
        save('TABLE_BARRIER_ALONE_DOES_NOT_PROTECT_FUNCTION_DDL',**changed,original_function_restored=True,
            global_writer_or_catalog_DDL_closure=False)

        a.execute('lock table '+schema+'.facts in exclusive mode nowait');a.rollback()
        b.execute('lock table '+schema+'.facts in exclusive mode nowait')
        save('TRANSACTION_END_RELEASES_BARRIER',second_session_acquired_after_release=True)
        if len(report['cases'])!=9:raise AssertionError('NINE_EXACT_MODEL_CONTROLS_REQUIRED')
        report.update(status='PASS_LOCK_PRIMITIVES_NOT_ERP_WRITER_CLOSURE',counts={'PASS':9},
            actual_distinct_backends=2,model_rows_and_sequence_unchanged=True,
            SRE_needs_separate_row_locks=True,EXCLUSIVE_has_broader_contention=True,
            table_barrier_does_not_close_function_DDL_or_current_rights=True)
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error))
    finally:
        for conn in(a,b):
            if conn is not None and not conn.closed:conn.rollback()
        if created and a is not None and not a.closed:
            try:
                a.execute('drop schema '+schema+' cascade');a.commit()
                remaining=a.execute('select count(*)from pg_namespace where nspname=%s',(schema,)).fetchone()[0]
                report['owned_model_schema_removed']=remaining==0;a.rollback()
            except BaseException as error:report['cleanup_error_type']=type(error).__name__
        for conn in(a,b):
            if conn is not None:conn.close()
        report['both_connections_closed']=all(conn is None or conn.closed for conn in(a,b))
        if report.get('owned_model_schema_removed')is not True or not report['both_connections_closed']:
            report['status']='INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report.get(key)for key in('status','counts','actual_distinct_backends',
        'owned_model_schema_removed','both_connections_closed','error_type','error')}))
    return 0 if report['status']=='PASS_LOCK_PRIMITIVES_NOT_ERP_WRITER_CLOSURE'else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true',required=True);p.parse_args()
    raise SystemExit(run(os.environ['PGLOCK_MODEL_URL']))
