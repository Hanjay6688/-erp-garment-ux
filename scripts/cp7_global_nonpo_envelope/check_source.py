"""Physical preparation checks only; no DB/client import or Native operation."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def check():
    p=HERE/'SOURCE.json';manifest=json.loads(p.read_bytes())
    assert manifest['classification']=='CLOSED_GLOBAL_ENVELOPE_LOCK_PRIMITIVE_PREPARATION_NOT_QUALIFICATION'
    assert manifest['runtime_entry']is None and manifest['actual_Native_cases']==0
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],env=env)
    assert git('rev-parse',manifest['base_head']+'^{tree}').decode().strip()==manifest['base_tree']
    def entries(ref):
        result={}
        for line in git('ls-tree','-rz',ref).split(b'\0'):
            if line:
                meta,name=line.split(b'\t',1);result[name.decode()]=meta.decode()
        return result
    base,current=entries(manifest['base_head']),entries('HEAD')
    assert all(current.get(name)==meta for name,meta in base.items()),'GLOBAL_ENVELOPE_PREPARED_PARENT_CHANGED'
    physical={str(f.relative_to(ROOT))for f in HERE.rglob('*')if f.is_file()and'__pycache__'not in f.parts}
    assert physical==set(manifest['files'])|{str(p.relative_to(ROOT))},'GLOBAL_ENVELOPE_EXACT_OWN_SOURCE'
    for name,expected in manifest['files'].items():
        f=ROOT/name;assert f.is_file()and not f.is_symlink()and not f.stat().st_mode&0o111
        raw=f.read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected,name
    proof=json.loads((HERE/'SYNTAX_AND_SOURCE_CONTROLS.json').read_bytes())
    for name,expected in proof['files'].items():
        raw=(HERE/name).read_bytes();assert len(raw)==expected['bytes']and sha256(raw).hexdigest()==expected['sha256']
    assert proof['SQL_executed']==proof['Native_cases']==0 and proof['actual_installer_or_owning_hooks']==0
    assert len(set(proof['required_actual_accepted15a_relation_keys']))==42
    spec=importlib.util.spec_from_file_location('global_envelope_preparation_gate',HERE/'admission.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    assert gate.RUNTIME_ENTRY is None and gate.PARENT_HEAD is None and gate.PARENT_TREE is None and gate.PARENT_ROOT_RECEIPT is None
    try:gate.parent()
    except ValueError as error:assert str(error)=='CP7_GLOBAL_ENVELOPE_ACTUAL_FINAL_PARENT_AND_OWNING_SCOPE_PENDING'
    else:raise ValueError('GLOBAL_ENVELOPE_PARENT_GATE_WAS_OPENED')
    return dict(status='GLOBAL_PRIVATE_ENVELOPE_SOURCE_ONLY_NOT_RUNTIME_OR_PROFILE_QUALIFICATION',
        unchanged_parent_blobs_and_modes=len(base),own_source_pins=len(manifest['files']),
        parent_gate_closed=True,runtime_entry=None,profile_seed_statements=0,
        actual_ERP_SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
