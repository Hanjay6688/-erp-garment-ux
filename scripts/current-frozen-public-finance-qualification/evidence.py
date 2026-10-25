"""Verify complete current Native52 and retained Auth3/races7 actual Originals."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_current_transport_original_schema import checked_group

def validate(repo,here,proofs,actuals,product,ids):
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    assert set(proofs)==set(actuals)=={cfg['native_variable'],cfg['prior_variable']}
    parent=json.loads((repo/cfg['native_path']).read_bytes())
    assert parent['contract']=='cp7.current-frozen-public-finance-native52-qualification.v1'
    assert len(ids)==len(set(ids))==10
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
            assert p['head']==cfg['prior_head']
            assert d['label']=='CP7_CURRENT_VERSIONED_PERFORMANCE_FINANCE10'
            assert d['source_declaration']['current_installation']==product.predecessor.predecessor.predecessor.sources()
            for name in('cases.py','utc_snapshot.py'):
                path='scripts/current-versioned-performance-finance-qualification/'+name
                assert d['source_declaration']['qualification']['files'][path]==sha256((repo/path).read_bytes()).hexdigest()
            assert d['required_case_ids']==list(ids)and d['observed_case_count']==d['expected_case_count']==10
            groups=d['transport_groups'];assert set(groups)=={'finance_auth','finance_races'}
            assert groups['finance_auth']['counts']=={'PASS':3}and groups['finance_races']['counts']=={'PASS':7}
            assert groups['finance_auth']['real_auth']and not groups['finance_auth']['jwt_signed_by_runtime']and not groups['finance_auth']['test_only_usage_grant']
            checked_group(groups['finance_auth'],list(ids[:3]),races=False)
            checked_group(groups['finance_races'],list(ids[3:]),races=True)
            assert len(d['copy_catalog_admissions'])==1 and len(d['race_copy_catalog_admissions'])==7
            assert len(d['full_capture_snapshot_observations'])==7
            assert all(x['all_fields_retained']==23 and x['session_timezone_restored']for x in d['full_capture_snapshot_observations'])
        checked[variable]=dict(p,observed_status='PASS')
    return checked
