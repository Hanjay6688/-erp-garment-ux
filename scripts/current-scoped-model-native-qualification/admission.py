"""Admit full history and exact scoped-model component Originals before DB."""
from pathlib import Path
from hashlib import sha256
import importlib.util, json, os, subprocess, sys
import cp7_ow11_model_scoped_dataset_cases as dataset
import cp7_ow11_model_scoped_evaluation_cases as evaluation
import cp7_ow11_model_scoped_evaluation_transport_cases as transport
import cp7_ow11_model_scoped_evaluation_browser_cases as browser

PROVIDERS = {
    'SCOPED_DATASET_ORIGINAL_REPORT': dataset,
    'SCOPED_EVALUATION_ORIGINAL_REPORT': evaluation,
    'SCOPED_EVALUATION_TRANSPORT_ORIGINAL_REPORT': transport,
    'SCOPED_EVALUATION_BROWSER_ORIGINAL_REPORT': browser,
}
VARIABLES = set(PROVIDERS) | {
    'CURRENT_MODEL_HISTORY_ORIGINAL_REPORT',
    'CURRENT_MODEL_HISTORY_RESTORE_ORIGINAL_REPORT',
    'FIRST_SCOPED_MODEL_NATIVE_ORIGINAL_REPORT',
}


def source_path(key, path):
    if key == 'model_scoped_dataset_source_sha256':
        assert '/' not in path
        return 'scripts/cp7_model_scoped_dataset/' + path
    return path if path.startswith(('scripts/', 'src/')) else 'scripts/' + path


