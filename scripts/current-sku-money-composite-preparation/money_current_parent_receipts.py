"""Bounded console receipts; complete original reports remain artifact files."""
from hashlib import file_digest
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
NAMES=('SKU_CURRENT_PARENT_MONEY_RUNTIME_SUPERVISION.json','CP7_SKU_CURRENT_PARENT_MONEY_QUALIFICATION.json',
    'CP7_SKU_CURRENT_PARENT_MONEY_NATIVE19.json','CP7_SKU_CURRENT_PARENT_MONEY_NATIVE19_PREFLIGHT.json','CP7_SKU_CURRENT_PARENT_MONEY_NATIVE19_BUSINESS_DAY_FIRST_ATTEMPT.json',
    'SKU_CURRENT_PARENT_MONEY_FINAL_GATE.json','SKU_CURRENT_MANDOR17_ORIGINAL_ADMISSION.json',
    'SKU_CURRENT_MONEY19_ORIGINAL_ADMISSION.json','SKU_CURRENT_PARENT_MONEY_PREREQUISITE_FILES.json',
    'SKU_CURRENT_PARENT_MONEY_FROZEN_EXECUTION_RECEIPT.json','T3_PACKAGE_INSTALL.json',
    'T3_BACKUP_RESTORE_DRILL.json','T3_PACKAGE_FILES_INSTALL.json','SKU_COST_ARTIFACT_COPY_RECEIPT.json')


def receipts(root):
    if root.is_symlink():raise ValueError('SKU_COMPOSITE_RECEIPT_DIRECTORY_SYMLINK')
    result={};missing=[]
    for name in NAMES:
        path=root/name
        if path.is_symlink():raise ValueError('SKU_COMPOSITE_RECEIPT_ORIGINAL_SYMLINK')
        if not path.exists():missing.append(name);continue
        if not path.is_file():raise ValueError('SKU_COMPOSITE_RECEIPT_REGULAR_ORIGINAL_REQUIRED')
        with path.open('rb')as stream:result[name]=dict(bytes=path.stat().st_size,sha256=file_digest(stream,'sha256').hexdigest())
    value=dict(status='ORIGINAL_FILE_HASH_RECEIPTS_ONLY_NOT_QUALIFICATION',originals=result,missing=missing,
        originals_remain_complete_files=True,report_bodies_printed=False,actual_case_credit=0)
    raw=(json.dumps(value,sort_keys=True)+'\n').encode()
    if len(raw)>16384:raise ValueError('SKU_COMPOSITE_BOUNDED_CONSOLE_RECEIPT')
    root.mkdir(parents=True,exist_ok=True);out=root/'SKU_CURRENT_PARENT_MONEY_ORIGINAL_FILE_RECEIPTS.json'
    if out.exists():
        if out.is_symlink()or out.read_bytes()!=raw:raise ValueError('SKU_COMPOSITE_FIRST_RECEIPT_CHANGED')
    else:
        with out.open('xb')as stream:stream.write(raw)
    return value


if __name__=='__main__':print(json.dumps(receipts(ROOT/'cp6-proof/t3'),sort_keys=True),flush=True)
