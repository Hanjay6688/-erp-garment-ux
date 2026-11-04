"""Read-only export of one completed Afui run; never imports ERP or uses SQL."""
from hashlib import sha256, file_digest
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import gzip
import json
import os
import stat
import urllib.error
import urllib.request
import zipfile

REPO = 'Hanjay6688/-erp-garment-ux'
RUN = 41878688074
JOB = 126745157733
ARTIFACT = 13367154838
HEAD = '92a376091a1d1ea9901648e614f3e5212677a81f'
SIZE = 2276307014
DIGEST = 'd04992f22e47eeaea136f68d94de3e0d121cb967b1a0b811fe86e14884f41e46'
PART_BYTES = 400 * 1024 * 1024
SELECTED = frozenset(('CP7_AFUI_GOOD_NONPAYABLE_FULL15.json', 'AFUI_RUNTIME_SUPERVISION.json',
    'AFUI_DURABLE_RUNTIME.json', 'AFUI_DURABLE_PREFLIGHT.json', 'AFUI_FINAL_GATE.json',
    'AFUI_BROWSER_SETTINGS_STATE.json', 'AFUI_BROWSER_NATIVE_PREREQUISITE.json',
    'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', 'T3_PACKAGE_FILES_INSTALL.json'))


def require(value, reason):
    if not value:
        raise ValueError(reason)


def pin(path):
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=file_digest(stream, 'sha256').hexdigest())


