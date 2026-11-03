"""Require nineteen actual current-parent money cases and the complete owning recovery.

Reads exact Originals, never connects to ERP, never counts old parent cases
as fresh and never accepts the prepared/source-only report as a qualification.
"""
from pathlib import Path
import ast,importlib.util,json,re,subprocess
from money_execution_bindings import admission
from money_execution_bindings import component
import money_gate_support as money_gate
import money_current_parent_runtime as runtime

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN=runtime.LABEL+'.json'
NATIVE=component.LABEL+'.json'
PREFLIGHT=component.LABEL+'_PREFLIGHT.json'
SUPERVISION='SKU_CURRENT_PARENT_MONEY_RUNTIME_SUPERVISION.json'


def typed_reader():
    path=ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py'
    spec=importlib.util.spec_from_file_location('money_current_parent_exact_typed_reader',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def case_ids():return money_gate.case_ids(runtime,admission)


def validate(p,docs,head,ids):
    main,native,package,backup,owned=[docs[n]for n in(MAIN,NATIVE,'T3_PACKAGE_INSTALL.json','T3_BACKUP_RESTORE_DRILL.json',SUPERVISION)]
    if any(value.get('synthetic_receipt_not_an_actual_qualification')is True for value in(main,native,package,backup,owned)):
        raise ValueError('SKU_COMPOSITE_GATE_SYNTHETIC_PACKET_REFUSED')
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids=[component.CASE],
        required_case_ids_pass=True,actual_Native_cases=19,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        actual_browser_cases=0,actual_business_cases=19,real_Auth_HTTP_qualified=False,real_Auth_browser_claim=False,
        qualification_scope='CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY',baseline_full22_all_rows_all_sequences_equal=True,
        restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
        used_guard_refused_before_DDL=True,full_combined_final_qualification=False,
        production_go=False,independent_acceptance=False),'SKU_COMPOSITE_GATE_FRESH_NATIVE19_AND_FULL_RESTORE')
    p.exact(set(main['committed']),{component.CASE},'SKU_COMPOSITE_GATE_ONE_CURRENT_COMPONENT')
    part=main['committed'][component.CASE]
    money_gate.validate_preflight(p,part,docs[PREFLIGHT])
    p.fields(part,dict(status='PASS',actual_Native_cases=19,actual_Auth_browser=False,actual_two_session_races=0,
        qualification_scope='NATIVE_COMPONENT_ONLY',used_guard_refused_before_DDL=True,
        failure_evidence_preserved=True,acceptance_requires_complete_outer_restore_and_package=True,
        physical_FIFO_preserved=True,economic_valuation='SKU_LOCATION_GRADE_MOVING_AVERAGE_WITH_SOURCE_CENTS',
        production_go=False,independent_acceptance=False),'SKU_COMPOSITE_GATE_COMPONENT_NINETEEN_ACTUAL_CASES')
    p.exact(part['native'],native,'SKU_COMPOSITE_GATE_COMPLETE_NATIVE_ORIGINAL_NOT_PROJECTED')
    p.fields(native,dict(status='PASS',planned_case_ids=ids,counts={'PASS':19},missing=[],
        complete_boundary_restored=True,production_go=False,independent_acceptance=False),
        'SKU_COMPOSITE_GATE_ALL_NINETEEN_ORIGINAL_CASES')
    p.exact(set(native['cases']),set(ids),'SKU_COMPOSITE_GATE_EXACT_CURRENT_CASE_SET')
    p.exact(native['final'],{name:'PASS'for name in ids},'SKU_COMPOSITE_GATE_ALL_CASES_FINAL_PASS')
    for name,row in native['cases'].items():
        p.fields(row,dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True),
            'SKU_COMPOSITE_GATE_EACH_CASE_RESTORED:'+name)
        p.exact(row['session_leaks'],dict(advisory_locks=0,advisory_lock_keys=[],other_sessions=[]),
            'SKU_COMPOSITE_GATE_EACH_CASE_NO_LOCK_OR_SESSION_LEAK:'+name)
    p.fields(main['focused_preuse_removal'],dict(used_guard_before_DDL=True),
        'SKU_COMPOSITE_GATE_UNUSED_INVERSE_EXECUTED')
    p.exact(package['gate'],p.GATES,'SKU_COMPOSITE_GATE_ALL_FIVE_ACTUAL_PACKAGE_GATES')
    identity=package['run_identity'];run_id=identity['run_id']
    if type(run_id)is not str or re.fullmatch('[1-9][0-9]*',run_id)is None:
        raise ValueError('SKU_COMPOSITE_GATE_ACTUAL_RUN_ID')
    p.fields(identity,dict(tool_head=head,github_sha=head,run_attempt='1'),'SKU_COMPOSITE_GATE_ONE_OWNING_CANDIDATE')
    p.fields(owned,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=head,github_run_id=run_id,
        github_run_attempt='1',worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,
        process_group_empty=True,process_tree_empty=True,signals=[],actual_case_credit=0,production_go=False,
        job_budget_seconds=21600,work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600),
        'SKU_COMPOSITE_GATE_WORKER_REAPED_AND_FULL_RECOVERY_BUDGETS')
    p.fields(backup,dict(status='RESTORED_IDENTICAL'),'SKU_COMPOSITE_GATE_COMPLETE_BACKUP_DRILL')
    if not backup['checks']or any(type(v)is not bool or not v for v in backup['checks'].values()):
        raise ValueError('SKU_COMPOSITE_GATE_EVERY_TYPED_BACKUP_CHECK')
    p.exact(backup['data']['differ'],{},'SKU_COMPOSITE_GATE_NO_RESTORE_ROW_DIFFERENCE')
    return dict(run_id=run_id,actual_Native_cases=19,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        actual_two_session_races=0,prior_parent_cases_not_counted_as_fresh=True,
        package_all_five=True,production_go=False,independent_acceptance=False)