def admitted(repo, here, ids, product, business):
    spec = importlib.util.spec_from_file_location('qualified_history_native25', here / 'frozen_admission.py')
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    predecessor = frozen.invoke()
    assert predecessor['current_installation'] == product.predecessor.sources()
    pins = json.loads((here / 'SOURCE.json').read_bytes())
    assert pins['contract'] == 'cp7.current-scoped-model-native30-qualification.v1'
    assert pins['case_ids'] == list(ids) and len(ids) == len(set(ids)) == 30
    declaration = pins['frozen_declaration']
    assert declaration == dict(path='scripts/current-model-history-native-qualification/SOURCE.json',
                               head=frozen.FROZEN_HEAD, sha256=predecessor['source_manifest_sha256'])
    assert sha256((repo / declaration['path']).read_bytes()).hexdigest() == declaration['sha256']
    changes = {path: dict(frozen_sha256=digest, current_sha256=sha256((repo / path).read_bytes()).hexdigest())
               for path, digest in predecessor['qualification']['files'].items()
               if sha256((repo / path).read_bytes()).hexdigest() != digest}
    assert changes == pins['explicit_current_source_changes']
    assert changes == json.loads((here / 'EXPLICIT_CURRENT_SOURCE_CHANGES.json').read_bytes())
    for path, digest in pins['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--', str(here)], text=True).strip()
    assert set(pins['actual_qualification_originals']) == VARIABLES
    originals = {}
    for variable, proof in pins['actual_qualification_originals'].items():
        raw = Path(os.environ[variable]).read_bytes()
        assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256'], variable
        actual = json.loads(raw)
        if variable=='FIRST_SCOPED_MODEL_NATIVE_ORIGINAL_REPORT':
            assert actual['status']==proof['status']=='INCOMPLETE'
            assert actual['qualification_commit']==proof['head']=='862bedbaa04afa130b984c1f474f71d03d0380e6'
            assert actual['cp6_restored']and actual['advisor_gate']and actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
            assert actual['native']['counts']=={'PASS':29,'INCOMPLETE':1}and not actual['required_case_ids_pass']
            assert actual['required_case_ids']==list(ids)and actual['observed_case_count']==30
            assert actual['native']['cases']['OW11_MODEL_HISTORY_RUNTIME_ACTUAL_CAPTURE_REPLAY_IMMUTABLE']['status']=='INCOMPLETE'
            originals[variable]=dict(proof,observed_status=actual['status'])
            continue
        assert actual['status'] == proof['status'] == 'PASS'
        assert actual['cp6_restored'] and actual['advisor_gate']
        if variable == 'CURRENT_MODEL_HISTORY_ORIGINAL_REPORT':
            assert actual['qualification_commit'] == proof['head'] == frozen.FROZEN_HEAD
            assert actual['source_declaration']['current_installation'] == product.predecessor.sources()
            assert actual['source_declaration']['qualification'] == predecessor['qualification']
            assert actual['required_case_ids'] == list(business.previous.IDS)
            assert actual['required_case_ids_pass'] and actual['native']['counts'] == {'PASS': 25}
            assert actual['observed_case_count'] == 25 and actual['complete_preuse_removal']
            assert actual['baseline_full22_all_rows_all_sequences_equal'] and actual['baseline_advisors_equal']
            for row in actual['native']['cases'].values():
                assert row['full_boundary_restored'] and row['public_schema_unchanged']
        elif variable == 'CURRENT_MODEL_HISTORY_RESTORE_ORIGINAL_REPORT':
            assert (actual.get('qualification_commit') or actual.get('candidate_commit')) == proof['head']
            assert actual['source_declaration']['current_installation'] == product.predecessor.sources()
            assert len(actual['steps']) == 8 and actual['required_steps_pass']
            assert all(row['status'] == 'PASS' for row in actual['steps'])
            assert actual['restore_raw_public_equal']
        else:
            provider = PROVIDERS[variable]
            assert actual['required_case_ids'] == provider.IDS
            assert actual['required_case_ids_pass'] and actual['required_case_counts_pass']
            assert actual['observed_case_count'] == sum(map(len, provider.IDS.values()))
            source_sets = 0
            for key, sources in actual.items():
                if key.endswith('source_sha256') and isinstance(sources, dict):
                    source_sets += 1
                    for path, digest in sources.items():
                        relative = source_path(key, path)
                        assert sha256((repo / relative).read_bytes()).hexdigest() == digest, (variable, relative)
            assert source_sets > 0
            for group, names in provider.IDS.items():
                observed = actual[group]
                cases = observed.get('races' if group == 'races' else 'cases', {})
                assert observed['counts'] == {'PASS': len(names)} and set(cases) == set(names)
                assert all(row['status'] == 'PASS' for row in cases.values())
                if group == 'native':
                    assert observed['complete_boundary_restored']
                    for row in cases.values():
                        assert row['full_boundary_restored'] and row['public_schema_unchanged']
                else:
                    assert observed['database_remaining'] == 0 and not observed.get('session_leaks')
                    assert not observed.get('cleanup_failures')
                    if group in ('http', 'browser'):
                        assert observed['real_auth']
                        assert observed['auth_counts'] == dict(before=[0, 0, 0, 0], after=[0, 0, 0, 0], restored=True)
                    if group == 'browser':
                        assert observed['host_exit'] == 0 and observed['console_errors'] == 0
        originals[variable] = dict(proof, observed_status=actual['status'])
    loaded = []
    for name, module in tuple(sys.modules.items()):
        if name.startswith(('cp6_', 'cp7_sales_')) and getattr(module, '__file__', None):
            path = Path(module.__file__)
            assert sha256(path.read_bytes()).hexdigest() == pins['files']['scripts/' + path.name]
            loaded.append(name)
    binding=business.source_binding()
    assert binding['explicit_history_replay_guard']['explicit_AST_changes']==dict(rollback_calls=1,refusal_constants=1)
    return dict(qualified_current_history=predecessor, current_installation=product.sources(),
                qualification=pins, actual_originals_verified=originals,
                actual_loaded_modules_verified=loaded, retained_business_cases=business.source_binding(),
                production_go=False, independent_acceptance=False)
