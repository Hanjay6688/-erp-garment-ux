"""Verify imported source bytes and the existing shell contract lock.

This receipt checks provenance and shape ownership, not ERP business execution.
It uses only the standard library and never rewrites the imported framework.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT/'docs/cp7/framework-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    verified = []
    for line in (FRAMEWORK/'SHA256SUMS.txt').read_text().splitlines():
        expected, name = line.split('  ', 1)
        path = (FRAMEWORK/name).resolve()
        assert path.is_relative_to(FRAMEWORK.resolve()), 'CONTRACT_PATH_OUTSIDE_BUNDLE'
        assert sha(path) == expected, ('ORIGINAL_FRAMEWORK_DRIFT', name)
        verified.append(name)
    assert len(verified) == 48, 'FRAMEWORK_HASH_MANIFEST_CHANGED'
    lock = {}
    for name in ('analysis.schema.json', 'analysis.example.json', 'backbone.ts',
                 'notification.ts', 'reasons.json', 'reminder.rules.json'):
        origin = FRAMEWORK/'contracts'/name
        shell = ROOT/'docs/cp7/contracts'/name
        assert origin.read_bytes() == shell.read_bytes(), ('SHELL_CONTRACT_DRIFT', name)
        lock[name] = sha(origin)
    for filename, origin in (('contract.ts', 'backbone.ts'),
                             ('notificationContract.ts', 'notification.ts'),
                             ('reasons.json', 'reasons.json')):
        assert (ROOT/'src/cp7'/filename).read_bytes() == (FRAMEWORK/'contracts'/origin).read_bytes()
    packets = json.loads((FRAMEWORK/'registries/work_packets.json').read_text())
    cases = json.loads((FRAMEWORK/'registries/cases.json').read_text())
    requirements = json.loads((FRAMEWORK/'registries/requirements.json').read_text())
    assert len(packets) == 22 and len(cases) == 84 and len(requirements) == 271
    assert all(case['erp_status'] == 'NOT_RUN' for case in cases)
    result = dict(status='PASS', scope='ORIGINAL_BYTES_AND_SHELL_CONTRACT_LOCK_ONLY',
                  original_files_verified=len(verified), contract_sha256=lock,
                  packets=22, cases=84, requirement_groups=271,
                  erp_case_verdict='NOT_RUN', production_go=False)
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    run()
