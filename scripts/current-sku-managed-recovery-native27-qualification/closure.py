"""Every public f3d blob + exact new namespace/workflow; closed generated outputs."""
from hashlib import sha1,sha256
from pathlib import Path
from types import ModuleType
import importlib.util
import json
import os
import stat
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('sku27_closed_source_transition',HERE/'transition.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])

def raw(path,mode,*,root=ROOT):
    path=Path(path);root=Path(root)
    if not path.is_relative_to(root):raise ValueError('SKU27_SOURCE_PATH_ESCAPE')
    for parent in path.parents:
        if parent.is_symlink():raise ValueError('SKU27_SOURCE_ANCESTOR_SYMLINK:'+str(path.relative_to(root)))
        if parent==root:break
    else:raise ValueError('SKU27_SOURCE_PATH_ESCAPE')
    info=path.lstat()
    if mode=='120000':
        assert stat.S_ISLNK(info.st_mode),'SKU27_PARENT_SYMLINK_TYPE_CHANGED';return os.readlink(path).encode()
    assert mode in('100644','100755')and stat.S_ISREG(info.st_mode),'SKU27_SOURCE_FILE_TYPE_CHANGED'
    assert bool(info.st_mode&0o111)==(mode=='100755'),'SKU27_SOURCE_EXECUTABLE_MODE_CHANGED'
    return path.read_bytes()

def verify_files(root_or_files,files=None):
    root=ROOT if files is None else Path(root_or_files)
    files=root_or_files if files is None else files
    for name,pin in files.items():
        assert not Path(name).is_absolute()and'..'not in Path(name).parts,'SKU27_SOURCE_PATH_ESCAPE'
        value=raw(root/name,pin.get('mode','100644'),root=root)
        if len(value)!=pin['bytes']or sha256(value).hexdigest()!=pin['sha256']:
            raise ValueError('SKU27_EXACT_DECLARED_BYTES_CHANGED:'+name)
        if'blob'in pin and sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()!=pin['blob']:
            raise ValueError('SKU27_IMMUTABLE_PARENT_GIT_BLOB_CHANGED:'+name)

def parent_files():
    value=json.loads(raw(HERE/'PARENT_SOURCE.json','100644'))
    assert value['head']==t.BASE and value['tree']==t.TREE
    assert git('rev-parse',t.BASE+'^{tree}').decode().strip()==t.TREE
    entries={}
    for entry in git('ls-tree','-r','-z',t.BASE).split(b'\0'):
        if not entry:continue
        metadata,name=entry.split(b'\t',1);mode,kind,blob=metadata.decode().split();assert kind=='blob'
        entries[name.decode()]=dict(mode=mode,blob=blob)
    assert entries=={name:{key:pin[key]for key in('mode','blob')}for name,pin in value['files'].items()},'SKU27_PARENT_GIT_CLOSURE_CHANGED'
    verify_files(value['files'])
    return value['files']

def prepared_product():
    path=ROOT/'scripts/current-sku-recovery-material-lock/transition.py';raw_source=path.read_bytes()
    expected=json.loads((ROOT/'scripts/current-sku-recovery-material-lock/SOURCE.json').read_bytes())['files'][str(path.relative_to(ROOT))]
    assert len(raw_source)==expected['bytes']and sha256(raw_source).hexdigest()==expected['sha256']
    before="'--no-renames', BASE, '--'";after="'--no-renames', BASE, '"+t.PRODUCT_HEAD+"', '--'"
    text=raw_source.decode();assert text.count(before)==1;text=text.replace(before,after,1)
    assert text.replace(after,before,1).encode()==raw_source
    module=ModuleType('sku27_owning_prepared_source_historical_endpoint');module.__file__=str(path)
    exec(compile(text,str(path),'exec'),module.__dict__)
    proof=module.admitted()
    return dict(proof,one_historical_scope_endpoint=t.PRODUCT_HEAD,
      original_sha256=sha256(raw_source).hexdigest(),derived_sha256=sha256(text.encode()).hexdigest(),
      original_source43_bytes_unchanged=True,current_material_transition20_pins_unchanged=True)

def historical_proofs():
    archive=json.loads((ROOT/'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes());assert len(archive['files'])==24
    paths=set()
    for pin in archive['files']:
        path=pin['path'];assert path.startswith('.github/workflows/')and path.endswith('.yml')and path not in paths;paths.add(path)
        if(ROOT/path).exists():
            value=raw(ROOT/path,'100644');assert len(value)==pin['bytes']and sha256(value).hexdigest()==pin['sha256']
            assert value==(ROOT/pin['archive']).read_bytes()
    return paths

def generated(names):
    pins={};reports={}
    for label,filename in [('preDB','generated_receipts.py'),('SKU','generated_sku.py'),('later','generated_later.py')]:
        module=t.load('sku27_exact_generated_'+label,HERE/filename);found,summary=module.admit(ROOT,HERE,names)
        assert not set(pins)&set(found),'SKU27_GENERATED_CLASS_OVERLAP';pins.update(found);reports[label]=summary
    return pins,reports

def source_only(*,require_clean=True):
    source=json.loads(raw(HERE/'SOURCE.json','100644'));assert source['base_head']==t.BASE and source['base_tree']==t.TREE
    base=parent_files();verify_files(source['files']);product=prepared_product()
    for name in source['allowed_changes']:assert name==t.WORKFLOW or name.startswith(t.NS+'/')
    changed=set(git('diff','--name-only',t.BASE,'HEAD').decode().splitlines())
    assert changed<=set(source['allowed_changes']),'SKU27_UNDECLARED_COMMITTED_SOURCE'
    own={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc'}
    expected={name for name in source['files']if name.startswith(t.NS+'/')}|{t.NS+'/SOURCE.json'}
    assert own==expected,'SKU27_UNDECLARED_OWN_SOURCE'
    for name in own:assert not(ROOT/name).is_symlink(),'SKU27_OWN_SOURCE_SYMLINK'
    proofs=historical_proofs();reports={}
    if require_clean:
        assert not git('status','--porcelain','--untracked-files=no').strip(),'SKU27_DIRTY_TRACKED_SOURCE'
        untracked={name.decode()for name in git('ls-files','--others','--exclude-standard','-z').split(b'\0')if name}
        outputs,reports=generated(untracked-proofs)
        assert untracked<=proofs|set(outputs),'SKU27_UNDECLARED_UNTRACKED_SOURCE'
        assert changed==set(source['allowed_changes']),'SKU27_COMMITTED_SOURCE_CLOSURE_INCOMPLETE'
    return dict(status='EXACT_PUBLIC_F3D_AND_NEW_NATIVE27_QUALIFIER_SOURCE',unchanged_parent_files=len(base),
      parent_sql_exceptions=0,prepared_product=product,current_physical_sources=True,
      generated_non_source_output_classes=reports,financial_quantity_fullcensus_oracles_changed=False,
      actual_successor_execution=False,production_go=False,independent_acceptance=False)
