"""Current original Native30 and whole package gates; no global acceptance."""
from pathlib import Path
import importlib.util,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN='CP7_CURRENT_COMPLETE_D1_E_NATIVE30.json'
RAW='CP7_CURRENT_COMPLETE_D1_E_NATIVE30_CASES.json'
CASE='CURRENT_COMPLETE_D1_E_NATIVE30'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def gate(directory,head):
    load('complete_DE_actual_parent_before_any_report_read',HERE/'admission.py').parent_receipt()
    p=load('complete_DE_original_typed_actual_report_gate',
        ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    source=load('complete_DE_original_business_source_ids',HERE/'native_business.py').source_controls()
    ids=source['D1_case_ids']+source['E_case_ids']
    main=p.strict((directory/MAIN).read_bytes());raw=p.strict((directory/RAW).read_bytes())
    package=p.strict((directory/'T3_PACKAGE_INSTALL.json').read_bytes())
    supervised=load('complete_DE_own_supervision_receipt',HERE/'runtime_controls.py').receipt(p,
        p.strict((directory/'DE_RUNTIME_SUPERVISION.json').read_bytes()),head,package['run_identity']['run_id'])
    backup=p.strict((directory/'T3_BACKUP_RESTORE_DRILL.json').read_bytes())
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids=[CASE],required_case_ids_pass=True,
        actual_Native_cases=30,actual_browser_cases=0,actual_business_cases=30,actual_Auth_HTTP_cases=0,
        actual_two_session_races=0,retained_permanent6_fresh_case_credit=0,real_Auth_browser_claim=False,
        real_Auth_HTTP_qualified=False,baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,
        cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        production_go=False,independent_acceptance=False),'COMPLETE_DE_ACTUAL_NATIVE30_AND_FULL_RESTORE')
    p.exact(set(main['committed']),{CASE},'COMPLETE_DE_ONE_CURRENT_COMPONENT')
    part=main['committed'][CASE]
    p.fields(part,dict(status='PASS',business_counts={'PASS':30},actual_Native_cases=30,actual_D1_cases=13,
        actual_E_cases=17,actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        real_Auth=False,reader_remains_installed=True,retained_permanent6_fresh_case_credit=0,
        original_business_callback_changes=0,used_guard_refused_before_DDL=True,D_complete=False,E_complete=False,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False),
        'COMPLETE_DE_NO_RETAINED_OR_GLOBAL_OR_AUTH_CREDIT')
    p.exact(raw,part['native'],'COMPLETE_DE_RAW_NATIVE30_EQUALS_EMBEDDED')
    p.fields(raw,dict(status='PASS',counts={'PASS':30},planned_case_ids=ids,missing=[],
        final={key:'PASS'for key in ids},complete_boundary_restored=True),
        'COMPLETE_DE_ORIGINAL_CURRENT_THIRTY_STRICT_CASES')
    p.exact(list(raw['cases']),ids,'COMPLETE_DE_EXACT_ORIGINAL_CASE_ORDER')
    if raw.get('business_day_retried')or raw.get('business_day_first_attempt'):
        raise ValueError('COMPLETE_DE_SINGLE_BUSINESS_DAY_ATTEMPT_REQUIRED')
    for name,row in raw['cases'].items():
        p.fields(row,dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True,
            session_leaks=dict(advisory_locks=0,advisory_lock_keys=[],other_sessions=[])),
            'COMPLETE_DE_ORIGINAL_STRICT_CASE:'+name)
        if row.get('business_day_rollover'):raise ValueError('COMPLETE_DE_CASE_ROLLED_OVER:'+name)
    used=part['separate_committed_E_witness']
    p.fields(used,dict(status='NATIVE_E_CORRECTION_COMMITTED',E_Native_case_credit=0,real_Auth=False,
        actual_used_inverse_error='COMPLETE_CREDIT_DE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE',
        same_original_money_event_and_journal_preserved_by_unchanged_E_post=True,
        original_source_sale_and_payment_immutable=True,physical_HPP_cash_and_cost_GL_unchanged=True),
        'COMPLETE_DE_ACTUAL_ORIGINAL_COMMITTED_E_USE')
    p.exact(used['before'],used['after'],'COMPLETE_DE_USED_INVERSE_RAW_NO_EFFECT')
    if len(used['before']['actual_all22'])!=22:raise ValueError('COMPLETE_DE_COMPLETE_RAW22_REQUIRED')
    p.exact(package['gate'],p.GATES,'COMPLETE_DE_ALL_FIVE_ACTUAL_PACKAGE_GATES')
    p.fields(package['run_identity'],dict(tool_head=head,github_sha=head,run_attempt='1'),
        'COMPLETE_DE_EXACT_OWNING_PACKAGE')
    p.fields(backup,dict(status='RESTORED_IDENTICAL'),'COMPLETE_DE_ACTUAL_BACKUP_DRILL')
    if not backup['checks']or any(type(v)is not bool or not v for v in backup['checks'].values()):
        raise ValueError('COMPLETE_DE_ALL_TYPED_BACKUP_CHECKS_REQUIRED')
    p.exact(backup['data']['differ'],{},'COMPLETE_DE_BACKUP_NO_ROW_DIFFERENCE')
    return dict(status='CURRENT_COMPLETE_D1_E_NATIVE30_AND_ALL5_PASS',head=head,actual_fresh_cases=30,
        retained_permanent6_fresh_case_credit=0,actual_browser_cases=0,actual_Auth_HTTP_cases=0,
        actual_two_session_races=0,D_complete=False,E_complete=False,runtime_supervision=supervised,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    load('complete_DE_actual_parent_before_final_report_gate',HERE/'admission.py').parent_receipt()
    value=gate(ROOT/'cp6-proof/t3',subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip())
    (ROOT/'cp6-proof/t3/DE30_FINAL_GATE.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
