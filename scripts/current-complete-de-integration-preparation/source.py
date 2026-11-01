"""Closed additive D1/E sources over the exact prepared complete parent."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='15a2170cea88cd03a4d1bcaa0873a969d495b9fa'
TREE='3fe772a1314ae6bc7c4f36f72e3fda8738eb70fc'
PREFIXES=('scripts/cp7_credit_correction_de/','scripts/cp7_complete_credit_de/',
    'scripts/current-complete-de-integration-preparation/')
WORKFLOW='.github/workflows/cp7-current-complete-de-native30.yml'


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


def actual_parent_receipt():
    spec=importlib.util.spec_from_file_location('complete_DE_exact_parent_before_workflow',HERE/'admission.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.parent_receipt()


def admit_workflow(declaration):
    """Only the exact declared template, after actual parent acceptance."""
    path=ROOT/WORKFLOW
    if WORKFLOW not in declaration['files']:
        if path.exists()or path.is_symlink():raise ValueError('COMPLETE_DE_UNDECLARED_WORKFLOW_REFUSED')
        return None
    if not path.is_file():raise ValueError('COMPLETE_DE_DECLARED_WORKFLOW_MISSING')
    data=raw(WORKFLOW)
    if declaration['files'][WORKFLOW]!={'bytes':len(data),'sha256':sha256(data).hexdigest()}:
        raise ValueError('COMPLETE_DE_EXACT_WORKFLOW_SOURCE_PIN_REQUIRED')
    if data!=raw(str(HERE.relative_to(ROOT))+'/native30.workflow.yml.txt'):
        raise ValueError('COMPLETE_DE_WORKFLOW_MUST_EQUAL_REVIEWED_TEMPLATE')
    receipt=actual_parent_receipt()
    if receipt['head']!=BASE or receipt['tree']!=TREE:
        raise ValueError('COMPLETE_DE_WORKFLOW_REQUIRES_EXACT_SOURCE_BASE_QUALIFICATION')
    return dict(status='EXACT_DECLARED_WORKFLOW_AND_ROOT_ACCEPTED_PARENT_SOURCE',
        parent_head=BASE,parent_tree=TREE,actual_case_credit=0)


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
    if any(not(n.startswith(PREFIXES)or n==WORKFLOW)for n in allowed):
        raise ValueError('COMPLETE_DE_ONLY_THREE_OWN_NAMESPACES_AND_EXACT_WORKFLOW_ALLOWED')
    if set(current)-set(base)-allowed:raise ValueError('COMPLETE_DE_UNDECLARED_TRACKED_SOURCE')
    for name,pin in value['files'].items():
        data=raw(name)
        if len(data)!=pin['bytes']or sha256(data).hexdigest()!=pin['sha256']:
            raise ValueError('COMPLETE_DE_OWN_SOURCE_PIN_CHANGED:'+name)
    physical={str(p.relative_to(ROOT))for prefix in PREFIXES for p in(ROOT/prefix).rglob('*')
        if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
    if physical!=allowed-{WORKFLOW}:raise ValueError('COMPLETE_DE_CLOSED_OWN_SOURCE_REQUIRED')
    workflow=admit_workflow(value)
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
        explicit_workflow_source=workflow,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)
