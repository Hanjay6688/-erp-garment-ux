"""Verify complete Native52 and retained actual browser Original bytes."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_current_transport_original_schema import checked_group

def validate(repo,here,proofs,actuals,product,ids):
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    assert set(proofs)==set(actuals)=={cfg['native_variable'],cfg['prior_variable']}
    parent=json.loads((repo/cfg['native_path']).read_bytes())
    assert parent['contract']=='cp7.current-frozen-public-finance-native52-qualification.v1'
    assert len(ids)==len(set(ids))==cfg['count']
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
    kind=cfg['kind'];assert p['head']==cfg['prior_head']
    assert d['label']=='CP7_CURRENT_VERSIONED_PERFORMANCE_'+('BROWSER6'if kind=='browser'else'TRANSPORT28')
    assert d['source_declaration']['current_installation']==product.predecessor.predecessor.predecessor.sources()
    old=repo/('scripts/current-versioned-performance-'+kind+'-qualification')
    for rel in cfg['core_business_files']:
        assert d['source_declaration']['qualification']['files'][rel]==sha256((repo/rel).read_bytes()).hexdigest(),rel
    for path in old.iterdir():
        if path.is_file()and path.name!='SOURCE.json':
            rel=str(path.relative_to(repo));assert d['source_declaration']['qualification']['files'][rel]==sha256(path.read_bytes()).hexdigest(),rel
    assert d['expected_case_count']==d['observed_case_count']==cfg['count']
    assert d['required_case_ids']==list(ids)and d['required_case_ids_pass']and d['complete_preuse_removal']
    groups=d['browser_groups'if kind=='browser'else'transport_groups'];observed=[]
    for name,g in groups.items():
        race=name.endswith('_races');cases=g['races'if race else'cases'];observed+=list(cases)
        assert g['counts']=={'PASS':len(cases)}and all(x['status']=='PASS'for x in cases.values())
        assert g['status']=='RUN_COMPLETE'and g['database_remaining']==0 and not g.get('cleanup_failures')and not g.get('session_leaks')
        if kind=='transport':checked_group(g,list(cases),races=race)
        if not race:
            assert g['real_auth']and not g['jwt_signed_by_runtime']and not g['test_only_usage_grant']
            assert g['auth_counts']==dict(before=[0]*4,after=[0]*4,restored=True)
            assert not g['cleanup']['cleanup_failures']and not g['cleanup']['rest_remaining']
        if kind=='browser':
            assert g['host_exit']==g['console_errors']==0 and g['host_status']=='RUN_COMPLETE'
            assert not g['auth_cleanup_failures']and not g['host_error']
    assert len(observed)==len(set(observed))==cfg['count']and set(observed)==set(ids)
    assert len(d['copy_catalog_admissions'])==3
    assert len(d.get('race_copy_catalog_admissions',[]))==(19 if kind=='transport'else 0)
    for c in d['copy_catalog_admissions']+d.get('race_copy_catalog_admissions',[]):
        assert c['full22_after_must_equal_original_install']and c['all22_groups_equal_original_install']
        assert not c['product_state_modified']and not c['Native_or_schema_or_RPC_permissions_changed']
