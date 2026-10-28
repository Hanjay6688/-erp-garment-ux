"""Exact accepted parent and source-race evidence before any composed DB use."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import os
import subprocess


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def accepted_race(repo, proof, directory, current):
    raw = (directory / proof['name']).read_bytes()
    assert len(raw) == proof['bytes'] and sha256(raw).hexdigest() == proof['sha256']
    actual = json.loads(raw)
    assert actual['status'] == proof['status'] == 'PASS'
    assert actual['qualification_commit'] == proof['head']
    assert actual['production_go'] is actual['independent_acceptance'] is False
    source = json.loads((repo / 'scripts/current-finance-reader-source-race-qualification/SOURCE.json').read_bytes())
    assert actual['source_declaration']['qualification'] == source
    assert actual['source_declaration']['current_installation'] == current['predecessor']['predecessor']['predecessor']
    for path, digest in source['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    gate = json.loads((directory / 'T3_PACKAGE_INSTALL.json').read_bytes())['gate']
    assert gate == proof['package_gate'] == {k: True for k in (
        'installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')}
    for key in ('source_change_race_qualification', 'required_case_ids_pass', 'cp6_restored',
                'advisor_gate', 'baseline_full22_all_rows_all_sequences_equal',
                'baseline_advisors_equal', 'used_guard_refused_before_DDL'):
        assert actual[key] is True, key
    assert actual['complete_preuse_removal'] and actual['baseline_role_cleanup']['baseline_roles_exact']
    assert actual['observed_case_count'] == actual['expected_case_count'] == 1
    assert set(actual['committed']) == set(source['case_ids'])
    case = next(iter(actual['committed'].values()))
    assert case['status'] == 'PASS' and case['official_metrics_exact'] == 24
    for key in ('snapshot_change_detected_before_count_seal', 'failed_capture_immutable',
                'failed_result_refused', 'fresh_capture_ready', 'independent_book_signature',
                'fresh_recovery_full_unchanged_official_report_equal'):
        assert case[key] is True, key
    return dict(head=proof['head'], sha256=proof['sha256'], actual_status='PASS',
                source_race_and_full_restore_accepted=True, all_package_gates=True)


def admitted(repo, here, ids, product, native):
    prerequisite = product.prerequisites()
    pins = json.loads((here / 'SOURCE.json').read_bytes())
    assert pins['contract'] == 'cp7.d17-18.readonly-finance-composition-native13-cron1.v1'
    assert pins['case_ids'] == list(ids) and len(ids) == len(set(ids)) == 14
    assert pins['source_race_receipt'] == prerequisite['source_race']
    assert pins['production_go'] is pins['independent_acceptance'] is False
    for path, digest in pins['files'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
    changed = subprocess.check_output(['git', '-C', str(repo), 'diff', '--name-only', pins['merge_head'], 'HEAD'], text=True).splitlines()
    assert all(p.startswith('scripts/current-finance-readonly-integration-qualification/')
               or p == '.github/workflows/cp7-d17-18-readonly-finance-composition.yml' for p in changed)
    guard = load('readonly_composition_probe_guard', here / 'source_guard.py').check(repo, here)
    selected = load('readonly_composition_cases_guard', here / 'cases.py').source_binding()
    parent = load('readonly_composition_actual_UI_parent', repo / 'scripts/current-progress-finance-ui-browser-qualification/probe.py').admitted()
    current = product.sources()
    assert parent['current_installation'] == current['predecessor']
    predecessor, _, _, _ = product.runtime()
    previous = json.loads((repo / 'scripts/current-choice-finance-cron-qualification/SOURCE.json').read_bytes())
    checker = load('readonly_composition_parent_evidence', repo / 'scripts/current-choice-finance-cron-qualification/evidence.py')
    checked = {kind: checker.checked(repo, proof, os.environ[proof['directory_variable']], predecessor, parent)
               for kind, proof in previous['actual_originals'].items()}
    race = accepted_race(repo, prerequisite['source_race'],
                         Path(os.environ['D17_18_COMPOSED_RACE_DIRECTORY']), current['predecessor'])
    return dict(qualification=pins, current_installation=current, qualified_current_UI=parent,
                accepted_parent_originals=checked, accepted_source_race=race,
                retained_native_cases=selected, focused_probe_guard=guard,
                focused_preuse_delta_only=True, full_parent_inverse_repeated=False,
                full_parent_preuse_retained_from_accepted_original=True,
                default_adopted=False, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    probe = load('readonly_composition_probe_admission', here / 'probe.py')
    result = probe.admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED', pins=len(result['qualification']['files']),
                          prepared_cases=14, actual_cases_executed=False)))
