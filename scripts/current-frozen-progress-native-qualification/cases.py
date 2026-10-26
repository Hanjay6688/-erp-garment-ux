"""Focused new telemetry boundary on the actual full ERP predecessor.

SQL Auth claims are real Native checks, not an HTTP/browser qualification.
All business fixture posting goes through the unchanged qualified Native path.
"""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from time import monotonic
import importlib.util,json,uuid
import cp7_current_analysis_progress.installation as product
import cp7_p21_current_chain_rehearsal_probe as chain

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qualified_public_finance_progress_fixtures',ROOT/'scripts/current-frozen-public-native-qualification/public_finance_cases.py')
finance=importlib.util.module_from_spec(spec);spec.loader.exec_module(finance)
staged=finance.staged
RPC='erp_cp7_get_frozen_analysis_progress_v1'
IDS=('PROGRESS_FULL22_AUTHORITY_AND_INVERSE_GUARD',
     'PROGRESS_RUNNING_REOPEN_REAL_COUNTS_NO_WRITES',
     'PROGRESS_OPERATIONAL_DONE_FINANCE_PENDING_THEN_OFFICIAL_RESULT',
     'PROGRESS_CURRENT_ACCESS_REDACTION_AND_FOREIGN_REQUEST',
     'PROGRESS_CHANGED_BOOK_FAILURE_VISIBLE_AND_FRESH_REQUEST_RECOVERY')
STATE=CHECKER=None

@contextmanager
def installed(state,checker):
    global STATE,CHECKER
    old=STATE,CHECKER;STATE,CHECKER=state,checker
    try:yield dict(focused_case_ids=list(IDS),qualified_parent_cases_rerun=False,
                   formulas_and_fixtures_unchanged=True,production_go=False)
    finally:STATE,CHECKER=old

def at(value):return datetime.fromisoformat(value)

def worker_lock(cur,capture_id,expected_own_lock):
    # Reassemble the signed bigint lock key, independently of the endpoint's
    # split-key lookup. Native steps run in this same outer transaction, so
    # their xact advisory lock remains held after READY/FAILED until rollback.
    own,foreign=cur.execute("""
        select count(*) filter(where pid=pg_backend_pid()),
               count(*) filter(where pid<>pg_backend_pid())
        from pg_catalog.pg_locks
        where locktype='advisory' and granted and mode='ExclusiveLock'
          and objsubid=1
          and database=(select oid from pg_catalog.pg_database where datname=current_database())
          and ((classid::bigint<<32)|objid::bigint)=
              pg_catalog.hashtextextended('CP7:FINANCE_CAPTURE_STEP:'||%s::text,0)
    """,(capture_id,)).fetchone()
    assert foreign==0,('UNEXPECTED_CONCURRENT_WORKER',foreign)
    assert own==int(expected_own_lock),('NATIVE_TRANSACTION_LOCK_MISMATCH',own,expected_own_lock)
    return 'LOCK_HELD'if expected_own_lock else'NO_LOCK_OBSERVED'

