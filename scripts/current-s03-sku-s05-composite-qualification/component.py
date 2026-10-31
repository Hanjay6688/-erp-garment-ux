"""One actual joined installation: Native14 + SKU7 + S05 Native10 + browser6."""
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE='CURRENT_S03_SKU_S05_NATIVE31_BROWSER6'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def scheduler_quiet(url):
    return load('joined_current_quiet_scheduler',ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def exercise(conn,cur,database,url,report,state):
    admission=load('joined_component_before_ERP_admission',HERE/'admission.py');proof=admission.admitted()
    import psycopg
    from cp7_s03_sku_composition import composition as product
    if state['sources']!=proof['current_installation']or state['sources']!=product.sources():
        raise ValueError('JOIN_EXACT_ACTUAL_INSTALLATION_REQUIRED')
    report.update(status='INCOMPLETE',actual_Native_cases=0,actual_browser_cases=0,
        retained_current_SKU27_parent=proof['qualified_SKU_parent'],retained_qualified_S03_backend14_parent=proof['qualified_S03_parent'],
        retained_parent_cases_are_not_fresh_case_credit=True,production_go=False,independent_acceptance=False)
    # Native14 must run first: its strict sequence-prefix proof starts at the
    # exact initial preuse boundary, before any other component commits a use.
    first=report['fresh_S03_Native14']=dict(status='INCOMPLETE')
    load('joined_complete_fresh_S03_Native14',HERE/'native_s03.py').exercise(conn,cur,database,url,first,state)
    if first.get('status')!='PASS'or first.get('actual_Native_cases')!=14 or first.get('used_guard_refused_before_DDL')is not True:
        raise ValueError('JOIN_FRESH_S03_NATIVE14_AND_USED_INVERSE_REQUIRED')
    second=report['fresh_SKU_Native7']=dict(status='INCOMPLETE')
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        load('joined_complete_SKU_Native7',HERE/'native_sku.py').exercise(connection,cursor,database,url,second,state)
    if second.get('status')!='PASS'or second.get('actual_Native_cases')!=7 or second.get('used_guard_refused_before_DDL')is not True:
        raise ValueError('JOIN_FRESH_SKU_NATIVE7_REQUIRED')
    native,derivation=load('joined_complete_S05_Native10_binding',HERE/'native_s05.py').component()
    third=report['fresh_S05_Native10']=dict(status='INCOMPLETE',source_binding=derivation)
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        native.exercise(connection,cursor,database,url,third,state)
    if third.get('status')!='PASS'or third.get('actual_Native_cases')!=10 or third.get('used_guard_refused_before_DDL')is not True:
        raise ValueError('JOIN_FRESH_S05_NATIVE10_REQUIRED')
    fourth=report['fresh_S03_browser4']=dict(status='INCOMPLETE')
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        load('joined_complete_S03_real_App_browser4',HERE/'s03_component.py').exercise(connection,cursor,database,url,fourth,state)
    if fourth.get('status')!='PASS'or fourth.get('actual_browser_cases')!=4:
        raise ValueError('JOIN_FRESH_S03_REAL_AUTH_BROWSER4_REQUIRED')
    fifth=report['fresh_S05_browser2']=dict(status='INCOMPLETE')
    load('joined_complete_S05_real_App_browser2',HERE/'s05_browser.py').exercise(url,state,fifth)
    if fifth.get('status')!='PASS'or fifth.get('actual_browser_cases')!=2:
        raise ValueError('JOIN_FRESH_S05_REAL_AUTH_BROWSER2_REQUIRED')
    groups=(first['native']['cases'],first['reader_native3']['cases'],second['native']['cases'],
        third['native']['cases'],fourth['browser']['cases'],fifth['browser']['cases'])
    cases={key:dict(status=row['status'])for group in groups for key,row in group.items()}
    if sum(map(len,groups))!=len(cases)or len(cases)!=37 or any(row['status']!='PASS'for row in cases.values()):
        raise ValueError('JOIN_EXACT_37_UNIQUE_FRESH_CASES_REQUIRED')
    report.update(status='PASS',business_cases=cases,business_counts={'PASS':37},actual_Native_cases=31,
        actual_browser_cases=6,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        retained_SKU27_fresh_case_credit=0,used_guard_refused_before_DDL=True,
        full_outer_restore_Auth_and_all5_required=True,Afui_positive_HPP_zero_reimbursement_coverage=False,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)
