"""Keep the entire previous candidate exact and this additive bridge unarmed."""
from hashlib import sha1
from pathlib import Path
import importlib.util
import json

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
    paths={v.decode()for v in assembly.git(root,'ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')if v}
    expected={str((HERE/name).relative_to(root))for name in manifest['files']}|{str((HERE/'SOURCE.json').relative_to(root))}
    require(paths-parent==expected,'SKU_MONEY_COMPOSITE_EXACT_ADDITIVE_NAMESPACE')
    require(manifest['active_workflow_added']is False and manifest['actual_parent_adopted']is False
        and all(getattr(assembly.admission,name)is None for name in assembly.admission.GATES),
        'SKU_MONEY_COMPOSITE_PREPARATION_ALL_GATES_CLOSED')
    return dict(status='CURRENT_MANDOR_MOVING_MONEY_SOURCE_BRIDGE_PASS_NOT_ERP',source=own,
        unchanged_parent_files=len(parent),own_files=len(expected),moving_routes=6,money_routes=5,
        whole_current_parent_state_bound=True,parent_state_projection=False,
        active_workflow_added=False,actual_composite_cases=0,actual_Auth_HTTP_cases=0,
        actual_browser_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
