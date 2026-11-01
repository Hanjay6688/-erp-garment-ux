"""One actual permanent delta, raw used refusal, Auth and full package gates."""
from pathlib import Path
import importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN='CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2.json'
CASE='PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2'


def supervision(p,value,head,run_id):
    p.fields(value,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=head,
        github_run_id=run_id,github_run_attempt='1',worker_exit=0,deadline_reached=False,
        external_signal=None,orphaned_child=False,process_group_empty=True,process_tree_empty=True,
        signals=[],actual_case_credit=0,production_go=False,job_budget_seconds=21600,
        work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600),
        'PERMANENT_COMPLETE_OWNED_PROCESS_REAP_BEFORE_DATABASE_REMOVAL')
    return dict(status='PERMANENT_SUPERVISION_ACCEPTED',actual_case_credit=0)


def gate(directory,head):
    spec=importlib.util.spec_from_file_location('permanent_typed_actual_report_gate',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    main=p.strict((directory/MAIN).read_bytes());package=p.strict((directory/'T3_PACKAGE_INSTALL.json').read_bytes())
    supervised=supervision(p,p.strict((directory/'PERMANENT_RUNTIME_SUPERVISION.json').read_bytes()),
        head,package['run_identity']['run_id'])
    backup=p.strict((directory/'T3_BACKUP_RESTORE_DRILL.json').read_bytes())
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids_pass=True,
        actual_Native_cases=0,actual_browser_cases=2,actual_business_cases=2,
        retained_Native_cases=4,retained_cases_are_not_fresh=True,candidate_case_coverage=6,
        financial_groups_rerun=False,source_invariant_reuse=True,prior_runs_aggregated=True,
        actual_Auth_HTTP_cases=0,actual_two_session_races=0,retained_join37_fresh_case_credit=0,
        baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
        baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        production_go=False,independent_acceptance=False),'ACTUAL_PERMANENT_DELTA_AND_COMPLETE_RESTORE')
    p.exact(set(main['committed']),{CASE},'ONE_ACTUAL_PERMANENT_DELTA')
    part=main['committed'][CASE]
    p.fields(part,dict(status='PASS',business_counts={'PASS':2},actual_Native_cases=0,actual_browser_cases=2,
        retained_Native_cases=4,retained_cases_are_not_fresh=True,candidate_case_coverage=6,
        financial_groups_rerun=False,source_invariant_reuse=True,prior_runs_aggregated=True,
        retained_join37_fresh_case_credit=0,permanent_reader_remains_installed=True,
        global_writer_or_permission_or_lock_closure=False,Afui_positive_HPP_zero_reimbursement_coverage=False),
        'PERMANENT_DELTA_NO_RETAINED_OR_UNPROVEN_FRESH_CREDIT')
    spec=importlib.util.spec_from_file_location('permanent_exact_retained4_final_gate',HERE/'retained4.py')
    retained=importlib.util.module_from_spec(spec);spec.loader.exec_module(retained)
    reuse=retained.invariant_sources(main['source_declaration']['current_installation'])
    p.exact(part['retained_permanent_financial4'],reuse,'ACTUAL_ROOT_RETAINED4_AND_WHOLE_CURRENT_SOURCE_IDENTITY')
    p.exact(part['retained4_original_admission'],retained.original_admission(),'ACTUAL_FAILED_ORIGINAL_ARCHIVE_ADMITTED_BEFORE_DB')
    p.exact(set(part['business_cases']),set(reuse['missing_case_ids']),'ONLY_TWO_MISSING_BROWSER_CASES_RUN')
    if any(row['status']!='PASS'for row in part['business_cases'].values()):
        raise ValueError('PERMANENT_S05_TWO_FRESH_BROWSER_CASES_REQUIRED')
    p.fields(part['source_connection_release'],dict(cursor_closed=True,connection_closed=True,foreign_backends_terminated=0),
        'OWN_SOURCE_CONNECTION_RELEASED_WITHOUT_TOUCHING_FOREIGN_BACKENDS')
    witness=part['separate_committed_Native_use']
    p.fields(witness,dict(status='NATIVE_BUSINESS_COMMITTED',Native_case_credit=0,
        used_inverse_guard_refused_before_DDL=True,reader_remains_installed=True),'ACTUAL_COMMITTED_USE_NOT_A_TEST_ROW')
    p.exact(witness['before'],witness['after'],'ACTUAL_USED_REFUSAL_ALL22_ROWS_AND_ALL_SEQUENCES')
    if len(witness['before']['actual_all22'])!=22:
        raise ValueError('PERMANENT_S05_COMPLETE_RAW_ALL22_REQUIRED')
    # Financial4 remain the exact Root-validated old cases, never executed here.
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
    return dict(status='CURRENT_PERMANENT_S05_RETAINED4_FRESH_BROWSER2_AND_ALL5_PASS',head=head,
        actual_fresh_cases=2,retained_Native_cases=4,retained_cases_are_not_fresh=True,candidate_case_coverage=6,
        financial_groups_rerun=False,source_invariant_reuse=True,prior_runs_aggregated=True,retained_join37_fresh_case_credit=0,reader_remains_installed=True,
        runtime_supervision=supervised,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    value=gate(ROOT/'cp6-proof/t3',subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip())
    (ROOT/'cp6-proof/t3/PERMANENT_FINAL_GATE.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
