"""Exact immutable phase2 parent plus closed context inventory; no database."""
from pathlib import Path,PurePosixPath
from hashlib import sha1,sha256
import argparse
import importlib.util
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='e46233133753cd31b0b4120a3a5a88be745aa223'
NS='scripts/current-final-composition-context-qualification/'
INVENTORY_PIN=dict(bytes=983292,sha256='a81485c98d206e38702bb53fcb60cf6c3feaf1b350a58c3fd6172e6e1281a107')
CLOSED='FINAL_CONTEXT_RUNTIME_CLOSED_ACTUAL_COMPOSITE_RAW_ACL_AND_PHASE_PROOFS_REQUIRED'


def require(ok,message):
    if not ok:raise ValueError(message)


def document(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'FINAL_CONTEXT_DUPLICATE_JSON_KEY');result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError('FINAL_CONTEXT_NONFINITE_JSON')))


def git(*args):return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def regular(name,root=ROOT):
    rel=PurePosixPath(name)
    require(not rel.is_absolute()and '..'not in rel.parts and'\\'not in name and str(rel)==name,
            'FINAL_CONTEXT_UNSAFE_SOURCE_PATH')
    path=Path(root)/name
    require(not any(p.is_symlink()for p in(path,*path.parents)if p.is_relative_to(root)),
            'FINAL_CONTEXT_SOURCE_LINK:'+name)
    require(path.is_file(),'FINAL_CONTEXT_SOURCE_FILE_REQUIRED:'+name)
    return path


def checked_file(name,expected,root=ROOT):
    require(set(expected)=={'bytes','sha256','mode'}and type(expected['bytes'])is int
        and expected['mode']in('100644','100755'),'FINAL_CONTEXT_TYPED_SOURCE_PIN_REQUIRED')
    p=regular(name,root);raw=p.read_bytes()
    require(pin(raw)=={k:expected[k]for k in('bytes','sha256')},'FINAL_CONTEXT_SOURCE_BYTES_CHANGED:'+name)
    require(bool(p.stat().st_mode&0o111)==(expected['mode']=='100755'),'FINAL_CONTEXT_SOURCE_MODE_CHANGED:'+name)
    return raw


def parent_integrity():
    count=0
    for row in git('ls-tree','-rz','--full-tree',BASE).split(b'\0'):
        if not row:continue
        metadata,name=row.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=name.decode()
        require(kind=='blob'and mode in('100644','100755'),'FINAL_CONTEXT_UNEXPECTED_PARENT_SOURCE_TYPE')
        p=regular(name);raw=p.read_bytes()
        require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,
                'FINAL_CONTEXT_IMMUTABLE_PARENT_CHANGED:'+name)
        require(bool(p.stat().st_mode&0o111)==(mode=='100755'),'FINAL_CONTEXT_IMMUTABLE_PARENT_MODE_CHANGED:'+name)
        count+=1
    return count


def check(require_clean=True):
    cfg=document(regular(NS+'SOURCE.json').read_bytes())
    require(cfg['base']==BASE and cfg['runtime_entry']is None and cfg['actual_Native_credit']==0,
            'FINAL_CONTEXT_SOURCE_CANNOT_OPEN_RUNTIME')
    own={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()or p.is_symlink()}
    require(own==set(cfg['files'])|{NS+'SOURCE.json'},'FINAL_CONTEXT_EXACT_OWN_SOURCE_REQUIRED')
    require(all(name.startswith(NS)for name in own),'FINAL_CONTEXT_OWN_NAMESPACE_ONLY')
    for name,expected in cfg['files'].items():checked_file(name,expected)
    require(pin(regular(NS+'INVENTORY.json').read_bytes())==INVENTORY_PIN,'FINAL_CONTEXT_ROOT_INVENTORY_CHANGED')
    changed=set(git('diff','--name-only',BASE,'HEAD').decode().splitlines())
    require(changed<=own,'FINAL_CONTEXT_UNDECLARED_COMMITTED_SOURCE')
    untracked={n.decode()for n in git('ls-files','--others','--exclude-standard','-z').split(b'\0')if n}
    require(untracked<=own,'FINAL_CONTEXT_UNDECLARED_UNTRACKED_SOURCE')
    if require_clean:
        require(not git('status','--porcelain','--untracked-files=no').strip(),'FINAL_CONTEXT_DIRTY_TRACKED_SOURCE')
        require(not untracked and changed==own,'FINAL_CONTEXT_SOURCE_NOT_FULLY_COMMITTED')
    unchanged=parent_integrity();inventory=document(regular(NS+'INVENTORY.json').read_bytes())
    require(inventory['base']==BASE and inventory['runtime_entry']is None
        and inventory['full_final_catalogue_captured']is False
        and inventory['current_actor_request_backend_tx_phase_and_original_domain_guards_qualified']is False,
        'FINAL_CONTEXT_INCOMPLETE_RUNTIME_MUST_REMAIN_CLOSED')
    return dict(status='EXACT_PHASE2_PLUS_CLOSED_CONTEXT_SOURCE_ONLY',immutable_parent=BASE,
        unchanged_parent_files=unchanged,new_source_files=len(cfg['files']),
        actual_narrow_profiles={k:len(v['names'])for k,v in inventory['narrow_profiles'].items()},
        common_context_tables=51,original_known_tables=30,additional_existing_tables=21,
        proposed_final_tables=56,actual_final_composite=False,
        raw_ACLs_and_reader_visibility_bound=False,active_authority_decided=False,
        runtime_entry=None,actual_Native_credit=0,production_go=False,independent_acceptance=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source',action='store_true');group.add_argument('--runtime',action='store_true')
    args=parser.parse_args()
    if args.runtime:raise ValueError(CLOSED)
    print(json.dumps(check(),sort_keys=True))


if __name__=='__main__':main()
