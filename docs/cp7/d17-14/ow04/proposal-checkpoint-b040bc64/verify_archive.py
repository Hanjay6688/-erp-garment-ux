"""Verify the inert checkpoint without importing or executing its contents."""
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath

base = Path(__file__).resolve().parent
manifest_bytes = (base / 'ARCHIVE_PLAN.json').read_bytes()
manifest = json.loads(manifest_bytes)
receipt = json.loads((base / 'CHECKPOINT_RECEIPT.json').read_text())
archive = base / 'UNINSTALLED_PROPOSALS.tar.gz'
assert hashlib.sha256(manifest_bytes).hexdigest() == receipt['source_manifest_sha256']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == receipt['archive_sha256']
expected = {r['relative_path']: r for r in
            manifest['entries'] + manifest['identical_content_aliases']}
assert len(expected) == receipt['logical_files_restored']
with tarfile.open(archive, 'r:gz') as package:
    members = package.getmembers()
    assert len(members) == len(expected)
    assert {m.name for m in members} == set(expected)
    for member in members:
        path = PurePosixPath(member.name)
        assert member.isfile() and not path.is_absolute() and '..' not in path.parts
        row = expected[member.name]
        data = package.extractfile(member).read()
        assert member.size == len(data) == row['bytes'], member.name
        assert hashlib.sha256(data).hexdigest() == row['sha256'], member.name
print(json.dumps({'status': 'PASS', 'files': len(expected),
                  'scope': 'ARCHIVE_INTEGRITY_ONLY_NOT_NATIVE_OR_FEATURE_PROOF'}))
