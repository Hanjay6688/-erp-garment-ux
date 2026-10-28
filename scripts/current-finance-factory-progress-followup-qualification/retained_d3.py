"""Bind D3's six PASS groups and exact first factory observation cutoff."""
from hashlib import sha256
import json

CHILDREN=('COMBINED_UNCHANGED_CHILD_VISIBILITY','COMBINED_NULL_SNAPSHOT_REFUSAL_AND_RECOVERY',
    'COMBINED_UNCHANGED_NATIVE20','COMBINED_INDEPENDENT_SIGNATURE','COMBINED_CURRENT_PUBLIC_ACTUAL_CRON',
    'COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS','COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON')


def gate(config):
    proof=config.get('retained_d3')
    if config.get('allow_qualification_execution')is not True or not proof or proof.get('status')!='INCOMPLETE':
        raise ValueError('ACTUAL_D3_FIRST_FACTORY_CUTOFF_REQUIRED')
    assert config['production_go']is config['independent_acceptance']is False
    assert(config['max_wait_seconds'],config['stall_seconds'],config['legacy_wait_seconds'])==(900,150,300)
    return proof


def bind(proof,raw,package):
    for value,size,digest in ((raw,proof['bytes'],proof['sha256']),
        (package,proof['package_bytes'],proof['package_sha256'])):
        assert len(value)==size and sha256(value).hexdigest()==digest,'D3_RETAINED_ORIGINAL_BYTES_CHANGED'
    return json.loads(raw),json.loads(package)


def checked(proof,raw,package_raw,declaration):
    value,package=bind(proof,raw,package_raw)
    assert value['qualification_commit']==proof['head']and value['status']=='INCOMPLETE'
    assert value['source_declaration']==declaration,'D3_COMPLETE_SOURCE_DECLARATION_CHANGED'
    assert package['gate']=={key:key!='writer_runtime'for key in
        ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')}
    for key in('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):
        assert value[key]is True,key
    assert value['production_go']is value['independent_acceptance']is False
    group=next(iter(value['committed'].values()));cases=group['cases'];assert set(cases)==set(CHILDREN)
    assert all(cases[key]['status']=='PASS'for key in CHILDREN[:-1])and cases[CHILDREN[-1]]['status']=='INCOMPLETE'
    for case in cases.values():
        restored=case['installed_baseline_restoration']
        for key in('pre_restore_observation_complete','all22_all_rows_all_sequences_roles_exact','complete_database_dump_restored'):
            assert restored[key]is True,key
        assert restored['unexpected_catalog_change']is False and not restored.get('guard_error')
    assert cases[CHILDREN[0]]['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    native=cases['COMBINED_UNCHANGED_NATIVE20']['native']
    assert native['status']=='PASS'and native['counts']=={'PASS':20}and native['complete_boundary_restored']is True
    assert len(native['cases'])==20 and all(c['status']=='PASS'and c['full_boundary_restored']is True for c in native['cases'].values())
    stream=value['exact_streaming_data_validation']
    assert stream['status']=='PASS'and stream['old_SQLSTATE']=='54000'
    assert stream['large_rows']==1024 and stream['minimum_large_payload_bytes']==307200000
    for key in('old_hashes_equal_before_and_after','actual_old_array_limit_reproduced','duplicate_multiplicity_preserved',
        'temporary_regression_fully_removed','ERP_rows_sequences_and_catalog_definitions_unchanged'):
        assert stream[key]is True,key
    assert stream['excluded_tables']==stream['skipped_rows_or_fields']==0
    assert stream['ordinary_statement_limits_changed']is False
    verification=value['complete_installed_verification']
    assert verification['status']=='EXACT_COMBINED_CONSISTENT_READERS_ALL22'
    assert verification['Native_money_stock_HPP_definitions_unchanged']is True
    assert verification['opening']['original_Native_body_and_metadata_unchanged']is True
    assert verification['opening']['opening_date_and_HPP_arithmetic_unchanged']is True
    pairs=cases['COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS']['pairs']
    assert set(pairs)=={'SMALL','PRICE_PERCENT','FACTORY_1200X3'}
    assert all(pair['status']=='PASS'and pair['entire_official_report_equal_except_captured_at']is True for pair in pairs.values())
    price=pairs['PRICE_PERCENT']['combined_reader'];assert price['observed_nonstable_financial_readers']=={}
    assert 'erp.product_opening_physical_at(uuid,date)'not in price['observed_reader_catalog']
    assert price['observed_reader_catalog']['cp7_finance.read_opening_physical_at_consistent_v1(uuid,date)']['volatility']=='s'
    factory=cases[CHILDREN[-1]]
    assert 300<=factory['elapsed_seconds']<305 and factory['observed_finance_state']=='READY'
    assert len(factory['observed_job_states'])==2 and set(factory['observed_job_states'].values())=={'RUNNING'}
    assert factory['page_or_test_ticks']==0 and factory['test_schedule_override']is None
    assert factory['all_runs_recorded']is factory['schedules_removed_and_unrelated_jobs_unchanged']is True
    assert factory['cron_runs']and all(row['status']=='succeeded'and row['end']is not None for row in factory['cron_runs'])
    jobs=factory['terminal_diagnostics']['job_rows'];assert len(jobs)==2
    assert all(row['state']=='RUNNING'and 0<row['units_done']<row['unit_count']and row['failure_code']is None for row in jobs)
    assert factory['terminal_diagnostics']['manual_steps']==0 and factory['terminal_diagnostics']['job_or_capture_state_changed']is False
    return dict(head=proof['head'],original_sha256=proof['sha256'],retained_whole_status='INCOMPLETE',
        six_groups_and_all_seven_restorations_PASS=True,actual_307MB_regression_PASS=True,
        factory_still_RUNNING_at_300_seconds=True,observed_units=[row['units_done']for row in jobs],
        total_units=[row['unit_count']for row in jobs],whole_not_promoted=True,production_go=False,independent_acceptance=False)
