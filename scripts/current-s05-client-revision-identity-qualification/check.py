"""Verify one client parser correction; no old manifest is rewritten or bypassed."""
from hashlib import sha1, sha256
from pathlib import Path
import argparse
import json
import os
import stat
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='519d1760a3bad06a346b3d4b3cc0203664615634'
PRODUCT=('src/accessoryStandardReport.ts','src/accessoryStandardReport.test.ts')


def exact_json(actual,expected):
    if type(actual)is not type(expected):return False
    if type(expected)is dict:return set(actual)==set(expected)and all(exact_json(actual[k],v)for k,v in expected.items())
    if type(expected)is list:return len(actual)==len(expected)and all(exact_json(a,b)for a,b in zip(actual,expected))
    return actual==expected


def strict_json(raw):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('S05_CLIENT_DUPLICATE_SOURCE_KEY')
            result[k]=v
        return result
    def constant(_):raise ValueError('S05_CLIENT_NONFINITE_SOURCE_VALUE')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


def git(*args):
    return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))


def physical(path):
    p=ROOT/path
    for ancestor in (p,*p.parents):
        if ancestor==ROOT:break
        if ancestor.is_symlink():raise ValueError('S05_CLIENT_SOURCE_SYMLINK:'+path)
    if not stat.S_ISREG(p.lstat().st_mode):raise ValueError('S05_CLIENT_REGULAR_FILE_REQUIRED:'+path)
    return p.read_bytes()


def pins():
    paths=sorted([*PRODUCT,*(str(p.relative_to(ROOT))for p in HERE.iterdir()if p.is_file()and p.name!='SOURCE.json')])
    result={}
    for p in paths:
        raw=physical(p);mode=stat.S_IMODE((ROOT/p).stat().st_mode)
        if mode!=0o644:raise ValueError('S05_CLIENT_SOURCE_MODE_CHANGED:'+p)
        result[p]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest(),mode='100644')
    return result


def immutable():
    count=0
    for line in git('ls-tree','-rz',BASE).split(b'\0'):
        if not line:continue
        meta,raw_name=line.split(b'\t',1);mode,kind,blob=meta.decode().split();name=raw_name.decode()
        raw=physical(name)
        if kind!='blob':raise ValueError('S05_CLIENT_PARENT_BLOB_REQUIRED:'+name)
        if stat.S_IMODE((ROOT/name).stat().st_mode)!=(0o755 if mode=='100755'else 0o644):
            raise ValueError('S05_CLIENT_PARENT_MODE_CHANGED:'+name)
        if name in PRODUCT:continue
        if sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=blob:
            raise ValueError('S05_CLIENT_IMMUTABLE_PARENT_CHANGED:'+name)
        count+=1
    original=git('show',BASE+':'+PRODUCT[0]).decode();current=physical(PRODUCT[0]).decode()
    before='return { id: idText(x.id), material_id:';after='return { id: uuid(x.id), material_id:'
    if original.count(before)!=1 or current!=original.replace(before,after,1):
        raise ValueError('S05_CLIENT_EXACT_ONE_REVISION_VALIDATOR_CHANGE_REQUIRED')
    allowed=set(PRODUCT)|{str(p.relative_to(ROOT))for p in HERE.iterdir()if p.is_file()}
    changed=set(git('diff','--name-only',BASE).decode().splitlines())|set(git('ls-files','--others','--exclude-standard').decode().splitlines())
    if not changed<=allowed:raise ValueError('S05_CLIENT_UNALLOCATED_FILE:'+repr(sorted(changed-allowed)))
    return count


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');args=parser.parse_args()
    count=immutable();value=dict(contract='cp7.s05.client-native-uuid-revision.v1',base=BASE,unchanged_parent_files=count,files=pins(),
        old_manifests_unchanged=True,Native_code_changed=False,actual_browser_cases=0,production_go=False,independent_acceptance=False)
    target=HERE/'SOURCE.json'
    if args.freeze:
        if os.environ.get('CI')or os.environ.get('GITHUB_ACTIONS')=='true':raise ValueError('S05_CLIENT_RESEAL_IN_CI_REFUSED')
        target.write_text(json.dumps(value,indent=2)+'\n')
    else:
        if stat.S_IMODE(target.stat().st_mode)!=0o644:raise ValueError('S05_CLIENT_MANIFEST_MODE_CHANGED')
        if not exact_json(strict_json(physical(str(target.relative_to(ROOT)))),value):raise ValueError('S05_CLIENT_EXACT_CURRENT_SOURCE_REQUIRED')
    print(json.dumps(dict(status='SOURCE_ONLY_NO_DB',unchanged_parent_files=count,files=len(value['files']),actual_browser_cases=0)))
