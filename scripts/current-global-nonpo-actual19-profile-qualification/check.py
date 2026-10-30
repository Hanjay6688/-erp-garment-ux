"""Closed finite source transition. No installer, database or runtime admission."""
from pathlib import Path,PurePosixPath
from hashlib import sha1,sha256
from types import ModuleType
import argparse
import importlib.util
import json
import os
import re
import stat
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='14b6490e4ceab9fa8806c78fe10ddc820580de21'
NS='scripts/current-global-nonpo-actual19-profile-qualification/'
PRODUCT='scripts/cp7_global_nonpo_native_graph_adapter/'
OLD='scripts/current-global-nonpo-native-graph-qualification/'
MODIFIED={PRODUCT+'AUTHORITY.json',PRODUCT+'authority.sql'}
CLOSED='ACTUAL19_SOURCE_PROFILE_CLOSED_NO_FINAL_PARENT_OR_GLOBAL_RUNTIME'
CAPTURE_PIN=dict(bytes=53674,sha256='7bae0b9efd389ca70a66b322fafca54e05538ad7d5b42b4f5d68f46d962f48e0')


def require(ok,message):
    if not ok:raise ValueError(message)


def document(raw):
    def pairs(values):
        result={}
        for key,value in values:
            require(key not in result,'ACTUAL19_DUPLICATE_JSON_KEY:'+key);result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('ACTUAL19_NONFINITE_JSON')))


def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],env=dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONDONTWRITEBYTECODE='1'))
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def regular(name,root=ROOT):
    rel=PurePosixPath(name)
    require(not rel.is_absolute()and '..'not in rel.parts and'\\'not in name and str(rel)==name,'ACTUAL19_UNSAFE_SOURCE_PATH')
    path=Path(root)/name
    require(not any(p.is_symlink()for p in(path,*path.parents)if p.is_relative_to(root)),'ACTUAL19_SOURCE_LINK:'+name)
    require(path.is_file(),'ACTUAL19_SOURCE_FILE_REQUIRED:'+name)
    return path


def checked_file(name,expected,root=ROOT):
    require(set(expected)=={'bytes','sha256','mode'}and type(expected['bytes'])is int
            and re.fullmatch('[0-9a-f]{64}',expected['sha256'])is not None
            and expected['mode']in('100644','100755'),'ACTUAL19_TYPED_PIN_REQUIRED')
    p=regular(name,root);raw=p.read_bytes()
    require(pin(raw)=={k:expected[k]for k in('bytes','sha256')},'ACTUAL19_SOURCE_BYTES_CHANGED:'+name)
    require(bool(p.stat().st_mode&0o111)==(expected['mode']=='100755'),'ACTUAL19_SOURCE_MODE_CHANGED:'+name)
    return raw


def parent_integrity():
    entries={}
    for row in git('ls-tree','-rz','--full-tree',BASE).split(b'\0'):
        if row:
            metadata,name=row.split(b'\t',1);entries[name.decode()]=metadata.decode().split()
    for name,(mode,kind,blob)in entries.items():
        if name in MODIFIED:continue
        p=regular(name);raw=p.read_bytes()
        require(kind=='blob'and mode in('100644','100755'),'ACTUAL19_UNSUPPORTED_INHERITED_SOURCE_TYPE')
        require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,'ACTUAL19_FROZEN_PUBLIC_FILE_CHANGED:'+name)
        require(bool(p.stat().st_mode&0o111)==(mode=='100755'),'ACTUAL19_FROZEN_PUBLIC_MODE_CHANGED:'+name)
    return len(entries)-len(MODIFIED)


