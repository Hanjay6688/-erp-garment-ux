"""Prepared complete D1 Native13 + E Native17; real committed use separately."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE='CURRENT_COMPLETE_D1_E_NATIVE30'
LABEL='CP7_CURRENT_COMPLETE_D1_E_NATIVE30_CASES'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def scheduler_quiet(url):
    return load('complete_DE_original_scheduler_quiet',
        ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def retain(native,report):
    out=ROOT/'cp6-proof/t3';out.mkdir(parents=True,exist_ok=True);files=[]
    for name in(LABEL+'.json',LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        path=native.r1.OUT/name
        if path.is_file():
            raw=path.read_bytes();(out/name).write_bytes(raw)
            files.append(dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest()))
    report['strict_group_originals']=files


def exercise(conn,cur,database,url,report,state):
    bridge=load('complete_DE_actual_Native30_business',HERE/'native_business.py')
    work=bridge.bind(state)
    witness,derivation=load('complete_DE_original_committed_E_derivation',HERE/'witness.py').business()
    witness.require_local(conn,cur)
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_catalog_state import exact_public_catalog
    import cp6_bd_probe as financial_truth
    native=work.native;product=work.product;control=helper.control
    report.update(status='INCOMPLETE',actual_Native_cases=0,actual_browser_cases=0,actual_Auth_HTTP_cases=0,
        actual_two_session_races=0,real_Auth=False,retained_permanent6_fresh_case_credit=0,
        reader_remains_installed=True,D_complete=False,E_complete=False,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)
    with control.product_catalog(cur):product.verify(cur,state)
    conn.rollback();cur.close();conn.close()
    monitor=load('complete_DE_runtime_phases',HERE/'runtime_note.py')
    metadata=load('complete_DE_owning_readonly_system_metadata',HERE/'system_metadata.py')
    with monitor.phase('DE_READONLY_SYSTEM_METADATA_BEFORE_NATIVE30'):
        report['read_only_system_metadata_before_native30']=metadata.capture_pair(url)
    def verify(cursor):
        with control.product_catalog(cursor):return product.verify(cursor,state)
    try:
        with bridge.fixture_imports(),exact_public_catalog(native,retain_raw=True)as public:
            with monitor.phase('DE_NATIVE30_ORIGINAL_CALLBACKS'):
                actual=native.strict_group(LABEL,work.cases,verify)
    finally:retain(native,report)
    report.update(native=actual,public_catalog_observation=public,source_control=work.source_control)
    if(actual.get('status')!='PASS'or actual.get('counts')!={'PASS':30}
       or actual.get('planned_case_ids')!=list(work.IDS)or set(actual.get('cases',{}))!=set(work.IDS)
       or actual.get('complete_boundary_restored')is not True):
        raise ValueError('COMPLETE_DE_ALL_THIRTY_ORIGINAL_NATIVE_CASES_REQUIRED')
    for key,row in actual['cases'].items():
        if(row.get('status')!='PASS'or row.get('full_boundary_restored')is not True
           or row.get('public_schema_unchanged')is not True or row.get('business_day_rollover')):
            raise ValueError('COMPLETE_DE_ORIGINAL_FULL_STRICT_CASE_REQUIRED:'+key)
    if actual.get('business_day_retried')or actual.get('business_day_first_attempt'):
        raise ValueError('COMPLETE_DE_SINGLE_REAL_BUSINESS_DAY_ATTEMPT_REQUIRED')
    with bridge.fixture_imports(),monitor.phase('DE_ORIGINAL_COMMITTED_E_USE_AND_USED_REFUSAL'):
        used=witness.committed_witness(url,state,work.E,product,control,financial_truth)
    if(used.get('status')!='NATIVE_E_CORRECTION_COMMITTED'or used.get('E_Native_case_credit')!=0
       or used.get('before')!=used.get('after')):
        raise ValueError('COMPLETE_DE_REAL_COMMITTED_E_USE_AND_RAW_USED_REFUSAL_REQUIRED')
    report['separate_committed_E_witness']=dict(used,source_derivation=derivation)
    with monitor.phase('DE_READONLY_SYSTEM_METADATA_AFTER_NATIVE30_AND_COMMITTED_USE'):
        report['read_only_system_metadata_after_native30_and_committed_use']=metadata.capture_pair(url)
    report.update(status='PASS',actual_Native_cases=30,business_counts={'PASS':30},
        actual_D1_cases=13,actual_E_cases=17,used_guard_refused_before_DDL=True,
        original_business_callback_changes=0,all_outer_restore_and_five_package_gates_still_required=True)
