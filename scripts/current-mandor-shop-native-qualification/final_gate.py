"""Gate six actual Native cases, original observations and owning restoration.

This reader never connects to ERP. It cannot accept a prepared parent, partial
run, synthetic bundle, or counts borrowed from the accepted Afui qualification.
"""
from hashlib import sha256
from pathlib import Path,PurePosixPath
import gzip,importlib.util,json,re,subprocess,sys
import admission

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN='CP7_FG_MANDOR_NATIVE6.json'
RAW='CP7_FG_MANDOR_NATIVE6_STRICT.json'
CASE='FG_MANDOR_NATIVE6_SELECTED_WEEK_PARTIAL_RELEASE_REVERSE_REFUSALS_STORE'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def original(p,directory,reference):
    name=reference.get('path');parts=PurePosixPath(name).parts if type(name)is str else ()
    if(len(parts)!=2 or parts[0]!='MANDOR_NATIVE_ORIGINALS' or '\\'in name
        or re.fullmatch(r'MANDOR_(NATIVE6|COMMITTED_USE)_[0-9]{4}_(REPLAY|REFUSAL)_(BEFORE|AFTER)\.json\.gz',parts[-1])is None):
        raise ValueError('MANDOR_GATE_FIXED_COMPLETE_ORIGINAL_PATH')
    path=directory.joinpath(*parts)
    if path.is_symlink()or path.parent.is_symlink():raise ValueError('MANDOR_GATE_ORIGINAL_SYMLINK_REFUSED')
    packed=path.read_bytes();p.exact(pin(packed),reference['compressed'],'MANDOR_GATE_COMPLETE_COMPRESSED_ORIGINAL')
    raw=gzip.decompress(packed);p.exact(pin(raw),reference['raw'],'MANDOR_GATE_COMPLETE_RAW_ORIGINAL')
    p.fields(reference,dict(complete_actual22_data_and_sequences=True),'MANDOR_GATE_UNPROJECTED_OBSERVATIONS')
    value=p.strict(raw)
    p.exact(set(value),{'actual_all22','full_data_and_sequences'},'MANDOR_GATE_FULL_ORIGINAL_GROUPS')
    if len(value['actual_all22'])!=22:raise ValueError('MANDOR_GATE_ALL_TWENTYTWO_GROUPS_REQUIRED')
    return reference['raw'],value


def observations(p,directory,value):
    """Resolve every replay/refusal original, rather than trusting a PASS label."""
    count=0;assets={}
    def walk(row):
        nonlocal count
        if type(row)is dict:
            if 'before_original'in row or 'after_original'in row:
                before,a=original(p,directory,row['before_original']);after,b=original(p,directory,row['after_original'])
                p.exact(before,after,'MANDOR_GATE_ZERO_EFFECT_COMPLETE_ORIGINAL_BYTES')
                p.exact(a,b,'MANDOR_GATE_ZERO_EFFECT_COMPLETE_CATALOGUE_ROWS_SEQUENCES')
                for key in('before_original','after_original'):
                    reference=row[key];name=reference['path']
                    if name in assets:p.exact(assets[name],reference,'MANDOR_GATE_ORIGINAL_REFERENCE_UNCHANGED')
                    assets[name]=reference
                count+=1
            for child in row.values():walk(child)
        elif type(row)is list:
            for child in row:walk(child)
    walk(value)
    return count,assets


