"""Closed raw prerequisites; B HTTP evidence remains component credit only."""
from hashlib import sha256
from pathlib import Path
import json
from cp7_current_transport_original_schema import checked_group

PRIVATE_VARIABLE='CURRENT_FROZEN_FINANCE_NATIVE_ORIGINAL_REPORT'
B_VARIABLE='B_FROZEN_PUBLIC_FACADE_ORIGINAL_REPORT'
PRIVATE_HEAD='a3088e214f5babc46e4016734cce11925acd34d8'
B_HEAD='c1dd6b5cd231701be3be35bb7dd45c3856ace8fa'


def validate(repo,here,proofs,actuals,product):
    assert set(proofs)==set(actuals)=={PRIVATE_VARIABLE,B_VARIABLE}
    for variable,actual in actuals.items():
        assert proofs[variable]['status']==actual['status']=='PASS'
        assert actual['production_go']is actual['independent_acceptance']is False
        assert actual['cp6_restored']is actual['advisor_gate']is True
    proof,actual=proofs[PRIVATE_VARIABLE],actuals[PRIVATE_VARIABLE]
    assert proof['head']==actual['qualification_commit']==PRIVATE_HEAD
    assert actual['label']=='CP7_CURRENT_FROZEN_FINANCE_NATIVE45'
    assert actual['source_declaration']['current_installation']==product.predecessor.sources()
    old=json.loads((repo/'scripts/current-frozen-finance-native-qualification/SOURCE.json').read_bytes())
    assert actual['source_declaration']['qualification']==old
    assert actual['required_case_ids']==old['case_ids']and actual['required_case_ids_pass']
    assert actual['expected_case_count']==actual['observed_case_count']==45
    assert actual['native']['counts']=={'PASS':45}and set(actual['native']['cases'])==set(old['case_ids'])
    for key in('baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','restore_raw_public_equal'):
        assert actual[key]is True,key
    for key in('all22_preinstall_equal','all_rows_and_sequences_equal','global_used_guard_before_any_DDL'):
        assert actual['complete_preuse_removal'][key]is True,key
    for name,row in actual['native']['cases'].items():
        assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged'],name
        assert all(value in(0,[],{})for value in row.get('session_leaks',{}).values())
        day=row['business_day'];assert day['planned']==day['before']==day['after']
    official=actual['native']['cases']['OW12_FROZEN_FINANCE_OPERATIONAL_FIRST_OFFICIAL_FINANCE']
    assert official['official_metric_count']==24 and official['official_sections_equal']and official['unknown_never_zero']
    assert official['independent_book_signature']and official['sealed_operational_original_unchanged']
    validate_B(here,proofs[B_VARIABLE],actuals[B_VARIABLE],product)
    return {key:dict(value,observed_status='PASS',component_only=key==B_VARIABLE)
            for key,value in proofs.items()}


def validate_B(here,proof,actual,product):
    assert proof['status']==actual['status']=='PASS'
    assert actual['production_go']is actual['independent_acceptance']is False
    assert actual['cp6_restored']is actual['advisor_gate']is True
    assert proof['head']==B_HEAD and actual['label']=='CP7_OW12B_FROZEN_FACADE'
    assert actual['full_A_chain_qualified']is actual['public_or_default_request_adopted']is False
    assert actual['official_finance_included']is actual['full_factory3600_qualified']is False
    assert actual['actual_Auth_HTTP_credit']is actual['actual_concurrency']is actual['public_facade_transport_qualified']is True
    assert actual['required_case_ids_pass']and actual['required_case_counts_pass']
    contract=json.loads((here/'B_CONTRACT.json').read_bytes())
    assert actual['predeclared_case_contract']==contract
    assert contract['contract']=='cp7.ow12b.frozen-facade-transport.v2'
    assert actual['required_case_ids']==contract['required_case_ids']
    assert actual['required_case_counts']==contract['required_case_counts']==dict(native=3,races=3,http=2)
    assert actual['expected_case_count']==actual['observed_case_count']==8
    assert actual['target_v2_source_sha256']==actual['frozen_facade_source_sha256']==contract['target_v2_source_sha256']
    assert actual['frozen_facade_source_sha256'][product.public.render.B_PATH.removeprefix('scripts/')]==product.public.render.B_SHA256
    assert len(actual['frozen_facade_source_sha256'])==90
    assert all(actual['restore_components'].values())and actual['all_other_predecessor_definitions_and_owners_unchanged']
    for group,ids in contract['required_case_ids'].items():
        value=actual[group]
        if group=='native':
            assert value['status']=='PASS'and value['complete_boundary_restored']and not value['missing']
            assert value['counts']=={'PASS':3}and set(value['cases'])==set(ids)
            for row in value['cases'].values():
                assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']
                day=row['business_day'];assert day['planned']==day['before']==day['after']
        else:checked_group(value,ids,races=group=='races')
    http=actual['http']
    assert http['real_auth']and not http['jwt_signed_by_runtime']and not http['test_only_usage_grant']
    assert http['auth_counts']==dict(before=[0]*4,after=[0]*4,restored=True)
    for row in actual['races']['races'].values():
        assert row['actual_blocking_backend_observed']and row['no_orphan_job_or_ERP_effect']
    return dict(status='PASS_COMPONENT_PREREQUISITE_ONLY',counts=dict(native=3,races=3,http=2),source_pins=90,new_A_Auth_HTTP_credit=False)
