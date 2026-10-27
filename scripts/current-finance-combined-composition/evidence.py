"""The combined product cannot inherit a diagnostic PASS that never happened."""
from hashlib import sha256
import json
CHILDREN={
 'REPORT_BOOK_INDEPENDENT_CANONICAL_SIGNATURE',
 'REPORT_BOOK_UNCHANGED_CHILD_VISIBILITY_COUNTEREXAMPLE',
 'REPORT_BOOK_ASSIGNED_TRANSACTION_NULL_SNAPSHOT_AND_RECOVERY',
 'REPORT_BOOK_UNCHANGED_NATIVE20','REPORT_BOOK_UNCHANGED_ACTUAL_MINUTE_CRON',
 'REPORT_BOOK_SMALL_PRICE_FACTORY_OVERHEAD',
 'UNCHANGED_SINGLE_CHECK_DIAGNOSTIC_WITH_COMPLETE_RESTORATION'}


def gate(config):
    accepted=config.get('accepted_consistency')
    if config.get('allow_database_execution')is not True or not accepted or accepted.get('status')!='PASS':
        raise ValueError('COMBINED_FINANCE_ACTUAL_CONSISTENCY_PASS_REQUIRED')
    return accepted


def accepted(binding,raw,package_raw,expected_source,current_installation):
    for data,size,digest in ((raw,binding['bytes'],binding['sha256']),
        (package_raw,binding['package_bytes'],binding['package_sha256'])):
        if len(data)!=size or sha256(data).hexdigest()!=digest:
            raise ValueError('COMBINED_FINANCE_ORIGINAL_CHANGED')
    value=json.loads(raw);package=json.loads(package_raw)
    assert value['status']=='PASS' and value['qualification_commit']==binding['head']
    assert package['gate']=={k:True for k in ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')}
    assert value['source_declaration']['qualification']==expected_source
    assert value['source_declaration']['current_installation']==current_installation
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal',
        'baseline_advisors_equal','used_guard_refused_before_DDL','actual_cron_claim','required_case_ids_pass'):
        assert value.get(key)is True,'COMBINED_FINANCE_ACCEPTANCE_MISSING:'+key
    assert value['production_go']is value['independent_acceptance']is value['default_adopted']is False
    assert value['performance_qualification']is value['full_combined_final_qualification']is False
    assert set(value['committed'])==set(expected_source['case_ids']) and len(value['committed'])==1
    group=next(iter(value['committed'].values()));cases=group['cases'];first=group['baseline_null_snapshot_counterexample']
    assert group['status']=='PASS' and set(cases)==CHILDREN
    assert first['status']=='INCOMPLETE' and first['error']=='ASSIGNED_TRANSACTION_MUST_NOT_SEAL_MIXED_BOOK'
    assert first['unsafe_ready_observed']is first['mixed_signature_confirmed']is True
    assert first['observed_report_snapshot']is None and first['source_commit_after_early_chunks']is True
    assert first['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    for case in [first,*cases.values()]:
        restored=case['installed_baseline_restoration']
        assert restored['all22_all_rows_all_sequences_roles_exact']is restored['complete_database_dump_restored']is True
        assert restored.get('unexpected_catalog_change')is False
    assert all(c['status']=='PASS' for c in cases.values())
    native=cases['REPORT_BOOK_UNCHANGED_NATIVE20']['native']
    assert native['counts']=={'PASS':20} and native['complete_boundary_restored']is True
    assert cases['REPORT_BOOK_UNCHANGED_ACTUAL_MINUTE_CRON']['report_and_collected_book_signatures_equal']is True
    assert cases['REPORT_BOOK_ASSIGNED_TRANSACTION_NULL_SNAPSHOT_AND_RECOVERY']['fresh_uuid_recovery_ready']is True
    return value,dict(head=binding['head'],original_sha256=binding['sha256'],package_sha256=binding['package_sha256'],
        all_seven_diagnostics_and_full_restores=True,baseline_first_failure_retained=True,
        combined_reader_not_yet_qualified=True,production_go=False,independent_acceptance=False)
