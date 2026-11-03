"""Copy exact prerequisite bytes; retain new frozen-parent outputs separately.

Never overwrite a conflicting file or use a symlink. Retention compares full
file hashes with the pre-run manifest and keeps every changed/new file intact;
it neither projects JSON nor manufactures case or restoration results.
"""
from hashlib import file_digest
from pathlib import Path
import argparse,json,shutil
import materialize_parent,qualification

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT.parent/'qualified-afui-parent'
OWN=ROOT/'cp6-proof/t3'
PARENT=FROZEN/'cp6-proof/t3'
MANIFEST=OWN/'MANDOR_PARENT_PREREQUISITE_FILES.json'
RETAINED=OWN/'MANDOR_FROZEN_PARENT_EXECUTION'


def require(value,message):
    if not value:raise ValueError(message)


def regular(path,root):
    require(root.is_absolute()and root.resolve()==root and path.is_relative_to(root)
        and '..'not in path.relative_to(root).parts and not path.is_symlink(),
        'MANDOR_PARENT_ARTIFACT_PATH_OR_SYMLINK')
    for part in(path,*path.parents):
        require(not part.is_symlink(),'MANDOR_PARENT_ARTIFACT_ANCESTOR_SYMLINK')
        if part==root:break


def pin(path):
    with path.open('rb')as stream:return dict(bytes=path.stat().st_size,sha256=file_digest(stream,'sha256').hexdigest())


def inventory(root):
    require(root.is_dir()and not root.is_symlink(),'MANDOR_PARENT_ARTIFACT_REGULAR_DIRECTORY')
    result={}
    for path in sorted(root.rglob('*')):
        regular(path,root)
        if path.is_dir():continue
        require(path.is_file(),'MANDOR_PARENT_ARTIFACT_NONREGULAR_FILE')
        result[path.relative_to(root).as_posix()]=pin(path)
    return result


def copy_exact(source,destination,source_root,destination_root,expected):
    regular(source,source_root);regular(destination,destination_root)
    require(source.is_file()and pin(source)==expected,'MANDOR_PARENT_ARTIFACT_SOURCE_CHANGED')
    if destination.exists():
        require(destination.is_file()and pin(destination)==expected,'MANDOR_PARENT_ARTIFACT_EXISTING_BYTES_CONFLICT')
        return False
    destination.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb')as inp,destination.open('xb')as out:shutil.copyfileobj(inp,out,1024*1024)
    require(pin(destination)==expected,'MANDOR_PARENT_ARTIFACT_COPY_NOT_IDENTICAL')
    return True


def prepare():
    _,parent=qualification.actual_parent()
    materialize_parent.materialize()
    require(not MANIFEST.exists()and not RETAINED.exists(),'MANDOR_PARENT_ARTIFACT_SINGLE_PREPARATION')
    sources=inventory(OWN);PARENT.mkdir(parents=True,exist_ok=True)
    copied=[]
    for name,expected in sources.items():
        if copy_exact(OWN/name,PARENT/name,OWN,PARENT,expected):copied.append(name)
    result=dict(status='EXACT_PREREQUISITE_BYTES_FOR_FROZEN_AFUI_PARENT',head=parent['head'],tree=parent['tree'],
        original_sources=sources,parent_before_runtime=inventory(PARENT),copied=copied,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)
    with MANIFEST.open('x')as out:out.write(json.dumps(result,indent=2)+'\n')
    return dict(status=result['status'],source_files=len(sources),new_copies=len(copied),actual_Native_cases=0)


def retain():
    if not MANIFEST.exists():return dict(status='PARENT_EXECUTION_NOT_PREPARED',actual_Native_cases=0)
    regular(MANIFEST,OWN);baseline=json.loads(MANIFEST.read_bytes())
    require(baseline['status']=='EXACT_PREREQUISITE_BYTES_FOR_FROZEN_AFUI_PARENT','MANDOR_PARENT_ARTIFACT_EXACT_BASELINE_MANIFEST')
    current=inventory(PARENT);changed={n:p for n,p in current.items()if baseline['parent_before_runtime'].get(n)!=p}
    retained=[]
    for name,expected in changed.items():
        copy_exact(PARENT/name,RETAINED/name,PARENT,RETAINED,expected);retained.append(name)
    result=dict(status='ALL_NEW_OR_CHANGED_FROZEN_PARENT_OUTPUT_BYTES_RETAINED',files=changed,
        missing_baseline_files=sorted(set(baseline['parent_before_runtime'])-set(current)),
        files_overwritten=False,JSON_or_row_projection=False,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)
    receipt=OWN/'MANDOR_FROZEN_PARENT_EXECUTION_RECEIPT.json'
    raw=(json.dumps(result,indent=2)+'\n').encode()
    if receipt.exists():require(receipt.read_bytes()==raw,'MANDOR_PARENT_ARTIFACT_RETENTION_RECEIPT_CHANGED')
    else:
        with receipt.open('xb')as out:out.write(raw)
    return dict(status=result['status'],retained_files=len(retained),missing_baseline_files=len(result['missing_baseline_files']),actual_Native_cases=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--retain',action='store_true');args=parser.parse_args()
    print(json.dumps(prepare()if args.prepare else retain(),sort_keys=True))
