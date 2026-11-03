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
    require(manifest['base']==dict(public_head='92f099e63ae46b1adac51cc7900811e9ea201437',
        tree='8e48277b86c0325ae15793cd4d6b5094033c8c0e'),'SKU_MONEY_COMPOSITE_EXACT_PREPARATION_BASE')
    parent=set()
    for item in assembly.git(root,'ls-tree','-rz',manifest['base']['tree']).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.decode().split();name=name.decode();parent.add(name)
        path=root/name;require(kind=='blob'and path.is_file()and not path.is_symlink(),
            'SKU_MONEY_COMPOSITE_REGULAR_PARENT_SOURCE:'+name)
        raw=path.read_bytes();require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,
            'SKU_MONEY_COMPOSITE_UNDECLARED_PARENT_CHANGE:'+name)
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
        gate_state='EXACT_ACTUAL_ROOTS_BOUND_COMPOSITE_NOT_YET_QUALIFIED'
    else:
        require(manifest['active_workflow_added']is False
            and all(getattr(assembly.admission,name)is None for name in assembly.admission.GATES),
            'SKU_MONEY_COMPOSITE_PREPARATION_ALL_GATES_CLOSED')
        receipt=None;gate_state='ALL_TEN_GATES_UNSET'
    return dict(status='CURRENT_MANDOR_MOVING_MONEY_SOURCE_BRIDGE_PASS_NOT_ERP',source=own,
        unchanged_parent_files=len(parent),own_files=len(expected),moving_routes=6,money_routes=5,
        whole_current_parent_state_bound=True,parent_state_projection=False,
        active_workflow_added=manifest['active_workflow_added'],actual_parent_gate_state=gate_state,
        actual_parent_receipt=receipt,execution=execution,workflow=workflow_proof,
        actual_composite_cases=0,actual_Auth_HTTP_cases=0,
        actual_browser_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