def save(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(route):
    require(route.startswith('/repos/' + REPO + '/actions/'), 'FIXED_REPOSITORY_ACTIONS_READ_ONLY_API')
    request = urllib.request.Request('https://api.github.com' + route,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'FixedAfuiEvidenceIntake'})
    try:
        return urllib.request.build_opener(NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code == 302:
            location = error.headers['Location'];parsed = urlsplit(location)
            require(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password,
                    'HTTPS_ARCHIVE_REDIRECT_REQUIRED')
            # No authenticated request or Authorization header crosses hosts.
            return urllib.request.urlopen(urllib.request.Request(location, headers={'User-Agent': 'FixedAfuiEvidenceIntake'}), timeout=60)
        raise ValueError('GITHUB_READ_HTTP_STATUS_' + str(error.code)) from None


def metadata(route, target):
    with api(route) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    require(len(raw) <= 4 * 1024 * 1024, 'BOUNDED_CANONICAL_METADATA_REQUIRED')
    with target.open('xb') as stream:
        stream.write(raw)
    return json.loads(raw)


def copy_stream(source, target, maximum=None):
    count, digest = 0, sha256()
    while True:
        chunk = source.read(4 * 1024 * 1024)
        if not chunk:
            return dict(bytes=count, sha256=digest.hexdigest())
        count += len(chunk)
        require(maximum is None or count <= maximum, 'ORIGINAL_BYTE_LIMIT_EXCEEDED')
        target.write(chunk);digest.update(chunk)


def split(path, destination, part_bytes, source_pin):
    require(pin(path) == source_pin, 'COMPLETE_SOURCE_ARCHIVE_MUST_MATCH_BEFORE_SPLIT')
    parts = []
    with path.open('rb') as stream:
        number = 0
        while True:
            chunk = stream.read(part_bytes)
            if not chunk:
                break
            number += 1;directory = destination / f'part-{number:03d}';directory.mkdir()
            target = directory / f'AFUI_COMPLETE_ORIGINAL_PART_{number:03d}.bin'
            with target.open('xb') as output:
                output.write(chunk)
            parts.append(dict(number=number, name=target.name, **pin(target)))
    require(sum(p['bytes'] for p in parts) == source_pin['bytes'], 'ALL_SOURCE_BYTES_MUST_BE_PRESENT_ONCE')
    digest = sha256()
    for part in parts:
        with (destination / f"part-{part['number']:03d}" / part['name']).open('rb') as stream:
            while chunk := stream.read(4 * 1024 * 1024):
                digest.update(chunk)
    require(digest.hexdigest() == source_pin['sha256'], 'EXACT_REASSEMBLY_HASH_REQUIRED_BEFORE_PUBLICATION')
    return parts


def main():
    root = Path('afui-evidence-intake-20261105');root.mkdir()
    out = root / 'diagnostics';out.mkdir()
    run = metadata(f'/repos/{REPO}/actions/runs/{RUN}', out / 'SOURCE_RUN_API.json')
    require(run['id'] == RUN and run['head_sha'] == HEAD and run['run_attempt'] == 1
            and run['status'] == 'completed' and run['conclusion'] == 'failure', 'EXACT_COMPLETED_FAILED_ORIGINAL_RUN_REQUIRED')
    meta = metadata(f'/repos/{REPO}/actions/artifacts/{ARTIFACT}', out / 'SOURCE_ARTIFACT_API.json')
    require(meta['id'] == ARTIFACT and meta['name'] == 'cp7-afui-good-nonpayable-full15-1'
            and meta['workflow_run']['id'] == RUN and meta['workflow_run']['head_sha'] == HEAD
            and meta['size_in_bytes'] == SIZE and meta['digest'] == 'sha256:' + DIGEST and meta['expired'] is False,
            'EXACT_CANONICAL_SOURCE_ARTIFACT_REQUIRED')
    original = root / 'AFUI_COMPLETE_ORIGINAL.zip'
    with api(f'/repos/{REPO}/actions/artifacts/{ARTIFACT}/zip') as source, original.open('xb') as target:
        actual = copy_stream(source, target, SIZE)
    require(actual == dict(bytes=SIZE, sha256=DIGEST), 'COMPLETE_ORIGINAL_ARCHIVE_BYTES_CHANGED')
    save(out / 'SOURCE_ARCHIVE_PIN.json', actual)
    index, selected = [], []
    with zipfile.ZipFile(original) as archive:
        require(len(archive.infolist()) == len(set(archive.namelist())), 'DUPLICATE_ORIGINAL_MEMBER_REFUSED')
        seen = set()
        for member in archive.infolist():
            name = PurePosixPath(member.filename)
            require(name.parts and not name.is_absolute() and '..' not in name.parts and '\\' not in member.filename
                    and not stat.S_ISLNK(member.external_attr >> 16), 'UNSAFE_ORIGINAL_MEMBER_REFUSED')
            index.append(dict(name=member.filename, bytes=member.file_size, compressed_bytes=member.compress_size, crc32=member.CRC))
            if member.is_dir() or not (name.name in SELECTED or name.name.startswith('AFUI_') and
                    ('FIRST_FAILURE' in name.name or 'CLEANUP_FAILURE' in name.name)):
                continue
            require(name.name not in seen, 'AMBIGUOUS_DIAGNOSTIC_ORIGINAL_REFUSED');seen.add(name.name)
            target = out / (name.name + '.original.gz')
            with archive.open(member) as source, target.open('xb') as stream:
                with gzip.GzipFile(filename='', fileobj=stream, mode='wb', compresslevel=6, mtime=0) as compressed:
                    raw = copy_stream(source, compressed, member.file_size)
            require(raw['bytes'] == member.file_size, 'COMPLETE_SELECTED_MEMBER_REQUIRED')
            selected.append(dict(original_name=member.filename, original=raw, retained_name=target.name, gzip=pin(target)))
    require('CP7_AFUI_GOOD_NONPAYABLE_FULL15.json' in seen and 'AFUI_RUNTIME_SUPERVISION.json' in seen,
            'COMPLETE_ORIGINAL_FAILURE_AND_SUPERVISION_REPORTS_REQUIRED')
    save(out / 'ZIP_INDEX.json', index)
    parts = split(original, root, PART_BYTES, actual)
    manifest = dict(classification='EXACT_COMPLETED_FAILED_AFUI_ORIGINAL_READ_ONLY_TRANSPORT_NO_ACCEPTANCE',
        source_repository=REPO, source_run_id=RUN, source_job_id=JOB, source_attempt=1, source_head=HEAD,
        source_artifact_id=ARTIFACT, complete_archive=actual, parts=parts, selected_complete_originals=selected,
        all_source_bytes_retained_once=True, exact_reassembly_hash_verified=True,
        full_archive_CRC_not_yet_verified=True, ERP_commands_executed=0, financial_acceptance_credit=0,
        production_go=False, independent_acceptance=False)
    save(out / 'INTAKE_MANIFEST.json', manifest)
    for part in parts:
        save(root / f"part-{part['number']:03d}" / 'INTAKE_MANIFEST.json', manifest)
    require(sum(p.stat().st_size for p in out.iterdir()) < 450 * 1024 * 1024, 'CONNECTOR_SIZED_DIAGNOSTICS_REQUIRED')
    print(json.dumps(dict(status='COMPLETE_ORIGINAL_RETAINED_IN_SIX_EXACT_PARTS', source=actual,
        parts=len(parts), selected_complete_originals=len(selected), ERP_commands_executed=0)))


if __name__ == '__main__':
    main()
