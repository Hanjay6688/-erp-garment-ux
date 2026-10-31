"""Require all fresh cases and the complete outer five gates from one run."""
from pathlib import Path
import importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN='CP7_CURRENT_S03_SKU_S05_NATIVE31_BROWSER6.json'

def gate(directory,head):
    spec=importlib.util.spec_from_file_location('joined_final_typed_originals',HERE/'parents.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    main=p.strict((directory/MAIN).read_bytes());package=p.strict((directory/'T3_PACKAGE_INSTALL.json').read_bytes())
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids_pass=True,
        actual_Native_cases=31,actual_browser_cases=6,actual_business_cases=37,actual_Auth_HTTP_cases=0,
        actual_two_session_races=0,baseline_full22_all_rows_all_sequences_equal=True,
        restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
        used_guard_refused_before_DDL=True,production_go=False,independent_acceptance=False),'ACTUAL_COMPOSITE_AND_COMPLETE_RESTORE')
    p.exact(set(main['committed']),{'CURRENT_S03_SKU_S05_NATIVE31_BROWSER6'},'ONE_ACTUAL_COMPOSITE')
    part=main['committed']['CURRENT_S03_SKU_S05_NATIVE31_BROWSER6']
    p.fields(part,dict(status='PASS',business_counts={'PASS':37},actual_Native_cases=31,actual_browser_cases=6,
        retained_SKU27_fresh_case_credit=0,global_writer_or_permission_or_lock_closure=False,
        Afui_positive_HPP_zero_reimbursement_coverage=False),'NO_RETAINED_OR_UNPROVEN_CREDIT')
    if len(part['business_cases'])!=37 or any(row['status']!='PASS'for row in part['business_cases'].values()):
        raise ValueError('JOIN_37_UNIQUE_CURRENT_FRESH_CASES_REQUIRED')
    for name,count in [('fresh_S03_browser4',4),('fresh_S05_browser2',2)]:
        browser=part[name]['browser']
        p.fields(browser,dict(status='RUN_COMPLETE',counts={'PASS':count},real_auth=True,jwt_signed_by_runtime=False,
            host_exit=0,host_status='RUN_COMPLETE',console_errors=0,database_remaining=0,
            auth_cleanup_failures=[],session_leaks=[],auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)),name)
        if browser.get('cleanup_failures')or browser.get('business_day_retried')or browser.get('business_day_first_attempt'):
            raise ValueError('JOIN_CURRENT_SINGLE_ATTEMPT_AND_AUTH_CLEANUP_REQUIRED')
    p.exact(package['gate'],p.GATES,'ACTUAL_ALL5')
    p.fields(package['run_identity'],dict(tool_head=head,github_sha=head,run_attempt='1'),'EXACT_CURRENT_PACKAGE')
    return dict(status='CURRENT_JOIN_NATIVE31_BROWSER6_AND_ALL5_PASS',qualification_commit=head,
        actual_fresh_cases=37,retained_SKU27_fresh_case_credit=0,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    result=gate(ROOT/'cp6-proof/t3',subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip())
    (ROOT/'cp6-proof/t3/JOIN_FINAL_GATE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
