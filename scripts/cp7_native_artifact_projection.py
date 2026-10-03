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


def retain_requested_images(source, receipt, requested, destination):
    """Copy bounded exact PNG members after the whole Original ZIP is verified."""
    assert isinstance(requested, list) and len(requested) <= 8
    assert all(isinstance(name, str) and name == Path(name).name
               and name.endswith('.png') for name in requested)
    assert len(set(requested)) == len(requested)
    records = {}
    for name in requested:
        expected = receipt['all_zip_members'][name]
        assert 0 < expected['bytes'] <= 2 * 1024 * 1024
        raw = source.read(name)
        assert len(raw) == expected['bytes']
        assert hashlib.sha256(raw).hexdigest() == expected['sha256']
        assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        target = Path(destination) / 'images' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        records[name] = dict(expected, file='images/' + name,
                             original_bytes_unchanged=True,
                             visual_review='NOT_AUTOMATICALLY_QUALIFIED')
    return records


def verify_declared_case_counts(report, manifest):
    if 'required_case_counts' in report:
        assert report['required_case_counts'] == manifest['required_case_counts']
        return
    if manifest['expected_status'] == 'PASS':
        # Fixed analysis reports omit the redundant declared budget field.
        assert {g: report[g]['counts'] for g in manifest['required_case_counts']} == {
            g: {'PASS': n} for g, n in manifest['required_case_counts'].items()}
        return
    # A first incomplete fixed-analysis Original needs exact explicit counts;
    # preserve its failures rather than admitting it as a qualified report.
    assert report['status'] == manifest['expected_status'] == 'INCOMPLETE'
    counts = manifest['incomplete_case_counts']
    assert set(counts) == set(manifest['required_case_counts'])
    assert any(c.get('INCOMPLETE', 0) > 0 for c in counts.values())
    for group, budget in manifest['required_case_counts'].items():
        observed = report[group]['counts']
        assert observed == counts[group] and set(observed) <= {'PASS', 'INCOMPLETE'}
        assert all(type(n) is int and n > 0 for n in observed.values())
        assert sum(observed.values()) == budget
        cases = report[group]['races' if group == 'races' else 'cases']
        actual = {}
        for case in cases.values():
            actual[case['status']] = actual.get(case['status'], 0) + 1
        assert len(cases) == budget and actual == observed


def project(manifest_path, destination):
    manifest = json.loads(Path(manifest_path).read_text())
    repository = manifest['repository']
    assert repository == 'Hanjay6688/-erp-garment-ux'
    assert manifest['expected_status'] in ('PASS', 'INCOMPLETE')
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
    expected_conclusion = 'success' if manifest['expected_status'] == 'PASS' else 'failure'
    assert run['status'] == 'completed' and run['conclusion'] == expected_conclusion
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
    verify_declared_case_counts(report, manifest)
    if manifest['expected_status'] == 'PASS':
        assert report['browser']['console_errors'] == 0
    metadata = {key: manifest[key] for key in (
        'run_id', 'job_id', 'artifact_id', 'artifact_name', 'source_commit',
        'source_tree', 'zip_bytes', 'zip_sha256', 'runtime_report',
        'expected_status', 'expected_case_count',
    )}
    metadata['zip_verification_runtime'] = 'GITHUB_ACTIONS_READ_ONLY_ARTIFACT_PROJECTION'
    receipt = retain(archive, metadata, destination)
    with zipfile.ZipFile(archive) as source:
        images = retain_requested_images(source, receipt,
                                         manifest.get('image_members', []), destination)
    diagnostics = {}
    requested = manifest.get('diagnostic_members', [])
    optional = manifest.get('optional_diagnostic_members', [])
    if requested or optional:
        assert len(set(requested + optional)) == len(requested + optional)
        diagnostic_target = destination / 'diagnostics'
        diagnostic_target.mkdir()
        with zipfile.ZipFile(archive) as source:
            for member in requested + optional:
                assert member == Path(member).name and member.endswith(('_FAILURE.json', '_READ_PROFILE.json'))
                if member not in source.namelist() and member in optional:
                    continue
                raw = source.read(member)
                expected = receipt['all_zip_members'][member]
                assert len(raw) == expected['bytes']
                assert hashlib.sha256(raw).hexdigest() == expected['sha256']
                (diagnostic_target / member).write_bytes(raw)
                diagnostics[member] = expected
                if member.endswith('_FAILURE.json'):
                    diagnostic = json.loads(raw)
                    print(json.dumps(dict(exact_failure_diagnostic=member,
                                          original_error=diagnostic.get('error'),
                                          visible_panel_text=str(diagnostic.get('text', ''))[:12000]),
                                     ensure_ascii=False))
                elif member.endswith('_READ_PROFILE.json'):
                    profile = json.loads(raw)
                    public_metrics = {key: profile[key] for key in
                                      ('status', 'diagnostic_only', 'read_only', 'saved_runs_added',
                                       'Native_HTTP_timeout_changed', 'steps', 'sqlstate', 'error')
                                      if key in profile}
                    print(json.dumps(dict(exact_read_profile=member, metrics=public_metrics)))
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
        exact_failure_diagnostics=diagnostics,
        exact_original_images=images,
    )
    (destination / 'PROJECTION.json').write_text(json.dumps(projection, indent=2) + '\n')
    archive.unlink()
    print(json.dumps(projection))


if __name__ == '__main__':
    project(sys.argv[1], sys.argv[2])
