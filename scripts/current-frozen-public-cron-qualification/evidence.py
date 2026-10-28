"""Verify complete current Native52 and retained actual minute cron1 actual Originals."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_current_transport_original_schema import checked_group

def validate(repo,here,proofs,actuals,product,ids):
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    assert set(proofs)==set(actuals)=={cfg['native_variable'],cfg['prior_variable']}
    parent=json.loads((repo/cfg['native_path']).read_bytes())
    assert parent['contract']=='cp7.current-frozen-public-finance-native52-qualification.v1'
    assert len(ids)==len(set(ids))==1
    checked={}
    for variable,p in proofs.items():
        d=actuals[variable]
        assert d['status']==p['status']=='PASS'
        assert d['production_go']is False and d['independent_acceptance']is False
        assert(d.get('qualification_commit')or d.get('candidate_commit'))==p['head']
        assert d['cp6_restored']and d['advisor_gate']and d['restore_raw_public_equal']
        assert d['complete_preuse_removal']and d['required_case_ids_pass']
        if variable==cfg['native_variable']:
            assert p['head']==cfg['native_head']
            assert d['label']=='CP7_CURRENT_FROZEN_PUBLIC_FINANCE_NATIVE52'
            assert d['source_declaration']['current_installation']==product.sources()
            assert d['source_declaration']['qualification']==parent
            assert d['required_case_ids']==parent['case_ids']
            assert d['native']['counts']=={'PASS':52}
            assert d['expected_case_count']==d['observed_case_count']==52
            assert set(d['native']['cases'])==set(parent['case_ids'])
            assert d['baseline_full22_all_rows_all_sequences_equal']and d['baseline_advisors_equal']
            for key in('all22_preinstall_equal','all_rows_and_sequences_equal','global_used_guard_before_any_DDL'):
                assert d['complete_preuse_removal'][key]is True,key
            for case in d['native']['cases'].values():
                assert case['status']=='PASS'and case['full_boundary_restored']and case['public_schema_unchanged']
                assert all(v in(0,[],{})for v in case.get('session_leaks',{}).values())
                day=case['business_day'];assert day['planned']==day['before']==day['after']
            official=d['native']['cases']['OW12_FROZEN_PUBLIC_FINANCE_OPERATIONAL_FIRST_OFFICIAL_FINANCE']
            assert official['official_metric_count']==24 and official['official_sections_equal']
            assert official['unknown_never_zero']and official['independent_book_signature']
            assert official['sealed_operational_original_unchanged']
        else:
            validate_prior(repo,cfg,p,d,product,ids)
        checked[variable]=dict(p,observed_status='PASS')
    return checked


def validate_prior(repo,cfg,p,d,product,ids):
    assert p['head']==cfg['prior_head']
    assert d['label']=='CP7_CURRENT_VERSIONED_PERFORMANCE_CRON1'
    assert d['source_declaration']['current_installation']==product.predecessor.predecessor.predecessor.sources()
    for name in('runner.py','probe.py'):
        path='scripts/current-versioned-performance-cron-qualification/'+name
        assert d['source_declaration']['qualification']['files'][path]==sha256((repo/path).read_bytes()).hexdigest()
    assert d['required_case_ids']==list(ids)and d['expected_case_count']==d['observed_case_count']==1
    assert d['actual_cron_claim']and d['manual_steps']==0 and d['changed_schedule']is False
    assert d['baseline_full22_all_rows_all_sequences_equal']and d['baseline_advisors_equal']
    assert d['used_guard_refused_before_DDL']and d['scheduler_quiet_before_baseline_restore']
    assert set(d['committed'])==set(ids)
    case=d['committed'][ids[0]]
    assert case['status']=='PASS'and case['manual_finance_or_operational_steps']==0
    assert case['page_or_test_ticks']==0 and case['test_schedule_override']is None
    assert case['metric_count']==24 and 0<=case['elapsed_seconds']<300
    assert case['observed_finance_state']=='READY'and len(case['observed_job_states'])==2
    assert set(case['observed_job_states'].values())=={'DONE'}
    for key in('official_sections_and_metrics_exact','independent_book_signature','unknown_never_zero',
        'Native_money_stock_HPP_unchanged','server_runner_active','all22_catalog_exact',
        'all_runs_recorded','schedules_removed_and_unrelated_jobs_unchanged','same_UUID_no_second_effect'):
        assert case[key]is True,key
    assert case['cron_runs']and all(r['status']=='succeeded'and r['end']is not None for r in case['cron_runs'])
