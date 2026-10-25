"""Require the corrected contract6 actual PASS before Native20 regression."""
from pathlib import Path
from hashlib import sha256
import importlib.util, json, os, subprocess, sys


def admitted(repo, here, ids, product, business):
    path = repo / 'scripts/current-selected-return-contract-qualification/probe.py'
    spec = importlib.util.spec_from_file_location('selected_return_contract_gate', path)
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    predecessor = parent.admitted()
    assert predecessor['current_installation'] == product.sources()
    pins = json.loads((here / 'SOURCE.json').read_bytes())
    assert pins['contract'] == 'cp7.current-selected-return-native20-qualification.v1'
    assert pins['case_ids'] == list(ids) and len(ids) == len(set(ids)) == 20
    for path, digest in pins['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--', str(here)], text=True).strip()
    assert (here / 'cases.py').read_bytes() == (repo / 'scripts/current-model-target-native-qualification/cases.py').read_bytes()
    assert set(pins['actual_qualification_originals']) == {'CURRENT_SELECTED_RETURN_CONTRACT_ORIGINAL_REPORT', 'CURRENT_MODEL_TARGET_ORIGINAL_REPORT'}
    originals = {}
    for variable, proof in pins['actual_qualification_originals'].items():
        path = Path(os.environ[variable]); raw = path.read_bytes()
        assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256']
        actual = json.loads(raw)
        assert actual['status'] == proof['status'] == 'PASS'
        assert actual['qualification_commit'] == proof['head']
        assert actual['cp6_restored'] and actual['advisor_gate']
        assert actual['baseline_full22_all_rows_all_sequences_equal'] and actual['baseline_advisors_equal']
        assert actual['required_case_ids_pass'] and actual['complete_preuse_removal']
        if variable == 'CURRENT_SELECTED_RETURN_CONTRACT_ORIGINAL_REPORT':
            assert actual['baseline']['counts'] == actual['native']['counts'] == {'PASS': 6}
            assert actual['execution_count'] == 12
            assert actual['source_declaration']['qualification'] == predecessor['qualification']
            assert actual['source_declaration']['current_installation'] == product.sources()
            assert actual['required_case_ids'] == list(parent.IDS)
            for phase in ('baseline', 'native'):
                for row in actual[phase]['cases'].values():
                    assert row['full_boundary_restored'] and row['public_schema_unchanged']
        else:
            assert actual['native']['counts'] == {'PASS': 20} and actual['observed_case_count'] == 20
            assert actual['required_case_ids'] == list(ids)
            assert actual['source_declaration']['current_installation'] == product.predecessor.sources()
        originals[variable] = dict(proof, observed_status=actual['status'])
    loaded = []
    for name, module in tuple(sys.modules.items()):
        if name.startswith(('cp6_', 'cp7_sales_')) and getattr(module, '__file__', None):
            path = Path(module.__file__)
            assert sha256(path.read_bytes()).hexdigest() == pins['files']['scripts/' + path.name]
            loaded.append(name)
    return dict(qualified_selected_return_contract=predecessor, current_installation=product.sources(),
                qualification=pins, actual_originals_verified=originals,
                actual_loaded_modules_verified=loaded, retained_business_cases=business.source_binding(),
                unchanged_twenty_business_cases=True, production_go=False, independent_acceptance=False)
