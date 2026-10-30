"""Closed non-source output rules for the unchanged frozen CI producers.

These receipts never authorize a source, Original, install or business result.
Every authoritative Original reader still verifies its own full bytes/hash.
"""
from pathlib import Path, PurePosixPath
from hashlib import sha256
from datetime import datetime, timezone
import json
import math
import re
import stat
import uuid

CONTRACT = 'GENERATED_RECEIPTS.json'
FROZEN = 'cp6-proof/t3/FROZEN_SOURCE_WORKTREES.json'
PREFIX = 'cp6-proof/t3/ARTIFACT_FETCH/'
NAME = re.compile(r'^([0-9a-f]{32})-([1-3])\.json$')
HEX = re.compile(r'^[0-9a-f]{64}$')
TRANSIENT = re.compile(rb'^gh:[^\r\n]*HTTP (502|503|504)\b', re.M)
DELAYS = (2, 5)
EMPTY = sha256(b'').hexdigest()
FIELDS = {'artifact_id', 'attempt', 'exit_code', 'http_status', 'recorded_at_utc',
          'elapsed_seconds', 'stdout_bytes', 'stdout_sha256', 'stderr_bytes',
          'stderr_sha256', 'retry', 'delay_seconds', 'partial_stdout_forwarded',
          'downstream_original_hash_and_size_checks_unchanged'}


def fail(label):
    raise ValueError('S03_GENERATED_RECEIPT_' + label)


def path(root, relative):
    root = Path(root).resolve()
    name = PurePosixPath(relative)
    if (name.is_absolute() or str(name) != relative or not name.parts
            or any(p in ('', '.', '..') for p in name.parts)):
        fail('UNSAFE_PATH')
    target = root
    for part in name.parts:
        target = target / part
        if target.is_symlink():
            fail('SYMLINK:' + relative)
    if not target.is_file() or not stat.S_ISREG(target.stat().st_mode):
        fail('REGULAR_FILE_REQUIRED:' + relative)
    return target


def pin(root, relative, limit=512 * 1024 * 1024):
    target = path(root, relative)
    size = target.stat().st_size
    if size > limit:
        fail('SIZE_BOUND:' + relative)
    digest = sha256()
    with target.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return dict(bytes=size, sha256=digest.hexdigest())


def pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            fail('DUPLICATE_JSON_KEY:' + key)
        result[key] = value
    return result


def document(root, relative):
    target = path(root, relative)
    if target.stat().st_size > 1024 * 1024:
        fail('JSON_SIZE_BOUND:' + relative)
    try:
        return json.loads(target.read_bytes(), object_pairs_hook=pairs,
                          parse_constant=lambda value: fail('NONFINITE_JSON:' + value))
    except (json.JSONDecodeError, UnicodeError) as error:
        fail('INVALID_JSON:' + relative)


def contract(root, here):
    rel = str((Path(here) / CONTRACT).relative_to(root))
    value = document(root, rel)
    if value['version'] != 'cp7.s03.generated-nonsource-receipts.v1':
        fail('CONTRACT')
    for name, expected in value['producer_files'].items():
        if pin(root, name) != expected:
            fail('FROZEN_PRODUCER_CHANGED:' + name)
    return value


def frozen(root, names, cfg):
    if FROZEN not in names:
        return {}
    value = document(root, FROZEN)
    if value != cfg['frozen_worktree_document']:
        fail('FROZEN_WORKTREE_METADATA')
    # Equality alone accepts bool as int; preserve the exact producer types.
    if type(value['network_fetches']) is not int or type(value['source_worktree_count']) is not int:
        fail('FROZEN_WORKTREE_TYPES')
    if any(value[key] is not expected for key, expected in
           (('single_full_history', True), ('source_refs_substituted', False), ('auditor_head_unchanged', True))):
        fail('FROZEN_WORKTREE_FLAGS')
    return {FROZEN: pin(root, FROZEN)}


