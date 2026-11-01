"""Retain actual unchanged financial4; run only missing browser2 and full restore."""
from pathlib import Path
import importlib.util,os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE='PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def scheduler_quiet(url):
    return load('permanent_original_quiet_scheduler',ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def committed_use(url,state,raw_receipt,report):
    bridge=load('permanent_full_financial_core_for_real_used_witness',HERE/'persistent_financial.py')
    business,product,_=bridge.business(state,raw_receipt)
    import psycopg
    import cp6_bd_probe as financial_truth
    from cp7_p21_current_chain_rehearsal_probe import helper
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        if(connection.info.host not in('127.0.0.1','localhost')or connection.info.port!=54322
           or cursor.execute('select current_database()').fetchone()!=('cp6_rollback',)):
            raise ValueError('PERMANENT_S05_REAL_USED_WITNESS_LOCAL_ONLY')
        with helper.control.product_catalog(cursor):product.verify(cursor,state)
        business.f.admin(cursor)
        if not cursor.execute('select count(*)from erp.app_users').fetchone()[0]:business.f.hp.b.api.seed(cursor)
        cursor.execute('grant usage on schema erp to authenticated')  # retained SQL harness overlay only
        today=cursor.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        before_truth=financial_truth.all_truth(cursor)
        fixture,output,physical=business.pair(cursor,today)
        original_accrual=business.original_accrual(cursor,fixture)
        binding=business.source_hash(cursor,fixture)
        made=business.allocate(cursor,fixture,output)
        oracle=business.f.assert_pool(cursor,fixture,made,output)
        if business.original_accrual(cursor,fixture)!=original_accrual or business.source_hash(cursor,fixture)!=binding:
            raise ValueError('PERMANENT_S05_USED_WITNESS_CHANGED_ORIGINAL_ACCRUAL_OR_SOURCE')
        after_truth=financial_truth.all_truth(cursor)
        if not financial_truth.truth_quiet(before_truth,after_truth):
            raise ValueError('PERMANENT_S05_USED_WITNESS_NEW_FINANCIAL_FINDING')
        with helper.control.product_catalog(cursor):product.verify(cursor,state)
        cursor.execute('set constraints all immediate');cursor.execute('set constraints all deferred')
        connection.commit()
        with helper.control.product_catalog(cursor):
            _,_,_,_,catalog=product.runtime()
            before_catalog,before_data=catalog._catalog_rows(cursor),catalog._data(cursor)
            try:product.rollback_delta_preuse(cursor,state)
            except ValueError as error:
                if str(error)!=product.USED_ERROR:raise
            else:raise AssertionError('PERMANENT_S05_USED_INVERSE_NOT_REFUSED')
            after_catalog,after_data=catalog._catalog_rows(cursor),catalog._data(cursor)
            if before_catalog!=after_catalog or before_data!=after_data:
                raise ValueError('PERMANENT_S05_USED_REFUSAL_CHANGED_ALL22_ROWS_OR_SEQUENCES')
            product.verify(cursor,state)
        connection.rollback()
    report.update(status='NATIVE_BUSINESS_COMMITTED',Native_case_credit=0,
        scope='PERMANENT_READER_REAL_SOURCE_CHOICE_AND_NATIVE_COST_ALLOCATION',
        committed_choice_and_allocation=made,independent_Native_pool_oracle=oracle,
        original_accrual=original_accrual,original_source_binding=binding,
        Native_financial_truth_before=before_truth,Native_financial_truth_after=after_truth,
        before=dict(actual_all22=before_catalog,full_data_and_sequences=before_data),
        after=dict(actual_all22=after_catalog,full_data_and_sequences=after_data),
        used_inverse_guard_refused_before_DDL=True,reader_remains_installed=True)


def exercise(conn,cur,database,url,report,state):
    notes=load('permanent_component_published_diagnostics',HERE/'runtime_note.py')
    proof=load('permanent_complete_current_source_and_parent_admission',HERE/'admission.py').admitted()
    if state['sources']!=proof['current_installation']:
        raise ValueError('PERMANENT_S05_EXACT_ACTUAL_COMPLETE_INSTALLATION_REQUIRED')
    raw_receipt=Path(os.environ['PERMANENT_JOIN37_ROOT_INTAKE']).read_bytes()
    report.update(status='INCOMPLETE',actual_Native_cases=0,actual_browser_cases=0,
        retained_join37_fresh_case_credit=0,permanent_reader_remains_installed=True,
        production_go=False,independent_acceptance=False)
    metadata=load('permanent_owning_readonly_system_metadata',HERE/'system_metadata.py')
    with notes.phase('PERMANENT_READONLY_METADATA_BEFORE_NATIVE'):
        report['read_only_system_metadata_before_native']=metadata.capture_pair(url,raw_receipt)
    retained=load('permanent_keep_actual_financial4_without_rerun',HERE/'retained4.py')
    report['retained_permanent_financial4']=retained.invariant_sources(state['sources'])
    report['retained4_original_admission']=retained.original_admission()
    # The omitted strict group used to release this owning source connection.
    # Release our own connection before the real witness and template copy.
    report['source_connection_release']=retained.release_source(conn,cur)
    witness=report['separate_committed_Native_use']=dict(status='INCOMPLETE')
    with notes.phase('PERMANENT_NATIVE_COMMITTED_WITNESS_ZERO_CASE_CREDIT'):
        committed_use(url,state,raw_receipt,witness)
    second=report['fresh_permanent_browser2']=dict(status='INCOMPLETE')
    with notes.phase('PERMANENT_BROWSER2'):
        load('permanent_complete_normal_App_browser2',HERE/'persistent_browser.py').exercise(
            url,state,second,raw_parent_receipt=raw_receipt)
    if second.get('status')!='PASS'or second.get('actual_browser_cases')!=2:
        raise ValueError('PERMANENT_S05_ACTUAL_NORMAL_APP_BROWSER2_REQUIRED')
    with notes.phase('PERMANENT_READONLY_METADATA_AFTER_NATIVE_BROWSER'):
        report['read_only_system_metadata_after_native_and_browser']=metadata.capture_pair(url,raw_receipt)
    cases={key:dict(status=row['status'])for key,row in second['browser']['cases'].items()}
    if set(cases)!=set(report['retained_permanent_financial4']['missing_case_ids'])or any(row['status']!='PASS'for row in cases.values()):
        raise ValueError('PERMANENT_S05_EXACT_TWO_MISSING_BROWSER_CASES_REQUIRED')
    report.update(status='PASS',business_cases=cases,business_counts={'PASS':2},actual_Native_cases=0,
        retained_Native_cases=4,retained_cases_are_not_fresh=True,candidate_case_coverage=6,
        financial_groups_rerun=False,source_invariant_reuse=True,prior_runs_aggregated=True,
        actual_browser_cases=2,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        used_guard_refused_before_DDL=True,retained_join37_fresh_case_credit=0,
        global_writer_or_permission_or_lock_closure=False,Afui_positive_HPP_zero_reimbursement_coverage=False,
        full_outer_restore_Auth_and_all5_required=True)
