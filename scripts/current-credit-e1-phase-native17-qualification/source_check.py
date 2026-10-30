"""Actual complete publicfe2 files/modes, then exact319 plus bounded additions.

Generated outputs grant no source authority, case credit or qualified status.
All Git reads are public ancestors and explicitly offline.
"""
from pathlib import Path, PurePosixPath
from hashlib import sha1, sha256
from types import ModuleType
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-credit-e1-phase-native17-qualification/'
WORKFLOW = '.github/workflows/cp7-credit-e1-phase-native17.yml'
BACKEND = 'fe2ae370c00e68437c4951c28c3a1038ce35fb38'
TREE = '600d4575309e67a5575d7896382b38a27e000d7e'
PHASE = 'scripts/current-credit-e1-consumer-phase-successor/'


def git(root, *args):
    return subprocess.check_output(['git','-C',str(root),*args], env={**os.environ,
        'GIT_NO_LAZY_FETCH':'1','GIT_OPTIONAL_LOCKS':'0'})


def regular(root, name):
    relative=PurePosixPath(name)
    if relative.is_absolute() or str(relative)!=name or '..' in relative.parts:
        raise ValueError('E_PHASE23_UNSAFE_SOURCE_PATH:'+name)
    path=Path(root)
    if path.is_symlink():raise ValueError('E_PHASE23_SOURCE_ROOT_SYMLINK')
    for part in relative.parts:
        path=path/part
        if path.is_symlink():raise ValueError('E_PHASE23_SOURCE_SYMLINK:'+name)
    if not path.is_file():raise ValueError('E_PHASE23_SOURCE_REGULAR_FILE_REQUIRED:'+name)
    return path


def pin(root, name, expected):
    path=regular(root,name);raw=path.read_bytes()
    if type(expected['bytes']) is not int or len(raw)!=expected['bytes'] or sha256(raw).hexdigest()!=expected['sha256']:
        raise ValueError('E_PHASE23_DECLARED_SOURCE_CHANGED:'+name)
    if 'mode' in expected and bool(path.stat().st_mode&0o111)!=(expected['mode']=='100755'):
        raise ValueError('E_PHASE23_DECLARED_MODE_CHANGED:'+name)
    return raw


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m


def generated(root,here,names):
    accepted={};summary={}
    for label,file in (('preDB','generated_receipts.py'),('E1','generated_e1.py'),('later','generated_later.py')):
        value,info=load('e_phase_closed_'+label,here/file).admit(root,here,names)
        if set(value)&set(accepted):raise ValueError('E_PHASE23_DUPLICATE_OUTPUT_CLASS')
        accepted.update(value);summary[label]=info
    return accepted,summary


