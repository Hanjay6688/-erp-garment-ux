"""Writer-only seal of the explicit successor; old SOURCE remains immutable."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def write():
    if os.environ.get('CI')or os.environ.get('GITHUB_ACTIONS')=='true':raise ValueError('ACTUAL19_SOURCE_FREEZE_IN_CI_FORBIDDEN')
    s=importlib.util.spec_from_file_location('actual19_freeze_guard',HERE/'check.py')
    guard=importlib.util.module_from_spec(s);s.loader.exec_module(guard)
    guard.require(guard.pin((HERE/'CAPTURE.json').read_bytes())==guard.CAPTURE_PIN,'ACTUAL19_ROOT_CAPTURE_NOT_EXACT')
    guard.parent_integrity()
    authority,sql,proof=guard.load_deriver().bundle()
    if (ROOT/guard.PRODUCT/'authority.sql').read_bytes()!=sql:raise ValueError('ACTUAL19_DERIVE_EXACT_SOURCE_BEFORE_SEAL')
    if json.loads((ROOT/guard.PRODUCT/'AUTHORITY.json').read_bytes())!=authority:raise ValueError('ACTUAL19_EXACT_AUTHORITY_BEFORE_SEAL')
    paths={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and p.name!='SOURCE.json'}|guard.MODIFIED
    files={}
    for name in sorted(paths):
        if '__pycache__'in name or name.endswith('.pyc'):raise ValueError('ACTUAL19_BYTECODE_FREEZE_FORBIDDEN')
        p=guard.regular(name);raw=p.read_bytes()
        files[name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest(),mode='100755'if p.stat().st_mode&0o111 else'100644')
    result=dict(contract='cp7.global-nonpo.actual19-source-profile.v1',base=guard.BASE,
        runtime_entry=None,actual_Native_credit=0,production_go=False,independent_acceptance=False,files=files)
    (HERE/'SOURCE.json').write_text(json.dumps(result,indent=2)+'\n')
    return guard.check(require_clean=False)


if __name__=='__main__':print(json.dumps(write(),sort_keys=True))
