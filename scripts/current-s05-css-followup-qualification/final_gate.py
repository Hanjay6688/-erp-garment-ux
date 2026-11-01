"""Fresh browser2 and all five new gates; retained35 are always labelled old."""
from pathlib import Path
import importlib.util,json,subprocess,re
from hashlib import sha256

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-s03-sku-s05-composite-qualification'
MAIN='CP7_CURRENT_S05_CSS_RETAIN35_BROWSER2.json'
CASE='CURRENT_S05_CSS_RETAINED35_FRESH_BROWSER2'
ALL22=('aggregates','columns','constraints','database_authority','default_privileges','enums','event_triggers',
    'extensions','functions','indexes','inheritance','memberships','policies','relations','roles','rules','schemas',
    'sequence_ownership','sequences','triggers','type_implementation','types')

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def full_census(value,p):
    catalog=value['actual_all22'];data=value['full_data_and_sequences']
    p.exact(set(catalog),set(ALL22),'EXACT_ALL22_CATALOG_CLASSES')
    if not all(type(v)is dict for v in catalog.values()):raise ValueError('FOCUSED_TYPED_ALL22_CATALOG_REQUIRED')
    tables={name for name,row in catalog['relations'].items()if row[1]in('r','p','m')}
    sequences={'sequence:'+name for name in catalog['sequences']}
    p.exact(len(sequences),15,'ALL_FIFTEEN_CURRENT_SEQUENCES')
    p.exact(set(data),tables|sequences,'ALL_CURRENT_RELATION_ROWS_AND_ALL_SEQUENCE_KEYS')
    for name,row in data.items():
        if type(row)is not list or len(row)!=2:raise ValueError('FOCUSED_EXACT_DATA_ABI_REQUIRED')
        if name in sequences:
            if type(row[0])is not str or re.fullmatch(r'-?\d+',row[0])is None or type(row[1])is not bool:
                raise ValueError('FOCUSED_EXACT_SEQUENCE_ABI_REQUIRED')
        elif type(row[0])is not int or row[0]<0 or type(row[1])is not str or re.fullmatch('[0-9a-f]{64}',row[1])is None:
            raise ValueError('FOCUSED_EXACT_ROW_COUNT_HASH_ABI_REQUIRED')
    return dict(tables=len(tables),sequences=len(sequences),catalog_groups=22)