def check(root=ROOT,here=HERE,*,require_clean=True):
    root,here=Path(root),Path(here)
    source=json.loads(regular(root,NS+'SOURCE.json').read_bytes())
    cfg=json.loads(regular(root,NS+'CONFIG.json').read_bytes())
    load('e_phase_source_parent_gate',here/'gate.py').selected(cfg)
    if source['prepared_backend_head']!=BACKEND or source['prepared_backend_tree']!=TREE:
        raise ValueError('E_PHASE23_PUBLIC_BACKEND_REQUIRED')
    if git(root,'rev-parse',BACKEND+'^{tree}').decode().strip()!=TREE:
        raise ValueError('E_PHASE23_PUBLIC_TREE_CHANGED')
    if git(root,'rev-parse',BACKEND+'^').decode().strip()!=cfg['retained_failed_E17']['head']:
        raise ValueError('E_PHASE23_FAILED_PARENT_BINDING_CHANGED')
    entries={}
    for row in git(root,'ls-tree','-r','-z',BACKEND).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode().split();name=name.decode()
        if kind!='blob' or mode not in ('100644','100755'):raise ValueError('E_PHASE23_UNSUPPORTED_PUBLIC_MEMBER')
        path=regular(root,name);raw=path.read_bytes()
        actual=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if actual!=oid or bool(path.stat().st_mode&0o111)!=(mode=='100755'):
            raise ValueError('E_PHASE23_FROZEN_PUBLIC_BYTES_OR_MODE_CHANGED:'+name)
        entries[name]=dict(mode=mode,blob=oid)
    own={name for name in source['files'] if name.startswith(NS)}|{NS+'SOURCE.json',WORKFLOW}
    expected_namespace=own-{WORKFLOW}
    actual_namespace=set()
    for path in here.rglob('*'):
        if path.is_symlink():raise ValueError('E_PHASE23_SOURCE_SYMLINK:'+str(path.relative_to(root)))
        if path.is_file():actual_namespace.add(str(path.relative_to(root)))
    if actual_namespace!=expected_namespace:raise ValueError('E_PHASE23_OWN_NAMESPACE_NOT_CLOSED')
    for name,expected in source['files'].items():pin(root,name,expected)
    phase_raw=regular(root,PHASE+'SOURCE.json').read_bytes()
    if sha256(phase_raw).hexdigest()!=cfg['prepared_backend']['source_sha256'] or len(json.loads(phase_raw)['files'])!=319:
        raise ValueError('E_PHASE23_FROZEN_SOURCE319_CHANGED')
    tracked=set(git(root,'ls-files','-z').decode().split('\0'))-{''}
    untracked=set(git(root,'ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    # Include ignored generated files as well; an ignore rule never authorizes JSON/code.
    folder=root/'cp6-proof/t3'
    outputs=set()
    if (root/'cp6-proof').is_symlink():raise ValueError('E_PHASE23_GENERATED_ANCESTOR_SYMLINK')
    if folder.exists() or folder.is_symlink():
        if folder.is_symlink():raise ValueError('E_PHASE23_GENERATED_ANCESTOR_SYMLINK')
        for path in folder.rglob('*'):
            if path.is_symlink():raise ValueError('E_PHASE23_GENERATED_SYMLINK:'+str(path.relative_to(root)))
            if path.is_file():outputs.add(str(path.relative_to(root)))
    accepted,classes=generated(root,here,outputs)
    if outputs!=set(accepted):raise ValueError('E_PHASE23_UNKNOWN_GENERATED_OUTPUT:'+repr(sorted(outputs-set(accepted))))
    archive=json.loads(regular(root,'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes())
    proof_paths={item['path']for item in archive['files']}
    if tracked-set(entries)-own or untracked-set(entries)-own-proof_paths-set(accepted):
        raise ValueError('E_PHASE23_UNKNOWN_SOURCE_OR_RECEIPT:'+repr(sorted((tracked|untracked)-set(entries)-own-proof_paths-set(accepted))))
    changed=set(git(root,'diff','--name-only',BACKEND,'HEAD').decode().splitlines())
    if not changed<=own:raise ValueError('E_PHASE23_ONLY_NEW_QUALIFIER_AND_WORKFLOW_ALLOWED')
    if require_clean:
        if git(root,'status','--porcelain','--untracked-files=no').strip():
            raise ValueError('E_PHASE23_COMMITTED_CLEAN_SOURCE_REQUIRED')
        if not own<=tracked or changed!=own:
            raise ValueError('E_PHASE23_COMPLETE_NEW_NAMESPACE_MUST_BE_COMMITTED')
    # Original319 checks every historical base byte/mode and all financial derivation guards.
    raw=regular(root,PHASE+'check.py').read_bytes()
    text,proof=load('e_phase_counted_complete319_reader',here/'derive.py').prepared_check(raw)
    m=ModuleType('e_phase_complete319_explicit_additive_reader');m.__file__=str(root/PHASE/'check.py')
    exec(compile(text,str(root/PHASE/'check.py'),'exec'),m.__dict__)
    historical=m.check(root,root/PHASE,additive_paths=frozenset(own|set(accepted)))
    transition=json.loads(regular(root,NS+'PRODUCT_TRANSITION.json').read_bytes())
    for name,pair in transition['product_changes'].items():pin(root,name,pair['after'])
    if len(transition['product_changes'])!=2 or transition['private_function_count']!={'before':40,'after':41}:
        raise ValueError('E_PHASE23_EXACT_TWO_SOURCE_PRIVATE41_TRANSITION_REQUIRED')
    return dict(status='EXACT_PUBLIC_FE2_SOURCE319_AND_NEW_QUALIFIER_ADMITTED',
        public_files=len(entries),public_bytes_modes_snapshot_sha256=sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest(),
        source_pins=len(source['files']),historical319=historical,additive_reader_derivation=proof,
        generated_output_classes=classes,actual_new_Native=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check()))
