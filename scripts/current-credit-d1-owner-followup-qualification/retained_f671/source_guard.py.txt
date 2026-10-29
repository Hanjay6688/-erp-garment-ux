"""Declared exact sources. This is prepared qualification, not Native PASS."""
from hashlib import sha256
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = dict(published_commit='0770541c94937ee5013c8ea9ae607c99260d2993',
            equivalent_local_commit='8a8dcb8509f1d6b33600239521a9b157c81bf9bc',
            tree='b0f5a4d1ff6541874a09881519baacb86b91fa1f')
NAMESPACE = 'scripts/current-credit-d1-continuation-qualification/'


def admitted(root=ROOT):
    file = root / NAMESPACE / 'SOURCE.json'
    pins = json.loads(file.read_bytes())
    assert pins['base_candidate'] == BASE, 'D1_CONT_BASE_SOURCE_CHANGED'
    assert len(pins['case_ids']) == len(set(pins['case_ids'])) == 3, 'D1_CONT_THREE_CASES_REQUIRED'
    assert pins['status'] == 'PREPARED_NOT_ACTUAL_NATIVE_PASS'
    assert pins['prerequisite'] == 'EXACT_ACTUAL_NATIVE13_PASS_AND_OWNING_REPAIRED_INSTALLED_D1_STAGE'
    assert pins['D_complete'] is False and pins['E_complete'] is False and pins['production_go'] is False
    required = (NAMESPACE+'cases.py', NAMESPACE+'native_fixture.py', NAMESPACE+'oracle.py', NAMESPACE+'source_guard.py',
                'scripts/cp7_customer_credit/consumer/native_basic_cases.py',
                'scripts/cp7_customer_credit/consumer/native_refund_cases.py',
                'scripts/cp7_customer_credit/consumer/cp7_ow04_consumer_fixture.py',
                'scripts/cp7_credit_correction_de/cases.py', 'scripts/cp7_credit_correction_de/proof.sql',
                'scripts/current-credit-de-native-qualification/native_runner.py',
                'scripts/cp7_ow04_restore_bundle.py', 'scripts/cp6_auditor_runner.py',
                'scripts/cp7_customer_credit/kernel/kernel.sql')
    assert all(path in pins['files'] for path in required), 'D1_CONT_REQUIRED_SOURCE_PIN_MISSING'
    assert len(pins['D1_runtime_files']) == 9
    for path, expected in pins['files'].items():
        assert sha256((root/path).read_bytes()).hexdigest() == expected, ('D1_CONT_SOURCE_CHANGED', path)
    for name, expected in pins['D1_runtime_files'].items():
        assert pins['files']['scripts/cp7_credit_correction_de/'+name] == expected, 'D1_CONT_D1_STAGE_PIN_CHANGED'
    return dict(status='D1_CONT_PREPARED_EXACT_SOURCES_NOT_RUNTIME_PASS', base_candidate=pins['base_candidate'],
                source_files=len(pins['files']), source_manifest_sha256=sha256(file.read_bytes()).hexdigest(),
                case_ids=pins['case_ids'], actual_Native_execution=False, actual_Auth_browser=False,
                D_complete=False, E_complete=False, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    print(json.dumps(admitted(), indent=2))
