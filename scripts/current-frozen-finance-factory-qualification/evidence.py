"""Six original performance suites remain baseline prerequisites, plus actual Native45."""
from hashlib import sha256
import importlib.util
import json


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def validate(repo,config,proofs,actuals,product):
    import cp7_current_versioned_performance_installation as baseline_product
    previous=load('retained_performance_factory_actual_evidence',repo/'scripts/current-versioned-performance-factory-qualification/evidence.py')
    old_config=json.loads((repo/config['retained_performance_config']).read_bytes())
    baseline_variables=set(old_config['followups'].values())|{old_config['first_failure_variable']}
    variable=config['private_native_variable']
    assert set(proofs)==set(actuals)==baseline_variables|{variable}
    assert len(proofs)==config['required_actual_originals']==8
    sources,verified=previous.validate(repo,old_config,{k:proofs[k]for k in baseline_variables},
        {k:actuals[k]for k in baseline_variables},baseline_product)
    proof,actual=proofs[variable],actuals[variable]
    assert actual['label']=='CP7_CURRENT_FROZEN_FINANCE_NATIVE45'
    assert actual['status']==proof['status']=='PASS'and actual['qualification_commit']==proof['head']
    assert actual['production_go']is actual['independent_acceptance']is False
    for key in('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal',
               'baseline_advisors_equal','restore_raw_public_equal','required_case_ids_pass'):
        assert actual[key]is True,key
    assert actual['complete_preuse_removal']['all22_preinstall_equal']
    assert actual['complete_preuse_removal']['all_rows_and_sequences_equal']
    assert actual['complete_preuse_removal']['global_used_guard_before_any_DDL']
    assert actual['expected_case_count']==actual['observed_case_count']==45
    assert actual['native']['counts']=={'PASS':45}
    path='scripts/current-frozen-finance-native-qualification/SOURCE.json'
    pins=json.loads((repo/path).read_bytes())
    assert actual['source_declaration']['qualification']==pins
    assert actual['source_declaration']['current_installation']==product.sources()
    assert actual['required_case_ids']==pins['case_ids']
    assert set(actual['native']['cases'])==set(pins['case_ids'])
    for row in actual['native']['cases'].values():
        assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']
        assert all(v in(0,[],{})for v in row.get('session_leaks',{}).values())
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    sources['private_native']=pins
    verified[variable]=dict(proof,observed_status='PASS')
    return sources,verified
