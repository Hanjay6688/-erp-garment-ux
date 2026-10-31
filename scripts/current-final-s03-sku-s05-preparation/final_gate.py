"""One actual permanent delta, raw used refusal, Auth and full package gates."""
from pathlib import Path
import importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN='CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2.json'
CASE='PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2'


def gate(directory,head):
    spec=importlib.util.spec_from_file_location('permanent_typed_actual_report_gate',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    main=p.strict((directory/MAIN).read_bytes());package=p.strict((directory/'T3_PACKAGE_INSTALL.json').read_bytes())
    backup=p.strict((directory/'T3_BACKUP_RESTORE_DRILL.json').read_bytes())
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids_pass=True,
        actual_Native_cases=4,actual_browser_cases=2,actual_business_cases=6,
        actual_Auth_HTTP_cases=0,actual_two_session_races=0,retained_join37_fresh_case_credit=0,
        baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
        baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        production_go=False,independent_acceptance=False),'ACTUAL_PERMANENT_DELTA_AND_COMPLETE_RESTORE')
    p.exact(set(main['committed']),{CASE},'ONE_ACTUAL_PERMANENT_DELTA')
    part=main['committed'][CASE]
    p.fields(part,dict(status='PASS',business_counts={'PASS':6},actual_Native_cases=4,actual_browser_cases=2,
        retained_join37_fresh_case_credit=0,permanent_reader_remains_installed=True,
        global_writer_or_permission_or_lock_closure=False,Afui_positive_HPP_zero_reimbursement_coverage=False),
        'PERMANENT_DELTA_NO_RETAINED_OR_UNPROVEN_FRESH_CREDIT')
    if len(part['business_cases'])!=6 or any(row['status']!='PASS'for row in part['business_cases'].values()):
        raise ValueError('PERMANENT_S05_SIX_UNIQUE_FRESH_CASES_REQUIRED')
    witness=part['separate_committed_Native_use']
    p.fields(witness,dict(status='NATIVE_BUSINESS_COMMITTED',Native_case_credit=0,
        used_inverse_guard_refused_before_DDL=True,reader_remains_installed=True),'ACTUAL_COMMITTED_USE_NOT_A_TEST_ROW')
    p.exact(witness['before'],witness['after'],'ACTUAL_USED_REFUSAL_ALL22_ROWS_AND_ALL_SEQUENCES')
    if len(witness['before']['actual_all22'])!=22:
        raise ValueError('PERMANENT_S05_COMPLETE_RAW_ALL22_REQUIRED')
    native=part['fresh_permanent_financial4']['native']
    p.fields(native,dict(status='PASS',counts={'PASS':4},complete_boundary_restored=True),'ACTUAL_NATIVE4')
    for row in native['cases'].values():
        p.fields(row,dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True),'ACTUAL_STRICT_FINANCIAL_CASE')
        read=row['permanent_S05_read']
        p.fields(read,dict(status='PASS',reader_remained_installed=True,business_DML=False,all_fields_retained=True),'ACTUAL_PERSISTENT_PUBLIC_READ')
        p.exact(read['before'],read['after'],'EVERY_PERSISTENT_READ_ALL22_ROWS_AND_ALL_SEQUENCES')
    browser=part['fresh_permanent_browser2']['browser']
    p.fields(browser,dict(status='RUN_COMPLETE',counts={'PASS':2},real_auth=True,jwt_signed_by_runtime=False,
        host_exit=0,host_status='RUN_COMPLETE',console_errors=0,database_remaining=0,
        auth_cleanup_failures=[],session_leaks=[],auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)),
        'PERMANENT_NORMAL_APP_DESKTOP_MOBILE_AND_AUTH_RESTORED')
    if browser.get('cleanup_failures')or browser.get('business_day_retried')or browser.get('business_day_first_attempt'):
        raise ValueError('PERMANENT_S05_SINGLE_ATTEMPT_AND_COMPLETE_AUTH_CLEANUP_REQUIRED')
    p.exact(package['gate'],p.GATES,'ACTUAL_PERMANENT_ALL_FIVE_GATES')
    p.fields(package['run_identity'],dict(tool_head=head,github_sha=head,run_attempt='1'),'ACTUAL_CURRENT_OWNING_PACKAGE')
    p.fields(backup,dict(status='RESTORED_IDENTICAL'),'ACTUAL_BACKUP_DRILL')
    if not backup['checks']or any(type(value)is not bool or not value for value in backup['checks'].values()):
        raise ValueError('PERMANENT_S05_ALL_TYPED_BACKUP_CHECKS_REQUIRED')
    return dict(status='CURRENT_PERMANENT_S05_FINANCIAL4_BROWSER2_AND_ALL5_PASS',head=head,
        actual_fresh_cases=6,retained_join37_fresh_case_credit=0,reader_remains_installed=True,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    value=gate(ROOT/'cp6-proof/t3',subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip())
    (ROOT/'cp6-proof/t3/PERMANENT_FINAL_GATE.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