def validate(main,package,backup,supervision,head,proof,p):
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids=[CASE],required_case_ids_pass=True,
        actual_Native_cases=0,actual_browser_cases=2,actual_business_cases=2,actual_Auth_HTTP_cases=0,
        actual_two_session_races=0,retained_Native_cases=31,retained_S03_browser_cases=4,
        retained_cases_are_not_fresh=True,baseline_full22_all_rows_all_sequences_equal=True,
        restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
        used_guard_refused_before_DDL=True,production_go=False,independent_acceptance=False),'FOCUSED_FRESH2_AND_COMPLETE_RESTORE')
    if any(main.get(k)for k in ('error','restore_error','restore_traceback')):raise ValueError('FOCUSED_NO_RUNTIME_OR_RESTORE_ERRORS')
    p.exact(set(main['committed']),{CASE},'ONE_FOCUSED_OWNING_COMPONENT')
    component=main['committed'][CASE]
    p.fields(component,dict(status='PASS',business_counts={'PASS':2},actual_Native_cases=0,actual_browser_cases=2,
        retained_Native_cases=31,retained_S03_browser_cases=4,retained_case_count=35,candidate_case_coverage=37,
        used_guard_refused_before_DDL=True,retained_cases_are_not_fresh=True,
        Afui_positive_HPP_zero_reimbursement_coverage=False,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False),'FOCUSED_COMPONENT_NO_INVENTED_FRESH35')
    p.exact(component['retained35'],proof,'EXACT_ACTUAL_ROOT_AND_SOURCE_INVARIANCE_IN_RUNTIME')
    expected=proof['receipt']['missing_case_ids'];p.exact(set(component['business_cases']),set(expected),'ONLY_MISSING_TWO_FRESH_IDENTITIES')
    for row in component['business_cases'].values():p.fields(row,dict(status='PASS'),'FRESH_BROWSER_ID_PASS')
    browser=component['fresh_S05_browser2']['browser']
    p.fields(browser,dict(status='RUN_COMPLETE',counts={'PASS':2},planned_case_ids=expected,real_auth=True,
        jwt_signed_by_runtime=False,host_exit=0,host_status='RUN_COMPLETE',database_remaining=0,console_errors=0,
        auth_cleanup_failures=[],session_leaks=[],auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)),
        'ACTUAL_NORMAL_APP_REAL_AUTH_BROWSER2_AND_CLEANUP')
    p.exact(list(browser['cases']),expected,'EXACT_FRESH_BROWSER_ORDER')
    for row in browser['cases'].values():
        p.fields(row,dict(status='PASS'),'ACTUAL_FRESH_BROWSER_PASS')
        if row.get('business_day_rollover'):raise ValueError('FOCUSED_NO_WIB_ROLLOVER')
    if any(browser.get(k)for k in ('error','host_error','cleanup_failures','business_day_retried','business_day_first_attempt')):
        raise ValueError('FOCUSED_NO_RETRY_OR_BROWSER_FAILURE')
    p.exact(browser['script_sha256'],sha256((PARENT/'browser.mjs').read_bytes()).hexdigest(),'UNCHANGED_REAL_BROWSER_ASSERTIONS')
    fresh=component['fresh_S05_browser2']
    p.fields(fresh,dict(status='PASS',actual_browser_cases=2,actual_Native_cases=0),'ACTUAL_COMPLETE_FRESH_BROWSER_COMPONENT')
    if not fresh.get('reader_post_browser_inverse')or fresh.get('reader_cleanup_failure'):raise ValueError('FOCUSED_READER_INVERSE_REQUIRED')
    admissions=fresh['copy_catalog_admissions'];p.exact(len(admissions),1,'ONE_ACTUAL_COMMITTED_BROWSER_COPY')
    p.fields(admissions[0],dict(all22_groups_equal_original_install=True),'FULL_BROWSER_COPY_CATALOG_BOUNDARY')
    before=component['used_inverse_refusal_before'];p.exact(before,component['used_inverse_refusal_after'],'COMPLETE_USED_INVERSE_ZERO_EFFECT')
    census=full_census(before,p)
    p.exact(package['gate'],p.GATES,'ALL_FIVE_FRESH_PACKAGE_GATES')
    p.fields(package['run_identity'],dict(tool_head=head,github_sha=head,run_attempt='1'),'ACTUAL_FOCUSED_PACKAGE_IDENTITY')
    p.fields(supervision,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=head,github_run_attempt='1',
        worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,signals=[],
        process_group_empty=True,process_tree_empty=True,job_budget_seconds=7200,work_budget_seconds=5400,
        recovery_reserve_seconds=1200,artifact_reserve_seconds=600,actual_case_credit=0,production_go=False),
        'HARD_BUDGET_AND_COMPLETE_PROCESS_REAP_BEFORE_DATABASE_STOP')
    p.exact(supervision['github_run_id'],package['run_identity']['run_id'],'SAME_ACTUAL_FOCUSED_JOB_RUN')
    p.fields(backup,dict(status='RESTORED_IDENTICAL'),'FRESH_ACTUAL_BACKUP_DRILL')
    p.exact(set(backup['checks']),{'restore_errors_only_pg_cron','catalog_explained','data_identical','engine_answer_present','engine_equal'},'ALL_FIVE_ORIGINAL_BACKUP_CHECKS_PRESENT')
    if not all(type(v)is bool and v for v in backup['checks'].values()):raise ValueError('FOCUSED_ALL_TYPED_BACKUP_CHECKS')
    p.exact(backup['data']['differ'],{},'NO_BACKUP_ROW_DIFFERENCE')
    p.fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'ALL_BASELINE_ROLES_RESTORED')
    p.fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,database_owner_acl_and_settings_preserved=True),
        'COMPLETE_OUTER_RESTORE')
    return dict(status='FRESH_S05_BROWSER2_ALL5_AND_SOURCE_INVARIANT_RETAINED35',qualification_commit=head,
        fresh_cases=2,retained_cases=35,candidate_case_coverage=37,retained_cases_are_not_fresh=True,used_refusal_census=census,
        production_go=False,independent_acceptance=False)

def gate(directory,head):
    p=load('focused_final_typed_originals',PARENT/'parents.py')
    proof=load('focused_final_actual_retention',HERE/'admission.py').retained()
    read=lambda name:p.strict((directory/name).read_bytes())
    return validate(read(MAIN),read('T3_PACKAGE_INSTALL.json'),read('T3_BACKUP_RESTORE_DRILL.json'),
        read('S05_FOLLOWUP_SUPERVISION.json'),head,proof,p)

if __name__=='__main__':
    head=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    value=gate(ROOT/'cp6-proof/t3',head)
    (ROOT/'cp6-proof/t3/S05_FOLLOWUP_FINAL_GATE.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value))
