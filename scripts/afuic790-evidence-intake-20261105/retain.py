"""Read-only export of one completed Afui run; never imports ERP or uses SQL."""
from hashlib import sha256, file_digest
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import gzip
import base64
import json
import os
import re
import sys
import stat
import urllib.error
import urllib.request
import zipfile

REPO = 'Hanjay6688/-erp-garment-ux'
RUN = 41968344868
JOB = 127050501104
HEAD = 'c790a7e42cd3389c4bf1631cb9413ae2f1f9f9fc'
BRANCH = 'astra-a/afui-good-nonpayable-20261102'
ARTIFACT_NAME = 'cp7-afui-good-nonpayable-full15-1'
# Filled only by the exact terminal run/job and canonical artifact API checks.
ARTIFACT = SIZE = DIGEST = None
PART_BYTES = 400 * 1024 * 1024
MAX_PARTS = 16
DIRECTORY = 'afuic790-evidence-intake-20261105'
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
    require(type(part_bytes) is int and 0 < part_bytes <= PART_BYTES
            and 0 < source_pin['bytes'] <= part_bytes * MAX_PARTS, 'BOUNDED_COMPLETE_SOURCE_PART_COUNT_REQUIRED')
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


def original_context(root, out):
    global ARTIFACT, SIZE, DIGEST
    run = metadata(f'/repos/{REPO}/actions/runs/{RUN}', out / 'SOURCE_RUN_API.json')
    require(run['id'] == RUN and run['head_sha'] == HEAD and run['run_attempt'] == 1
            and run['head_branch'] == BRANCH and run['status'] == 'completed'
            and run['conclusion'] in ('success', 'failure'), 'EXACT_TERMINAL_CURRENT_OWNING_RUN_REQUIRED')
    jobs = metadata(f'/repos/{REPO}/actions/runs/{RUN}/jobs?per_page=100&page=1', out / 'SOURCE_JOBS_API.json')
    require(jobs['total_count'] == len(jobs['jobs']) and len(jobs['jobs']) <= 100,
            'COMPLETE_CURRENT_SOURCE_JOB_LIST_REQUIRED')
    owners = [x for x in jobs['jobs'] if x['id'] == JOB]
    require(len(owners) == 1, 'ONE_EXACT_CURRENT_SOURCE_JOB_REQUIRED')
    job = owners[0]
    require(job['id'] == JOB and job['run_id'] == RUN and job['head_sha'] == HEAD and job['run_attempt'] == 1
            and job['status'] == 'completed' and job['conclusion'] == run['conclusion'],
            'EXACT_TERMINAL_CURRENT_OWNING_JOB_REQUIRED')
    artifacts = []
    for page in range(1, 11):
        data = metadata(f'/repos/{REPO}/actions/runs/{RUN}/artifacts?per_page=100&page={page}',
                        out / f'SOURCE_ARTIFACTS_PAGE_{page:03d}.json')
        require(type(data['total_count']) is int and 0 < data['total_count'] <= 1000,
                'BOUNDED_COMPLETE_CURRENT_ARTIFACT_LIST_REQUIRED')
        artifacts.extend(data['artifacts'])
        if len(artifacts) >= data['total_count']:
            break
    require(len(artifacts) == data['total_count'] and len({x['id'] for x in artifacts}) == len(artifacts),
            'EVERY_UNIQUE_CURRENT_ARTIFACT_API_PAGE_REQUIRED')
    selected = [x for x in artifacts if x['name'] == ARTIFACT_NAME]
    require(len(selected) == 1, 'ONE_CANONICAL_FINAL_CURRENT_ORIGINAL_REQUIRED')
    candidate = selected[0]
    require(type(candidate['id']) is int and candidate['id'] > 0, 'CANONICAL_FINAL_ARTIFACT_ID_REQUIRED')
    meta = metadata(f"/repos/{REPO}/actions/artifacts/{candidate['id']}", out / 'SOURCE_ARTIFACT_API.json')
    require(meta['id'] == candidate['id'] and meta['name'] == ARTIFACT_NAME
            and meta['workflow_run']['id'] == RUN and meta['workflow_run']['head_sha'] == HEAD
            and meta['workflow_run']['head_branch'] == BRANCH and meta['expired'] is False
            and type(meta['size_in_bytes']) is int and 0 < meta['size_in_bytes'] <= PART_BYTES * MAX_PARTS
            and re.fullmatch('sha256:[a-f0-9]{64}', meta['digest'])
            and all(meta[k] == candidate[k] for k in ('id', 'name', 'size_in_bytes', 'digest', 'workflow_run')),
            'EXACT_CANONICAL_SOURCE_ARTIFACT_REQUIRED')
    observed = (meta['id'], meta['size_in_bytes'], meta['digest'][7:])
    require(ARTIFACT is None or observed == (ARTIFACT, SIZE, DIGEST), 'FIRST_CANONICAL_SOURCE_IDENTITY_MUST_NOT_CHANGE')
    ARTIFACT, SIZE, DIGEST = observed


