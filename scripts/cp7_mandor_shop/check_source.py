"""Exact preparation input and byte checks, with no ERP import or SQL call."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def check():
    manifest=HERE/'SOURCE.json';value=json.loads(manifest.read_bytes())
    assert value['classification']=='CLOSED_FG_MANDOR_STORAGE_EVENT_PREPARATION_NOT_QUALIFICATION'
    assert value['actual_Native_cases']==0 and value['production_go']is False and value['independent_acceptance']is False
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],env=env)
    assert git('rev-parse',value['base_head']+'^{tree}').decode().strip()==value['base_tree']
    def entries(ref):
        result={}
        for line in git('ls-tree','-rz',ref).split(b'\0'):
            if line:
                metadata,path=line.split(b'\t',1);result[path.decode()]=metadata.decode()
        return result
    base,current=entries(value['base_head']),entries('HEAD')
    assert all(current.get(name)==item for name,item in base.items()),'FG_MANDOR_PREPARED_PARENT_BLOB_OR_MODE_CHANGED'
    physical={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
    assert physical==set(value['files'])|{str(manifest.relative_to(ROOT))},'FG_MANDOR_CLOSED_OWN_SOURCE_REQUIRED'
    for name,expected in value['files'].items():
        p=ROOT/name;assert p.is_file()and not p.is_symlink()and not p.stat().st_mode&0o111
        raw=p.read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected,('FG_MANDOR_SOURCE_PIN_CHANGED',name)
    spec=importlib.util.spec_from_file_location('fg_mandor_storage_preparation_gate_only',HERE/'admission.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    assert gate.RUNTIME_ENTRY is None
    try:gate.accepted_parent(b'not-a-parent-receipt')
    except ValueError as error:assert str(error)=='CP7_MANDOR_SHOP_ACTUAL_FINAL_ACCEPTED_PARENT_PENDING'
    else:raise ValueError('FG_MANDOR_PREPARATION_PARENT_GATE_WAS_OPEN')
    model=json.loads((HERE/'STORAGE_MODEL_CONTROLS.json').read_bytes())
    assert model['status']=='FG_MANDOR_ISOLATED_STORAGE_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert model['actual_Native_cases']==0 and model['actual_Auth_HTTP_cases']==0 and model['actual_two_session_races']==0
    for name,expected in model['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    return dict(status='FG_MANDOR_EXACT_STORAGE_PREPARATION_SOURCE_ONLY',unchanged_parent_blobs_and_modes=len(base),
        own_source_pins=len(value['files']),storage_model_controls=len(model['results']),parent_gate_closed=True,
        runtime_entry=None,ERP_imports=0,SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