def gate(directory,head):
    parent_raw,sku_raw,receipt=runtime.actual_inputs()
    p=typed_reader();ids=case_ids();names=(MAIN,NATIVE,PREFLIGHT,'T3_PACKAGE_INSTALL.json','T3_BACKUP_RESTORE_DRILL.json',SUPERVISION)
    raw={}
    for name in names:
        path=directory/name
        if path.is_symlink()or directory.is_symlink():raise ValueError('SKU_COMPOSITE_GATE_ORIGINAL_SYMLINK')
        raw[name]=path.read_bytes()
    docs={name:p.strict(value)for name,value in raw.items()}
    result=validate(p,docs,head,ids)
    refs=docs[MAIN]['committed'][component.CASE]['strict_group_originals']
    native_refs=[r for r in refs if r['name']==NATIVE]
    if len(native_refs)!=1:raise ValueError('SKU_COMPOSITE_GATE_ONE_FIRST_NATIVE_ORIGINAL_REQUIRED')
    p.exact({k:native_refs[0][k]for k in('bytes','sha256')},admission.pin(raw[NATIVE]),
        'SKU_COMPOSITE_GATE_EXACT_FIRST_NATIVE_BYTES')
    fence=runtime.load('money_current_parent_final_packet_import_DB_fence',
        runtime.FROZEN_AFUI/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read():
        engine=runtime.runtime()
        with engine.inherited_admission.parent_scope():sources=engine.admitted()
    p.exact(docs[MAIN]['source_declaration'],sources,'SKU_COMPOSITE_GATE_COMPLETE_NATURAL_SOURCE_GRAPH')
    return dict(status='CURRENT_MANDOR_PARENT_SKU_MONEY_NATIVE19_AND_ALL5_PASS',head=head,**result,
        accepted_sources=receipt,parent_root=admission.pin(parent_raw),SKU_root=admission.pin(sku_raw),
        originals={n:admission.pin(v)for n,v in raw.items()},
        concurrent_current_permission_Auth_browser_followups_pending=True,full_combined_final_qualification=False)


if __name__=='__main__':
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    value=gate(ROOT/'cp6-proof/t3',head)
    path=ROOT/'cp6-proof/t3/SKU_CURRENT_PARENT_MONEY_FINAL_GATE.json'
    with path.open('x')as stream:stream.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value,sort_keys=True))
