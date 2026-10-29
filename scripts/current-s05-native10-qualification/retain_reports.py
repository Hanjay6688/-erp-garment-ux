"""Preserve original report bytes after every outcome; no relabelled results."""
import base64
import gzip
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]/'cp6-proof/t3'
NAMES = ('CP7_S05_ACCESSORY_STANDARD_NATIVE10.json', 'CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES.json',
         'CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES_BUSINESS_DAY_FIRST_ATTEMPT.json',
         'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', 'T3_PACKAGE_FILES_INSTALL.json')


def preserve(root=ROOT):
    for name in NAMES:
        path = Path(root)/name
        if not path.is_file():
            continue
        raw = path.read_bytes(); packed = gzip.compress(raw, mtime=0)
        yield dict(s05_original_report_bytes=True, name=name, raw_bytes=len(raw), raw_sha256=sha256(raw).hexdigest(),
                   gzip_bytes=len(packed), gzip_sha256=sha256(packed).hexdigest(), gzip_base64=base64.b64encode(packed).decode('ascii'))


if __name__ == '__main__':
    for row in preserve():
        print(json.dumps(row), flush=True)
