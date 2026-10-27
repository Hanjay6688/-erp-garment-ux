"""Accept exact restored components; never promote the first failed whole run."""
from hashlib import sha256
import json

COMPONENTS='QUALIFIED_COMPONENTS_FOR_COMBINED_QUALIFICATION'
NATIVE='REPORT_BOOK_UNCHANGED_NATIVE20'
CRON='REPORT_BOOK_UNCHANGED_ACTUAL_MINUTE_CRON'


def gate(config):
    accepted=config.get('accepted_consistency')
    if (config.get('allow_database_execution')is not True or not accepted
        or accepted.get('status')!=COMPONENTS
        or accepted.get('retained84',{}).get('status')!='INCOMPLETE'
        or accepted.get('focused',{}).get('status')!='PASS'):
        raise ValueError('COMBINED_FINANCE_ACTUAL_CONSISTENCY_PASS_REQUIRED')
    assert config['production_go']is config['independent_acceptance']is False
    return accepted


def bound_original(binding,raw,package_raw):
    for data,size,digest in ((raw,binding['bytes'],binding['sha256']),
        (package_raw,binding['package_bytes'],binding['package_sha256'])):
        if len(data)!=size or sha256(data).hexdigest()!=digest:
            raise ValueError('COMBINED_FINANCE_ORIGINAL_CHANGED')
    return json.loads(raw),json.loads(package_raw)


def restored(case):
    proof=case['installed_baseline_restoration']
    assert proof['all22_all_rows_all_sequences_roles_exact']is proof['complete_database_dump_restored']is True
    assert proof['unexpected_catalog_change']is False
    assert not proof.get('guard_error')


def baseline(first):
    assert first['status']=='INCOMPLETE' and first['error']=='ASSIGNED_TRANSACTION_MUST_NOT_SEAL_MIXED_BOOK'
    assert first['unsafe_ready_observed']is first['mixed_signature_confirmed']is True
    assert first['observed_report_snapshot']is None and first['source_commit_after_early_chunks']is True
    assert first['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    restored(first)


def accepted_components(binding,retained_raw,retained_package,focused_raw,focused_package,
                        retained_source,focused_source,current_installation,retained_evidence):
    old,old_package=bound_original(binding['retained84'],retained_raw,retained_package)
    value,package=bound_original(binding['focused'],focused_raw,focused_package)
    old_source=old['source_declaration']
    assert old_source['qualification']==retained_source
    assert old_source['current_installation']==current_installation
    _,retained_summary=retained_evidence.retained(binding['retained84'],retained_raw,retained_package,old_source)
    assert old_package['gate']['writer_runtime']is False and old['status']=='INCOMPLETE'
    assert value['status']=='PASS' and value['qualification_commit']==binding['focused']['head']
    assert package['gate']=={k:True for k in ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')}
    source=value['source_declaration']
    assert source['qualification']==focused_source and source['current_installation']==current_installation
    assert source['unchanged_actual84_source']==old_source and source['retained_actual84']==retained_summary
    assert source['focused_execution_only']is True
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal',
        'baseline_advisors_equal','used_guard_refused_before_DDL','actual_cron_claim','required_case_ids_pass',
        'native20_repeated_unchanged','diagnostic_collection_completed'):
        assert value.get(key)is True,'COMBINED_FINANCE_ACCEPTANCE_MISSING:'+key
    assert value['manual_steps_scope']=='FOCUSED_NATIVE20_CRON1_WITH_COMPLETE_RESTORATION'
    assert value['manual_steps']==0 and value['changed_schedule']is False
    assert value['production_go']is value['independent_acceptance']is value['default_adopted']is False
    assert value['performance_qualification']is value['full_combined_final_qualification']is False
    assert value['formal_CP7C_started']is value['real_Auth_browser_claim']is False
    assert set(value['committed'])==set(focused_source['case_ids']) and len(value['committed'])==1
    assert value['required_case_ids']==focused_source['case_ids']
    group=next(iter(value['committed'].values()));cases=group['cases']
    assert group['status']=='PASS' and set(cases)=={NATIVE,CRON}
    baseline(group['baseline_null_snapshot_counterexample'])
    assert group['first_null_snapshot_counterexample_retained_as_INCOMPLETE']is True
    assert group['candidate_schema_never_projected_into_parent_catalog']is True
    assert group['rollback_only_native_group_not_claimed_as_committed_fixture']is True
    for case in cases.values():
        assert case['status']=='PASS'
        restored(case)
        assert case['installed_baseline_restoration']['parent_inverse_refused_before_DDL']is True
    old_cases=next(iter(old['committed'].values()))['cases']
    native=cases['REPORT_BOOK_UNCHANGED_NATIVE20']['native']
    assert native['status']=='PASS' and native['counts']=={'PASS':20}
    assert native['complete_boundary_restored']is True
    assert set(native['cases'])==set(old_cases[NATIVE]['native']['cases']) and len(native['cases'])==20
    assert all(case['status']=='PASS'and case['full_boundary_restored']is True for case in native['cases'].values())
    assert cases[NATIVE]['original_Native13_plus_capture7_unchanged']is True
    for key in retained_evidence.REPORT_IDS:
        case=native['cases'][key]
        assert case['fixture_preparation']['status']=='PASS'
        assert case['original_report_case_and_oracles_unchanged']is case['fixture_preparation_inside_case_savepoint']is True
    cron=cases[CRON]
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
    return value,dict(status=COMPONENTS,retained84=retained_summary,
        focused_head=binding['focused']['head'],focused_original_sha256=binding['focused']['sha256'],
        focused_package_sha256=binding['focused']['package_sha256'],
        retained_restored_pass_groups=sorted(retained_evidence.PASSED),fresh_focused_pass_groups=sorted(cases),
        all_seven_components_and_full_restores=True,old_whole_status='INCOMPLETE',
        fresh_groups_executed=2,whole_old_result_not_promoted_to_PASS=True,
        combined_reader_not_yet_qualified=True,production_go=False,independent_acceptance=False)
