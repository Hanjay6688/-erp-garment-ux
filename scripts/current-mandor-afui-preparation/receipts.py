"""Stream fixed complete Original file pins; no Root, DB or success credit."""
from hashlib import file_digest
from pathlib import Path
import json
import os
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NAMES = ('CP7_FG_MANDOR_NATIVE9_STRICT.json', 'CP7_FG_MANDOR_NATIVE9_STRICT_BUSINESS_DAY_FIRST_ATTEMPT.json',
         'CP7_FG_MANDOR_NATIVE9_STRICT_PREREQUISITES.json', 'CP7_FG_MANDOR_NATIVE9.json',
         'MANDOR_SESSION4_ORIGINAL.json', 'MANDOR_HTTP2_ORIGINAL.json', 'MANDOR_BROWSER_FIXTURE.json',
         'MANDOR_BROWSER_STATE.json', 'MANDOR_BROWSER2_ORIGINAL.json', 'MANDOR_RUNTIME_SUPERVISION.json',
         'MANDOR_DURABLE_RUNTIME.json', 'AFUI_DURABLE_PREFLIGHT.json', 'MANDOR_NATIVE9_FINAL_GATE.json',
         'AFUI15_PARENT_ORIGINAL_ADMISSION.json', 'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json',
         'T3_PACKAGE_FILES_INSTALL.json', 'SKU_COST_ARTIFACT_COPY_RECEIPT.json')


def regular(path):
    if not path.is_file() or any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError('MANDOR_RECEIPT_EXACT_REGULAR_ORIGINAL_REQUIRED')
    return path


def receipts(directory):
    if any(parent.is_symlink() for parent in (directory, *directory.parents)):
        raise ValueError('MANDOR_RECEIPT_REGULAR_PROOF_DIRECTORY_REQUIRED')
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / name for name in NAMES if (directory / name).exists() or (directory / name).is_symlink()]
    for base, pattern in ((directory, r'MANDOR_ACCESS_[A-Z0-9_]+_[a-f0-9]{32}\.json\.gz'),
                          (directory / 'MANDOR_CASE_STDOUT', r'(?:[a-f0-9]{64}\.jsonl|CP7_FG_MANDOR_NATIVE9_STRICT(?:_BUSINESS_DAY_FIRST_ATTEMPT)?\.json)')):
        if base.exists() or base.is_symlink():
            if any(parent.is_symlink() for parent in (base, *base.parents)):
                raise ValueError('MANDOR_RECEIPT_NO_SYMLINK_DIRECTORY')
            paths.extend(path for path in base.iterdir() if re.fullmatch(pattern, path.name))
    originals = {}
    for path in sorted(paths):
        with regular(path).open('rb') as stream:
            originals[str(path.relative_to(directory))] = dict(bytes=os.fstat(stream.fileno()).st_size,
                sha256=file_digest(stream, 'sha256').hexdigest())
    value = dict(status='COMPLETE_MANDOR_ORIGINAL_FILE_BYTE_RECEIPTS_NOT_QUALIFICATION', originals=originals,
                 actual_case_credit=0, full_restore_verified=False, production_go=False, independent_acceptance=False)
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    target = directory / 'MANDOR_CURRENT_COMPLETE_ORIGINAL_RECEIPTS.json'
    if target.exists() or target.is_symlink():
        if regular(target).read_bytes() != raw:
            raise ValueError('MANDOR_RECEIPT_FIRST_ORIGINAL_RECEIPT_CHANGED')
    else:
        with target.open('xb') as stream:
            stream.write(raw)
    return value


if __name__ == '__main__':
    value = receipts(ROOT / 'cp6-proof/t3')
    print(json.dumps(dict(status=value['status'], complete_files=len(value['originals']), actual_case_credit=0)))
