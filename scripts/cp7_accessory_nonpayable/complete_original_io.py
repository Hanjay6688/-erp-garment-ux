"""Complete immutable snapshot bytes in bounded buffers, without ERP imports.

The encoder options, newline and gzip bytes match the existing writers. A
complete file is published atomically and never replaces a different original.
Only complete named outputs are linked to the existing durable transport.
"""
from hashlib import sha256, file_digest
from pathlib import Path
import gzip
import json
import os
import re
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'cp6-proof/t3'
FIXED = frozenset((
    'CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9.json',
    'CP7_AFUI_GOOD_NONPAYABLE_FULL15_NATIVE9_BUSINESS_DAY_FIRST_ATTEMPT.json',
    'AFUI_BROWSER_NATIVE_PREREQUISITE.json',
    'AFUI_BROWSER_SETTINGS_STATE.json',
))


def regular(path):
    path = Path(path)
    if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('AFUI_COMPLETE_ORIGINAL_REGULAR_ABSOLUTE_PATH_REQUIRED')
    return path


def pin(path):
    path = regular(path)
    with path.open('rb') as stream:
        return dict(bytes=os.fstat(stream.fileno()).st_size, sha256=file_digest(stream, 'sha256').hexdigest())


def identical(first, second):
    with regular(first).open('rb') as a, regular(second).open('rb') as b:
        while True:
            left, right = a.read(1024 * 1024), b.read(1024 * 1024)
            if left != right:
                return False
            if not left:
                return True


def finish(partial, target, conflict):
    if target.exists():
        if not identical(partial, target):
            raise ValueError(conflict)
    else:
        # Exclusive publication: a concurrent original can never be replaced.
        os.link(partial, target)
    partial.unlink()


def encoded(value):
    for part in json.JSONEncoder(sort_keys=True, default=str).iterencode(value):
        yield part.encode('utf-8')
    yield b'\n'


def save_sorted(target, value, conflict):
    target = regular(target)
    digest = sha256()
    size = 0
    with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent,
            prefix='.' + target.name + '.', suffix='.partial', delete=False) as stream:
        partial = Path(stream.name)
        for chunk in encoded(value):
            stream.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        stream.flush()
        os.fsync(stream.fileno())
    finish(partial, target, conflict)
    return dict(name=target.name, bytes=size, sha256=digest.hexdigest())


def copy_exact(source, target, conflict):
    source, target = regular(source), regular(target)
    before = pin(source)
    if source == target:
        return dict(name=target.name, **before)
    if target.exists():
        if not identical(source, target) or pin(source) != before:
            raise ValueError(conflict)
        return dict(name=target.name, **before)
    with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent,
            prefix='.' + target.name + '.', suffix='.partial', delete=False) as stream:
        partial = Path(stream.name)
        with source.open('rb') as original:
            while chunk := original.read(1024 * 1024):
                stream.write(chunk)
        stream.flush()
        os.fsync(stream.fileno())
    if pin(partial) != before or pin(source) != before:
        raise ValueError(conflict)
    finish(partial, target, conflict)
    return dict(name=target.name, **before)


def save_gzip_sorted(target, value):
    target = regular(target)
    digest, packed_digest = sha256(), sha256()
    size = packed_size = 0
    compressor = zlib.compressobj(level=9, wbits=31)
    with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent,
            prefix='.' + target.name + '.', suffix='.partial', delete=False) as stream:
        partial = Path(stream.name)
        for chunk in encoded(value):
            digest.update(chunk)
            size += len(chunk)
            packed = compressor.compress(chunk)
            stream.write(packed)
            packed_digest.update(packed)
            packed_size += len(packed)
        packed = compressor.flush()
        stream.write(packed)
        packed_digest.update(packed)
        packed_size += len(packed)
        stream.flush()
        os.fsync(stream.fileno())
    # These gzip snapshots have always been exclusive outputs, including an
    # identical-name collision. Keep that original refusal behavior.
    os.link(partial, target)
    partial.unlink()
    return dict(name=target.name, bytes=size, sha256=digest.hexdigest(),
                gzip_bytes=packed_size, gzip_sha256=packed_digest.hexdigest())


def read_verified_json(path, expected, refusal):
    path = regular(path)
    if pin(path)['sha256'] != expected:
        raise ValueError(refusal)
    with path.open('r', encoding='utf-8') as stream:
        return json.load(stream)


def publish(target):
    target = regular(target)
    name = target.name
    allowed = (name in FIXED
        or re.fullmatch(r'AFUI_ACCESS_[A-Z0-9_]+_[a-f0-9]{32}_FULL_CENSUS\.json\.gz', name)
        or re.fullmatch(r'AFUI_(DESKTOP|MOBILE390)_[A-Z0-9_]+_FULL_CURRENT_CENSUS\.json\.gz', name))
    # Failure-capture files retain their existing owning final-artifact path;
    # the incremental transport remains a fixed set of complete output kinds.
    if not allowed:
        return
    if target.parent != OUT:
        raise ValueError('AFUI_COMPLETE_ORIGINAL_FIXED_OWNING_OUTPUT_REQUIRED')
    destination = regular(OUT / 'AFUI_CASE_STDOUT')
    destination.mkdir(parents=True, exist_ok=True)
    linked = destination / name
    if linked.exists():
        if not identical(target, linked):
            raise ValueError('AFUI_COMPLETE_ORIGINAL_TRANSPORT_COPY_CONFLICT')
        return
    os.link(target, linked)
