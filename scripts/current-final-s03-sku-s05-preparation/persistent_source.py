"""Closed final-assembly preparation sources over the exact financial base."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='33988923ab3bad708b21f3c74002f1309a3644e1'
TREE='b5698d239cb1744c95b49c71c9d68131d8af5f83'
PREFIXES=('scripts/cp7_current_s03_sku_s05/','scripts/current-final-s03-sku-s05-preparation/')
WORKFLOW='.github/workflows/cp7-final-s03-sku-s05.yml'


def git(*args):
    return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],
        env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1'))


def entries(ref):
    result={}
    for row in git('ls-tree','-rz',ref).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,blob=meta.decode().split()
        if kind!='blob'or mode not in('100644','100755'):
            raise ValueError('PERMANENT_S05_REGULAR_SOURCE_REQUIRED')
        result[name.decode()]=(mode,blob)
    return result


def raw(name):
    path=Path(name)
    if path.is_absolute()or'..'in path.parts:raise ValueError('PERMANENT_S05_SOURCE_PATH_ESCAPE')
    full=ROOT/path
    if any(p.is_symlink()for p in(full,*full.parents))or not full.is_file():
        raise ValueError('PERMANENT_S05_REGULAR_PHYSICAL_SOURCE_REQUIRED:'+name)
    if full.stat().st_mode&0o111:
        raise ValueError('PERMANENT_S05_EXACT_NONEXECUTABLE_SOURCE_MODE_REQUIRED:'+name)
    return full.read_bytes()


def preflight(*,require_clean=True):
    manifest=str(HERE.relative_to(ROOT))+'/PREPARATION.json'
    declaration=json.loads(raw(manifest))
    if(declaration['base_head']!=BASE or declaration['actual_new_Native_cases']!=0
       or declaration['production_go']is not False or declaration['independent_acceptance']is not False):
        raise ValueError('PERMANENT_S05_EXACT_PREPARATION_NOT_ACCEPTANCE_REQUIRED')
    if git('rev-parse',BASE+'^{tree}').decode().strip()!=TREE:
        raise ValueError('PERMANENT_S05_FINANCIAL_BASE_TREE_CHANGED')
    base=entries(BASE);current=entries('HEAD')
    for name,value in base.items():
        if current.get(name)!=value:raise ValueError('PERMANENT_S05_FINANCIAL_BASE_BLOB_MODE_CHANGED:'+name)
    allowed=set(declaration['files'])|{manifest}
    if any(not(name.startswith(PREFIXES)or name==WORKFLOW)for name in allowed):
        raise ValueError('PERMANENT_S05_ONLY_OWN_NAMESPACES_AND_WORKFLOW_ALLOWED')
    for name,pin in declaration['files'].items():
        value=raw(name)
        if type(pin['bytes'])is not int or len(value)!=pin['bytes']or sha256(value).hexdigest()!=pin['sha256']:
            raise ValueError('PERMANENT_S05_OWN_SOURCE_CHANGED:'+name)
    physical={str(p.relative_to(ROOT))for prefix in PREFIXES for p in(ROOT/prefix).rglob('*')
        if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
    if physical!={name for name in allowed if name.startswith(PREFIXES)}:
        raise ValueError('PERMANENT_S05_CLOSED_OWN_SOURCE_REQUIRED')
    if set(current)-set(base)-allowed:raise ValueError('PERMANENT_S05_UNDECLARED_TRACKED_SOURCE')
    if require_clean:
        if git('diff','--name-only','--no-ext-diff','HEAD','--').strip()or git('diff','--cached','--name-only','--no-ext-diff','--').strip():
            raise ValueError('PERMANENT_S05_PHYSICAL_TRACKED_SOURCE_CHANGED')
        if set(current)!=set(base)|allowed:raise ValueError('PERMANENT_S05_ALL_CURRENT_SOURCES_MUST_BE_COMMITTED')
        history=json.loads(raw('scripts/current-workflow-history-isolation/ARCHIVE.json'))
        historical={row['path']:row for row in history['files']}
        executable={'.py','.pyc','.mjs','.cjs','.js','.ts','.tsx','.sql','.yml','.yaml','.sh'}
        for value in git('ls-files','--others','--exclude-standard','-z').split(b'\0'):
            if not value:continue
            name=value.decode()
            if name in historical:
                pin=historical[name];value=raw(name)
                if len(value)!=pin['bytes']or sha256(value).hexdigest()!=pin['sha256']:
                    raise ValueError('PERMANENT_S05_HISTORICAL_PROOF_CHANGED:'+name)
            elif Path(name).suffix in executable and not name.startswith('cp6-ui-build/'):
                raise ValueError('PERMANENT_S05_UNDECLARED_EXECUTABLE:'+name)
    return dict(status='EXACT_UNCHANGED_FINANCIAL_BASE_AND_CLOSED_PERMANENT_READER_SOURCES',
        base_head=BASE,base_tree=TREE,unchanged_base_blobs_and_modes=len(base),own_current_paths=len(allowed),
        actual_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(preflight(),sort_keys=True))
