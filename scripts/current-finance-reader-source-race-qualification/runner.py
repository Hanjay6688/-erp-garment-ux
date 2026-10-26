"""Fresh committed units and an observed two-backend source change; prepared only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic,sleep
import importlib.util,json,uuid
import psycopg

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
retained=load('source_race_reader_dependencies',ROOT/'scripts/current-finance-check-reuse-diagnostic/runner.py')
patch=load('source_race_disposable_patch',HERE/'clone_patch.py')
base,product=retained.finance,retained.product
capture=base.finance
scheduler_quiet=retained.scheduler_quiet
CASE='FINANCE_FRESH_SNAPSHOT_CONCURRENT_BOOK_CHANGE_AND_RECOVERY'

def bounded(cur):
    cur.execute("set local statement_timeout='8s'")
    cur.execute("set local lock_timeout='2s'")

def normalized(value):
    report=dict(value);stamp=report.pop('captured_at');assert stamp
    return report

def measured_report(url,dates,candidate):
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        bounded(cur)
        assert cur.execute('select pg_current_xact_id_if_assigned()').fetchone()==(None,)
        before=retained.table_writes(cur);started=monotonic()
        value=capture.call(cur,'select cp7_finance_capture.report_unit(%s::jsonb)',(json.dumps(dates),))
        elapsed=round((monotonic()-started)*1000,3)
        writes=retained.writes_delta(before,retained.table_writes(cur))
        xid=cur.execute('select pg_current_xact_id_if_assigned()::text').fetchone()[0]
        if candidate:
            assert value['snapshot']is not None and xid is None,'FRESH_READER_LOST_MVCC_SNAPSHOT'
            assert writes=={},('FRESH_READER_WRITES',writes)
        assert elapsed<8000
        conn.rollback()
    return value,dict(candidate=candidate,millis=elapsed,snapshot=value['snapshot'],
        transaction_id_after=xid,table_write_attempts=writes,rolled_back=True)

def capture_row(cur,cid):
    base.staged.b.api.admin(cur)
    return cur.execute('select to_jsonb(c)from cp7_finance_capture.captures c where id=%s',(cid,)).fetchone()[0]

def fresh_step(url,cid,started=None,pids=None):
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        bounded(cur)
        # Only the diagnostic coordinated wait needs to reach the ordinary8s
        # statement ceiling; all other lock acquisition remains bounded at2s.
        if started is not None:cur.execute("set local lock_timeout='8s'")
        assert cur.execute('select pg_current_xact_id_if_assigned()').fetchone()==(None,)
        if pids is not None:pids.append(cur.execute('select pg_backend_pid()').fetchone()[0])
        if started is not None:started.set()
        before=retained.table_writes(cur);t=monotonic();value=capture.step(cur,cid)
        elapsed=round((monotonic()-t)*1000,3);assert elapsed<8000
        writes=retained.writes_delta(before,retained.table_writes(cur))
        assert not{k:v for k,v in writes.items()if k.startswith('erp.')},('CAPTURE_CHANGED_ERP',writes)
        row=capture_row(cur,cid);conn.commit()
    return value,row,dict(millis=elapsed,state=value['state'],units_done=value['units_done'],
        table_write_attempts=writes,committed=True)

def finish(url,cid,report,label):
    trail=report.setdefault(label,[])
    for _ in range(50):
        value,row,observed=fresh_step(url,cid);trail.append(observed)
        report['manual_committed_steps']+=1
        if value['state']!='RUNNING':return value,row,trail
        assert len(trail)<2 or trail[-1]['units_done']>trail[-2]['units_done'],'CAPTURE_NO_REAL_PROGRESS'
    raise AssertionError('SMALL_CAPTURE_DID_NOT_FINISH')

def exercise(conn,cur,database_module,url,report):
    assert conn.info.host in('localhost','127.0.0.1')and conn.info.port==54322
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    # No prepared invocation can execute before exact source and actual prior
    # runtime binding. The outer probe will run its complete admission as well.
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    assert pins['actual_reuse']['head']=='f038a6ecc5a71278554eab62ab7df4f4ced9b7bc'
    assert pins['actual_reuse']['status']=='PASS'
    bounded(cur)
    granted,_=database_module._foundation(cur)
    today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    base.setup(cur,today)
    report['price_percent_fixture']=retained.price_fixture.seed(cur,today)
    cid=capture.start(cur,capture.query(today));dates=capture_row(cur,cid)['dates']
    chunk_rows=capture.call(cur,'select cp7_finance_capture.chunk_rows()')
    if granted:cur.execute('revoke usage on schema erp from authenticated')
    conn.commit()
    original,observed=measured_report(url,dates,False)
    assert 0<original['rows']['journal']<=chunk_rows,'RACE_FIXTURE_REQUIRES_ONE_JOURNAL_CHUNK'
    report['unchanged_fresh_report']=observed
    key='CP7:FINANCE_READER_RACE:'+str(uuid.uuid4());state=None
    report.update(case_id=CASE,diagnostic_only=True,actual_cron_claim=False,manual_committed_steps=0,
        product_timeout_changed=False,production_go=False,previous_factory_failures_remain_INCOMPLETE=True)
    try:
        bounded(cur)
        state=patch.install(cur,product.catalog,key);conn.commit()
        report['temporary_patch']=state['evidence']
        candidate,observed=measured_report(url,dates,True)
        assert normalized(candidate['report'])==normalized(original['report'])and candidate['rows']==original['rows']
        report['candidate_fresh_report']=observed
        report['whole_report_equal_in_separate_fresh_transactions']=True
        worker_pids=[];started=Event();waited=False
        with psycopg.connect(url)as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=1)as pool:
            bounded(h)
            holder_pid=h.execute('select pg_backend_pid()').fetchone()[0]
            h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(key,))
            future=pool.submit(fresh_step,url,cid,started,worker_pids)
            try:
                assert started.wait(5),'FINANCE_READER_WORKER_DID_NOT_START'
                deadline=monotonic()+5
                while monotonic()<deadline:
                    if h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))',(worker_pids[0],)).fetchone()[0]:
                        waited=True;break
                    sleep(.025)
                assert waited,'FINANCE_READER_ACTUAL_BLOCKING_PID_NOT_OBSERVED'
                grant=not h.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
                if grant:h.execute('grant usage on schema erp to authenticated')
                posted=capture.given(h,today,'900.00');capture.b.api.admin(h)
                if grant:h.execute('revoke usage on schema erp from authenticated')
                holder.commit()
            finally:holder.rollback()
            first,held,step_observation=future.result(timeout=15)
            report['manual_committed_steps']+=1
        assert len(worker_pids)==1 and holder_pid!=worker_pids[0]
        assert first['state']=='RUNNING'and first['units_done']==1
        assert held['report_snapshot']is not None,'RACING_REPORT_SNAPSHOT_MISSING'
        assert normalized(held['report'])==normalized(original['report']),'RACING_REPORT_MIXED_NEW_SOURCE'
        bounded(cur);patch.remove_hold(cur,state);conn.commit()
        current,current_observed=measured_report(url,dates,True)
        assert current['rows']['journal']>original['rows']['journal']
        assert normalized(current['report'])!=normalized(original['report'])
        failed,sealed,trail=finish(url,cid,report,'failure_steps')
        assert failed['state']=='FAILED'and failed['failure_code']=='CP7_FINANCE_CAPTURE_SOURCE_CHANGED'
        # The first journal scan must see the invisible-at-report-time Native
        # posting. A rejection only at the final row-count seal is insufficient.
        assert len(trail)==1 and failed['units_done']==1 and sealed['failure_unit']==1
        assert sealed['source_hash']is None and sealed['book_signature']is None
        repeated,same,again=fresh_step(url,cid);assert same==sealed and repeated==failed
        report['manual_committed_steps']+=1
        with psycopg.connect(url)as check,check.cursor()as c:
            bounded(c)
            try:
                with check.transaction():capture.call(c,'select cp7_finance_capture.result(%s)',(cid,))
            except psycopg.Error as error:assert error.sqlstate=='P0001'and error.diag.message_primary=='CP7_FINANCE_CAPTURE_NOT_READY'
            else:raise AssertionError('FAILED_CAPTURE_RESULT_ESCAPED')
            assert c.execute('select count(*)from pg_stat_activity where pid=any(%s)',([holder_pid,*worker_pids],)).fetchone()==(0,)
            fresh=capture.start(c,capture.query(today));assert str(fresh)!=str(cid);check.commit()
        ready,ready_row,recovery=finish(url,fresh,report,'recovery_steps')
        assert ready['state']=='READY'and ready['failure_code']is None
        with psycopg.connect(url)as check,check.cursor()as c:
            bounded(c);result=capture.call(c,'select cp7_finance_capture.result(%s)',(fresh,))
            signature,counts=capture.independent_signature(c,result['dates']['as_of'])
            assert signature==result['book_signature']
            assert counts=={f:result['capture']['plan'][f]['rows']for f in capture.FAMILIES}
            metrics,readiness=capture.metrics(c,result);assert len(metrics)==24
            assert all('value'not in x for x in metrics.values()if x['state']=='UNKNOWN')
            assert capture_row(c,cid)==sealed
            check.rollback()
        assert normalized(result['report'])==normalized(current['report'])
        report.update(actual_two_backend_pids=[holder_pid,*worker_pids],actual_blocking_PID_observed=waited,
            concurrent_Native_post=posted,held_before_change_report_exact=True,racing_report_snapshot=held['report_snapshot'],
            snapshot_change_detected_before_count_seal=True,
            source_changed_failure=failed,failed_capture_immutable=True,failed_result_refused=True,
            old_capture_id=str(cid),fresh_capture_id=str(fresh),fresh_capture_ready=True,
            independent_book_signature=True,official_metrics_exact=24,unknown_never_zero=True,
            first_step=step_observation,failure_steps=trail,terminal_replay=again,recovery_steps=recovery,
            current_fresh_report=current_observed,current_candidate_report=result['report'],source_change_race_qualification=True,
            actual_backend_sessions_closed=True)
    finally:
        conn.rollback()
        if state is not None:
            bounded(cur)
            patch.restore(cur,product.catalog,state);conn.commit()
            report['temporary_patch_all22_catalog_restored']=True
    official,official_observed=measured_report(url,dates,False)
    assert normalized(official['report'])==normalized(report.pop('current_candidate_report'))
    report['fresh_recovery_full_unchanged_official_report_equal']=True
    report['unchanged_official_after_recovery']=official_observed
    report.update(status='PASS',diagnostic_collection_completed=True,factory_native_finance_qualified=False,
        performance_qualification=False,price_percent_branch_qualification=True,
        report_check_reuse_implemented=False,product_adoption=False)