def core():
    root = Path(DIRECTORY);root.mkdir(exist_ok=True)
    out = root / 'core';out.mkdir();original_context(root, out)
    original = root / 'COMPLETE_SOURCE_JOB.log'
    with api(f'/repos/{REPO}/actions/jobs/{JOB}/logs') as source, original.open('xb') as target:
        actual = copy_stream(source, target)
    save(out / 'SOURCE_JOB_LOG_PIN.json', actual)
    selected, diagnostic, long_lines = [], [], 0
    wanted = {'AFUI_RUNTIME_SUPERVISION.json', 'CP7_AFUI_GOOD_NONPAYABLE_FULL15.json'}
    with original.open('rb') as stream:
        while True:
            line = stream.readline(512 * 1024 * 1024 + 1)
            if not line:
                break
            if not line.endswith(b'\n') and len(line) > 512 * 1024 * 1024:
                long_lines += 1
                while line and not line.endswith(b'\n'):
                    line = stream.readline(1024 * 1024)
                continue
            if len(line) < 16000 and any(k in line for k in (b'NONPAYABLE_', b'Traceback', b'BROWSER_GROUP',
                    b'SESSION_GROUP', b'Error:', b'ValueError', b' File ', b'RAISED')):
                diagnostic.append(line.decode('utf-8', errors='replace').rstrip('\n'))
            if b'"ow04_original_report_bytes": true' not in line[:2048]:
                continue
            prefix = line.find(b'{');header = line[prefix:prefix + 1024]
            if not any(('"name": "' + name + '"').encode() in header for name in wanted):
                continue
            value = json.loads(line[prefix:]);name = value['name']
            require(name not in {v['original_name'] for v in selected}, 'DUPLICATE_LOG_RECEIPT_REFUSED')
            packed = base64.b64decode(value['gzip_base64'], validate=True)
            require(dict(bytes=len(packed), sha256=sha256(packed).hexdigest()) ==
                    dict(bytes=value['gzip_bytes'], sha256=value['gzip_sha256']), 'EXACT_COMPLETE_LOG_RECEIPT_GZIP_REQUIRED')
            target = out / (name + '.original.gz')
            with target.open('xb') as output:
                output.write(packed)
            digest, count = sha256(), 0
            with gzip.open(target, 'rb') as uncompressed:
                while chunk := uncompressed.read(4 * 1024 * 1024):
                    count += len(chunk);digest.update(chunk)
            require(dict(bytes=count, sha256=digest.hexdigest()) == dict(bytes=value['raw_bytes'], sha256=value['raw_sha256']),
                    'EXACT_COMPLETE_UNCOMPRESSED_LOG_ORIGINAL_REQUIRED')
            selected.append(dict(original_name=name, original=dict(bytes=count, sha256=digest.hexdigest()),
                retained_name=target.name, gzip=pin(target)))
            del value, packed, line
    save(out / 'DIAGNOSTIC_SELECTED_SHORT_LOG_LINES.json', dict(classification='DIAGNOSTIC_EXCERPT_NOT_COMPLETE_ORIGINAL',
        lines=diagnostic[-500:], skipped_long_lines=long_lines, source_complete_log=actual, financial_acceptance_credit=0))
    complete_log = out / 'COMPLETE_SOURCE_JOB.log.original.gz'
    with original.open('rb') as source, complete_log.open('xb') as target:
        with gzip.GzipFile(filename='', fileobj=target, mode='wb', compresslevel=6, mtime=0) as compressed:
            require(copy_stream(source, compressed) == actual, 'COMPLETE_SOURCE_JOB_LOG_BYTES_CHANGED')
    save(out / 'CORE_MANIFEST.json', dict(classification='EXACT_COMPLETE_ORIGINAL_REPORTS_FROM_COMPLETED_SOURCE_JOB_LOG',
        source_run_id=RUN, source_job_id=JOB, source_head=HEAD, source_attempt=1, source_log=actual,
        source_log_original=dict(retained_name=complete_log.name, original=actual, gzip=pin(complete_log)),
        selected_complete_originals=selected, financial_acceptance_credit=0, ERP_commands_executed=0))
    require({v['original_name'] for v in selected} == wanted, 'BOTH_COMPLETE_SOURCE_LOG_ORIGINAL_REPORTS_REQUIRED')
    require(sum(p.stat().st_size for p in out.iterdir()) < 450 * 1024 * 1024, 'CONNECTOR_SIZED_CORE_REQUIRED')
    print(json.dumps(dict(status='COMPLETE_CURRENT_ORIGINAL_AND_SUPERVISION_LOG_RECEIPTS_VERIFIED_NOT_ACCEPTANCE', reports=selected)))


