"""Only the missing actual S05 browsers; retained35 never become fresh cases."""
from pathlib import Path
import importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-s03-sku-s05-composite-qualification'
CASE='CURRENT_S05_CSS_RETAINED35_FRESH_BROWSER2'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def scheduler_quiet(url):
    return load('focused_unchanged_scheduler_cleanup',ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)

def foundation_precheck(cur):
    return load('focused_original_fixture_readiness',HERE/'foundation.py').check_before_install(cur)

def release_source_for_copy(conn,cur):
    """Release only our committed source connection, never another backend."""
    info=conn.info
    if(info.host not in('127.0.0.1','localhost')or info.port!=54322 or info.dbname!='cp6_rollback'
        or type(info.backend_pid)is not int or info.backend_pid<=0):
        raise ValueError('FOCUSED_EXACT_OWN_LOCAL_SOURCE_CONNECTION_REQUIRED')
    pid=info.backend_pid
    try:cur.close()
    finally:conn.close()
    if cur.closed is not True or conn.closed is not True:
        raise ValueError('FOCUSED_SOURCE_CONNECTION_MUST_BE_CLOSED_BEFORE_BROWSER_COPY')
    return dict(phase='AFTER_FOUNDATION_COMMIT_BEFORE_READER_OR_COPY',database='cp6_rollback',
        backend_pid=pid,cursor_closed=True,connection_closed=True,foreign_backends_terminated=0,
        actual_Native_case_credit=0)

def exercise(conn,cur,database,url,report,state):
    admission=load('focused_component_actual_retention',HERE/'admission.py');proof=admission.retained()
    p=load('focused_component_typed_truth',PARENT/'parents.py')
    p.exact(admission.json_pin(state['sources']),proof['receipt']['qualified_financial_sources'],'EXACT_INSTALLED_RETAINED_FINANCIAL_SOURCE')
    import psycopg
    from cp7_s03_sku_composition import composition as product
    from cp7_p21_current_chain_rehearsal_probe import helper
    report.update(status='INCOMPLETE',retained35=proof,actual_Native_cases=0,actual_browser_cases=0,
        retained_cases_are_not_fresh=True,production_go=False,independent_acceptance=False)
    foundation=report['fixture_foundation']=dict(status='INCOMPLETE')
    load('focused_original_committed_fixture_setup',HERE/'foundation.py').prepare(cur,product,state,helper.control,foundation)
    conn.commit()  # The unchanged historical setup was committed by the omitted Native witness.
    # PostgreSQL createdb -T requires zero source sessions, including idle ones.
    # The owning engine's context manager also accepts an already closed handle.
    report['source_connection_release']=release_source_for_copy(conn,cur)
    fresh=report['fresh_S05_browser2']=dict(status='INCOMPLETE')
    load('focused_unchanged_real_Auth_S05_browser2',PARENT/'s05_browser.py').exercise(url,state,fresh)
    p.fields(fresh,dict(status='PASS',actual_browser_cases=2,actual_Native_cases=0),'COMPLETE_FRESH_S05_BROWSER2_REQUIRED')
    expected=proof['receipt']['missing_case_ids'];p.exact(set(fresh['browser']['cases']),set(expected),'ONLY_MISSING_TWO_CASES_RUN')
    for row in fresh['browser']['cases'].values():p.fields(row,dict(status='PASS'),'ACTUAL_BROWSER_PASS')
    # The unchanged Native browser prerequisites commit actual business use.
    # Prove the original full-data used guard refuses before any DDL, without
    # resetting a sequence or rerunning a previously qualified Native group.
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        catalog=product.runtime()[-1]
        with helper.control.product_catalog(cursor):
            product.verify(cursor,state)
            before=dict(actual_all22=catalog._catalog_rows(cursor),full_data_and_sequences=catalog._data(cursor))
            if before['full_data_and_sequences']==state['preuse_data_and_sequences']:
                raise ValueError('FOCUSED_ACTUAL_COMMITTED_NATIVE_PREPARATION_REQUIRED')
            cursor.execute('SAVEPOINT focused_real_used_inverse')
            refused=False
            try:product.rollback_delta_preuse(cursor,state)
            except ValueError as error:
                if str(error)!=product.USED_ERROR:raise
                refused=True
            finally:
                cursor.execute('ROLLBACK TO SAVEPOINT focused_real_used_inverse')
                cursor.execute('RELEASE SAVEPOINT focused_real_used_inverse')
            if not refused:raise ValueError('FOCUSED_USED_INVERSE_MUST_REFUSE')
            after=dict(actual_all22=catalog._catalog_rows(cursor),full_data_and_sequences=catalog._data(cursor))
            p.exact(after,before,'FULL_RAW_USED_REFUSAL_HAS_ZERO_EFFECT')
            report['used_inverse_refusal_before']=before;report['used_inverse_refusal_after']=after
            connection.rollback()
    report.update(status='PASS',business_cases={case:dict(status='PASS')for case in expected},business_counts={'PASS':2},
        actual_Native_cases=0,actual_browser_cases=2,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        retained_Native_cases=31,retained_S03_browser_cases=4,retained_case_count=35,candidate_case_coverage=37,
        used_guard_refused_before_DDL=True,full_outer_restore_Auth_and_all5_required=True,
        Afui_positive_HPP_zero_reimbursement_coverage=False,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False)
