"""Move one canonical Actions ZIP in bounded pieces without changing its bytes.

No ERP imports, database access, archive extraction, or qualification credit.
The expected identity is supplied only after the original run is terminal.
"""
from hashlib import file_digest, sha256
from pathlib import Path, PurePosixPath
import argparse
import json
import re
import subprocess
import zipfile

CHUNK_BYTES = 256 * 1024 * 1024
MAX_PARTS = 4
REPOSITORY = 'Hanjay6688/-erp-garment-ux'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def exact(actual, expected, reason):
    require(type(actual) is type(expected), reason + ':TYPE')
    if type(expected) is dict:
        require(set(actual) == set(expected), reason + ':KEYS')
        for key in expected:
            exact(actual[key], expected[key], reason + '/' + key)
    elif type(expected) is list:
        require(len(actual) == len(expected), reason + ':LENGTH')
        for index, (left, right) in enumerate(zip(actual, expected)):
            exact(left, right, reason + '/' + str(index))
    else:
        require(actual == expected, reason + ':VALUE')


def read_json(path):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'DUPLICATE_JSON_KEY')
            value[key] = item
        return value

    def constant(value):
        raise ValueError('NONFINITE_JSON: ' + value)

    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs, parse_constant=constant)


def identity(value):
    require(type(value) is dict and set(value) == {
        'repository', 'head', 'tree', 'run_id', 'job_id', 'run_attempt',
        'artifact_id', 'artifact_name', 'archive'}, 'CLOSED_ORIGINAL_IDENTITY_REQUIRED')
    exact(value['repository'], REPOSITORY, 'EXACT_REPOSITORY_REQUIRED')
    for key in ('head', 'tree'):
        require(type(value[key]) is str and re.fullmatch('[0-9a-f]{40}', value[key]), 'FULL_' + key.upper())
    for key in ('run_id', 'job_id', 'run_attempt', 'artifact_id'):
        require(type(value[key]) is int and value[key] > 0, 'POSITIVE_INTEGER_' + key.upper())
    require(type(value['artifact_name']) is str and value['artifact_name'], 'ARTIFACT_NAME_REQUIRED')
    archive = value['archive']
    require(type(archive) is dict and set(archive) == {'bytes', 'sha256'}, 'CLOSED_ARCHIVE_PIN_REQUIRED')
    require(type(archive['bytes']) is int and 0 < archive['bytes'] <= MAX_PARTS * CHUNK_BYTES,
            'ARCHIVE_SIZE_OUTSIDE_TRANSPORT_BUDGET')
    require(type(archive['sha256']) is str and re.fullmatch('[0-9a-f]{64}', archive['sha256']), 'ARCHIVE_SHA256_REQUIRED')
    return value


def pin(path):
    with Path(path).open('rb') as stream:
        digest = file_digest(stream, 'sha256').hexdigest()
    return dict(bytes=Path(path).stat().st_size, sha256=digest)


def verify_archive(path, expected):
    exact(pin(path), expected, 'CANONICAL_ARCHIVE_BYTES_OR_SHA_CHANGED')
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'DUPLICATE_CANONICAL_MEMBER')
        for name in names:
            relative = PurePosixPath(name)
            require(name and not relative.is_absolute() and '..' not in relative.parts
                    and str(relative) == name, 'UNSAFE_CANONICAL_MEMBER')
        require(archive.testzip() is None, 'CANONICAL_ZIP_CRC_FAILURE')
        return len(names)


