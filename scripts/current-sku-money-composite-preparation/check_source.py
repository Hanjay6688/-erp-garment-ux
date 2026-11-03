"""Keep the entire previous candidate exact and this additive bridge unarmed."""
from hashlib import sha1
from pathlib import Path
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('money_composite_source_fence',HERE/'assembly.py')
assembly=importlib.util.module_from_spec(spec);spec.loader.exec_module(assembly)


def check():
    own=assembly.source_manifest();manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    require=assembly.require;root=assembly.ROOT
    require(manifest['base']==dict(public_head='c296fd06167ddd177e1192c1008992e2a1e3d628',
        tree='fdd36962a7de81482ccca02e6ff96597cfc20081'),'SKU_MONEY_COMPOSITE_EXACT_PREPARATION_BASE')
    parent=set()
    for item in assembly.git(root,'ls-tree','-rz',manifest['base']['tree']).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=name.decode();parent.add(name)
        path=root/name;require(kind=='blob'and path.is_file()and not path.is_symlink(),
            'SKU_MONEY_COMPOSITE_REGULAR_PARENT_SOURCE:'+name)
        raw=path.read_bytes();require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,
            'SKU_MONEY_COMPOSITE_UNDECLARED_PARENT_CHANGE:'+name)
    current_mandor_files=len(parent)
    retained=manifest['retained_moving_preparation']
    require(retained['tree']=='8e48277b86c0325ae15793cd4d6b5094033c8c0e'
        and retained['namespace']=='scripts/current-sku-composite-preparation/',
        'SKU_MONEY_RETAINED_MOVING_SOURCE_IDENTITY')
    expected_retained={}
    for item in assembly.git(root,'ls-tree','-rz',retained['tree'],'--',retained['namespace']).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=name.decode()
        require(kind=='blob'and mode=='100644'and name not in parent,'SKU_MONEY_RETAINED_MOVING_REGULAR_ADDITION')
        path=root/name;raw=assembly.git(root,'show',retained['tree']+':'+name)
        require(path.is_file()and not path.is_symlink()and path.read_bytes()==raw,
            'SKU_MONEY_RETAINED_MOVING_SOURCE_CHANGED:'+name)
        expected_retained[name]=dict(blob=blob,pin=assembly.admission.pin(raw));parent.add(name)
    require(len(expected_retained)==23 and expected_retained==retained['files'],
        'SKU_MONEY_RETAINED_COMPLETE_MOVING_NAMESPACE')
    execution=assembly.load('current_money_exact_execution_source_routes',HERE/'execution_routes.py').check()
    require(execution==manifest['execution'],'SKU_MONEY_COMPOSITE_EXACT_EXECUTION_DERIVATIONS')
    previous=list(sys.path)
    try:
        sys.path.insert(0,str(HERE))
        workflow=assembly.load('current_money_exact_workflow_routes',HERE/'money_current_parent_workflow.py')
        workflow_proof=workflow.check()
    finally:sys.path[:]=previous
    paths={v.decode()for v in assembly.git(root,'ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')if v}
    expected={str((HERE/name).relative_to(root))for name in manifest['files']}|{str((HERE/'SOURCE.json').relative_to(root))}
    if manifest['active_workflow_added']:
        require(manifest['actual_parent_adopted']is True,'SKU_MONEY_COMPOSITE_ACTIVE_REQUIRES_ACTUAL_PARENTS')
        expected.add(workflow.WORKFLOW)
    require(paths-parent==expected,'SKU_MONEY_COMPOSITE_EXACT_ADDITIVE_NAMESPACE')
    if manifest['actual_parent_adopted']:
        previous=list(sys.path)
        try:
            sys.path.insert(0,str(HERE))
            runtime=assembly.load('current_money_exact_bound_runtime_intake',HERE/'money_current_parent_runtime.py')
            _,_,receipt=runtime.actual_inputs()
        finally:sys.path[:]=previous
        gate_state='EXACT_CURRENT_MANDOR_ROOT_AND_UNQUALIFIED_MONEY_SOURCE_BOUND'
    else:
        require(manifest['active_workflow_added']is False
            and all(getattr(assembly.admission,name)is None for name in assembly.admission.GATES),
            'SKU_MONEY_COMPOSITE_PREPARATION_ALL_GATES_CLOSED')
        receipt=None;gate_state='ALL_TEN_GATES_UNSET'
    return dict(status='CURRENT_MANDOR_MOVING_MONEY_SOURCE_BRIDGE_PASS_NOT_ERP',source=own,
        unchanged_parent_files=current_mandor_files,retained_moving_preparation_files=len(expected_retained),
        current_reviewed_UI_preserved=True,own_files=len(expected),moving_routes=6,money_routes=5,
        whole_current_parent_state_bound=True,parent_state_projection=False,
        active_workflow_added=manifest['active_workflow_added'],actual_parent_gate_state=gate_state,
        actual_parent_receipt=receipt,execution=execution,workflow=workflow_proof,
        actual_composite_cases=0,actual_Auth_HTTP_cases=0,
        actual_browser_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
