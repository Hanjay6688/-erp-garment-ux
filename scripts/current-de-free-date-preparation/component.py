"""Prepared actual Native FREE3 plus a separate zero-credit committed witness."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE='CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3'
LABEL='CP7_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_CASES'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def scheduler_quiet(url):
    return load('free_date_original_scheduler_quiet',
        ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def require_local(conn,cur):
    if(conn.info.host not in('localhost','127.0.0.1')or conn.info.port!=54322
       or cur.execute('select current_database()').fetchone()!=('cp6_rollback',)):
        raise ValueError('FREE_DATE_NATIVE_LOCAL_DISPOSABLE_DATABASE_ONLY')


def retain(native,report):
    destination=ROOT/'cp6-proof/t3';destination.mkdir(parents=True,exist_ok=True);pins=[]
    for name in(LABEL+'.json',LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        path=native.r1.OUT/name
        if not path.is_file():continue
        raw=path.read_bytes();out=destination/name
        if out.exists()and out.read_bytes()!=raw:
            raise ValueError('FREE_DATE_FIRST_ACTUAL_NATIVE_ORIGINAL_OVERWRITE_REFUSED')
        if not out.exists():
            with out.open('xb')as stream:stream.write(raw)
        pins.append(dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest()))
    report['strict_group_originals']=pins


def full_case(cur,operation,work,control):
    """Retain full current22/ALL rows/sequences after an actual rolled-back case.

    The unchanged strict runner still owns its outer savepoint, CP6/public
    boundary and session checks. This inner case savepoint adds the complete
    current product boundary without replacing that runner or its callbacks.
    """
    catalog=work.product.runtime()[4]
    with control.product_catalog(cur):
        work.product.verify(cur,work.state)
        before=dict(actual_all22=catalog._catalog_rows(cur),
                    full_data_and_sequences=catalog._data(cur))
    cur.execute('savepoint free_date_full_current_case')
    error=None;result=None
    try:result=operation()
    except Exception as failed:error=failed
    try:
        cur.execute('rollback to savepoint free_date_full_current_case')
        cur.execute('release savepoint free_date_full_current_case')
    except Exception as failed:
        raise ValueError('FREE_DATE_CASE_TRANSACTION_BOUNDARY_LOST; original='+str(error))from failed
    if error is not None:raise error
    with control.product_catalog(cur):
        work.product.verify(cur,work.state)
        after=dict(actual_all22=catalog._catalog_rows(cur),
                   full_data_and_sequences=catalog._data(cur))
    if before!=after or len(before['actual_all22'])!=22:
        raise ValueError('FREE_DATE_ROLLED_BACK_CASE_CHANGED_FULL22_ROWS_OR_SEQUENCES')
    if type(result)is not dict:raise ValueError('FREE_DATE_ACTUAL_CASE_RESULT_OBJECT_REQUIRED')
    result['actual_full22_case_boundary']=dict(before=before,after=after)
    return result


def committed_use(url,state,work,bridge,control,financial_truth):
    # bind() already required the exact actual Native30 parent before imports.
    import psycopg
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        require_local(conn,cur)
        with control.product_catalog(cur):work.product.verify(cur,state)
        work.fixture.api.admin(cur)
        cur.execute('grant usage on schema erp to authenticated')  # Existing isolated SQL harness overlay.
        today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        before_truth=financial_truth.all_truth(cur)
        actual=bridge.post_one(cur,today,work.fixture)
        after_truth=financial_truth.all_truth(cur)
        if not financial_truth.truth_quiet(before_truth,after_truth):
            raise ValueError('FREE_DATE_COMMITTED_POST_NEW_FINANCIAL_TRUTH_FINDING')
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        conn.commit()
        result=dict(status='NATIVE_FREE_NOTE_COMMITTED',Native_case_credit=0,
            actual_issue_id=actual['issue'],actual_response=actual['made'],physical_at=actual['at'],
            posted_snapshot=actual['snapshot'],ledger_delta=actual['ledger_delta'],
            financial_truth_before=before_truth,financial_truth_after=after_truth,
            original_normal_post_route=True,source_lines=1,paid_companion_lines=0,
            mandatory_PO_or_FG_match=False,product_clock_changed=False)
        with control.product_catalog(cur):
            catalog=work.product.runtime()[4]
            before=dict(actual_all22=catalog._catalog_rows(cur),
                        full_data_and_sequences=catalog._data(cur))
            try:work.product.rollback_delta_preuse(cur,state)
            except ValueError as error:
                if str(error)!=work.product.USED_ERROR:raise
                result['actual_used_inverse_error']=str(error)
            else:raise ValueError('FREE_DATE_COMMITTED_USE_INVERSE_WAS_NOT_REFUSED')
            after=dict(actual_all22=catalog._catalog_rows(cur),
                       full_data_and_sequences=catalog._data(cur))
            if before!=after or len(before['actual_all22'])!=22:
                raise ValueError('FREE_DATE_USED_REFUSAL_CHANGED_FULL_CATALOG_ROWS_OR_SEQUENCES')
            result.update(before=before,after=after)
        conn.rollback();return result


def exercise(conn,cur,database,url,report,state):
    bridge=load('free_date_actual_Native3_business',HERE/'native_free.py')
    work=bridge.bind(state);require_local(conn,cur)
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_catalog_state import exact_public_catalog
    import cp6_bd_probe as financial_truth
    control=helper.control;native=work.runner
    work.state=state
    report.update(status='INCOMPLETE',actual_Native_cases=0,actual_browser_cases=0,
        actual_Auth_HTTP_cases=0,actual_two_session_races=0,real_Auth=False,
        retained_DE30_fresh_case_credit=0,reader_remains_installed=True,
        GOOD_eligibility_policy_decided=False,Afui_GOOD_nonpayable_path_complete=False,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)
    with control.product_catalog(cur):work.product.verify(cur,state)
    conn.rollback();cur.close();conn.close()
    monitor=load('free_date_exact_original_runtime_phases',
        ROOT/'scripts/current-complete-de-integration-preparation/runtime_note.py')
    def verify(cursor):
        with control.product_catalog(cursor):return work.product.verify(cursor,state)
    def cases(cursor,today):
        return [(name,lambda operation=operation:full_case(cursor,operation,work,control))
                for name,operation in work.cases(cursor,today)]
    try:
        with exact_public_catalog(native,retain_raw=True)as public:
            with monitor.phase('FREE_DATE_NATIVE3_ORIGINAL_PUBLIC_ROUTES'):
                actual=native.strict_group(LABEL,cases,verify)
    finally:retain(native,report)
    report.update(native=actual,public_catalog_observation=public,source_control=work.source_control)
    if(actual.get('status')!='PASS'or actual.get('counts')!={'PASS':3}
       or actual.get('planned_case_ids')!=list(work.IDS)or list(actual.get('cases',{}))!=list(work.IDS)
       or actual.get('complete_boundary_restored')is not True
       or actual.get('business_day_retried')or actual.get('business_day_first_attempt')):
        raise ValueError('FREE_DATE_ALL_THREE_FRESH_STRICT_NATIVE_CASES_REQUIRED')
    for key,row in actual['cases'].items():
        if(row.get('status')!='PASS'or row.get('full_boundary_restored')is not True
           or row.get('public_schema_unchanged')is not True or row.get('business_day_rollover')
           or row.get('session_leaks')!=dict(advisory_locks=0,advisory_lock_keys=[],other_sessions=[])):
            raise ValueError('FREE_DATE_COMPLETE_ORIGINAL_STRICT_CASE_REQUIRED:'+key)
    with monitor.phase('FREE_DATE_COMMITTED_NATIVE_USE_AND_USED_REFUSAL'):
        report['separate_committed_Native_use']=committed_use(url,state,work,bridge,control,financial_truth)
    report.update(status='PASS',actual_Native_cases=3,business_counts={'PASS':3},
        used_guard_refused_before_DDL=True,full_outer_restore_and_all5_required=True)
