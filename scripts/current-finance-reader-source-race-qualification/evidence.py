"""Actual composed-source paired proof is mandatory; prepared output gives no credit."""
from pathlib import Path
from hashlib import sha256
import json
HEAD='d05c568cca01085f87f7e48fe85c8d15ca43bffd'

def validate(repo,proof,raw,product,parent):
    assert proof['head']==HEAD and proof['status']=='PASS'
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    d=json.loads(raw);declared=json.loads((repo/'scripts/current-finance-check-reuse-diagnostic/SOURCE.json').read_bytes())
    assert d['label']=='CP7_D17_18_FINANCE_CHECK_REUSE_DIAGNOSTIC1'and d['status']=='PASS'
    assert d['qualification_commit']==HEAD and d['source_declaration']['qualification']==declared
    assert d['source_declaration']['current_installation']==product.sources()
    assert d['source_declaration']['retained_admission']==parent
    for path,digest in declared['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    for key in ('required_case_ids_pass','cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','used_guard_refused_before_DDL'):
        assert d[key]is True,key
    assert d['complete_preuse_removal']and d['production_go']is d['independent_acceptance']is False
    assert d['observed_case_count']==d['expected_case_count']==len(d['committed'])==1
    checked_case(repo,d,declared)
    return dict(proof,actual_composed_reuse_diagnostic_verified=True,performance_qualification=False)

def checked_case(repo,d,source):
    from decimal import Decimal,ROUND_HALF_UP
    assert d['actual_cron_claim']is d['changed_schedule']is d['factory3600_claim']is False
    assert d['manual_steps']==0 and d['used_guard_refused_before_DDL']
    assert len(d['committed'])==1 and set(d['committed'])==set(source['case_ids'])
    c=next(iter(d['committed'].values()))
    for key in ('diagnostic_only','diagnostic_collection_completed','all22_all_rows_and_sequences_unchanged_by_measurements',
                'previous_factory_failures_remain_INCOMPLETE','price_percent_branch_qualification','temporary_snapshot_check_reuse_diagnostic'):
        assert c[key]is True,key
    for key in ('actual_cron_claim','product_timeout_changed','production_go','factory_native_finance_qualified',
                'performance_qualification','source_change_race_qualification','report_check_reuse_implemented','product_adoption'):
        assert c[key]is False,key
    assert c['status']=='PASS'and c['manual_committed_steps']==0
    fixture=c['price_percent_fixture'];assert fixture['method']=='PRICE_PERCENT'
    expected=(Decimal(fixture['price'])*Decimal(fixture['percentage'])/100).quantize(Decimal('.000001'),rounding=ROUND_HALF_UP)
    assert Decimal(fixture['independently_rounded_unit_hpp'])==expected
    assert Decimal(fixture['independently_rounded_posted_value'])==(expected*fixture['qty']).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    assert fixture['real_Native_import_and_shared_price_writer']and fixture['posted_stock_and_journal_exact']
    assert fixture['actual_Auth_HTTP_credit']is fixture['source_change_race_qualification']is False
    if source.get('fixture_contract')=='SYNTHETIC_LEGACY_PRICE_NATIVE_CURRENT_AND_OPENING_V2':
        from datetime import datetime
        assert fixture['fixture_contract']==source['fixture_contract']
        assert fixture['direct_business_DML']is True
        assert fixture['direct_DML_scope']=='ONE_LEGACY_PRICE_FIXTURE_ROW_BEFORE_MEASUREMENTS'
        historical=fixture['historical_price_fixture']
        assert historical['synthetic']is True and historical['direct_insert_rows']==1
        assert historical['guards_disabled']is historical['native_historical_price_writer_credit']is False
        assert fixture['historical_price_selected_over_current']is True
        assert Decimal(fixture['price'])!=Decimal(fixture['current_price'])
        assert datetime.fromisoformat(historical['effective_from'])<=datetime.fromisoformat(fixture['opening_physical_at'])<datetime.fromisoformat(fixture['current_price_effective_from'])
        assert fixture['current_price_native_version_id'] and historical['id']
    else:
        assert 'fixture_contract'not in source
        assert fixture['direct_business_DML']is False
    snapshot=json.loads((repo/'scripts/current-finance-check-reuse-diagnostic/NATIVE_SNAPSHOT_SOURCE.json').read_bytes())
    composed=None;installed=None
    installed_marker='scripts/current-finance-check-reuse-diagnostic/INSTALLED_REPORT_SOURCE.json'
    if installed_marker in source['files']:
        installed=json.loads((repo/installed_marker).read_bytes())
        assert installed['strategy']=='SAME_REPORT_OFFICIAL_READINESS'
        assert installed['derived']['installed_snapshot_bytes']==14417
        assert installed['derived']['installed_snapshot_sha256']==installed['actual_f038_live_body_sha256']=='5687c8b4805f73baa68197121f9a4a90f5f123d6ff7da683e88301a485e3aab2'
        for path,digest in installed['sources'].items():assert source['files'][path]==digest,path
    marker='scripts/current-finance-check-reuse-diagnostic/COMPOSED_SNAPSHOT_SOURCE.json'
    if marker in source['files']:
        composed=json.loads((repo/marker).read_bytes())
        assert composed['base_body_sha256']==snapshot['body_sha256']
        assert composed['transform_order']==['cp7_note_report_bundle.patched_report','cp7_report_accounts_bundle.wrap']
        assert composed['installed_body_sha256']=='3fa59773edf43a6f10a60b4fc08bbd1074097c6449b4b5c56f93ff2b64facd69'
    assert installed is not None,'INSTALLED_READINESS_SOURCE_REQUIRED'
    assert set(c['pairs'])=={'SMALL','PRICE_PERCENT','FACTORY_1200X3'}
    for name,limit in (('SMALL',8000),('PRICE_PERCENT',8000),('FACTORY_1200X3',30000)):
        pair=c['pairs'][name];old,new=pair['unchanged_official'],pair['single_snapshot_check_candidate']
        assert pair['status']=='PASS'and pair['entire_official_report_equal']and pair['no_result_cache']
        assert pair['product_performance_qualification']is pair['full_factory_completion']is pair['caller_supplied_check_results']is False
        assert pair['official_check_calls_before']==3 and pair['official_check_calls_after']==2
        assert old['report_sha256']==new['report_sha256']and old['report_bytes']==new['report_bytes']and old['rows']==new['rows']
        for candidate,row in ((False,old),(True,new)):
            assert row['candidate']is candidate and row['status']=='COMPLETED_DIAGNOSTIC'
            assert row['diagnostic_only']and row['all22_all_data_and_sequences_restored']
            assert row['retries']==0 and row['statement_limit_ms']==limit and row['elapsed_ms']>=0
            assert row['excluded_comparison_fields']==['report.captured_at']
            counts={x['function']:x['calls']for x in row['functions']}
            assert counts['erp.run_v268_financial_report_checks()']==(2 if candidate else 3)
            if installed:assert counts['erp.period_readiness_v1(date,date)']==(1 if candidate else 2)
        assert new['table_write_attempts']=={}and new['all_data_and_sequences_unchanged_before_rollback']
        patch=new['temporary_patch']
        if installed:
            assert patch['strategy']=='SAME_REPORT_OFFICIAL_READINESS'and patch['installed_source_derivation']==installed
            assert patch['snapshot_original_body_sha256']==installed['derived']['installed_snapshot_sha256']
            assert patch['workspace_before_sha256']==installed['derived']['workspace_sha256']
            assert patch['workspace_before_sha256']!=patch['workspace_after_sha256']
            assert pair['official_readiness_calls_before']==patch['report_readiness_calls_before']==2
            assert pair['official_readiness_calls_after']==patch['report_readiness_calls_after']==1
            for key in ('exact_live_body_matches_composed_official_installers','original_Native_snapshot_and_preflight_unchanged',
                        'original_close_commands_unchanged','private_date_only_helper','private_helper_only_finance_reader',
                        'original_preflight_permission_and_rules_preserved'):
                assert patch[key]is True,key
            assert set(patch['original_close_command_sha256'])=={'erp.close_accounting_through(date,text)','erp.reopen_accounting_through(date,text)'}
            assert all(len(digest)==64 for digest in patch['original_close_command_sha256'].values())
        else:
            assert patch['snapshot_original_body_sha256']==(composed['installed_body_sha256']if composed else snapshot['body_sha256'])
            if composed:
                assert patch['installed_source_derivation']==composed
                assert patch['exact_live_body_matches_composed_official_installers']is patch['native_original_body_preserved']is True
            assert patch['snapshot_checks_before']==2 and patch['snapshot_checks_after']==1
            assert patch['exact_body_outside_one_aggregation_unchanged']
        assert patch['authority_unchanged']and patch['no_cache_or_client_supplied_check_result']
        assert patch['product_adoption']is patch['production_go']is False
        opening=patch['readonly_opening'];assert opening['original_resolver_unchanged']and opening['private_helper_not_callable_by_browser_or_worker']
        assert opening['changed_report_call_count']==opening['removed_lock_count']==1 and opening['removed_update_count']==2
        assert opening['original_body_sha256']=='d82bdae08187b2121b7a777e0b3973f292318b195a148762f3ba5998407bf48a'
        assert pair['elapsed_change_ms']==round(new['elapsed_ms']-old['elapsed_ms'],3)
    assert c['pairs']['FACTORY_1200X3']['unchanged_official']['table_write_attempts']['erp.opening_balance_items'][1]>=3600
    return dict(diagnostic_collection_only=True,paired_reports=c['pairs'],price_percent_fixture=fixture,
        runtime_environment=c['runtime_environment'],candidate_zero_table_writes=True,official_check_calls_reduced_from3_to2=True,
        actual_factory_completion=False,performance_qualification=False,source_change_race_qualification=False,
        report_check_reuse_implemented=False,product_adoption=False)