def read(cur,key,subject=None,*,expected_own_lock=False):
    before=product.catalog._data(cur);started=monotonic()
    wire=staged.limited(cur,RPC,(key,),subject)
    elapsed=round((monotonic()-started)*1000,3)
    assert elapsed<8000,('SMALL_PROGRESS_READ_OVER_BUDGET',elapsed)
    assert product.catalog._data(cur)==before,'TELEMETRY_READ_CHANGED_DATA_OR_SEQUENCES'
    assert set(wire)=={'contract_version','policy_id','observed_at','status','operational','finance','production_go'}
    assert wire['contract_version']=='cp7.frozen-analysis-progress.v1'and wire['policy_id']=='D17-18-20261026'
    assert wire['production_go']is False
    status=staged.checked(wire['status'],key)
    assert status==staged.status(cur,key,subject)
    op=wire['operational'];assert set(op)=={'created_at','last_activity_at','finished_at','worker_observation'}
    assert at(op['last_activity_at'])==at(status['last_progress_at'])
    assert at(op['created_at'])<=at(op['last_activity_at'])<=at(wire['observed_at'])
    assert op['worker_observation']=='NOT_EXPOSED'
    assert (op['finished_at']is not None)==(status['state']!='RUNNING')
    if op['finished_at']is not None:assert at(op['finished_at'])==at(op['last_activity_at'])
    side=status.get('finance_capture');m=wire['finance']
    if side is None or side['state']=='ACCESS_REVOKED':assert m is None
    else:
        assert m['capture_id']==side['capture']['capture_id']
        stored=finance.stored_capture(cur,m['capture_id'])
        for key1,key2 in [('created_at','created_at'),('last_activity_at','updated_at'),('finished_at','finished_at')]:
            assert (at(m[key1])if m[key1]is not None else None)==(at(stored[key2])if stored[key2]is not None else None)
        assert m['unit_attempts']==stored['unit_attempts']and m['report_ms']==stored['report_ms']
        expected=worker_lock(cur,m['capture_id'],expected_own_lock)
        assert m['worker_observation']==expected,('WORKER_OBSERVATION_MISMATCH',m['worker_observation'],expected)
        assert at(m['created_at'])<=at(m['last_activity_at'])<=at(wire['observed_at'])
    return wire,elapsed

