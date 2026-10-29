"""Retain exact existing outputs in bounded logs; never rewrite a raw Original."""
from pathlib import Path
import base64
import gzip
import hashlib
import json

NAMES = ('CP7_CREDIT_E1_NATIVE17.json', 'CP7_CREDIT_E1_NATIVE17_CASES.json',
         'CP7_CREDIT_E1_NATIVE17_CASES_BUSINESS_DAY_FIRST_ATTEMPT.json',
         'E1_TARGETED_CLIENT.json', 'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', 'T3_PACKAGE_FILES_INSTALL.json')


def retain(root):
    for name in NAMES:
        path = Path(root)/name
        if path.is_file():
            raw = path.read_bytes(); packed = gzip.compress(raw, mtime=0)
            print(json.dumps(dict(ow04_original_report_bytes=True, name=name, raw_bytes=len(raw),
                raw_sha256=hashlib.sha256(raw).hexdigest(), gzip_bytes=len(packed),
                gzip_sha256=hashlib.sha256(packed).hexdigest(), gzip_base64=base64.b64encode(packed).decode('ascii'))), flush=True)


if __name__ == '__main__':
    retain(Path('cp6-proof/t3'))
