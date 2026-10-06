"""Corruption controls on retained reports; no Native execution or new credit."""
import copy
import gzip
import json
import tempfile
import zipfile
from pathlib import Path

from cp7_integration_originals import retain, sha


def main():
    root = Path(__file__).resolve().parents[1]
    original = root / 'docs/cp7/evidence/integration-ab4/11391278462'
    receipt = json.loads((original / 'RECEIPT.json').read_text())
    reports = {name: json.loads(gzip.decompress((original / info['file']).read_bytes()))
               for name, info in receipt['root_originals'].items()}
    runtime = 'CP7_P13_FINANCE_READ.json'
    native_case = reports[runtime]['native']['planned_case_ids'][0]
    controls = [
        ('wrong package source', 'PACKAGE_SOURCE', lambda d: d['T3_PACKAGE_INSTALL.json']['run_identity'].update(tool_head='0' * 40)),
        ('false package gate', 'PACKAGE_GATE', lambda d: d['T3_PACKAGE_INSTALL.json']['gate'].update(writer_runtime=False)),
        ('Auth residue', 'AUTH_CLEANUP', lambda d: d['T3_PACKAGE_INSTALL.json'].update(auth_users_after=1)),
        ('missing restore', 'RESTORE_ADVISOR_GATE', lambda d: d[runtime].update(cp6_restored=False)),
        ('case failure', 'CASE_FAILURE', lambda d: d[runtime]['native']['cases'][native_case].update(status='INCOMPLETE')),
        ('missing planned identity', 'CASE_ID_SET', lambda d: d[runtime]['native']['planned_case_ids'].pop()),
        ('duplicate identity', 'DUPLICATE_CASE_ID', lambda d: d[runtime]['native']['planned_case_ids'].append(native_case)),
        ('bad count', 'CASE_COUNTS', lambda d: d[runtime]['native'].update(counts={'PASS': 7})),
        ('reduced budget', 'FULL_CASE_BUDGET', lambda d: d[runtime].update(expected_case_count=11)),
        ('fixture JWT', 'REAL_AUTH_REQUIRED', lambda d: d[runtime]['http'].update(jwt_signed_by_runtime=True)),
        ('console error', 'BROWSER_CONSOLE', lambda d: d[runtime]['browser'].update(console_errors=1)),
        ('failed backup', 'BACKUP_RESTORE', lambda d: d['T3_BACKUP_RESTORE_DRILL.json'].update(status='INCOMPLETE')),
    ]
    with tempfile.TemporaryDirectory(prefix='cp7-retention-control-') as temporary:
        base = Path(temporary)

        def run(candidate, index):
            archive = base / (str(index) + '.zip')
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as target:
                for name, value in candidate.items():
                    target.writestr(name, json.dumps(value, ensure_ascii=False).encode('utf8'))
            # These repacked archives are explicit retention-test stand-ins,
            # never the original GitHub artifact or additional Native evidence.
            data = archive.read_bytes()
            metadata = {key: receipt[key] for key in ('id', 'name', 'run_id', 'workflow_name', 'workflow_path')}
            metadata.update(local_path=str(archive), size_in_bytes=len(data), digest='sha256:' + sha(data),
                            expired=False, workflow_run=dict(head_sha=receipt['source_commit'], id=receipt['run_id']))
            return retain(metadata, base / ('out-' + str(index)), receipt['source_commit'], receipt['source_tree'])

        assert run(reports, 'positive')['status'] == 'VERIFIED_COMPLETE_ORIGINALS_RETAINED'
        for index, (name, expected, mutate) in enumerate(controls):
            candidate = copy.deepcopy(reports)
            mutate(candidate)
            try:
                run(candidate, index)
            except AssertionError as error:
                assert str(error) == expected, (name, expected, str(error))
            else:
                raise AssertionError('CORRUPTION_NOT_DETECTED:' + name)
    print(json.dumps(dict(status='PASS', complete_original_positive_control=1,
                         corruption_controls=len(controls), actual_Native_access=False,
                         Native_execution_credit=0, independent_acceptance=False)))


if __name__ == '__main__':
    main()
