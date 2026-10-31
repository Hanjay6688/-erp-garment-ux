"""Closed additive D1/E sources over the exact prepared complete parent."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='a6cc41ec58e4d0d0c8191f1b1fe5c27309fff559'
TREE='48c5e13acdb5d8fb9529f2ce1661e4fee09e2a5b'
PREFIXES=('scripts/cp7_credit_correction_de/','scripts/cp7_complete_credit_de/',
    'scripts/current-complete-de-integration-preparation/')


def git(*args):
    return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],
        env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1'))


def entries(ref):
    result={}
    for line in git('ls-tree','-rz',ref).split(b'\0'):
        if not line:continue
        metadata,path=line.split(b'\t',1);mode,kind,blob=metadata.decode().split()
        if kind!='blob'or mode not in('100644','100755'):raise ValueError('COMPLETE_DE_REGULAR_SOURCE_REQUIRED')
        result[path.decode()]=(mode,blob)
    return result


def raw(name):
    relative=Path(name)
    if relative.is_absolute()or'..'in relative.parts:raise ValueError('COMPLETE_DE_SOURCE_PATH_ESCAPE')
    path=ROOT/relative
    if(any(p.is_symlink()for p in(path,*path.parents))or not path.is_file()or path.stat().st_mode&0o111):
        raise ValueError('COMPLETE_DE_NONEXECUTABLE_PHYSICAL_SOURCE_REQUIRED:'+name)
    return path.read_bytes()


def preflight(*,require_clean=True):
    manifest=str(HERE.relative_to(ROOT))+'/SOURCE.json';value=json.loads(raw(manifest))
    if(value['base_head']!=BASE or value['base_tree']!=TREE or value['actual_Native_cases']!=0
       or value['production_go']is not False or value['independent_acceptance']is not False):
        raise ValueError('COMPLETE_DE_EXACT_PREPARATION_REQUIRED')
    if git('rev-parse',BASE+'^{tree}').decode().strip()!=TREE:raise ValueError('COMPLETE_DE_BASE_TREE_CHANGED')
    base,current=entries(BASE),entries('HEAD')
    for name,pin in base.items():
        if current.get(name)!=pin:raise ValueError('COMPLETE_DE_PREPARED_PARENT_BLOB_OR_MODE_CHANGED:'+name)
    allowed=set(value['files'])|{manifest}
    if any(not n.startswith(PREFIXES)for n in allowed):raise ValueError('COMPLETE_DE_ONLY_THREE_OWN_NAMESPACES_ALLOWED')
    if set(current)-set(base)-allowed:raise ValueError('COMPLETE_DE_UNDECLARED_TRACKED_SOURCE')
    for name,pin in value['files'].items():
        data=raw(name)
        if len(data)!=pin['bytes']or sha256(data).hexdigest()!=pin['sha256']:
            raise ValueError('COMPLETE_DE_OWN_SOURCE_PIN_CHANGED:'+name)
    physical={str(p.relative_to(ROOT))for prefix in PREFIXES for p in(ROOT/prefix).rglob('*')
        if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
    if physical!=allowed:raise ValueError('COMPLETE_DE_CLOSED_OWN_SOURCE_REQUIRED')
    if require_clean:
        if(git('diff','--name-only','--no-ext-diff','HEAD','--').strip()
           or git('diff','--cached','--name-only','--no-ext-diff','--').strip()):
            raise ValueError('COMPLETE_DE_PHYSICAL_TRACKED_SOURCE_CHANGED')
        if set(current)!=set(base)|allowed:raise ValueError('COMPLETE_DE_ALL_OWN_SOURCES_MUST_BE_COMMITTED')
        history=json.loads(raw('scripts/current-workflow-history-isolation/ARCHIVE.json'))
        historical={row['path']:row for row in history['files']}
        executable={'.py','.pyc','.mjs','.cjs','.js','.ts','.tsx','.sql','.yml','.yaml','.sh'}
        for item in git('ls-files','--others','--exclude-standard','-z').split(b'\0'):
            if not item:continue
            name=item.decode()
            if name in historical:
                pin=historical[name];data=raw(name)
                if len(data)!=pin['bytes']or sha256(data).hexdigest()!=pin['sha256']:
                    raise ValueError('COMPLETE_DE_HISTORICAL_SOURCE_PROOF_CHANGED:'+name)
            elif Path(name).suffix in executable and not name.startswith('cp6-ui-build/'):
                raise ValueError('COMPLETE_DE_UNDECLARED_EXECUTABLE:'+name)
    return dict(status='EXACT_UNCHANGED_COMPLETE_PARENT_AND_CLOSED_D1_E_PREPARATION',
        base_head=BASE,base_tree=TREE,unchanged_parent_blobs_and_modes=len(base),own_paths=len(allowed),
        actual_Native_cases=0,production_go=False,independent_acceptance=False)
