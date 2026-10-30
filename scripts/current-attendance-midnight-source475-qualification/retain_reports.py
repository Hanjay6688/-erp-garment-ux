"""Retain exact raw new1 reports; no invented strict15 or relabelled parent14."""
from pathlib import Path
import base64
import gzip
import hashlib
import json

NAMES = ('CP7_ATTENDANCE_MIDNIGHT_NATIVE1.json', 'CP7_ATTENDANCE_MIDNIGHT_NATIVE1_CASES.json',
         'MIDNIGHT_NATIVE1_FINAL_GATE.json', 'T3_PACKAGE_INSTALL.json',
         'T3_PACKAGE_FILES_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json')


def retain(folder):
    for name in NAMES:
        path = Path(folder) / name
        if path.is_file():
            raw = path.read_bytes()
            packed = gzip.compress(raw, mtime=0)
            print(json.dumps(dict(ow04_original_report_bytes=True, name=name,
                raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
                gzip_bytes=len(packed), gzip_sha256=hashlib.sha256(packed).hexdigest(),
                gzip_base64=base64.b64encode(packed).decode('ascii'))), flush=True)


if __name__ == '__main__':
    retain(Path('cp6-proof/t3'))
