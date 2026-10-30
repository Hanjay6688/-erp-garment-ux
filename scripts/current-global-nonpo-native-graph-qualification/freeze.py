"""Writer-only source freeze, not an installer/admission or catalogue generator."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PREFIXES=('scripts/cp7_global_nonpo_native_graph_adapter/','scripts/current-global-nonpo-native-graph-qualification/')


def freeze():
    if os.environ.get('CI'):raise ValueError('SOURCE_FREEZE_IN_CI_FORBIDDEN')
    spec=importlib.util.spec_from_file_location('global_inspector_source_writer_check',ROOT/'scripts/cp7_global_nonpo_native_graph_adapter/source.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);value.source_contract()
    authority=json.loads((ROOT/'scripts/cp7_global_nonpo_native_graph_adapter/AUTHORITY.json').read_bytes())
    census=json.loads((HERE/'WRITER_CENSUS.json').read_bytes())
    parent={name:pin for name,pin in census['inputs'].items()if not Path(name).is_absolute()}
    parent.update(authority['parent_source_files'])
    own={str(p.relative_to(ROOT))for prefix in PREFIXES for p in(ROOT/prefix).rglob('*')if p.is_file()and'__pycache__'not in p.parts}
    own.add(str((HERE/'SOURCE.json').relative_to(ROOT)))
    files={}
    for name in sorted((own|set(parent))-{str((HERE/'SOURCE.json').relative_to(ROOT))}):
        raw=(ROOT/name).read_bytes();files[name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
        if name in parent and files[name]!=parent[name]:raise ValueError('WRITER_CANNOT_RESEAL_FROZEN_PARENT:'+name)
        if name in parent:
            original=subprocess.check_output(['git','-C',str(ROOT),'show','cde78b2cc82e0a286174098458dab9815fdfd072:'+name],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
            if original!=raw:raise ValueError('PARENT_MUST_BE_EXACT_IMMUTABLE_PUBLIC_GIT_SOURCE:'+name)
    document=dict(contract='cp7.global-nonpo.readonly-inspector.source.v1',status='STANDALONE_PREPARATION_NOT_RUNTIME_QUALIFICATION',
        files=files,own_files=sorted(own),frozen_parent_files=parent,source_base='cde78b2cc82e0a286174098458dab9815fdfd072',
        required_final_composition_parent=None,runtime_entry=None,actual_Native=0,new_public_RPC=0,new_roles=0,
        writer_or_phantom_lock_closed=False,production_go=False,independent_acceptance=False)
    (HERE/'SOURCE.json').write_text(json.dumps(document,indent=2)+'\n')
    return dict(status=document['status'],files=len(files),own_files=len(own),actual_Native=0)


if __name__=='__main__':print(json.dumps(freeze()))
