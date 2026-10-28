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


def consistent_validation(value,cases):
    stream=value['exact_streaming_data_validation']
    assert stream['status']=='PASS' and stream['old_SQLSTATE']=='54000'
    for key in ('old_hashes_equal_before_and_after','actual_old_array_limit_reproduced',
        'duplicate_multiplicity_preserved','temporary_regression_fully_removed',
        'ERP_rows_sequences_and_catalog_definitions_unchanged'):
        assert stream[key]is True,key
    assert stream['large_rows']==1024 and stream['minimum_large_payload_bytes']==307200000
    assert stream['large_streamed_digest'][0]==1024 and len(stream['large_streamed_digest'][1])==64
    assert stream['excluded_tables']==stream['skipped_rows_or_fields']==0
    assert stream['ordinary_statement_limits_changed']is False
    guard=value['streaming_data_source_guard']
    for key in ('old_jsonb_array_text_hash_algorithm_unchanged',
        'namespace_table_selection_authority_GUC_and_all_sequences_unchanged','qualified_role_oracles_unchanged'):
        assert guard[key]is True,key
    assert guard['excluded_tables_added']==guard['rows_or_fields_skipped']==0
    installed=value['complete_installed_verification']
    assert installed['status']=='EXACT_COMBINED_CONSISTENT_READERS_ALL22'
    assert installed['Native_money_stock_HPP_definitions_unchanged']is True
    assert installed['new_private_functions']==4 and installed['changed_private_functions']==5
    for key in ('private_STABLE_opening_reader','original_Native_body_and_metadata_unchanged',
        'private_HPP_only_one_callee_replaced','opening_date_and_HPP_arithmetic_unchanged'):
        assert installed['opening'][key]is True,key
    assert installed['opening']['new_public_rpcs']==installed['opening']['broadened_role_privileges']==0
    for case in cases.values():
        restored=case['installed_baseline_restoration']
        assert restored['pre_restore_observation_complete']is True and not restored.get('guard_error')
    pairs=cases['COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS']['pairs']
    price=pairs['PRICE_PERCENT']['combined_reader']
    assert price['observed_nonstable_financial_readers']=={}
    observed=price['observed_reader_catalog']
    assert 'erp.product_opening_physical_at(uuid,date)'not in observed
    helper=observed['cp7_finance.read_opening_physical_at_consistent_v1(uuid,date)']
    assert helper['volatility']=='s'and helper['owner']=='postgres'and helper['config']==['search_path=""']
    return dict(actual_307MB_exact_hash_regression=True,complete_observations_and_restorations=True,
        private_STABLE_opening_reader_observed=True,Native_opening_and_HPP_arithmetic_unchanged=True)


def require_factory_progress(proof):
    assert proof['status'] == 'TERMINAL_DONE_AND_READY'
    for key in ('read_only', 'qualification_observation_only', 'actual_terminal_states_observed'):
        assert proof[key] is True, key
    assert proof['total_limit_seconds'] == 900 and proof['no_progress_limit_seconds'] == 150
    assert proof['legacy_limit_seconds'] == 300 and 0 <= proof['elapsed_seconds'] < 900
    assert proof['manual_steps'] == 0 and proof['minute_schedule_changed'] is proof['ordinary_statement_limits_changed'] is False
    states = proof['observed_job_states']
    assert len(states) == 2 and set(states.values()) == {'DONE'}
    assert proof['observed_finance_state'] == 'READY'
    expected = set(states) | {'finance'}
    previous = {}
    elapsed = -1
    changed_at = {}
    for frame in proof['frames']:
        at = frame['elapsed_seconds']
        assert elapsed <= at < 900
        elapsed = at
        rows = frame['jobs']
        assert set(rows) == expected
        for key, row in rows.items():
            assert row[0] in ('RUNNING', 'READY' if key == 'finance' else 'DONE')
            assert type(row[1]) is int and row[1] >= 0
            if key == 'finance' and row[2] is None:
                assert row[0] == 'RUNNING' and row[1] == 0
            else:
                assert type(row[2]) is int and row[1] <= row[2]
                if key == 'finance':
                    assert row[2] >= 2 and (row[0] != 'READY' or row[1] == row[2])
            if key == 'finance' and key in previous and previous[key][2] is not None:
                assert row[2] == previous[key][2]
            if key in previous:
                assert row[1] >= previous[key][1]
            if key not in previous or row != previous[key]:
                changed_at[key] = at
            if row[0] == 'RUNNING':
                assert at - changed_at[key] < 150.002
        previous = rows
    assert previous and previous['finance'][0] == 'READY'
    assert all((previous[key][0] == 'DONE' for key in states))
    if proof['extended_past_legacy_limit']:
        assert 300 <= proof['legacy_cutoff_observation']['elapsed_seconds'] < 900
    else:
        assert proof['elapsed_seconds'] < 300
    return dict(status='PASS_TERMINAL_FACTORY_PROGRESS', elapsed_seconds=proof['elapsed_seconds'], frames=len(proof['frames']), extended_past_300=proof['extended_past_legacy_limit'], read_only=True, manual_steps=0, ordinary_statement_limits_changed=False)


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
    consistent=consistent_validation(value,cases)
    progress=require_factory_progress(factory['factory_progress_observation'])
    return value,dict(head=proof['head'],original_sha256=proof['sha256'],package_sha256=proof['package_sha256'],
        all_seven_combined_groups_and_restorations=True,Native20=True,actual_cron_groups=2,
        factory1200x3=True,consistent_reader_and_streaming=consistent,factory_progress_observation=progress,
        real_Auth_browser_still_required=True,production_go=False,independent_acceptance=False)
