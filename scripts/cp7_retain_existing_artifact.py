"""Retain exact existing CI Originals without executing a product case.

Only manifest-pinned artifacts from this repository are read. The full archive
digest, source tree, run and job must match before reports are retained.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from cp7_native_runtime_receipt import retain


def main():
    assert len(sys.argv) == 3, 'Pinned record and output directory required'
    manifest = json.loads(Path(__file__).with_name('cp7_retained_artifact_manifest.json').read_text())
    assert manifest['contract'] == 'cp7.existing-native-artifact-retention.v1'
    repository = manifest['repository']
    assert repository == 'Hanjay6688/-erp-garment-ux' == os.environ['GITHUB_REPOSITORY']
    record = manifest['records'][sys.argv[1]]
    assert record['artifact_retention_only'] and record['new_execution_case_credit'] == 0
    assert sum(record['required_case_counts'].values()) == record['expected_case_count']

    def get(path):
        return json.loads(subprocess.check_output(['gh', 'api', 'repos/' + repository + '/' + path]))

    run = get('actions/runs/' + str(record['run_id']))
    assert run['head_sha'] == record['source_commit'] and run['status'] == 'completed'
    assert run['conclusion'] == ('success' if record['expected_status'] == 'PASS' else 'failure')
    commit = get('git/commits/' + record['source_commit'])
    assert commit['tree']['sha'] == record['source_tree']
    job = get('actions/jobs/' + str(record['job_id']))
    assert job['run_id'] == record['run_id'] and job['status'] == 'completed'
    assert job['conclusion'] == run['conclusion']
    artifact = get('actions/artifacts/' + str(record['artifact_id']))
    assert artifact['name'] == record['artifact_name'] and not artifact['expired']
    assert artifact['workflow_run']['id'] == record['run_id']
    assert artifact['workflow_run']['head_sha'] == record['source_commit']
    assert artifact['size_in_bytes'] == record['zip_bytes']
    assert artifact['digest'] == 'sha256:' + record['zip_sha256']
    destination = Path(sys.argv[2])
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'original-artifact.zip'
    with archive.open('wb') as output:
        subprocess.run(['gh', 'api', 'repos/' + repository + '/actions/artifacts/'
                        + str(record['artifact_id']) + '/zip'], stdout=output, check=True)
    digest = hashlib.sha256()
    with archive.open('rb') as original:
        while block := original.read(1024 * 1024):
            digest.update(block)
    assert archive.stat().st_size == record['zip_bytes'] and digest.hexdigest() == record['zip_sha256']
    receipt = retain(archive, record, destination / 'reports')
    assert receipt['counts'] == record['expected_counts']
    assert receipt['observed_case_count'] == record['expected_case_count']
    assert receipt['auth_users_before'] == receipt['auth_users_after'] == 0
    assert receipt['cp6_restored'] and all(receipt['restore_components'].values())
    assert receipt['advisor_gate'] and receipt['primary_unchanged']
    assert all(v for k, v in receipt['package_gate'].items() if k != 'writer_runtime')
    assert receipt['package_gate']['writer_runtime'] == (record['expected_status'] == 'PASS')
    print(json.dumps({'record': sys.argv[1], 'existing_run_id': record['run_id'],
                      'existing_case_count': receipt['observed_case_count'],
                      'new_execution_case_credit': 0, 'archive_digest_verified': True}))


if __name__ == '__main__':
    main()
