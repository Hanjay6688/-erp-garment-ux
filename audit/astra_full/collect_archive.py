"""Download the connector's short-lived reference and verify GitHub's recorded ZIP digest.
Only evidence from this auditor's explicitly selected run is supplied by the caller.
"""
from pathlib import Path
import hashlib, json, sys, urllib.request, zipfile

artifact_id, digest, url = sys.argv[1:]
assert artifact_id.isdigit()
root = Path('/workspace/scratch/eeb89eca3f58/audit-artifacts')
root.mkdir(exist_ok=True)
p = root / (artifact_id + '.zip')
if p.exists():
    data = p.read_bytes()
else:
    data = urllib.request.urlopen(url, timeout=45).read()
actual = hashlib.sha256(data).hexdigest()
assert actual == digest.removeprefix('sha256:'), ('ARCHIVE_DIGEST_MISMATCH', artifact_id, actual, digest)
p.write_bytes(data)
with zipfile.ZipFile(p) as z:
    for name in z.namelist():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
    z.extractall(p.with_suffix(''))
    print(json.dumps(dict(id=int(artifact_id), bytes=len(data), sha256=actual, files=len(z.namelist()), verified=True)))
