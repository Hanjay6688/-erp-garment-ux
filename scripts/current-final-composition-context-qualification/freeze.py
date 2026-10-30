"""Writer-only seal. Frozen phase2 files and old manifests are never rewritten."""
from pathlib import Path
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def write():
    if os.environ.get('CI')or os.environ.get('GITHUB_ACTIONS')=='true':raise ValueError('FINAL_CONTEXT_FREEZE_IN_CI_FORBIDDEN')
    spec=importlib.util.spec_from_file_location('final_context_writer_guard',HERE/'check.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    guard.require(guard.pin((HERE/'INVENTORY.json').read_bytes())==guard.INVENTORY_PIN,
                  'FINAL_CONTEXT_ROOT_INVENTORY_CHANGED')
    guard.parent_integrity();files={}
    for p in sorted(HERE.rglob('*')):
        if not(p.is_file()or p.is_symlink())or p.name=='SOURCE.json':continue
        name=str(p.relative_to(ROOT))
        guard.require('__pycache__'not in p.parts and p.suffix!='.pyc','FINAL_CONTEXT_BYTECODE_FREEZE_FORBIDDEN')
        p=guard.regular(name);files[name]=dict(guard.pin(p.read_bytes()),mode='100755'if p.stat().st_mode&0o111 else'100644')
    value=dict(contract='cp7.final-context.closed-source.v1',base=guard.BASE,
        runtime_entry=None,actual_Native_credit=0,production_go=False,independent_acceptance=False,files=files)
    (HERE/'SOURCE.json').write_text(json.dumps(value,indent=2)+'\n')
    return guard.check(require_clean=False)


if __name__=='__main__':print(json.dumps(write(),sort_keys=True))
