"""Finite actual-source successor, preserving all old manifests and guards."""
from pathlib import Path,PurePosixPath
from hashlib import sha1,sha256
import importlib.util
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='c397409a470c8c3d5f4963bbbdd7b676b1275af7'
IMPORTED='e299aa25fd96a422d71b16a2eb024011b3a6fa69'
NS='scripts/current-de-sku-parent-catalogue-qualification/'
WORKFLOW='.github/workflows/cp7-de-sku-parent-catalogue.yml'


def require(ok,message):
    if not ok:raise ValueError(message)


def document(raw):
    def pairs(items):
        value={}
        for key,item in items:
            require(key not in value,'DE_SKU_DUPLICATE_JSON_KEY');value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('DE_SKU_NONFINITE_JSON')))


def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def regular(name,root=ROOT):
    rel=PurePosixPath(name)
    require(not rel.is_absolute()and'..'not in rel.parts and'\\'not in name and str(rel)==name,'DE_SKU_UNSAFE_SOURCE_PATH')
    p=Path(root)/name
    require(not any(v.is_symlink()for v in(p,*p.parents)if v.is_relative_to(root)),'DE_SKU_SOURCE_LINK:'+name)
    require(p.is_file(),'DE_SKU_SOURCE_FILE_REQUIRED:'+name)
    return p


def checked_file(name,expected,root=ROOT):
    p=regular(name,root);raw=p.read_bytes()
    require(pin(raw)=={k:expected[k]for k in('bytes','sha256')},'DE_SKU_SOURCE_BYTES_CHANGED:'+name)
    require(bool(p.stat().st_mode&0o111)==(expected.get('mode','100644')=='100755'),'DE_SKU_SOURCE_MODE_CHANGED:'+name)
    return raw


def imported():
    value=document(regular(NS+'IMPORTED_SOURCE.json').read_bytes())
    require(value['base']==BASE and value['actual_command_runtime_opened']is False,'DE_SKU_EXACT_CLOSED_IMPORT_REQUIRED')
    for name,expected in value['records'].items():
        require(expected['source_head']==IMPORTED,'DE_SKU_PUBLIC_IMPORT_HEAD_CHANGED')
        raw=checked_file(name,expected)
        require(raw==git('show',IMPORTED+':'+expected.get('source_path',name)),'DE_SKU_PUBLIC_IMPORT_BYTES_CHANGED:'+name)
    return value['records']


def immutable_parent(imports):
    count=0
    for row in git('ls-tree','-rz',BASE).split(b'\0'):
        if not row:continue
        metadata,name=row.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=name.decode()
        require(kind=='blob'and mode in('100644','100755'),'DE_SKU_PARENT_SOURCE_TYPE_CHANGED')
        if name in imports:
            old=git('show',BASE+':'+name)
            require(sha256(old).hexdigest()==imports[name]['previous_sha256'],'DE_SKU_IMPORT_PREIMAGE_CHANGED')
            continue
        p=regular(name);raw=p.read_bytes()
        require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,'DE_SKU_IMMUTABLE_PARENT_CHANGED:'+name)
        require(bool(p.stat().st_mode&0o111)==(mode=='100755'),'DE_SKU_PARENT_MODE_CHANGED:'+name);count+=1
    return count


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def outputs(names):
    accepted=set();proofs={}
    for label,filename in(('early','generated_receipts.py'),('later','generated_later.py'),('SKU','generated_sku.py')):
        found,proof=load('de_sku_generated_'+label,HERE/filename).admit(ROOT,HERE,names)
        require(not accepted&set(found),'DE_SKU_GENERATED_OUTPUT_CLASS_OVERLAP')
        accepted.update(found);proofs[label]=proof
    archive=document((ROOT/'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes())
    for row in archive['files']:
        name=row['path']
        if name in names:
            checked_file(name,row)
            require(regular(name).read_bytes()==regular(row['archive']).read_bytes(),'DE_SKU_HISTORICAL_WORKFLOW_PROOF_CHANGED')
            accepted.add(name)
    require(set(names)<=accepted,'DE_SKU_UNKNOWN_UNTRACKED_SOURCE:'+','.join(sorted(set(names)-accepted)))
    return proofs


def preflight(require_clean=True):
    cfg=document(regular(NS+'SOURCE.json').read_bytes())
    require(cfg['base']==BASE and cfg['business_runtime_entry']is None and cfg['actual_business_cases']==0,
            'DE_SKU_EXACT_CATALOGUE_ONLY_SOURCE_REQUIRED')
    imports=imported();unchanged=immutable_parent(imports)
    for name,expected in cfg['files'].items():checked_file(name,expected)
    allowed=set(cfg['files'])|{NS+'SOURCE.json'}
    require(all(name.startswith(NS)or name in imports or name==WORKFLOW for name in allowed),'DE_SKU_SCOPE_ESCAPE')
    own={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()or p.is_symlink()}
    require(own=={name for name in allowed if name.startswith(NS)},'DE_SKU_EXACT_OWN_SOURCE_SET_REQUIRED')
    changed=set(git('diff','--name-only',BASE,'HEAD').decode().splitlines())
    require(changed<=allowed,'DE_SKU_UNDECLARED_COMMITTED_SOURCE')
    generated={}
    if require_clean:
        require(not git('status','--porcelain','--untracked-files=no').strip(),'DE_SKU_DIRTY_TRACKED_SOURCE')
        require(changed==allowed,'DE_SKU_COMMITTED_SOURCE_SET_INCOMPLETE')
        names={n.decode()for n in git('ls-files','--others','--exclude-standard','-z').split(b'\0')if n}
        generated=outputs(names)
    return dict(status='EXACT_C397_PLUS_PUBLIC_PHASE2_D1_E_SKU_CATALOGUE_SUCCESSOR',
        unchanged_parent_files=unchanged,exact_public_imports=len(imports),source_files=len(cfg['files']),
        old_source_manifests_resealed=False,old_catalogue_projections=False,generated_output_proofs=generated,
        actual_business_cases=0,actual_Native_cases=0,business_runtime_entry=None,production_go=False,independent_acceptance=False)


def admitted(repo=None,here=None,product=None):
    proof=preflight()
    if product is not None:
        require(Path(product.__file__).resolve()==(HERE/'stage.py').resolve(),'DE_SKU_ACTUAL_STAGE_MODULE_REQUIRED')
        proof['actual_stage_sources']=product.sources()
    return proof
