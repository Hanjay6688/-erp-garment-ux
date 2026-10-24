"""Require full current Native20 PASS and preserve the actual first contract failure."""
from pathlib import Path
from hashlib import sha256
import importlib.util, json, os, subprocess, sys


def admitted(repo, here, ids, product, business):
    path = repo / 'scripts/current-model-target-native-qualification/probe.py'
    spec = importlib.util.spec_from_file_location('target_contract_native20_gate', path)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    predecessor = native.admitted()
    assert predecessor['current_installation'] == product.sources()
    pins = json.loads((here / 'SOURCE.json').read_bytes())
    assert pins['case_ids'] == list(ids) and len(ids) == len(set(ids)) == 6
    for path, digest in pins['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, ('CURRENT_TARGET_CONTRACT_SOURCE_CHANGED', path)
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--', str(here)], text=True).strip()
    assert set(pins['actual_qualification_originals']) == {'CURRENT_MODEL_TARGET_ORIGINAL_REPORT', 'FIRST_CP6_CONTRACT_ORIGINAL_REPORT'}
    originals = {}
    for variable, proof in pins['actual_qualification_originals'].items():
        raw = Path(os.environ[variable]).read_bytes()
        assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256'], variable
        actual = json.loads(raw)
        assert actual['status'] == proof['status'] and actual['cp6_restored'] and actual['advisor_gate']
        assert actual['qualification_commit'] == proof['head']
        if variable == 'CURRENT_MODEL_TARGET_ORIGINAL_REPORT':
            assert actual['status'] == 'PASS' and actual['native']['counts'] == {'PASS': 20}
            assert actual['observed_case_count'] == 20 and actual['required_case_ids_pass']
            assert actual['required_case_ids'] == predecessor['qualification']['case_ids']
            assert actual['source_declaration']['qualification'] == predecessor['qualification']
            assert actual['source_declaration']['current_installation'] == product.sources()
            assert actual['baseline_full22_all_rows_all_sequences_equal'] and actual['baseline_advisors_equal']
            assert actual['complete_preuse_removal']
        else:
            assert actual['status'] == 'INCOMPLETE'
            assert actual['baseline']['counts'] == {'PASS': 6}
            assert actual['native']['counts'] == {'PASS': 5, 'INCOMPLETE': 1}
            assert actual['required_case_ids'] == list(ids)
            failed = {key: row for key, row in actual['native']['cases'].items() if row['status'] != 'PASS'}
            assert list(failed) == ['RETURN_REBOUND_CUSTOMER_ATOMIC_REFUSAL']
            assert 'OW04_SOURCE_CUSTOMER_MISMATCH' in str(next(iter(failed.values()))['error'])
            case_path = 'scripts/current-cp6-contract-qualification/cases.py'
            assert actual['source_declaration']['qualification']['files'][case_path] == sha256((repo / case_path).read_bytes()).hexdigest()
            assert Path(business.__file__).resolve() == (repo / case_path).resolve()
        originals[variable] = dict(proof, observed_status=actual['status'])
    loaded = []
    for name, module in tuple(sys.modules.items()):
        if name.startswith(('cp6_', 'cp7_sales_')) and getattr(module, '__file__', None):
            path = Path(module.__file__)
            assert sha256(path.read_bytes()).hexdigest() == pins['files']['scripts/' + path.name]
            loaded.append(name)
    return dict(qualified_current_target=predecessor, current_installation=product.sources(),
                qualification=pins, actual_originals_verified=originals,
                actual_loaded_modules_verified=loaded, unchanged_six_business_cases=True,
                first_failure_relabelled=False, production_go=False, independent_acceptance=False)
