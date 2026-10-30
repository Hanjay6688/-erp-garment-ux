"""Source-only checker. Runtime deliberately refuses before any ERP/DB import."""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='cde78b2cc82e0a286174098458dab9815fdfd072'
PREFIXES=('scripts/cp7_global_nonpo_native_graph_adapter/','scripts/current-global-nonpo-native-graph-qualification/')


def module():
    spec=importlib.util.spec_from_file_location('closed_global_nonpo_source',ROOT/'scripts/cp7_global_nonpo_native_graph_adapter/source.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def check():
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    if source['actual_Native']!=0 or source['required_final_composition_parent']is not None or source['runtime_entry']is not None:
        raise ValueError('UNEXECUTED_SOURCE_PREPARATION_CANNOT_OPEN_RUNTIME')
    for name,pin in source['files'].items():
        path=ROOT/name
        if path.is_symlink():raise ValueError('SOURCE_SYMLINK_NOT_ALLOWED:'+name)
        raw=path.read_bytes()
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('SOURCE_CHANGED:'+name)
    current={str(p.relative_to(ROOT))for prefix in PREFIXES for p in(ROOT/prefix).rglob('*')if p.is_file()and'__pycache__'not in p.parts}
    own=set(source['own_files'])
    if current!=own:raise ValueError('EXACT_OWN_SOURCE_KEYSET_CHANGED')
    git=lambda *args:subprocess.check_output(['git','-C',str(ROOT),*args],text=True)
    if git('rev-parse',BASE+'^{tree}').strip()!='915103541d247f544c4492db25953b4268d9c2e3':raise ValueError('EXACT_PUBLIC_BASE_REQUIRED')
    if any(not name.startswith(PREFIXES)for name in git('diff','--name-only',BASE).splitlines()):raise ValueError('OUTSIDE_ALLOCATED_SOURCE_CHANGED')
    for name,pin in source['frozen_parent_files'].items():
        raw=(ROOT/name).read_bytes()
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('FROZEN_GUARD_OR_PARENT_SOURCE_CHANGED:'+name)
        original=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+name],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
        if raw!=original:raise ValueError('PARENT_NOT_EXACT_IMMUTABLE_GIT_SOURCE:'+name)
    # This is an immutable Git/own-source scope check, not workspace admission.
    # Unattributed outside files are neither imported, allowed nor made evidence.
    # Root assembles the exact own Git delta without these unstaged outputs.
    extras=set(git('ls-files','--others','--exclude-standard').splitlines())-own
    proof=module().source_contract()
    return dict(proof,files=len(source['files']),current_guards_unchanged=True,
        scope='OWN_IMMUTABLE_GIT_AND_PINNED_SOURCE_ONLY',whole_workspace_admitted=False,
        outside_untracked_not_admitted=sorted(extras),outside_untracked_count=len(extras))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source',action='store_true');group.add_argument('--runtime',action='store_true');args=parser.parse_args()
    if args.runtime:module().runtime_entry()
    print(json.dumps(check(),indent=2))
