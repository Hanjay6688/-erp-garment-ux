"""Render source-derived definitions for local controls only. No DB or network."""
from pathlib import Path
import importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('local_S03_delta',HERE/'native_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
if __name__=='__main__':
    data=json.loads((HERE/'SOURCE_DERIVED_NATIVE_ABI.json').read_bytes())
    print(json.dumps(dict(classification='SOURCE_DERIVED_LOCAL_ONLY_NOT_RUNTIME_NATIVE',
        originals=data['definitions'],clones=delta.clones(data['definitions']),patched=delta.patched(data['definitions'])),ensure_ascii=False))
