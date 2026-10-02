"""Retain exact reports from a completed Native artifact; execute no ERP work."""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from cp7_native_runtime_receipt import retain


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        # GitHub's bearer token must never accompany the storage redirect.
        return None


def project(manifest_path, destination):
    manifest = json.loads(Path(manifest_path).read_text())
    repository = manifest['repository']
    assert repository == 'Hanjay6688/-erp-garment-ux'
    assert manifest['expected_status'] == 'PASS'
    token = os.environ['GH_TOKEN']
    api = f'https://api.github.com/repos/{repository}'
    opener = urllib.request.build_opener(NoRedirect())

    def request(path):
        return opener.open(urllib.request.Request(api + path, headers={
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }), timeout=60)

    def read_json(path):
        with request(path) as response:
            return json.load(response)

    run = read_json(f"/actions/runs/{manifest['run_id']}")
    artifact = read_json(f"/actions/artifacts/{manifest['artifact_id']}")
    commit = read_json(f"/git/commits/{manifest['source_commit']}")
    assert run['head_sha'] == manifest['source_commit']
    assert run['status'] == 'completed' and run['conclusion'] == 'success'
    assert commit['tree']['sha'] == manifest['source_tree']
    assert artifact['workflow_run']['id'] == manifest['run_id']
    assert artifact['name'] == manifest['artifact_name'] and not artifact['expired']
    assert artifact['size_in_bytes'] == manifest['zip_bytes']
    assert artifact['digest'] == 'sha256:' + manifest['zip_sha256']

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination.parent / f"native-original-{manifest['artifact_id']}.zip"
    try:
        response = request(f"/actions/artifacts/{manifest['artifact_id']}/zip")
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise
        location = error.headers['Location']
        assert urllib.parse.urlsplit(location).scheme == 'https'
        # A new unauthenticated request, with no copied GitHub headers.
        response = urllib.request.urlopen(location, timeout=60)
    digest = hashlib.sha256()
    with response, archive.open('wb') as target:
        while block := response.read(1024 * 1024):
            digest.update(block)
            target.write(block)
    assert archive.stat().st_size == manifest['zip_bytes']
    assert digest.hexdigest() == manifest['zip_sha256']
    with zipfile.ZipFile(archive) as source:
        report = json.loads(source.read(manifest['runtime_report']))
    assert report['source_sha256'] == manifest['source_bundle_sha256']
    assert report['required_case_counts'] == manifest['required_case_counts']
    assert report['browser']['console_errors'] == 0
    metadata = {key: manifest[key] for key in (
        'run_id', 'job_id', 'artifact_id', 'artifact_name', 'source_commit',
        'source_tree', 'zip_bytes', 'zip_sha256', 'runtime_report',
        'expected_status', 'expected_case_count',
    )}
    metadata['zip_verification_runtime'] = 'GITHUB_ACTIONS_READ_ONLY_ARTIFACT_PROJECTION'
    receipt = retain(archive, metadata, destination)
    projection = dict(
        contract='cp7.exact-native-artifact-projection.v1',
        status='EXACT_ORIGINAL_REPORTS_RETAINED',
        original_run_id=manifest['run_id'], original_artifact_id=manifest['artifact_id'],
        original_source_commit=manifest['source_commit'],
        original_source_tree=manifest['source_tree'],
        original_zip_sha256=digest.hexdigest(),
        report_receipt_sha256=hashlib.sha256((destination / 'RECEIPT.json').read_bytes()).hexdigest(),
        original_reports_gzip_sha256=receipt['original_reports_gzip_sha256'],
        projection_run_id=os.environ.get('GITHUB_RUN_ID'),
        projection_source_commit=os.environ.get('GITHUB_SHA'),
        Native_product_cases_reexecuted=0, Native_database_access=False,
        full_family_acceptance=False, independent_acceptance=False, production_go=False,
    )
    (destination / 'PROJECTION.json').write_text(json.dumps(projection, indent=2) + '\n')
    archive.unlink()
    print(json.dumps(projection))


if __name__ == '__main__':
    project(sys.argv[1], sys.argv[2])
