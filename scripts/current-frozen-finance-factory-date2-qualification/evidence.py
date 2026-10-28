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
    assert set(proofs)==set(actuals)==baseline_variables|{variable,config['wrong_fixture_failure_variable']}
    assert len(proofs)==config['required_actual_originals']==9
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
    validate_fixture_provenance(config,actuals[config['first_failure_variable']])
    variable=config['wrong_fixture_failure_variable'];proof=proofs[variable];failure=actuals[variable]
    assert failure['qualification_commit']==proof['head']=='c17b56ed91262757fb75d73d12b98a12edaa8f35'
    assert failure['label']=='CP7_CURRENT_VERSIONED_PERFORMANCE_FACTORY_FINANCE1'
    assert failure['status']==proof['status']=='INCOMPLETE'
    assert failure['error'].startswith('BF_HISTORY: master baru hanya mulai sekarang atau mendatang')
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','restore_raw_public_equal'):
        assert failure[key] is True,key
    assert failure['source_declaration']['qualification']['files']['scripts/current-versioned-performance-factory-output2-qualification/fixture.py']=='6dceb87ae35bb87527eba3176f80b292e5ab9ef2a4a4b5a813bf6d3f3097724e'
    verified[variable]=dict(proof,observed_status='INCOMPLETE',first_wrong_fixture_preserved=True)
    return sources,verified


def validate_fixture_provenance(config,actual):
    """Bind to the file actually executed by the retained run, not an older sibling."""
    path='scripts/current-factory-finance-runtime-qualification/fixture.py'
    digest='193197b3c288b382970250f2f3db4c38ea21e3fd45bb1729fe25f94ecbe5e3bd'
    assert config['fixture_path']==path and config['fixture_sha256']==digest
    assert actual['qualification_commit']==config['old_head']=='daab807531816353e499d7842897320ce42e8949'
    assert actual['source_declaration']['qualification']['files'][path]==digest
    case=actual['committed']['CURRENT_FACTORY_1200X3_ACTUAL_MINUTE_OFFICIAL_FINANCE']
    fixture=case['factory_fixture']
    assert fixture['status']=='PASS' and fixture['commercial_skus']==1200 and fixture['variants']==3600
    assert fixture['current_native_membership_verified'] is True
    assert fixture['historical_sales_precede_current_membership'] is True
    history=fixture['current_membership_posted_history_guard']
    assert history['all_rows_exact'] is True and history['historical_sales_relabelled'] is False
    assert history['tables']==sorted(['erp.sales_headers','erp.sales_items','erp.sale_stock_allocations',
        'erp.fg_stock_movements','erp.fg_lots','erp.journal_entries','erp.journal_lines',
        'erp.hpp_versions','erp.hpp_version_components'])
    return True
