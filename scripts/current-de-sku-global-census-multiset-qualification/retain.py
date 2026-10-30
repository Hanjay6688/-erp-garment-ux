"""Retain Original file identities; stdout contains no catalogue or data body."""
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('CP7_D1_E_SKU_GLOBAL_CENSUS_MULTISET.json', 'GLOBAL_ACTUAL_WRITER_SUPPLEMENT_V2.json',
    'DE_SKU_GLOBAL_CENSUS_MULTISET_GATE.json', 'CP7_SKU_GROUP_COST_NATIVE5.json',
    'CP7_SKU_GROUP_COST_NATIVE5_BUSINESS_DAY_FIRST_ATTEMPT.json', 'CP7_SKU_PAIR_CONVERSION_NATIVE.json',
    'CP7_SKU_PAIR_CONVERSION_NATIVE7.json', 'CP7_SKU_PAIR_CONVERSION_NATIVE7_BUSINESS_DAY_FIRST_ATTEMPT.json',
    'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', 'T3_PACKAGE_FILES_INSTALL.json',
    'SKU_COST_ARTIFACT_COPY_RECEIPT.json', 'GLOBAL_WRITER_RAW_CAPTURE.json')
REQUIRED = {NAMES[0], NAMES[1], NAMES[2], 'GLOBAL_WRITER_RAW_CAPTURE.json', 'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', 'T3_PACKAGE_FILES_INSTALL.json'}


def retain(directory):
    directory = Path(directory)
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise ValueError('GLOBAL_CENSUS_RETENTION_DIRECTORY_SYMLINK')
    files = {}
    for name in NAMES:
        path = directory / name
        if path.is_symlink(): raise ValueError('GLOBAL_CENSUS_RETENTION_ORIGINAL_SYMLINK:' + name)
        if not path.exists(): continue  # Preserve first-failure outputs too.
        if not path.is_file(): raise ValueError('GLOBAL_CENSUS_RETENTION_ORIGINAL_NOT_FILE:' + name)
        digest = sha256(); size = 0
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk); size += len(chunk)
        files[name] = dict(bytes=size, sha256=digest.hexdigest())
    return dict(status='ORIGINAL_BYTE_IDENTITIES_ONLY_NOT_QUALIFICATION', files=files,
        missing_required=sorted(REQUIRED - set(files)), full_raw_files_retained_by_artifact=True,
        metadata_or_data_bodies_printed=False, actual_Native_credit=0, runtime_entry=None,
        production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    directory = ROOT / 'cp6-proof/t3'; directory.mkdir(parents=True, exist_ok=True)
    value = retain(directory)
    with (directory / 'GLOBAL_CENSUS_MULTISET_ORIGINAL_RETENTION.json').open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
    print(json.dumps(dict(status=value['status'], files=len(value['files']), missing_required=value['missing_required'],
        metadata_or_data_bodies_printed=False, actual_Native_credit=0)))
