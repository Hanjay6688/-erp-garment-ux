"""Full retained admission plus exact actual A Native36 and three B Originals."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess

CONTRACT = 'cp7.current-frozen-units-native40-qualification.v1'
A_NATIVE = 'CURRENT_VERSIONED_PERFORMANCE_NATIVE_ORIGINAL_REPORT'
B_HEAD = '10a36e35b956febd9e34907f20fc5b782ec48dc1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def verify_original(actual, proof, contract, root):
    assert proof == contract['proof']
    assert actual['status'] == proof['status'] == 'PASS'
    assert actual['cp6_restored'] and actual['advisor_gate']
    assert actual['production_go'] is actual['independent_acceptance'] is False
    assert actual['required_case_ids_pass'] and actual['required_case_counts_pass']
    assert actual['required_case_ids'] == contract['case_ids']
    assert actual['observed_case_count'] == actual['expected_case_count'] == 4
    assert actual['native']['counts'] == {'PASS':4}
    assert actual['restore_components'] and all(actual['restore_components'].values())
    maps = {k:v for k,v in actual.items() if k.endswith('source_sha256') and isinstance(v,dict)}
    assert maps == contract['source_maps'] and maps
    for values in maps.values():
        for path, expected in values.items():
            relative = path if path.startswith(('scripts/','src/')) else 'scripts/'+path
            assert sha256((root/relative).read_bytes()).hexdigest() == expected, relative
    assert set(actual['native']['cases']) == set(contract['case_ids']['native'])
    for name, row in actual['native']['cases'].items():
        assert row['status'] == 'PASS' and row['full_boundary_restored'] and row['public_schema_unchanged']
        assert all(v in (0,[],{}) for v in row.get('session_leaks',{}).values())
        assert {k:v for k,v in row.items() if isinstance(v,bool)} == contract['case_boolean_contracts'][name]
    return dict(head=proof['head'], actual_case_count=4, source_maps=len(maps), new_A_runtime_credit=False)


def admitted(repo, here, ids, product, business):
    pins = json.loads((here/'SOURCE.json').read_bytes())
    contracts = json.loads((here/'B_COMPONENT_CONTRACTS.json').read_bytes())
    assert pins['contract'] == CONTRACT and pins['case_ids'] == list(ids)
    assert len(ids) == len(set(ids)) == 40
    assert set(pins['actual_qualification_originals']) == {A_NATIVE, *contracts}
    old_probe = repo/'scripts/current-versioned-performance-native-qualification/probe.py'
    retained = load('unchanged_full_performance_admission', old_probe)
    old = retained.admitted()
    assert old['current_installation'] == product.predecessor.sources()
    assert pins['retained_declaration_sha256'] == sha256(old_probe.with_name('SOURCE.json').read_bytes()).hexdigest()
    assert list(business.RETAINED_IDS) == old['qualification']['case_ids']
    for path, digest in old['qualification']['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest() == digest, path
    for path, digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest() == digest, path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    root = Path(os.environ['B_FROZEN_UNITS_SOURCE_ROOT']).resolve()
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip() == B_HEAD
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],text=True).strip()
    verified, actuals = {}, {}
    for variable, proof in pins['actual_qualification_originals'].items():
        raw = Path(os.environ[variable]).read_bytes()
        assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256'], variable
        actual = json.loads(raw)
        actuals[variable] = actual
        if variable in contracts:
            verified[variable] = verify_original(actual, proof, contracts[variable], root)
        else:
            assert actual['status'] == proof['status'] == 'PASS'
            assert actual['qualification_commit'] == proof['head'] == '88f36937ef7c0a42cc7761142678da5411ece68f'
            assert actual['label'] == 'CP7_CURRENT_VERSIONED_PERFORMANCE_NATIVE36'
            assert actual['production_go'] is actual['independent_acceptance'] is False
            for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal',
                        'baseline_advisors_equal','required_case_ids_pass','restore_raw_public_equal'):
                assert actual[key], key
            assert actual['complete_preuse_removal']
            assert actual['source_declaration']['qualification'] == old['qualification']
            assert actual['source_declaration']['current_installation'] == product.predecessor.sources()
            assert actual['required_case_ids'] == list(business.RETAINED_IDS)
            assert actual['native']['counts'] == {'PASS':36}
            assert actual['observed_case_count'] == actual['expected_case_count'] == 36
            assert set(actual['native']['cases']) == set(business.RETAINED_IDS)
            for row in actual['native']['cases'].values():
                assert row['status'] == 'PASS' and row['full_boundary_restored'] and row['public_schema_unchanged']
                assert all(v in (0,[],{}) for v in row.get('session_leaks',{}).values())
            verified[variable] = dict(head=proof['head'], actual_case_count=36)
    helper_pins = json.loads((here/'QUALIFIED_B_HELPERS.json').read_bytes())
    assert helper_pins['B_head'] == B_HEAD
    for name, digest in helper_pins['files'].items():
        raw = (root/'scripts'/name).read_bytes()
        assert raw == (repo/'scripts'/name).read_bytes() and sha256(raw).hexdigest() == digest
    declaration = json.loads((product.inputs.ROOT/'BOUND_B_SOURCES.json').read_bytes())
    expected_B_proofs = {json.dumps(v,sort_keys=True) for v in declaration['qualified_component_originals'].values()}
    assert expected_B_proofs == {json.dumps(pins['actual_qualification_originals'][v],sort_keys=True) for v in contracts}
    for path in declaration['files']:
        assert (repo/path).read_bytes() == (root/path).read_bytes()
    return dict(qualified_current_versioned_performance=old, current_installation=product.sources(),
                qualification=pins, actual_originals_verified=verified,
                exact_B_inputs=product.inputs.sources(), retained_business_cases=business.source_binding(),
                full_factory3600_finance_qualified=False, production_go=False, independent_acceptance=False)