def cases(cur,today):
    def catalog():
        CHECKER(cur)
        signature='public.'+RPC+'(uuid)'
        assert {r:cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(r,signature)).fetchone()[0]
                for r in ('anon','authenticated','service_role','cp7_alert')}==dict(anon=False,authenticated=True,service_role=False,cp7_alert=False)
        cur.execute('create view public.current_progress_inverse_guard as select public.'+RPC+'(null::uuid)value')
        held,data=product.catalog._catalog_rows(cur),product.catalog._data(cur)
        try:
            with chain.helper.control.product_catalog(cur):product.rollback_preuse(cur,STATE)
        except ValueError as error:assert str(error)=='CURRENT_PROGRESS_CURRENT_STATE_CHANGED'
        else:raise AssertionError('PROGRESS_EXTERNAL_DEPENDENCY_ACCEPTED')
        assert product.catalog._catalog_rows(cur)==held and product.catalog._data(cur)==data
        cur.execute('drop view public.current_progress_inverse_guard');CHECKER(cur)
        return dict(status='PASS',full22_delta_exact_one_RPC=True,authenticated_only=True,
                    dependent_view_refused_before_DDL=True,outer_preuse_inverse_required=True)

    def running():
        finance.setup(cur,today);key=uuid.uuid4();finance.request(cur,today,key)
        first,t1=read(cur,key);second,t2=read(cur,key)
        assert first['status']==second['status']
        assert first['operational']==second['operational']and first['finance']==second['finance']
        assert first['status']['units_done']==0 and first['status']['plan_final']is False
        assert first['status']['finance_capture']['capture']['units_total']is None
        old=product.catalog._data(cur);again=finance.request(cur,today,key)
        assert again==first['status']and product.catalog._data(cur)==old
        plain=uuid.uuid4();finance.request(cur,today,plain,None);third,t3=read(cur,plain)
        assert third['finance']is None and 'finance_capture'not in third['status']
        return dict(status='PASS',status_read_ms=[t1,t2,t3],unknown_totals_preserved=True,
                    same_request_same_job_and_capture=True,no_read_or_replay_DML=True,operational_only_redacted=True)

    def completed():
        finance.setup(cur,today);key=uuid.uuid4();initial=finance.request(cur,today,key)
        cid=finance.sidecar(initial,key,'RUNNING')['capture']['capture_id']
        done,calls=staged.drive(cur,key);assert done['state']=='DONE'
        waiting,t1=read(cur,key)
        assert waiting['operational']['finished_at']is not None and waiting['finance']['finished_at']is None
        assert waiting['status']['finance_capture']['state']=='RUNNING'
        ready,trail=finance.run_capture(cur,cid);assert ready['state']=='READY'
        final,t2=read(cur,key,expected_own_lock=True);reopened,t3=read(cur,key,expected_own_lock=True)
        assert final['operational']==reopened['operational']and final['finance']==reopened['finance']
        result=finance.sidecar(final['status'],key,'READY')['result']
        source=finance.finance.call(cur,'select cp7_finance_capture.result(%s)',(cid,))
        official=finance.finance.official(cur,source['dates'])
        for part in ('performance','financial_position','basis','data_confidence'):
            assert source['report']['snapshot'][part]==official['snapshot'][part]
        wanted,readiness=finance.finance.metrics(cur,source)
        assert len(wanted)==24 and {m['metric_id']:m['value']for m in result['metrics']}==wanted
        assert result['readiness']==readiness
        unknown=[key for key,value in wanted.items()if value['state']=='UNKNOWN']
        assert all('value'not in wanted[key]for key in unknown)
        return dict(status='PASS',status_read_ms=[t1,t2,t3],production_done_did_not_finish_finance=True,
                    reopened_terminal_timestamps_exact=True,official_metrics_exact=24,
                    readiness=readiness,unknown_metric_ids=unknown,unknown_never_zero=True,
                    operational_steps=len(calls),finance_steps=len(trail),
                    transaction_lock_observations=[waiting['finance']['worker_observation'],
                        final['finance']['worker_observation'],reopened['finance']['worker_observation']])

    def privacy():
        finance.setup(cur,today);subject,role=finance.finance.finance_cases.admin_actor(cur,staged.analysis)
        key=uuid.uuid4();finance.request(cur,today,key,subject=subject);visible,t1=read(cur,key,subject)
        other,_=finance.finance.finance_cases.admin_actor(cur,staged.analysis)
        foreign=staged.auth.refused(cur,lambda:staged.limited(cur,RPC,(key,),other),'CP7_ANALYSIS_JOB_UNAVAILABLE')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(role,));assert cur.rowcount==1
        hidden,t2=read(cur,key,subject)
        assert hidden['finance']is None and hidden['status']['finance_capture']['state']=='ACCESS_REVOKED'
        assert hidden['status']['finance_capture']['capture']is hidden['status']['finance_capture']['result']is None
        assert hidden['operational']==visible['operational']
        return dict(status='PASS',status_read_ms=[t1,t2],foreign_request_refused=foreign,
                    current_finance_access_hides_all_metadata_and_figures=True)

    def changed_source():
        finance.setup(cur,today);key=uuid.uuid4();initial=finance.request(cur,today,key)
        cid=finance.sidecar(initial,key,'RUNNING')['capture']['capture_id']
        first=finance.run_capture(cur,cid,once=True);assert first['state']=='RUNNING'and first['units_done']==1
        finance.finance.given(cur,today,'900.00')
        failed,trail=finance.run_capture(cur,cid);assert failed['state']=='FAILED'and failed['failure_code']=='CP7_FINANCE_CAPTURE_SOURCE_CHANGED'
        observed,t1=read(cur,key,expected_own_lock=True)
        assert observed['finance']['finished_at']is not None
        assert observed['status']['finance_capture']['state']=='FAILED'and observed['status']['finance_capture']['result']is None
        stored=finance.stored_capture(cur,cid)
        next_key=uuid.uuid4();fresh=finance.request(cur,today,next_key)
        new_id=finance.sidecar(fresh,next_key,'RUNNING')['capture']['capture_id'];assert new_id!=cid
        ready,_=finance.run_capture(cur,new_id);assert ready['state']=='READY'
        recovered,t2=read(cur,next_key,expected_own_lock=True)
        assert recovered['status']['finance_capture']['state']=='READY'
        assert finance.stored_capture(cur,cid)==stored
        return dict(status='PASS',status_read_ms=[t1,t2],failure_visible=True,failed_result_not_exposed=True,
                    failure_code=failed['failure_code'],fresh_request_recovered=True,old_failed_capture_immutable=True,
                    transaction_lock_observations=[observed['finance']['worker_observation'],recovered['finance']['worker_observation']])
    return list(zip(IDS,(catalog,running,completed,privacy,changed_source)))
