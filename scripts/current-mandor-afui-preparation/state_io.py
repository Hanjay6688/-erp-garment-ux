"""Lossless complete Mandor state I/O; no ERP import or database operation."""
from hashlib import sha256,file_digest
from pathlib import Path
import importlib,json,sys

ROOT=Path(__file__).resolve().parents[2]
ORIGINAL='MANDOR_BROWSER_STATE.json'
CACHE='MANDOR_BROWSER_STATE_CACHE.json'


def require(value,reason):
    if not value:raise ValueError(reason)


def codec():
    sys.path.insert(0,str(ROOT/'scripts'))
    module=importlib.import_module('cp7_accessory_nonpayable.lossless_state')
    require(Path(module.__file__).read_bytes()==(ROOT/'scripts/cp7_accessory_nonpayable/lossless_state.py').read_bytes(),
            'MANDOR_EXACT_CURRENT_LOSSLESS_STATE_MODULE')
    return module


def pin(path):
    path=Path(path)
    require(path.is_file()and not any(p.is_symlink()for p in(path,*path.parents)),
            'MANDOR_COMPLETE_STATE_REGULAR_ORIGINAL_REQUIRED')
    with path.open('rb')as stream:return dict(bytes=path.stat().st_size,sha256=file_digest(stream,'sha256').hexdigest())


def save(value,reference,directory=None):
    require(reference['name']==ORIGINAL,'MANDOR_COMPLETE_STATE_FIXED_ORIGINAL_NAME')
    directory=ROOT/'cp6-proof/t3'if directory is None else Path(directory)
    return codec().save(directory/CACHE,value,reference)


def reference(original):
    path=ROOT/'cp6-proof/t3'/CACHE
    current=dict(name=CACHE,**pin(path));document=json.loads(path.read_text())
    require(document['source_original']==original,'MANDOR_COMPLETE_CACHE_EXACT_ORIGINAL_REFERENCE')
    return current


def read(original,original_sha256,cache_sha256):
    original=Path(original);require(original.name==ORIGINAL,'MANDOR_COMPLETE_STATE_FIXED_INPUT')
    return codec().read(original.parent/CACHE,cache_sha256,original,original_sha256)


def verified(p,directory,original,cache):
    p.exact(original['name'],ORIGINAL,'MANDOR_COMPLETE_STATE_ORIGINAL_NAME')
    p.exact(cache['name'],CACHE,'MANDOR_COMPLETE_STATE_CACHE_NAME')
    for reference_value in(original,cache):
        p.exact(pin(directory/reference_value['name']),{k:reference_value[k]for k in('bytes','sha256')},
                'MANDOR_COMPLETE_STATE_EVERY_ORIGINAL_FILE_BYTE')
    value=read(directory/ORIGINAL,original['sha256'],cache['sha256'])
    p.exact(codec().canonical_pin(value),{k:original[k]for k in('bytes','sha256')},
            'MANDOR_COMPLETE_STATE_EVERY_DECODED_CANONICAL_BYTE')
    return value
