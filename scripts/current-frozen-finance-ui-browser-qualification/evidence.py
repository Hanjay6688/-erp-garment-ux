"""Admit exact complete Native52 and public Auth3/races7 Originals."""
from hashlib import sha256
import json
from cp7_current_transport_original_schema import checked_group

def validate(repo,here,proofs,actuals,product,ids):
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    assert list(ids)==cfg['case_ids'] and len(ids)==len(set(ids))==2
    assert set(proofs)==set(actuals)=={cfg['native_variable'],cfg['finance_variable']}
    checked={}
    for variable,p in proofs.items():
        d=actuals[variable]
        assert p['status']==d['status']=='PASS'
        assert d['production_go'] is False and d['independent_acceptance'] is False
        assert (d.get('candidate_commit')or d.get('qualification_commit'))==p['head']
        assert d['cp6_restored'] and d['advisor_gate'] and d['restore_raw_public_equal']
        assert d['required_case_ids_pass'] and d['complete_preuse_removal']
        assert d['source_declaration']['current_installation']==product.sources()
        kind='native' if variable==cfg['native_variable'] else 'finance'
        assert p['head']==cfg[kind+'_head']
        declaration=json.loads((repo/cfg[kind+'_path']).read_bytes())
        assert d['source_declaration']['qualification']==declaration
        for path,digest in declaration['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
        assert d['required_case_ids']==declaration['case_ids']
        if kind=='native':
            assert d['label']=='CP7_CURRENT_FROZEN_PUBLIC_FINANCE_NATIVE52'
            assert d['observed_case_count']==d['expected_case_count']==52 and d['native']['counts']=={'PASS':52}
            assert set(d['native']['cases'])==set(declaration['case_ids'])
            assert d['baseline_full22_all_rows_all_sequences_equal'] and d['baseline_advisors_equal']
            for key in ('all22_preinstall_equal','all_rows_and_sequences_equal','global_used_guard_before_any_DDL'):assert d['complete_preuse_removal'][key] is True
            for c in d['native']['cases'].values():
                assert c['status']=='PASS' and c['full_boundary_restored'] and c['public_schema_unchanged']
                assert all(v in (0,[],{}) for v in c.get('session_leaks',{}).values())
                day=c['business_day'];assert day['planned']==day['before']==day['after']
            c=d['native']['cases']['OW12_FROZEN_PUBLIC_FINANCE_OPERATIONAL_FIRST_OFFICIAL_FINANCE']
            assert c['official_metric_count']==24 and c['official_sections_equal'] and c['independent_book_signature']
            assert c['unknown_never_zero'] and c['sealed_operational_original_unchanged']
            # The retained posted fixture is deliberately not a report-READY fixture.
            assert c['readiness']=='BLOCKED' and c['unknown_metric_ids']
        else:
            assert d['label']=='CP7_CURRENT_FROZEN_PUBLIC_FINANCE10'
            assert d['observed_case_count']==d['expected_case_count']==10
            groups=d['transport_groups'];assert set(groups)=={'finance_auth','finance_races'}
            checked_group(groups['finance_auth'],declaration['case_ids'][:3],races=False)
            checked_group(groups['finance_races'],declaration['case_ids'][3:],races=True)
            assert len(d['copy_catalog_admissions'])==1 and len(d['race_copy_catalog_admissions'])==7
            for c in d['copy_catalog_admissions']+d['race_copy_catalog_admissions']:
                assert c['full22_after_must_equal_original_install'] and c['all22_groups_equal_original_install']
                assert not c['product_state_modified'] and not c['Native_or_schema_or_RPC_permissions_changed']
            observations=d['full_capture_snapshot_observations']
            assert len(observations)==7 and all(x['all_fields_retained']==23 and x['session_timezone_restored'] for x in observations)
            flow=groups['finance_auth']['cases']['CURRENT_FINANCE_AUTH_PUBLIC_FLOW_READY_REPLAY']
            assert flow['actual_Auth_request_step_status_READY_and_replay'] and flow['official_sections_and_24_metrics_equal']
            assert flow['private_finance_advancement_not_HTTP_or_cron'] and flow['sealed_operational_pages_unchanged']
            timings=groups['finance_auth']['cases']['CURRENT_FINANCE_AUTH_FOREIGN_ANON_CLOSED_QUERY']['actual_Auth_call_timings']
            assert timings and all(0<=x['millis']<8000 for x in timings)
            assert d['request_routes']=={'finance':'erp_cp7_request_bounded_frozen_finance_analysis_v2','operational':'erp_cp7_request_bounded_staged_analysis_v2'}
        checked[variable]=dict(p,observed_status='PASS')
    return checked
