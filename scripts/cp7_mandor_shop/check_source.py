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
    assert set(current)-set(base)==physical,'FG_MANDOR_ONLY_COMMITTED_CLOSED_OWN_SOURCE_REQUIRED'
    assert not git('diff','--name-only','HEAD','--').strip(),'FG_MANDOR_TRACKED_SOURCE_CHANGED'
    assert not git('diff','--cached','--name-only','--').strip(),'FG_MANDOR_STAGED_SOURCE_CHANGED'
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
    offset=json.loads((HERE/'OFFSET_MODEL_CONTROLS.json').read_bytes())
    assert offset['status']=='FG_MANDOR_PRIVATE_OFFSET_PROJECTION_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert offset['retained_67_storage_allocation_buyer_identity_controls_NOT_rerun']is True
    assert offset['previous_unpublished_19_offset_controls_NOT_reused_on_rebuilt_source']is True
    assert offset['actual_Native_cases']==offset['actual_Auth_HTTP_cases']==offset['actual_browser_cases']==offset['actual_two_session_races']==0
    assert offset['Native_payment_hooks_implemented']is False
    assert offset['authoritative_Native_paid_projection_integrated']is False
    for name,expected in offset['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    syntax=json.loads((HERE/'OFFSET_SQL_SYNTAX_CONTROLS.json').read_bytes())
    raw=(HERE/'offset_projection.sql').read_bytes()
    assert syntax['source']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    assert syntax['ERP_SQL_executed']==syntax['actual_Native_cases']==0
    assert syntax['new_private_functions_compiled']==3 and syntax['new_private_tables_compiled']==1
    payment=json.loads((HERE/'PAYMENT_MODEL_CONTROLS.json').read_bytes())
    assert payment['status']=='FG_MANDOR_PRIVATE_PAYMENT_OWNER_RETAINED19_NEW4_MODEL_CONTROLS_PASS_NOT_NATIVE'
    assert payment['retained_model_controls']==19 and payment['fresh_model_controls']==len(payment['results'])==4
    assert payment['retained_19_not_rerun']is True and payment['original_failed_suite_remains_failure']is True
    assert payment['all23_fresh_one_attempt']is False and payment['retained_95_previous_model_controls_NOT_rerun']is True
    assert payment['actual_Native_cases']==payment['actual_Auth_HTTP_cases']==payment['actual_browser_cases']==payment['actual_two_session_races']==0
    assert payment['Native_runtime_or_public_RPC_activated']is False
    assert payment['Native_column_type_maps']==32 and payment['new_private_functions_compiled']==4 and payment['Native_adapter_definitions_compiled']==8
    for name,expected in payment['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    retained=json.loads((HERE/'PAYMENT_RETAINED19_MODEL_CONTROLS.json').read_bytes())
    assert retained['completed_controls_retained']==len(retained['results'])==19
    assert retained['full_suite_pass']is False and retained['original_failure_relabelled_PASS']is False
    assert retained['actual_Native_cases']==0
    raw=retained['original_model_source'].encode()
    assert retained['original_model_source_pin']=={'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    for name,expected in retained['source_files'].items():
        raw=(HERE/name).read_bytes();assert {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}==expected
    assert payment['retained_controls']==retained['results']
    routes=json.loads((HERE/'PAYMENT_NATIVE_ROUTES_SOURCE_CONTROLS.json').read_bytes())
    spec=importlib.util.spec_from_file_location('fg_mandor_exact_payment_route_source',HERE/'native_payment_routes.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    reference=json.loads((HERE/'NATIVE_PAYMENT_OWNER_REFERENCE.json').read_bytes())
    definitions,actual_routes=native.derive(reference['functions'])
    assert routes==actual_routes and len(definitions)==8 and routes['source_routes']==17
    assert routes['actual_Native_cases']==routes['actual_SQL_executed']==0
    history=json.loads((HERE/'PAYMENT_MODEL_REPAIR_HISTORY.json').read_bytes())
    assert history['prior95_NOT_rerun']is True and history['completed19_NOT_rerun_for_last4']is True
    assert history['last4_first_attempt_PASS']is True and history['all23_fresh_one_attempt']is False
    assert history['actual_Native_cases']==0
    assert value['private_functions']==value['schema_and_event_functions']+value['private_allocation_functions']+value['private_buyer_functions']+value['private_sale_identity_functions']+value['private_offset_functions']+value['private_payment_functions']==25
    return dict(status='FG_MANDOR_EXACT_STORAGE_PREPARATION_SOURCE_ONLY',unchanged_parent_blobs_and_modes=len(base),
        own_source_pins=len(value['files']),storage_model_controls=len(model['results']),parent_gate_closed=True,
        private_allocation_model_controls=len(allocation['results']),retained_storage_controls_NOT_rerun=True,
        private_buyer_functions=6,private_buyer_model_controls=len(buyer['results']),
        private_sale_identity_functions=1,private_sale_identity_model_controls=len(identity['results']),
        private_offset_functions=3,private_offset_model_controls=len(offset['results']),
        private_payment_functions=4,retained_payment_model_controls=19,fresh_payment_model_controls=4,
        Native_payment_source_adapters=8,actual_payment_runtime_installed=False,
        retained_67_controls_NOT_rerun=True,Native_paid_projection_integration=False,
        Native_header_trigger_source_written=True,Native_header_trigger_ERP_qualification=False,
        retained_allocation_controls_NOT_rerun=True,
        runtime_entry=None,ERP_imports=0,SQL_executed=0,actual_Native_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
