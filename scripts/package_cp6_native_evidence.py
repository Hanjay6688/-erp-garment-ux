#!/usr/bin/env python3
"""Lossless transport for the complete, already bound native proof directory.

The final runtime manifest remains inside the archive without byte changes.
Solid XZ compression avoids repeating large catalog snapshots in each ZIP entry.
This changes transport only; it neither creates nor waives a business proof.
"""
import hashlib
import json
import lzma
import os
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath


MANIFEST = 'CP6_V2620U_RUNTIME_MANIFEST.json'
ARCHIVE = 'CP6_NATIVE_PROOF.tar.xz'
TRANSFER = 'CP6_NATIVE_TRANSFER.json'
MAX_BYTES = 500 * 1024 * 1024  # Leave ZIP overhead below the connector's 512 MiB limit.


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def package(proof, output, expected_identity):
    if not proof.is_dir() or proof.is_symlink() or output.exists():
        raise ValueError('CP6_TRANSFER_INVALID_INPUT_OR_EXISTING_OUTPUT')
    manifest = json.loads((proof / MANIFEST).read_text())
    if (manifest['status'] != 'PASS_EXACT_LOCAL_DISPOSABLE_CI'
            or manifest['production_go'] is not False
            or manifest['identity'] != expected_identity):
        raise ValueError('CP6_TRANSFER_REQUIRES_EXACT_SUCCESSFUL_RUNTIME')
    files = []
    for path in sorted(proof.rglob('*')):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError('CP6_TRANSFER_UNSUPPORTED_FILE_TYPE')
        if path.is_file():
            name = path.relative_to(proof).as_posix()
            logical = PurePosixPath(name)
            # Match the existing runtime manifest and raw upload policy exactly.
            if any(part.startswith('.') for part in logical.parts):
                continue
            if logical.is_absolute() or '..' in logical.parts or '\\' in name:
                raise ValueError('CP6_TRANSFER_UNSAFE_PATH')
            files.append((name, path))
    if {name for name, _ in files} != set(manifest['proof_files']) | {MANIFEST}:
        raise ValueError('CP6_TRANSFER_PAYLOAD_INVENTORY_MISMATCH')
    for name, path in files:
        if name == MANIFEST:
            continue
        pinned = manifest['proof_files'][name]
        if path.stat().st_size != pinned['bytes'] or file_hash(path) != pinned['sha256']:
            raise ValueError('CP6_TRANSFER_PAYLOAD_HASH_MISMATCH: ' + name)
    # Create output only after all admission checks. A failure cannot masquerade
    # as a successful transfer manifest or alter any input proof bytes.
    output.mkdir(parents=True)
    archive = output / ARCHIVE
    temporary = output / (ARCHIVE + '.partial')
    filters = [{'id': lzma.FILTER_LZMA2, 'preset': 1, 'dict_size': 16 * 1024 * 1024}]
    try:
        with lzma.open(temporary, 'wb', filters=filters) as compressed, \
                tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as tar:
            for name, path in files:
                info = tar.gettarinfo(str(path), arcname=name)
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                info.mode = 0o644
                with path.open('rb') as stream:
                    tar.addfile(info, stream)
        if temporary.stat().st_size > MAX_BYTES:
            raise ValueError('CP6_TRANSFER_EXCEEDS_CONNECTOR_SIZE_BOUNDARY')
        temporary.replace(archive)
        result = {
            'format': 'CP6_LOSSLESS_NATIVE_TRANSFER_V1', 'status': 'PASS',
            'identity': expected_identity, 'production_go': False,
            'archive': {'name': ARCHIVE, 'bytes': archive.stat().st_size,
                        'sha256': file_hash(archive)},
            'runtime_manifest': {'name': MANIFEST, 'sha256': file_hash(proof / MANIFEST)},
            'payload_files': len(manifest['proof_files']), 'archive_files': len(files),
            'source_pins': len(manifest['sources']),
            'input_proof_bytes': sum(path.stat().st_size for _, path in files),
            'all_input_files_included': True, 'payload_bytes_unchanged': True,
            'compression': 'XZ/LZMA2 preset 1, 16 MiB dictionary',
            'max_archive_bytes': MAX_BYTES,
        }
        (output / TRANSFER).write_text(json.dumps(result, indent=2) + '\n')
        return result
    except Exception:
        temporary.unlink(missing_ok=True)
        archive.unlink(missing_ok=True)
        raise


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: package_cp6_native_evidence.py PROOF_DIRECTORY OUTPUT_DIRECTORY')
    git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
    identity = {
        'repository': os.environ['GITHUB_REPOSITORY'],
        'ref_name': os.environ['GITHUB_REF_NAME'],
        'head_sha': os.environ['GITHUB_SHA'],
        'head_tree': git('rev-parse', 'HEAD^{tree}'),
        'parents': git('show', '-s', '--format=%P', 'HEAD').split(),
        'workflow': os.environ['GITHUB_WORKFLOW'],
        'run_id': int(os.environ['GITHUB_RUN_ID']),
        'run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']),
        'job': os.environ['GITHUB_JOB'],
    }
    if git('rev-parse', 'HEAD') != identity['head_sha']:
        raise SystemExit('CP6_TRANSFER_CHECKOUT_HEAD_MISMATCH')
    result = package(Path(sys.argv[1]), Path(sys.argv[2]), identity)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