def gate(directory,head):
    import qualification
    raw_parent,parent=qualification.actual_parent()  # Before artifact/ERP imports.
    p=load('mandor_exact_retained_typed_packet_reader',ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
    import cases
    docs={name:p.strict((directory/name).read_bytes())for name in(MAIN,RAW,'T3_PACKAGE_INSTALL.json',
        'T3_BACKUP_RESTORE_DRILL.json','MANDOR_RUNTIME_SUPERVISION.json')}
    main,native,package,backup,owned=[docs[name]for name in(MAIN,RAW,'T3_PACKAGE_INSTALL.json',
        'T3_BACKUP_RESTORE_DRILL.json','MANDOR_RUNTIME_SUPERVISION.json')]
    p.fields(main,dict(status='PASS',qualification_commit=head,required_case_ids=[CASE],required_case_ids_pass=True,
        actual_Native_cases=6,actual_Auth_HTTP_cases=0,actual_two_session_races=0,actual_browser_cases=0,
        actual_business_cases=6,real_Auth_HTTP_qualified=False,real_Auth_browser_claim=False,
        baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
        baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        full_combined_final_qualification=False,production_go=False,independent_acceptance=False),
        'MANDOR_GATE_SIX_CURRENT_CASES_AND_COMPLETE_RESTORATION')
    p.exact(set(main['committed']),{CASE},'MANDOR_GATE_ONE_CURRENT_COMPONENT')
    part=main['committed'][CASE]
    p.fields(part,dict(status='PASS',actual_Native_cases=6,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        actual_browser_cases=0,strict_case_ids=list(cases.IDS),used_guard_refused_before_DDL=True,
        actual_Mandor_Auth_browser_race_and_return_correction_acceptance_pending=True,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False),
        'MANDOR_GATE_NATIVE_ONLY_COMPONENT')
    p.fields(native,dict(status='PASS',planned_case_ids=list(cases.IDS),counts={'PASS':6},missing=[],
        complete_boundary_restored=True,production_go=False,independent_acceptance=False),'MANDOR_GATE_ORIGINAL_STRICT_NATIVE6')
    p.exact(set(native['cases']),set(cases.IDS),'MANDOR_GATE_EVERY_ACTUAL_NEW_CASE_PRESENT')
    assets={};pairs=0
    for name,row in native['cases'].items():
        p.fields(row,dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True,
            new_financial_findings={},actual_Auth_HTTP_cases=0,actual_browser_cases=0,actual_two_session_cases=0,
            owning_full_restore_and_all_five_required=True,production_go=False,independent_acceptance=False),
            'MANDOR_GATE_REAL_CASE_BOUNDARY_AND_FINANCIAL_FINDINGS:'+name)
        count,found=observations(p,directory,row)
        if count<1:raise ValueError('MANDOR_GATE_CASE_REPLAY_OR_REFUSAL_ORIGINAL_REQUIRED:'+name)
        pairs+=count;assets.update(found)
    for reference in part['strict_group_originals']:
        if reference['name']==RAW:p.exact(pin((directory/RAW).read_bytes()),{k:reference[k]for k in('bytes','sha256')},'MANDOR_GATE_FIRST_STRICT_ORIGINAL')
    if not any(r['name']==RAW for r in part['strict_group_originals']):raise ValueError('MANDOR_GATE_FIRST_STRICT_REPORT_REQUIRED')
    used=part['separate_committed_Native_use']
    p.fields(used,dict(status='ACTUAL_MANDOR_INVOICE_OFFSET_AND_NET_PAYROLL_COMMITTED',native_case_credit=0,
        actual_used_inverse_error='MANDOR_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE',used_guard_before_DDL=True),
        'MANDOR_GATE_ACTUAL_COMMITTED_USE_WITHOUT_EXTRA_CASE_CREDIT')
    count,found=observations(p,directory,used)
    if count<2:raise ValueError('MANDOR_GATE_COMMITTED_USE_REPLAY_AND_USED_REFUSAL_ORIGINALS_REQUIRED')
    pairs+=count;assets.update(found)
    p.exact(package['gate'],p.GATES,'MANDOR_GATE_ALL_FIVE_ACTUAL_PACKAGE_GATES')
    identity=package['run_identity'];run_id=identity['run_id']
    if type(run_id)is not str or re.fullmatch('[1-9][0-9]*',run_id)is None:raise ValueError('MANDOR_GATE_ACTUAL_RUN_ID_REQUIRED')
    p.fields(identity,dict(tool_head=head,github_sha=head,run_attempt='1'),'MANDOR_GATE_ONE_OWNING_CANDIDATE')
    p.fields(owned,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=head,github_run_id=run_id,
        github_run_attempt='1',worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,
        process_group_empty=True,process_tree_empty=True,signals=[],actual_case_credit=0,production_go=False,
        job_budget_seconds=21600,work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600),
        'MANDOR_GATE_OWNED_WORKER_COMPLETELY_REAPED_WITH_RETAINED_BUDGETS')
    p.fields(backup,dict(status='RESTORED_IDENTICAL'),'MANDOR_GATE_COMPLETE_BACKUP_DRILL')
    if not backup['checks']or any(type(v)is not bool or not v for v in backup['checks'].values()):
        raise ValueError('MANDOR_GATE_EVERY_TYPED_BACKUP_CHECK_REQUIRED')
    p.exact(backup['data']['differ'],{},'MANDOR_GATE_BACKUP_NO_ROW_DIFFERENCE')
    fence=load('mandor_final_packet_import_DB_fence',qualification.FROZEN/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read():
        engine=qualification.runtime()
        with engine.inherited_admission.parent_scope():sources=engine.admitted()
    p.exact(main['source_declaration'],sources,'MANDOR_GATE_COMPLETE_CURRENT_NATURAL_SOURCE_GRAPH')
    return dict(status='CURRENT_MANDOR_NATIVE6_AND_ALL5_PASS_AUTH_RACE_BROWSER_CORRECTION_PENDING',head=head,
        actual_Native_cases=6,actual_business_cases=6,actual_Auth_HTTP_cases=0,actual_two_session_races=0,actual_browser_cases=0,
        accepted_parent=dict(head=parent['head'],tree=parent['tree'],run_id=parent['run_id'],original=pin(raw_parent)),
        original_observation_pairs=pairs,raw_original_assets=assets,package_all_five=True,
        actual_Mandor_Auth_browser_race_and_return_correction_acceptance_pending=True,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    value=gate(ROOT/'cp6-proof/t3',head)
    (ROOT/'cp6-proof/t3/MANDOR_NATIVE6_FINAL_GATE.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value))
