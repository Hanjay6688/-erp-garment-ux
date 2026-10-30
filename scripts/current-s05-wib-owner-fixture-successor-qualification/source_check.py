"""Actual entire public52eed bytes/modes before any bounded historical reader."""
from pathlib import Path,PurePosixPath
from hashlib import sha1,sha256
import importlib.util
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='52eedc88e9aa2cd7470894c1f38ff9eb22f9cc60'
TREE='df8970c1c19d19b17c6a870d30adc535170725cc'
NS='scripts/current-s05-wib-owner-fixture-successor-qualification/'
WORKFLOW='.github/workflows/cp7-current-s05-wib-owner-fixture-successor.yml'


def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_OPTIONAL_LOCKS':'0'})


def regular(repo,name):
    rel=PurePosixPath(name)
    if rel.is_absolute()or '..'in rel.parts or str(rel)!=name:raise ValueError('S05_FIXTURE_UNSAFE_PATH:'+name)
    path=Path(repo)
    if path.is_symlink():raise ValueError('S05_FIXTURE_ROOT_SYMLINK')
    for part in rel.parts:
        path=path/part
        if path.is_symlink():raise ValueError('S05_FIXTURE_SOURCE_SYMLINK:'+name)
    if not path.is_file():raise ValueError('S05_FIXTURE_REGULAR_SOURCE_REQUIRED:'+name)
    return path


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def generated(repo,here,names):
    accepted={};classes={}
    for name,file in (('preDB','generated_receipts.py'),('later','generated_later.py')):
        pins,info=load('s05_fixture_outputs_'+name,here/file).admit(repo,here,names)
        if set(accepted)&set(pins):raise ValueError('S05_FIXTURE_DUPLICATE_OUTPUT_CLASS')
        accepted.update(pins);classes[name]=info
    return accepted,classes


def check(repo=ROOT,here=HERE,*,require_clean=True):
    repo,here=Path(repo),Path(here)
    cfg=json.loads(regular(repo,NS+'CONFIG.json').read_bytes());source=json.loads(regular(repo,NS+'SOURCE.json').read_bytes())
    if cfg['base_public_head']!=BASE or cfg['base_public_tree']!=TREE or cfg['accepted_fresh_native10']is not None:
        raise ValueError('S05_FIXTURE_CONCRETE_PUBLIC_SOURCE_BINDING_REQUIRED')
    if cfg['failed_52eed']['usable_prerequisite']is not False or cfg['production_go']is not False:raise ValueError('S05_FIXTURE_PREPARATION_NOT_ACCEPTANCE')
    if git(repo,'rev-parse',BASE+'^{tree}').decode().strip()!=TREE:raise ValueError('S05_FIXTURE_EXACT_PUBLIC_TREE_REQUIRED')
    entries={}
    for row in git(repo,'ls-tree','-r','-z',BASE).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode().split();name=name.decode()
        if kind!='blob'or mode not in('100644','100755'):raise ValueError('S05_FIXTURE_UNSUPPORTED_PUBLIC_GIT_MEMBER')
        p=regular(repo,name);raw=p.read_bytes()
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=oid or bool(p.stat().st_mode&0o111)!=(mode=='100755'):
            raise ValueError('S05_FIXTURE_PUBLIC_BYTES_OR_MODE_CHANGED:'+name)
        entries[name]=dict(mode=mode,blob=oid)
    own={p for p in source['files']if p.startswith(NS)}|{NS+'SOURCE.json',WORKFLOW}
    observed=set()
    for p in here.rglob('*'):
        if p.is_symlink():raise ValueError('S05_FIXTURE_OWN_SOURCE_SYMLINK')
        if p.is_file():observed.add(str(p.relative_to(repo)))
    if observed!=own-{WORKFLOW}:raise ValueError('S05_FIXTURE_OWN_NAMESPACE_NOT_CLOSED')
    for name,pin in source['files'].items():
        p=regular(repo,name);raw=p.read_bytes()
        if type(pin['bytes'])is not int or len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']or bool(p.stat().st_mode&0o111)!=(pin['mode']=='100755'):
            raise ValueError('S05_FIXTURE_DECLARED_SOURCE_CHANGED:'+name)
    old=regular(repo,cfg['historical_current_AC_source_path']).read_bytes()
    if sha256(old).hexdigest()!=cfg['historical_current_AC_source_sha256']or len(json.loads(old)['files'])!=242:raise ValueError('S05_FIXTURE_FROZEN_SOURCE242_CHANGED')
    archive=json.loads(regular(repo,'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes());proofs={}
    if len(archive['files'])!=24:raise ValueError('S05_FIXTURE_EXACT24_PROOF_INPUTS_REQUIRED')
    for item in archive['files']:
        raw=regular(repo,item['path']).read_bytes()
        if raw!=regular(repo,item['archive']).read_bytes()or len(raw)!=item['bytes']or sha256(raw).hexdigest()!=item['sha256']:raise ValueError('S05_FIXTURE_HISTORICAL_PROOF_CHANGED')
        proofs[item['path']]=item['sha256']
    outputs=set();folder=repo/'cp6-proof/t3'
    if (repo/'cp6-proof').is_symlink()or folder.is_symlink():raise ValueError('S05_FIXTURE_GENERATED_ANCESTOR_SYMLINK')
    if folder.exists():
        for p in folder.rglob('*'):
            if p.is_symlink():raise ValueError('S05_FIXTURE_GENERATED_SYMLINK:'+str(p.relative_to(repo)))
            if p.is_file():outputs.add(str(p.relative_to(repo)))
    accepted,classes=generated(repo,here,outputs)
    if outputs!=set(accepted):raise ValueError('S05_FIXTURE_UNKNOWN_GENERATED_OUTPUT:'+repr(sorted(outputs-set(accepted))))
    tracked=set(git(repo,'ls-files','-z').decode().split('\0'))-{''};untracked=set(git(repo,'ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    unknown=(tracked|untracked)-set(entries)-own-set(proofs)-set(accepted)
    if unknown:raise ValueError('S05_FIXTURE_UNKNOWN_SOURCE_OR_RECEIPT:'+repr(sorted(unknown)))
    if set(proofs)&tracked:raise ValueError('S05_FIXTURE_HISTORICAL_PROOFS_MUST_REMAIN_UNTRACKED')
    changed=set(git(repo,'diff','--name-only',BASE,'HEAD').decode().splitlines())
    if not changed<=own:raise ValueError('S05_FIXTURE_ONLY_NEW_NAMESPACE_AND_WORKFLOW_ALLOWED')
    if require_clean:
        if git(repo,'status','--porcelain','--untracked-files=no').strip():raise ValueError('S05_FIXTURE_COMMITTED_CLEAN_SOURCE_REQUIRED')
        if changed!=own or not own<=tracked:raise ValueError('S05_FIXTURE_COMPLETE_NEW_NAMESPACE_MUST_BE_COMMITTED')
    return dict(status='EXACT_COMPLETE_PUBLIC52EED_AND_NEW_FIXTURE_QUALIFIER_SOURCE_ONLY',
        source_pins=len(source['files']),public_files=len(entries),public_bytes_modes_snapshot_sha256=sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest(),
        historical_source242_unchanged=True,historical_untracked_proofs=24,generated_non_source_outputs=classes,
        product_changes=0,original_callback_body_changes=0,actual_new_Native=0,production_go=False)


if __name__=='__main__':print(json.dumps(check()))
