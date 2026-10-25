"""Admit corrected full Native20 and original full target restore8 evidence."""
from pathlib import Path
from hashlib import sha256
import importlib.util, json, os, subprocess


def admitted(repo, here, steps, product, recovery):
    spec = importlib.util.spec_from_file_location('selected_restore_refusal_guard',here/'selected_refusal.py')
    refusal = importlib.util.module_from_spec(spec);spec.loader.exec_module(refusal)
    spec = importlib.util.spec_from_file_location('selected_restore_retained_business',repo/'scripts/draft-return-isolation-qualification/cases.py')
    business = importlib.util.module_from_spec(spec);spec.loader.exec_module(business)
    refusal_binding=refusal.source_binding(business)
    spec = importlib.util.spec_from_file_location('selected_return_native20_gate',
        repo / 'scripts/current-selected-return-native-qualification/probe.py')
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    predecessor = native.admitted()
    assert predecessor['current_installation'] == product.sources()
    pins = json.loads((here / 'SOURCE.json').read_bytes())
    assert pins['contract'] == 'cp7.current-selected-return-used-restore8-qualification.v1'
    assert pins['required_steps'] == list(steps) and len(steps) == 8
    for path, digest in pins['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--', str(here)], text=True).strip()
    for name in ('fixture.py', 'opening_fixture.py', 'finance_fixture.py', 'model_fixture.py', 'target_fixture.py'):
        assert (here / name).read_bytes() == (repo / 'scripts/current-model-target-used-restore-qualification' / name).read_bytes()
    proofs = pins['actual_qualification_originals']
    assert set(proofs) == {'CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT', 'CURRENT_MODEL_TARGET_RESTORE_ORIGINAL_REPORT'}
    originals = {}
    for variable, proof in proofs.items():
        raw = Path(os.environ[variable]).read_bytes()
        assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256']
        actual = json.loads(raw)
        assert actual['status'] == proof['status'] == 'PASS' and actual['cp6_restored'] and actual['advisor_gate']
        assert (actual.get('qualification_commit') or actual.get('candidate_commit')) == proof['head']
        assert actual['baseline_full22_all_rows_all_sequences_equal'] and actual['baseline_advisors_equal']
        if variable == 'CURRENT_SELECTED_RETURN_NATIVE_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation'] == product.sources()
            assert actual['source_declaration']['qualification'] == predecessor['qualification']
            assert actual['native']['counts'] == {'PASS': 20} and actual['observed_case_count'] == 20
            assert actual['required_case_ids_pass'] and actual['required_case_ids'] == list(native.IDS)
            assert actual['complete_preuse_removal']
            for row in actual['native']['cases'].values():
                assert row['full_boundary_restored'] and row['public_schema_unchanged']
        else:
            assert actual['source_declaration']['current_installation'] == product.predecessor.sources()
            assert actual['required_steps_pass'] and actual['required_steps'] == list(steps)
            assert [row['step'] for row in actual['steps']] == list(steps)
            assert all(row['status'] == 'PASS' for row in actual['steps'])
            target = actual['dated_target_full_restore_checks']
            assert len(target) == 4 and all(row['exact_all_stored_columns_UTC'] and row['same_UUID_one_baseline_run'] for row in target)
            model = actual['model_full_restore_checks']
            assert len(model) == 4 and all(row['exact_immutable_v1_v2_input_assessment_payload'] and row['old_UUID_no_duplicate'] for row in model)
            finance = actual['finance_full_restore_checks']
            assert [row['label'] for row in finance] == ['BEFORE_RESTORED_CLEAR', 'AFTER_NEXT_NATIVE_RETURN']
            assert all(row['exact_capture_report_provenance_and_operational_pages'] and row['READY_read_and_same_UUID_replay'] and row['captures_for_job'] == 1 for row in finance)
        originals[variable] = dict(proof, observed_status='PASS')
    return dict(qualified_selected_return_native=predecessor, current_installation=product.sources(),
                recovery=recovery.sources(), qualification=pins, actual_originals_verified=originals,
                retained_refusal_business_source=refusal_binding,
                production_go=False, independent_acceptance=False)
