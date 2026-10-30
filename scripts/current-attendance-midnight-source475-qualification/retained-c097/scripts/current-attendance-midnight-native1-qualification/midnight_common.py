"""Strict local bytes and JSON helpers. No ERP, database or network imports."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import gzip
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-attendance-midnight-native1-qualification/'
WORKFLOW = '.github/workflows/cp7-attendance-midnight-native1.yml'
ID = 'S03_NATIVE_MIDNIGHT_OUTPUT_UTC17_SAME_SOURCE_CID_5_5_10'
LABEL = 'CP7_ATTENDANCE_MIDNIGHT_NATIVE1'
GROUP = 'CP7_ATTENDANCE_MIDNIGHT_NATIVE1_CASES'
CASE = 'S03_MIDNIGHT_NATIVE1_AND_UNCHANGED_USED_WITNESS'


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('MIDNIGHT_DUPLICATE_JSON_KEY:' + key)
        result[key] = value
    return result


def document(raw):
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('MIDNIGHT_INVALID_JSON_NUMBER')))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def regular(root, name):
    rel = PurePosixPath(name)
    if not rel.parts or rel.is_absolute() or '..' in rel.parts or '\\' in name or str(rel) != name:
        raise ValueError('MIDNIGHT_UNSAFE_RELATIVE_PATH:' + name)
    path = Path(root)
    if path.is_symlink():
        raise ValueError('MIDNIGHT_SOURCE_SYMLINK:' + name)
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('MIDNIGHT_SOURCE_SYMLINK:' + name)
    if not path.is_file():
        raise ValueError('MIDNIGHT_REGULAR_FILE_REQUIRED:' + name)
    return path


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def exact(raw, expected):
    if type(expected.get('bytes')) is not int or pin(raw) != expected:
        raise ValueError('MIDNIGHT_EXACT_BYTES_REQUIRED')
    return raw


def read_original(root, expected):
    packed = regular(root, expected['path']).read_bytes()
    exact(packed, expected['stored'])
    if expected['encoding'] == 'gzip':
        raw = gzip.decompress(packed)
    elif expected['encoding'] == 'raw':
        raw = packed
    else:
        raise ValueError('MIDNIGHT_ORIGINAL_ENCODING_REQUIRED')
    exact(raw, expected['raw'])
    return dict(raw=raw, document=document(raw), path=expected['path'])


def hash40(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{40}', value) is not None
