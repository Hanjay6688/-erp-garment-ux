"""Preserve actual64: real cron PASS, Native factory name error, whole failure."""
from hashlib import sha256
import json


def gate(config):
    if (config.get('allow_database_execution')is not True
        or config.get('retained64',{}).get('status')!='INCOMPLETE'):
        raise ValueError('CONSISTENCY_CORRECTED_ACTUAL64_REQUIRED')


def retained(proof,raw,package_raw,source):
    for value,size,digest in ((raw,proof['bytes'],proof['sha256']),
        (package_raw,proof['package_bytes'],proof['package_sha256'])):
        if len(value)!=size or sha256(value).hexdigest()!=digest:
            raise ValueError('CONSISTENCY_CORRECTED_ACTUAL64_BYTES_CHANGED')
    actual=json.loads(raw);package=json.loads(package_raw)
    assert actual['qualification_commit']==proof['head']=='64de326e819885f6982364a868a3fa11c8b9dd3d'
    assert actual['source_declaration']==source and actual['status']=='INCOMPLETE'
    assert package['gate']==dict(installed=True,primary_unchanged=True,
        backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    assert actual['production_go']is actual['independent_acceptance']is False
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):
        assert actual[key]is True,key
    assert len(actual['committed'])==1
    group=next(iter(actual['committed'].values()));cases=group['cases'];first=group['baseline_null_snapshot_counterexample']
    assert group['status']=='INCOMPLETE'
    assert set(cases)=={'REPORT_BOOK_UNCHANGED_NATIVE20','REPORT_BOOK_UNCHANGED_ACTUAL_MINUTE_CRON'}
    assert first['status']=='INCOMPLETE' and first['error']=='ASSIGNED_TRANSACTION_MUST_NOT_SEAL_MIXED_BOOK'
    assert first['unsafe_ready_observed']is first['mixed_signature_confirmed']is True
    assert first['observed_report_snapshot']is None and first['source_commit_after_early_chunks']is True
    assert first['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    for case in [first,*cases.values()]:
        restored=case['installed_baseline_restoration']
        assert restored['all22_all_rows_all_sequences_roles_exact']is restored['complete_database_dump_restored']is True
        assert restored['unexpected_catalog_change']is False and not restored.get('guard_error')
    native=cases['REPORT_BOOK_UNCHANGED_NATIVE20']
    assert native['status']=='INCOMPLETE' and 'native'not in native
    assert native['error']=="module 'cp7_p21_current_chain_rehearsal_probe' has no attribute 'prepare_attendance_seed'"
    assert 'base.chain.prepare_attendance_seed'in native['traceback'] and 'AttributeError:'in native['traceback']
    cron=cases['REPORT_BOOK_UNCHANGED_ACTUAL_MINUTE_CRON']
    assert cron['status']=='PASS'
    for key in ('report_and_collected_book_signatures_equal','unchanged_actual_minute_cron_oracles',
        'all_runs_recorded','schedules_removed_and_unrelated_jobs_unchanged','same_UUID_no_second_effect',
        'official_sections_and_metrics_exact','independent_book_signature','unknown_never_zero',
        'all22_catalog_exact','Native_money_stock_HPP_unchanged','all_capture_family_counts_exact',
        'unchanged_production_minute_schedule'):
        assert cron[key]is True,key
    assert cron['observed_finance_state']==cron['observed_choice_state']=='READY'
    assert len(cron['observed_job_states'])==2 and set(cron['observed_job_states'].values())=={'DONE'}
    assert cron['cron_runs'] and all(row['status']=='succeeded'and row['end']is not None for row in cron['cron_runs'])
    assert cron['manual_finance_or_operational_steps']==cron['page_or_test_ticks']==0
    assert cron['test_schedule_override']is None
    return actual,dict(head=proof['head'],whole_status='INCOMPLETE',original_sha256=proof['sha256'],
        package_sha256=proof['package_sha256'],actual_cron_component_status='PASS',
        Native20_not_executed=True,Native_factory_missing_helper_name_preserved=True,
        first_mixed_book_counterexample_proven=True,all_boundaries_restored=True,
        whole_old_result_not_promoted_to_PASS=True,production_go=False,independent_acceptance=False)
