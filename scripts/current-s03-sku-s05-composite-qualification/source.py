"""Exact joined base plus the one declared current qualifier namespace."""
from pathlib import Path
from hashlib import sha256,sha1
import importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREFIX=str(HERE.relative_to(ROOT))+'/'
BASE='b25eaae55a144aa03cc05f8f77109f5d0b02fbfb'
TREE='e08f5eba90fd9a2deeb53a0a483c49e7a080e31c'
WORKFLOW='.github/workflows/cp7-s03-sku-s05-composite.yml'
FOCUSED_WORKFLOW='.github/workflows/cp7-s03-sku-owner-access-native1.yml'
LAYOUT='src/accessory-standard-report.css'
FOLLOWUP_PREFIX='scripts/current-s05-css-followup-qualification/'
FOLLOWUP_WORKFLOW='.github/workflows/cp7-s05-css-followup.yml'
READER_MANIFEST='scripts/cp7_s05_s03_sku_composition/SOURCE.json'


def git(*args):
    return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],
        env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1'))


def entries(ref):
    result={}
    for row in git('ls-tree','-rz',ref).split(b'\0'):
        if not row:continue
        metadata,name=row.split(b'\t',1);mode,kind,blob=metadata.decode().split()
        if kind!='blob'or mode not in('100644','100755'):raise ValueError('JOIN_REGULAR_SOURCE_REQUIRED')
        result[name.decode()]=(mode,blob)
    return result


def raw(name,mode='100644'):
    relative=Path(name)
    if relative.is_absolute()or'..'in relative.parts:raise ValueError('JOIN_SOURCE_PATH_ESCAPE')
    path=ROOT/relative
    if any(p.is_symlink()for p in(path,*path.parents)):
        raise ValueError('JOIN_SOURCE_SYMLINK_FORBIDDEN:'+name)
    if not path.is_file()or bool(path.stat().st_mode&0o111)!=(mode=='100755'):
        raise ValueError('JOIN_SOURCE_FILE_MODE_CHANGED:'+name)
    return path.read_bytes()


def preflight(*,require_clean=True):
    value=json.loads(raw(PREFIX+'SOURCE.json'))
    if value['base_head']!=BASE or value['base_tree']!=TREE or value['actual_cases']!=0:
        raise ValueError('JOIN_EXACT_PREPARED_BASE_REQUIRED')
    if value['production_go']is not False or value['independent_acceptance']is not False:
        raise ValueError('JOIN_SOURCE_IS_NOT_ACCEPTANCE')
    if git('rev-parse',BASE+'^{tree}').decode().strip()!=TREE:raise ValueError('JOIN_BASE_TREE_CHANGED')
    for name,expected in value['files'].items():
        if sha256(raw(name)).hexdigest()!=expected:raise ValueError('JOIN_SOURCE_PIN_CHANGED:'+name)
    spec=importlib.util.spec_from_file_location('joined_closed_S05_css_derivation',HERE/'ui_layout.py')
    layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
    derived,layout_proof=layout.derive(git('show',BASE+':'+LAYOUT))
    if raw(LAYOUT)!=derived:raise ValueError('JOIN_EXACT_REVIEWED_S05_CSS_REQUIRED')
    spec=importlib.util.spec_from_file_location('joined_exact_current_reader_CSS_pin',ROOT/FOLLOWUP_PREFIX/'reader_binding.py')
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    reader_derived,reader_proof=reader.derive(git('show',BASE+':'+READER_MANIFEST))
    if raw(READER_MANIFEST)!=reader_derived:raise ValueError('JOIN_EXACT_CURRENT_READER_MANIFEST_DERIVATION_REQUIRED')
    reviewed={LAYOUT:derived,READER_MANIFEST:reader_derived}
    base=entries(BASE);current=entries('HEAD')
    for name,entry in base.items():
        if name in reviewed:
            content=reviewed[name]
            expected=(entry[0],sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest())
            if current.get(name)!=expected:raise ValueError('JOIN_COMMITTED_REVIEWED_S05_DERIVATION_REQUIRED:'+name)
            continue
        if current.get(name)!=entry:raise ValueError('JOIN_FROZEN_BASE_BLOB_MODE_CHANGED:'+name)
    allowed=set(value['files'])|{PREFIX+'SOURCE.json'}
    if any(not(name.startswith((PREFIX,FOLLOWUP_PREFIX))or name in(WORKFLOW,FOCUSED_WORKFLOW,LAYOUT,FOLLOWUP_WORKFLOW,READER_MANIFEST))for name in allowed):
        raise ValueError('JOIN_ONLY_OWN_NAMESPACE_AND_WORKFLOW_ALLOWED')
    if set(current)-set(base)-allowed:raise ValueError('JOIN_UNDECLARED_TRACKED_SOURCE')
    for name,expected in value['files'].items():
        content=raw(name)
        if sha256(content).hexdigest()!=expected:raise ValueError('JOIN_SOURCE_PIN_CHANGED:'+name)
    owned={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
    owned.update(str(p.relative_to(ROOT))for p in(ROOT/FOLLOWUP_PREFIX).rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc')
    if owned!={name for name in allowed if name.startswith((PREFIX,FOLLOWUP_PREFIX))}:
        raise ValueError('JOIN_CLOSED_OWN_SOURCE_REQUIRED')
    if require_clean:
        if git('diff','--name-only','--no-ext-diff','HEAD','--').strip():raise ValueError('JOIN_PHYSICAL_TRACKED_SOURCE_CHANGED')
        if git('diff','--cached','--name-only','--no-ext-diff','--').strip():raise ValueError('JOIN_INDEX_SOURCE_CHANGED')
        if set(current)!=set(base)|allowed:raise ValueError('JOIN_ALL_DECLARED_SOURCES_MUST_BE_COMMITTED')
        history=json.loads(raw('scripts/current-workflow-history-isolation/ARCHIVE.json'))
        historical={row['path']:row for row in history['files']}
        untracked={name.decode()for name in git('ls-files','--others','--exclude-standard','-z').split(b'\0')if name}
        executable={'.py','.pyc','.mjs','.cjs','.js','.ts','.tsx','.sql','.yml','.yaml','.sh'}
        for name in untracked:
            if name in historical:
                item=historical[name];content=raw(name)
                if len(content)!=item['bytes']or sha256(content).hexdigest()!=item['sha256']:
                    raise ValueError('JOIN_HISTORICAL_WORKFLOW_PROOF_CHANGED:'+name)
            elif Path(name).suffix in executable and not name.startswith('cp6-ui-build/'):
                raise ValueError('JOIN_UNDECLARED_EXECUTABLE_SOURCE:'+name)
    return dict(status='EXACT_CURRENT_S03_SKU_S05_BASE_AND_CLOSED_QUALIFIER_SOURCE',base_head=BASE,base_tree=TREE,
        unchanged_base_blobs_and_modes=len(base)-2,reviewed_S05_css_derivation=layout_proof,
        reviewed_current_reader_manifest_derivation=reader_proof,current_qualifier_files=len(allowed),
        current_own_source_hashes_verified=True,tracked_physical_changes_refused=require_clean,
        untracked_executable_sources_refused=require_clean,generated_outputs_are_not_source_waivers=True,
        actual_Native_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(preflight(),sort_keys=True))
