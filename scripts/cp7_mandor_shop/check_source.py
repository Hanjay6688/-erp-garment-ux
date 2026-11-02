"""Exact preparation input and byte checks, with no ERP import or SQL call."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def check():
    manifest=HERE/'SOURCE.json';value=json.loads(manifest.read_bytes())
    assert value['classification']=='CLOSED_FG_MANDOR_PRIVATE_BUYER_AND_ALLOCATION_PREPARATION_NOT_QUALIFICATION'
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
    allocation=json.loads((HERE/'ALLOCATION_MODEL_CONTROLS.json').read_bytes())
    assert allocation['status']=='FG_MANDOR_PRIVATE_ALLOCATION_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert allocation['retained_storage_15_controls_NOT_rerun']is True
    assert allocation['actual_Native_cases']==allocation['actual_Auth_HTTP_cases']==allocation['actual_two_session_races']==allocation['actual_browser_cases']==0
    for name,expected in allocation['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    syntax=json.loads((HERE/'ALLOCATION_SQL_SYNTAX_CONTROLS.json').read_bytes())
    raw=(HERE/'allocation.sql').read_bytes()
    assert syntax['source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert syntax['ERP_SQL_executed']==0 and syntax['actual_Native_cases']==0
    buyer=json.loads((HERE/'BUYER_MODEL_CONTROLS.json').read_bytes())
    assert buyer['status']=='FG_MANDOR_PRIVATE_BUYER_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert buyer['retained_storage_15_and_allocation_15_controls_NOT_rerun']is True
    assert buyer['actual_Native_cases']==buyer['actual_Auth_HTTP_cases']==buyer['actual_browser_cases']==buyer['actual_two_session_races']==0
    for name,expected in buyer['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    syntax=json.loads((HERE/'BUYER_SQL_SYNTAX_CONTROLS.json').read_bytes())
    raw=(HERE/'buyers.sql').read_bytes()
    assert syntax['source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert syntax['ERP_SQL_executed']==syntax['actual_Native_cases']==0
    repair=json.loads((HERE/'BUYER_UUID_INTEGER_QUOTIENT_REPAIR.json').read_bytes())
    route=repair['counted_route'];text=raw.decode()
    assert text.count(route['after'])==route['count']==1
    original=text.replace(route['after'],route['before'],1).encode()
    assert repair['first_source']=={'bytes':len(original),'sha256':sha256(original).hexdigest()}
    assert repair['changed_source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert repair['first_model_is_not_PASS']is True and repair['Native_cases']==repair['ERP_installations']==0
    identity=json.loads((HERE/'SALE_IDENTITY_MODEL_CONTROLS.json').read_bytes())
    assert identity['status']=='FG_MANDOR_NATIVE_HEADER_IDENTITY_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert identity['retained_storage_15_allocation_15_buyer_20_controls_NOT_rerun']is True
    assert identity['actual_Native_cases']==identity['actual_Auth_HTTP_cases']==identity['actual_browser_cases']==identity['actual_two_session_races']==0
    assert identity['Native_financial_functions_changed']==0
    for name,expected in identity['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    syntax=json.loads((HERE/'SALE_IDENTITY_SQL_SYNTAX_CONTROLS.json').read_bytes())
    raw=(HERE/'sale_identity.sql').read_bytes()
    assert syntax['source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert syntax['ERP_SQL_executed']==syntax['actual_Native_cases']==0
    assert value['private_functions']==value['schema_and_event_functions']+value['private_allocation_functions']+value['private_buyer_functions']+value['private_sale_identity_functions']==18
    return dict(status='FG_MANDOR_EXACT_STORAGE_PREPARATION_SOURCE_ONLY',unchanged_parent_blobs_and_modes=len(base),
        own_source_pins=len(value['files']),storage_model_controls=len(model['results']),parent_gate_closed=True,
        private_allocation_model_controls=len(allocation['results']),retained_storage_controls_NOT_rerun=True,
        private_buyer_functions=6,private_buyer_model_controls=len(buyer['results']),
        private_sale_identity_functions=1,private_sale_identity_model_controls=len(identity['results']),
        Native_header_trigger_source_written=True,Native_header_trigger_ERP_qualification=False,
        retained_allocation_controls_NOT_rerun=True,
        runtime_entry=None,ERP_imports=0,SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
