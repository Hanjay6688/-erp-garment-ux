"""Real PostgreSQL refusals and contention; no committed manual factory work."""
from contextlib import contextmanager
import uuid
import psycopg

@contextmanager
def rolled_back(cur):
    cur.execute('savepoint initial_worker_control')
    try:yield
    finally:
        cur.execute('rollback to savepoint initial_worker_control')
        cur.execute('release savepoint initial_worker_control')

def limit(cur,milliseconds):
    cur.execute("select set_config('statement_timeout',%s,true),set_config('lock_timeout','2s',true)",(str(milliseconds),))

def idle_tick(cur):
    value=cur.execute('select cp7_ops.factory_initial_tick_v1()').fetchone()[0]
    assert value['ran']is False and value['outcome']=='IDLE',value
    return value

def small(cur,today,finance,catalog,report):
    before=catalog._data(cur);held=catalog._catalog_rows(cur)
    with rolled_back(cur):
        key=str(uuid.uuid4());job=finance.request(cur,today,key,None)
        finance.staged.b.api.admin(cur)
        targets,done=cur.execute('select targets_total,units_done from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()
        assert 0<targets<1000 and done==0 and job['state']=='RUNNING'
        limit(cur,16000);answer=idle_tick(cur)
        assert cur.execute('select units_done,unit_attempts from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()==(0,0)
    assert catalog._data(cur)==before and catalog._catalog_rows(cur)==held
    report['small_job_not_taken_by_initial_worker']=dict(status='PASS',targets=targets,worker=answer,complete_savepoint_rollback=True)

def large(conn,cur,requests,finance,catalog,url,report):
    before=catalog._data(cur);held=catalog._catalog_rows(cur);checks=[]
    rows=cur.execute('select id,targets_total,units_done,unit_attempts from cp7_analysis_stage.jobs where request_id=any(%s::uuid[])order by id',(requests,)).fetchall()
    assert len(rows)==2 and all(r[1]>=1000 and r[2:]==(0,0)for r in rows)
    for key in requests:
        with rolled_back(cur):
            try:finance.staged.step(cur,key)
            except psycopg.Error as error:
                assert error.sqlstate=='55000'and error.diag.message_primary=='CP7_LARGE_INITIAL_PREPARATION_SERVER_REQUIRED'
            else:raise AssertionError('ORDINARY_PAGE_MUST_NOT_EXECUTE_LARGE_INITIAL_WORK')
        checks.append(dict(case='PUBLIC_8S_STEP_REFUSED_WITHOUT_ATTEMPT',request=key))
    for milliseconds in (0,8000,16001):
        with rolled_back(cur):
            limit(cur,milliseconds)
            try:cur.execute('select cp7_ops.factory_initial_tick_v1()')
            except psycopg.Error as error:
                assert error.sqlstate=='55000'and error.diag.message_primary=='CP7_RUNNER_STATEMENT_LIMIT_REQUIRED'
            else:raise AssertionError('INITIAL_WORKER_ACCEPTED_UNBOUNDED_OR_WRONG_LIMIT')
        checks.append(dict(case='PRIVATE_LIMIT_REFUSED',statement_limit_ms=milliseconds))
    with rolled_back(cur):
        limit(cur,8000)
        with finance.finance.as_capture(cur):value=cur.execute('select cp7_analysis_stage.run_next()').fetchone()[0]
        assert value==dict(ran=False,outcome='IDLE'),value
    checks.append(dict(case='ORDINARY_WORKER_SKIPS_LARGE_INITIAL'))
    with rolled_back(cur):
        limit(cur,8000)
        with finance.finance.as_capture(cur):
            value=cur.execute("select cp7_analysis_stage.step(%s,'{\"denied\":\"qualification-access-change\"}'::jsonb)",(rows[0][0],)).fetchone()[0]
        assert value['state']=='FAILED'
        assert cur.execute('select failure_code,unit_attempts from cp7_analysis_stage.jobs where id=%s',(rows[0][0],)).fetchone()==('CP7_ANALYSIS_ACCESS_CHANGED',0)
    checks.append(dict(case='EXISTING_ACCESS_CHANGE_PRECEDES_INITIAL_LIMIT_REFUSAL',complete_savepoint_rollback=True))
    assert catalog._data(cur)==before and catalog._catalog_rows(cur)==held
    conn.rollback()
    with psycopg.connect(url)as peer,peer.cursor()as locked:
        assert peer.info.host in('localhost','127.0.0.1')and peer.info.port==54322
        assert locked.execute('select current_database()').fetchone()==('cp6_rollback',)
        locked.execute('select id from cp7_analysis_stage.jobs where request_id=any(%s::uuid[])for update',(requests,)).fetchall()
        limit(cur,16000);answer=idle_tick(cur);conn.rollback();peer.rollback()
    checks.append(dict(case='SECOND_CONNECTION_SKIPS_BOTH_LOCKED_JOBS',worker=answer))
    assert catalog._data(cur)==before and catalog._catalog_rows(cur)==held
    assert cur.execute('select id,targets_total,units_done,unit_attempts from cp7_analysis_stage.jobs where request_id=any(%s::uuid[])order by id',(requests,)).fetchall()==rows
    conn.rollback()
    report['initial_worker_guards']=dict(status='PASS',checks=checks,all22_all_rows_and_sequences_unchanged=True,
        ordinary_public_limit_ms=8000,initial_private_limit_ms=16000,committed_operational_steps=0,
        actual_current_access_cases_retained_in_native20=True,real_Auth_browser_claim=False)