def artifact(root, relative, match, cfg):
    value = document(root, relative)
    if not isinstance(value, dict) or set(value) != FIELDS:
        fail('ARTIFACT_CLOSED_FIELDS')
    request, attempt = match.group(1), int(match.group(2))
    if uuid.UUID(request).version != 4 or uuid.UUID(request).variant != uuid.RFC_4122:
        fail('ARTIFACT_REQUEST_UUID4')
    for key in ('artifact_id', 'attempt', 'exit_code', 'stdout_bytes', 'stderr_bytes'):
        if type(value[key]) is not int or value[key] < 0:
            fail('ARTIFACT_INTEGER:' + key)
    for key in ('http_status', 'delay_seconds'):
        if value[key] is not None and type(value[key]) is not int:
            fail('ARTIFACT_INTEGER_OR_NULL:' + key)
    selected = cfg['artifacts'].get(str(value['artifact_id']))
    if selected is None or value['attempt'] != attempt or value['exit_code'] > 255:
        fail('ARTIFACT_ID_OR_ATTEMPT')
    if (type(value['elapsed_seconds']) not in (int, float)
            or not math.isfinite(value['elapsed_seconds']) or value['elapsed_seconds'] < 0
            or round(value['elapsed_seconds'], 3) != value['elapsed_seconds']):
        fail('ARTIFACT_ELAPSED')
    try:
        recorded = datetime.fromisoformat(value['recorded_at_utc'])
        if recorded.utcoffset() != timezone.utc.utcoffset(None) or recorded.isoformat() != value['recorded_at_utc']:
            fail('ARTIFACT_UTC_TIME')
    except (ValueError, TypeError):
        fail('ARTIFACT_UTC_TIME')
    if (value['partial_stdout_forwarded'] is not False
            or value['downstream_original_hash_and_size_checks_unchanged'] is not True
            or type(value['retry']) is not bool):
        fail('ARTIFACT_INHERITED_FLAGS')
    for channel in ('stdout', 'stderr'):
        digest = value[channel + '_sha256']
        if not isinstance(digest, str) or HEX.fullmatch(digest) is None:
            fail('ARTIFACT_DIGEST:' + channel)
        if value[channel + '_bytes'] == 0 and digest != EMPTY:
            fail('ARTIFACT_EMPTY_DIGEST:' + channel)
    accepted = {relative: pin(root, relative)}
    base = relative[:-5]
    if value['exit_code'] == 0:
        if (value['retry'] is not False or value['http_status'] is not None
                or value['delay_seconds'] is not None):
            fail('ARTIFACT_SUCCESS_RETRY')
        expected = selected['first_verified_success_zip']
        if expected is not None and dict(bytes=value['stdout_bytes'], sha256=value['stdout_sha256']) != expected:
            fail('ARTIFACT_SUCCESS_ZIP_PROVENANCE')
        for channel in ('stdout', 'stderr'):
            target = Path(root) / (base + '.' + channel + '.txt')
            if target.exists() or target.is_symlink():
                fail('ARTIFACT_SUCCESS_STREAM_MUST_BE_REMOVED')
    else:
        for channel in ('stdout', 'stderr'):
            name = base + '.' + channel + '.txt'
            observed = pin(root, name, limit=1024 * 1024 if channel == 'stderr' else 512 * 1024 * 1024)
            if observed != dict(bytes=value[channel + '_bytes'], sha256=value[channel + '_sha256']):
                fail('ARTIFACT_FAILED_STREAM_HASH:' + channel)
            accepted[name] = observed
        error = path(root, base + '.stderr.txt').read_bytes()
        transient = TRANSIENT.search(error)
        http = int(transient.group(1)) if transient else None
        retry = transient is not None and attempt < 3
        if (value['http_status'] != http or value['retry'] is not retry
                or value['delay_seconds'] != (DELAYS[attempt - 1] if retry else None)):
            fail('ARTIFACT_RETRY_POLICY')
    return request, value, accepted


def admit(root, here, names):
    """Return only validated relative paths/pins; unrelated names stay rejected."""
    root, here, names = Path(root).resolve(), Path(here).resolve(), set(names)
    cfg = contract(root, here)
    accepted = frozen(root, names, cfg)
    groups = {}
    for name in sorted(names):
        if not name.startswith(PREFIX):
            continue
        match = NAME.fullmatch(name[len(PREFIX):])
        if match is None:
            continue
        request, value, files = artifact(root, name, match, cfg)
        groups.setdefault(request, []).append(value)
        accepted.update(files)
    for request, values in groups.items():
        values.sort(key=lambda value: value['attempt'])
        if ([value['attempt'] for value in values] != list(range(1, len(values) + 1))
                or len(values) > 3 or len({value['artifact_id'] for value in values}) != 1):
            fail('ARTIFACT_REQUEST_ATTEMPT_CHAIN')
        if any(not value['retry'] for value in values[:-1]):
            fail('ARTIFACT_RETRY_CHAIN')
        final = values[-1]
        selected = cfg['artifacts'][str(final['artifact_id'])]
        if final['retry'] or (final['exit_code'] != 0 and not selected['optional_terminal_failure']):
            fail('ARTIFACT_REQUEST_INCOMPLETE')
        if [value['recorded_at_utc'] for value in values] != sorted(value['recorded_at_utc'] for value in values):
            fail('ARTIFACT_REQUEST_TIME_ORDER')
    counts = {}
    for values in groups.values():
        key = str(values[0]['artifact_id'])
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > cfg['artifacts'][key]['max_requests_per_admission']:
            fail('ARTIFACT_REQUEST_COUNT_BOUND')
    return accepted, dict(classification='BOUNDED_GENERATED_NON_SOURCE_RECEIPTS',
        files=len(accepted), frozen_worktree_receipts=int(FROZEN in accepted),
        artifact_requests=len(groups), artifact_attempts=sum(map(len, groups.values())),
        expected_total_request_count=None, arbitrary_source_allowed=False,
        authoritative_Original_readers_unchanged=True, Native_qualification_credit=0)