def load_deriver():
    spec=importlib.util.spec_from_file_location('actual19_exact_deriver',HERE/'derive.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def private_source_proof(deriver):
    text,route=deriver.source_proof();module=ModuleType('actual19_private_counted_source_proof')
    module.__file__=str(ROOT/PRODUCT/'source.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__)
    proof=module.source_contract()
    require(proof['runtime_entry']is None and proof['known_source_functions']==19
            and proof['own_private_STABLE_functions']==4 and proof['actual_Native_credit']==0,
            'ACTUAL19_READONLY_PRIVATE_SOURCE_PROOF_CHANGED')
    return dict(proof,private_counted_source_route=route,product_module_file_changed=False)


def check(*,require_clean=True):
    cfg=document(regular(NS+'SOURCE.json').read_bytes())
    require(cfg['contract']=='cp7.global-nonpo.actual19-source-profile.v1'
            and cfg['base']==BASE and cfg['runtime_entry']is None
            and cfg['actual_Native_credit']==0 and cfg['production_go']is False
            and cfg['independent_acceptance']is False,'ACTUAL19_EXACT_CLOSED_SOURCE_DECLARATION_REQUIRED')
    for name,value in cfg['files'].items():checked_file(name,value)
    require(pin(regular(NS+'CAPTURE.json').read_bytes())==CAPTURE_PIN,'ACTUAL19_ROOT_CAPTURE_NOT_EXACT')
    require(not any((ROOT/'scripts').rglob('*.pyc')),'ACTUAL19_PROJECT_BYTECODE_CACHE_REFUSED')
    own=set()
    for p in HERE.rglob('*'):
        require(not p.is_symlink(),'ACTUAL19_OWN_NAMESPACE_LINK')
        if p.is_file():own.add(str(p.relative_to(ROOT)))
    require(own=={name for name in cfg['files']if name.startswith(NS)}|{NS+'SOURCE.json'},'ACTUAL19_EXACT_OWN_NAMESPACE_REQUIRED')
    require(not any(name.endswith('.pyc')for name in own),'ACTUAL19_BYTECODE_SOURCE_REFUSED')
    allowed=own|MODIFIED
    require(set(cfg['files'])==allowed-{NS+'SOURCE.json'},'ACTUAL19_EXACT_TWO_PRODUCTS_AND_NEW_NAMESPACE_REQUIRED')
    for line in git('diff','--name-status','--no-renames',BASE).decode().splitlines():
        status,name=line.split('\t')
        require(name in allowed and(status=='M'if name in MODIFIED else status=='A'),'ACTUAL19_UNDECLARED_GIT_CHANGE:'+line)
    untracked={x.decode()for x in git('ls-files','--others','--exclude-standard','-z').split(b'\0')if x}
    require(untracked<=own,'ACTUAL19_UNKNOWN_UNTRACKED_SOURCE')
    if require_clean:
        require(not git('status','--porcelain','--untracked-files=no').strip(),'ACTUAL19_DIRTY_TRACKED_SOURCE')
        require(not untracked,'ACTUAL19_UNCOMMITTED_SOURCE')
    unchanged=parent_integrity()
    old_source=document(git('show',BASE+':'+OLD+'SOURCE.json'))
    require(regular(OLD+'SOURCE.json').read_bytes()==git('show',BASE+':'+OLD+'SOURCE.json'),'ACTUAL19_OLD_SOURCE_RESEALED')
    for name,value in old_source['files'].items():
        historical=git('show',BASE+':'+name)
        require(pin(historical)==value,'ACTUAL19_OLD_MANIFEST_DOES_NOT_MATCH_PUBLIC_BASE')
        if name not in MODIFIED:require(regular(name).read_bytes()==historical,'ACTUAL19_OLD_SCOPE_OR_GUARD_CHANGED')
    deriver=load_deriver();authority,sql,proof=deriver.bundle()
    require(regular(PRODUCT+'AUTHORITY.json').read_bytes()==(json.dumps(authority,indent=2,ensure_ascii=False)+'\n').encode(),
            'ACTUAL19_AUTHORITY_NOT_EXACT_CAPTURE_TRANSITION')
    require(regular(PRODUCT+'authority.sql').read_bytes()==sql,'ACTUAL19_SQL_NOT_EXACT_SEVEN_SUBSTITUTIONS')
    require(document((HERE/'DERIVATIONS.json').read_bytes())==proof,'ACTUAL19_DERIVATION_RECEIPT_CHANGED')
    source_proof=private_source_proof(deriver)
    require(authority['required_final_composition_parent']is None and authority['runtime_entry']is None
            and authority['new_roles']==authority['new_public_RPC']==[],'ACTUAL19_CANNOT_OPEN_FROZEN_PRODUCT_RUNTIME')
    return dict(status='EXACT_CURRENT19_FINITE_SOURCE_PROFILE_ONLY',immutable_public_parent=BASE,
        unchanged_parent_files=unchanged,source_files=len(cfg['files']),changed_expected_source_bodies=2,
        other_known_entries_unchanged=17,full_function_catalog_rows=19,actual_source_catalogues=3,
        raw_acl_NULL_vs_explicit_inferred=False,source_proof=source_proof,
        runtime_entry=None,required_final_composition_parent=None,writer_or_phantom_lock_closed=False,
        actual_Native_credit=0,production_go=False,independent_acceptance=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--source',action='store_true');g.add_argument('--runtime',action='store_true');args=p.parse_args()
    if args.runtime:raise ValueError(CLOSED)
    print(json.dumps(check(),sort_keys=True))


if __name__=='__main__':main()