def split_archive(path, expected, destination, *, chunk_bytes=CHUNK_BYTES):
    identity(expected)
    require(type(chunk_bytes) is int and 0 < chunk_bytes <= CHUNK_BYTES, 'CHUNK_BUDGET_REQUIRED')
    members = verify_archive(path, expected['archive'])
    require((expected['archive']['bytes'] + chunk_bytes - 1) // chunk_bytes <= MAX_PARTS, 'TOO_MANY_PARTS')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    parts, offset, whole = [], 0, sha256()
    with Path(path).open('rb') as stream:
        for index in range(MAX_PARTS):
            raw = stream.read(chunk_bytes)
            if not raw:
                break
            name = 'original.part-' + str(index)
            with (destination / name).open('xb') as output:
                output.write(raw)
            parts.append(dict(name=name, index=index, offset=offset, bytes=len(raw), sha256=sha256(raw).hexdigest()))
            whole.update(raw)
            offset += len(raw)
        require(not stream.read(1), 'ORIGINAL_NOT_FULLY_SPLIT')
    exact(offset, expected['archive']['bytes'], 'SPLIT_TOTAL_BYTES_CHANGED')
    exact(whole.hexdigest(), expected['archive']['sha256'], 'ORIGINAL_CHANGED_DURING_SPLIT')
    manifest = dict(status='CANONICAL_ARCHIVE_SPLIT_WITHOUT_REPACKING', original=expected,
        parts=parts, canonical_member_count=members, zip_crc_valid=True, safe_unique_members=True,
        ERP_execution=False, actual_case_credit=0)
    with (destination / 'TRANSPORT_MANIFEST.json').open('x') as output:
        output.write(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    return manifest


def join_archive(expected, manifest, directory, output):
    identity(expected)
    exact(manifest.get('status'), 'CANONICAL_ARCHIVE_SPLIT_WITHOUT_REPACKING', 'TRANSPORT_STATUS_CHANGED')
    exact(manifest.get('original'), expected, 'TRANSPORT_ORIGINAL_IDENTITY_CHANGED')
    exact(manifest.get('zip_crc_valid'), True, 'TRANSPORT_ZIP_CRC_NOT_PROVEN')
    exact(manifest.get('safe_unique_members'), True, 'TRANSPORT_MEMBERS_NOT_PROVEN')
    exact(manifest.get('ERP_execution'), False, 'TRANSPORT_MUST_NOT_EXECUTE_ERP')
    exact(manifest.get('actual_case_credit'), 0, 'TRANSPORT_MUST_NOT_AWARD_CASE_CREDIT')
    parts = manifest.get('parts')
    require(type(parts) is list and 0 < len(parts) <= MAX_PARTS, 'BOUNDED_ORDERED_PARTS_REQUIRED')
    directory = Path(directory).resolve()
    offset = 0
    for index, part in enumerate(parts):
        require(type(part) is dict and set(part) == {'name', 'index', 'offset', 'bytes', 'sha256'}, 'CLOSED_PART_REQUIRED')
        exact(part['name'], 'original.part-' + str(index), 'PART_NAME_OR_ORDER_CHANGED')
        exact(part['index'], index, 'PART_INDEX_CHANGED')
        exact(part['offset'], offset, 'PART_OFFSET_CHANGED')
        require(type(part['bytes']) is int and 0 < part['bytes'] <= CHUNK_BYTES, 'PART_BYTES_INVALID')
        path = directory / part['name']
        require(not path.is_symlink() and path.is_file(), 'REGULAR_PART_REQUIRED')
        exact(pin(path), dict(bytes=part['bytes'], sha256=part['sha256']), 'PART_BYTES_OR_SHA_CHANGED')
        offset += part['bytes']
    exact(offset, expected['archive']['bytes'], 'JOIN_TOTAL_BYTES_CHANGED')
    # Refuse an existing destination, including a symlink. Every part was
    # checked before any output is created; the final SHA covers byte order.
    with Path(output).open('xb') as target:
        for part in parts:
            with (directory / part['name']).open('rb') as stream:
                while raw := stream.read(1024 * 1024):
                    target.write(raw)
    members = verify_archive(output, expected['archive'])
    exact(members, manifest['canonical_member_count'], 'CANONICAL_MEMBER_COUNT_CHANGED')
    return dict(status='EXACT_CANONICAL_ARCHIVE_REASSEMBLED', original=expected,
        canonical_member_count=members, ERP_execution=False, actual_case_credit=0)


def api(path):
    raw = subprocess.check_output(['gh', 'api', '-H', 'Accept: application/vnd.github+json',
        '-H', 'X-GitHub-Api-Version: 2022-11-28', 'repos/' + REPOSITORY + '/' + path], timeout=60)
    return json.loads(raw)


def fetch_and_split(expected, directory):
    identity(expected)
    run = api('actions/runs/' + str(expected['run_id']))
    for key, wanted in dict(id=expected['run_id'], head_sha=expected['head'], run_attempt=expected['run_attempt'],
                            status='completed', conclusion='success').items():
        exact(run.get(key), wanted, 'TERMINAL_RUN_' + key.upper())
    exact(run['repository']['full_name'], REPOSITORY, 'RUN_REPOSITORY_CHANGED')
    commit = api('git/commits/' + expected['head'])
    exact(commit['tree']['sha'], expected['tree'], 'ACTUAL_TREE_CHANGED')
    job = api('actions/jobs/' + str(expected['job_id']))
    for key, wanted in dict(id=expected['job_id'], run_id=expected['run_id'], head_sha=expected['head'],
                            status='completed', conclusion='success').items():
        exact(job.get(key), wanted, 'TERMINAL_JOB_' + key.upper())
    artifact = api('actions/artifacts/' + str(expected['artifact_id']))
    for key, wanted in dict(id=expected['artifact_id'], name=expected['artifact_name'], expired=False,
                            size_in_bytes=expected['archive']['bytes'], digest='sha256:' + expected['archive']['sha256']).items():
        exact(artifact.get(key), wanted, 'IMMUTABLE_ARTIFACT_' + key.upper())
    exact(artifact['workflow_run']['id'], expected['run_id'], 'ARTIFACT_RUN_CHANGED')
    exact(artifact['workflow_run']['head_sha'], expected['head'], 'ARTIFACT_HEAD_CHANGED')
    directory = Path(directory)
    original = directory.parent / 'ORIGINAL.zip'
    with original.open('xb') as stream:
        subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github+json',
            '-H', 'X-GitHub-Api-Version: 2022-11-28',
            'repos/' + REPOSITORY + '/actions/artifacts/' + str(expected['artifact_id']) + '/zip'],
            stdout=stream, check=True, timeout=900)
    return split_archive(original, expected, directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('fetch-split', 'split', 'join'))
    parser.add_argument('--expected', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    expected = identity(read_json(args.expected))
    if args.operation == 'fetch-split':
        result = fetch_and_split(expected, args.directory)
    elif args.operation == 'split':
        require(args.archive is not None, 'ARCHIVE_PATH_REQUIRED')
        result = split_archive(args.archive, expected, args.directory)
    else:
        require(args.archive is not None, 'ARCHIVE_PATH_REQUIRED')
        result = join_archive(expected, read_json(args.directory / 'TRANSPORT_MANIFEST.json'), args.directory, args.archive)
    print(json.dumps(dict(status=result['status'], part_count=len(result.get('parts', [])),
        archive_bytes=expected['archive']['bytes'], ERP_execution=False, actual_case_credit=0)))


if __name__ == '__main__':
    main()
