"""Own combined runtime evidence is required before any Auth/browser DB use."""
from hashlib import sha256
import json

CHILDREN=frozenset(('COMBINED_UNCHANGED_CHILD_VISIBILITY','COMBINED_NULL_SNAPSHOT_REFUSAL_AND_RECOVERY',
    'COMBINED_UNCHANGED_NATIVE20','COMBINED_INDEPENDENT_SIGNATURE','COMBINED_CURRENT_PUBLIC_ACTUAL_CRON',
    'COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS','COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON'))


def gate(config):
    proof=config.get('accepted_combined')
    if config.get('allow_database_execution')is not True or not proof or proof.get('status')!='PASS':
        raise ValueError('COMBINED_BROWSER_ACTUAL_COMBINED_RUNTIME_REQUIRED')
    assert config['production_go']is config['independent_acceptance']is False
    return proof


def bind(proof,raw,package_raw):
    for value,size,digest in ((raw,proof['bytes'],proof['sha256']),
        (package_raw,proof['package_bytes'],proof['package_sha256'])):
        if len(value)!=size or sha256(value).hexdigest()!=digest:
            raise ValueError('COMBINED_BROWSER_ORIGINAL_BYTES_CHANGED')
    return json.loads(raw),json.loads(package_raw)


def accepted(proof,raw,package_raw,expected_source,current_installation):
    value,package=bind(proof,raw,package_raw)
    assert value['qualification_commit']==proof['head'] and value['status']=='PASS'
    assert package['gate']=={key:True for key in ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')}
    assert value['source_declaration']['qualification']==expected_source
    assert value['source_declaration']['current_installation']==current_installation
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal',
        'baseline_advisors_equal','used_guard_refused_before_DDL','actual_cron_claim','required_case_ids_pass',
        'combined_component_qualified','native20_repeated_unchanged'):
        assert value[key]is True,key
    assert value['production_go']is value['independent_acceptance']is value['default_adopted']is False
    assert value['full_combined_final_qualification']is value['performance_qualification']is False
    assert value['formal_CP7C_started']is value['real_Auth_browser_claim']is False
    assert set(value['committed'])==set(expected_source['case_ids']) and len(value['committed'])==1
    group=next(iter(value['committed'].values()));cases=group['cases']
    assert group['status']=='PASS' and set(cases)==CHILDREN
    assert group['actual_combined_installation']is True
    assert group['actual_minute_cron_groups']==2 and group['unchanged_native_cases']==20
    assert group['factory_current_public_jobs_completed']is group['used_guard_refused_before_DDL']is True
    assert group['real_Auth_browser_claim']is group['full_combined_final_qualification']is False
    for case in cases.values():
        assert case['status']=='PASS'
        restored=case['installed_baseline_restoration']
        assert restored['all22_all_rows_all_sequences_roles_exact']is restored['complete_database_dump_restored']is True
        assert restored['unexpected_catalog_change']is False and not restored.get('guard_error')
    assert cases['COMBINED_UNCHANGED_CHILD_VISIBILITY']['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    native=cases['COMBINED_UNCHANGED_NATIVE20']['native']
    assert native['status']=='PASS' and native['counts']=={'PASS':20} and len(native['cases'])==20
    assert native['complete_boundary_restored']is True
    assert all(case['status']=='PASS'and case['full_boundary_restored']is True for case in native['cases'].values())
    for key in ('COMBINED_CURRENT_PUBLIC_ACTUAL_CRON','COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON'):
        cron=cases[key]
        for name in ('report_and_collected_book_signatures_equal','all_runs_recorded',
            'schedules_removed_and_unrelated_jobs_unchanged','same_UUID_no_second_effect',
            'official_sections_and_metrics_exact','independent_book_signature','unknown_never_zero'):
            assert cron[name]is True,(key,name)
        assert cron['observed_finance_state']=='READY'
        assert len(cron['observed_job_states'])==2 and set(cron['observed_job_states'].values())=={'DONE'}
        assert cron['cron_runs'] and all(row['status']=='succeeded'and row['end']is not None for row in cron['cron_runs'])
        assert cron['page_or_test_ticks']==0 and cron['test_schedule_override']is None
    pairs=cases['COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS']['pairs']
    assert set(pairs)=={'SMALL','PRICE_PERCENT','FACTORY_1200X3'}
    assert all(pair['status']=='PASS'and pair['entire_official_report_equal_except_captured_at']is True for pair in pairs.values())
    factory=cases['COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON']
    assert factory['exact_1200_commercial_skus_three_sizes']is factory['factory_native_finance_qualified']is True
    return value,dict(head=proof['head'],original_sha256=proof['sha256'],package_sha256=proof['package_sha256'],
        all_seven_combined_groups_and_restorations=True,Native20=True,actual_cron_groups=2,
        factory1200x3=True,real_Auth_browser_still_required=True,production_go=False,independent_acceptance=False)
