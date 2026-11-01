"""Only the two missing lock controls; preserve the seven actual earlier PASS."""
from pathlib import Path
from hashlib import sha256
import argparse,json,os,uuid
from probe import target

OUT=Path('cp7-proof/GLOBAL_LOCK_DDL_FOCUSED2.json')
ORIGINAL_PROBE_SHA='074640e8923c1de68c47da5cc69a6aee918e42bedfffe2227e84823daa53099e'


def run(url):
    target(url,os.environ.get('PGLOCK_MODEL_CONFIRM'))
    raw=Path(__file__).with_name('probe.py').read_bytes()
    if sha256(raw).hexdigest()!=ORIGINAL_PROBE_SHA:raise ValueError('SEVEN_OLD_LOCK_CONTROLS_SOURCE_MUST_REMAIN_EXACT')
    import psycopg
    report=dict(status='INCOMPLETE',classification='FOCUSED_REAL_POSTGRES_DDL_AND_RELEASE2_ONLY',
        retained_original_head='33766513e53345b7e293c1378767960a1c6b219a',retained_original_run_id=41359313650,
        retained_original_probe_sha256=ORIGINAL_PROBE_SHA,retained7_rerun=False,actual_ERP_cases=0,
        global_writer_current_rights_or_phantom_closure=False,production_go=False,independent_acceptance=False,cases={})
    a=b=None;created=False;schema='cp7_lock_ddl_'+uuid.uuid4().hex
    try:
        a=psycopg.connect(url,connect_timeout=10);b=psycopg.connect(url,connect_timeout=10)
        report['sessions']=[]
        for conn in(a,b):
            row=conn.execute("select current_database(),current_setting('server_version_num'),pg_backend_pid(),"
                "exists(select 1 from pg_namespace where nspname='erp'),current_setting('transaction_isolation')").fetchone()
            if row[0]!='cp7_lock_modes'or row[1]!='170006'or row[3]is not False:raise ValueError('EXACT_NON_ERP_PG17_6_REQUIRED')
            report['sessions'].append(dict(database=row[0],server_version_num=row[1],backend_pid=row[2],isolation=row[4]))
            conn.execute("set statement_timeout='5s';set lock_timeout='250ms'");conn.commit()
        if report['sessions'][0]['backend_pid']==report['sessions'][1]['backend_pid']:raise ValueError('TWO_REAL_BACKENDS_REQUIRED')
        a.execute('create schema '+schema);created=True
        a.execute('create table '+schema+'.facts(id integer primary key,amount numeric(20,2))')
        a.execute('insert into '+schema+'.facts values(1,100),(2,200)')
        a.execute('create sequence '+schema+'.untouched start 11')
        signature=schema+'.code_v1()'
        initial='CREATE OR REPLACE FUNCTION '+signature+' RETURNS integer LANGUAGE sql AS $$ SELECT 11 $$'
        following='CREATE OR REPLACE FUNCTION '+signature+' RETURNS integer LANGUAGE sql AS $$ SELECT 22 $$'
        a.execute(initial);a.commit()
        def state(conn):
            return json.loads(json.dumps(dict(rows=conn.execute('select id,amount::text from '+schema+'.facts order by id').fetchall(),
                sequence=conn.execute('select last_value::text,is_called from '+schema+'.untouched').fetchone())))
        def observe(conn):
            row=conn.execute("select p.oid::text,p.prosrc,p.prorettype::regtype::text,p.provolatile,p.xmin::text,"
                "pg_get_functiondef(p.oid)from pg_proc p where p.oid=%s::regprocedure",(signature,)).fetchone()
            value=conn.execute('select '+signature).fetchone()[0]
            return dict(oid=row[0],prosrc=row[1],result_type=row[2],volatility=row[3],xmin=row[4],
                definition_sha256=sha256(row[5].encode()).hexdigest(),call_result=value,python_result_type=type(value).__name__)
        baseline=state(a);before=observe(a);a.commit();report['baseline']=baseline;report['function_before']=before
        if before['call_result']!=11:raise AssertionError('ACTUAL_INITIAL_SQL_FUNCTION_RESULT_REQUIRED')
        a.execute('lock table '+schema+'.facts in exclusive mode nowait')
        b.execute(following);b.commit()
        # Retain all three actual observations before imposing any assertion
        # about what another backend's active transaction sees.
        writer=observe(b);b.rollback();holder=observe(a)
        locks=a.execute("select mode,granted from pg_locks where pid=pg_backend_pid()and locktype='relation'"
            'and relation=%s::regclass order by mode',(schema+'.facts',)).fetchall()
        report['function_DDL_observations']=dict(writer_after_commit=writer,holder_before_release=holder,
            actual_holder_relation_locks=locks,after_DDL_rows_and_sequence=state(a))
        if(writer['prosrc']==before['prosrc']or writer['definition_sha256']==before['definition_sha256']
            or writer['call_result']!=22 or['ExclusiveLock',True]not in json.loads(json.dumps(locks))):
            raise AssertionError('ACTUAL_FUNCTION_DDL_COMMIT_UNDER_HELD_TABLE_BARRIER_REQUIRED')
        if state(a)!=baseline:raise AssertionError('MODEL_FUNCTION_DDL_CHANGED_ROWS_OR_SEQUENCE')
        report['cases']['FUNCTION_DDL_CAN_COMMIT_WHILE_OTHER_BACKEND_HOLDS_EXCLUSIVE_TABLE_LOCK']=dict(
            status='PASS',writer_new_function_result=writer['call_result'],
            holder_result_before_release=holder['call_result'],holder_visibility_observed_not_assumed=True,
            rows_and_sequence_unchanged=True,global_catalog_DDL_closure=False)
        a.commit()
        b.execute('lock table '+schema+'.facts in exclusive mode nowait');b.rollback()
        after=observe(a);report['function_after_holder_transaction_end']=after
        if after['call_result']!=22:raise AssertionError('ACTUAL_NEW_FUNCTION_AFTER_TRANSACTION_END_REQUIRED')
        a.rollback()
        report['cases']['TRANSACTION_END_RELEASES_BARRIER']=dict(status='PASS',second_backend_acquired_after_release=True,
            rows_and_sequence_unchanged=True)
        a.execute(initial);a.commit();restored=observe(a);a.rollback()
        if restored['definition_sha256']!=before['definition_sha256']or restored['call_result']!=11:
            raise AssertionError('ORIGINAL_MODEL_FUNCTION_MUST_BE_RESTORED')
        if state(a)!=baseline:raise AssertionError('FINAL_MODEL_ROWS_OR_SEQUENCE_CHANGED')
        a.rollback();report.update(status='PASS_FOCUSED_LOCK_DDL_AND_RELEASE2_NOT_ERP_CLOSURE',counts={'PASS':2},
            original_function_restored=True,model_rows_and_sequence_unchanged=True,actual_distinct_backends=2)
    except BaseException as error:report.update(error_type=type(error).__name__,error=str(error))
    finally:
        for conn in(a,b):
            if conn is not None and not conn.closed:conn.rollback()
        if created and a is not None and not a.closed:
            try:
                a.execute('drop schema '+schema+' cascade');a.commit()
                report['owned_model_schema_removed']=a.execute('select count(*)from pg_namespace where nspname=%s',(schema,)).fetchone()[0]==0
                a.rollback()
            except BaseException as error:report['cleanup_error_type']=type(error).__name__
        for conn in(a,b):
            if conn is not None:conn.close()
        report['both_connections_closed']=all(conn is None or conn.closed for conn in(a,b))
        if report.get('owned_model_schema_removed')is not True or not report['both_connections_closed']:report['status']='INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k)for k in('status','counts','actual_distinct_backends','error_type','error')}))
    return 0 if report['status']=='PASS_FOCUSED_LOCK_DDL_AND_RELEASE2_NOT_ERP_CLOSURE'else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true',required=True);p.parse_args()
    raise SystemExit(run(os.environ['PGLOCK_MODEL_URL']))