def archive():
    root = Path(DIRECTORY);root.mkdir(exist_ok=True)
    out = root / 'diagnostics';out.mkdir();original_context(root, out)
    original = root / 'AFUI_COMPLETE_ORIGINAL.zip'
    with api(f'/repos/{REPO}/actions/artifacts/{ARTIFACT}/zip') as source, original.open('xb') as target:
        actual = copy_stream(source, target, SIZE)
    require(actual == dict(bytes=SIZE, sha256=DIGEST), 'COMPLETE_ORIGINAL_ARCHIVE_BYTES_CHANGED')
    save(out / 'SOURCE_ARCHIVE_PIN.json', actual)
    index, selected = [], []
    with zipfile.ZipFile(original) as archive:
        require(len(archive.infolist()) == len(set(archive.namelist())), 'DUPLICATE_ORIGINAL_MEMBER_REFUSED')
        require(archive.testzip() is None, 'COMPLETE_CANONICAL_SOURCE_ZIP_CRC_REQUIRED')
        seen = set()
        for member in archive.infolist():
            index.append(dict(name=member.filename, bytes=member.file_size, compressed_bytes=member.compress_size, crc32=member.CRC))
        save(out / 'ZIP_INDEX.json', index)
        for member in archive.infolist():
            name = PurePosixPath(member.filename)
            require(name.parts and not name.is_absolute() and '..' not in name.parts and '\\' not in member.filename
                    and not stat.S_ISLNK(member.external_attr >> 16), 'UNSAFE_ORIGINAL_MEMBER_REFUSED')
            if member.is_dir() or member.file_size > 8 * 1024 * 1024 or not (name.name in SELECTED or name.name.startswith('AFUI_') and
                    ('FIRST_FAILURE' in name.name or 'CLEANUP_FAILURE' in name.name)):
                continue
            seen.add(name.name)
            target = out / (sha256(member.filename.encode()).hexdigest() + '__' + name.name + '.original.gz')
            with archive.open(member) as source, target.open('xb') as stream:
                with gzip.GzipFile(filename='', fileobj=stream, mode='wb', compresslevel=6, mtime=0) as compressed:
                    raw = copy_stream(source, compressed, member.file_size)
            require(raw['bytes'] == member.file_size, 'COMPLETE_SELECTED_MEMBER_REQUIRED')
            selected.append(dict(original_name=member.filename, original=raw, retained_name=target.name, gzip=pin(target)))
    require(any(PurePosixPath(v['name']).name == 'CP7_AFUI_GOOD_NONPAYABLE_FULL15.json' for v in index)
            and 'AFUI_RUNTIME_SUPERVISION.json' in seen, 'COMPLETE_SOURCE_ARCHIVE_REPORTS_REQUIRED')
    parts = split(original, root, PART_BYTES, actual)
    manifest = dict(classification='EXACT_TERMINAL_CURRENT_AFUI_ORIGINAL_READ_ONLY_TRANSPORT_NO_ACCEPTANCE',
        source_repository=REPO, source_run_id=RUN, source_job_id=JOB, source_attempt=1, source_head=HEAD,
        source_artifact_id=ARTIFACT, complete_archive=actual, parts=parts, selected_complete_originals=selected,
        all_source_bytes_retained_once=True, exact_reassembly_hash_verified=True,
        full_archive_CRC_verified=True, ERP_commands_executed=0, financial_acceptance_credit=0,
        production_go=False, independent_acceptance=False)
    save(out / 'INTAKE_MANIFEST.json', manifest)
    for part in parts:
        save(root / f"part-{part['number']:03d}" / 'INTAKE_MANIFEST.json', manifest)
    require(sum(p.stat().st_size for p in out.iterdir()) < 450 * 1024 * 1024, 'CONNECTOR_SIZED_DIAGNOSTICS_REQUIRED')
    print(json.dumps(dict(status='COMPLETE_CURRENT_ORIGINAL_RETAINED_IN_BOUNDED_EXACT_PARTS', source=actual,
        parts=len(parts), selected_complete_originals=len(selected), ERP_commands_executed=0)))


if __name__ == '__main__':
    require(sys.argv[1:] == ['all'], 'ONE_FIXED_READ_ONLY_TERMINAL_EXPORT_REQUIRED')
    # Preserve the complete canonical archive first. A missing log receipt
    # cannot discard any successfully verified whole-archive part.
    archive()
    core()
