"""Exact frozen base plus one owning qualifier namespace; no ERP imports."""
from pathlib import Path
from hashlib import sha1
import json,os,subprocess
import sku_current_parent_admission as admission
import sku_current_parent_assembly as assembly

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def require(value,message):
    if not value:raise ValueError(message)


def source():
    own=assembly.source_manifest();manifest=json.loads((HERE/'SOURCE.json').read_bytes())
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1')
    def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],env=env)
    require(git('rev-parse',manifest['base_head']+'^{tree}').decode().strip()==manifest['base_tree'],
        'SKU_COMPOSITE_EXACT_BASE_TREE')
    base={}
    for item in git('ls-tree','-rz',manifest['base_head']).split(b'\0'):
        if not item:continue
        meta,path=item.split(b'\t',1);mode,kind,blob=meta.decode().split();name=path.decode()
        require(kind=='blob'and mode in('100644','100755'),'SKU_COMPOSITE_REGULAR_BASE_SOURCE')
        file=ROOT/name;require(file.is_file()and not file.is_symlink(),'SKU_COMPOSITE_MISSING_BASE_SOURCE:'+name)
        raw=file.read_bytes();require(sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,
            'SKU_COMPOSITE_UNDECLARED_BASE_SOURCE_CHANGED:'+name)
        base[name]=blob
    prefix=str(HERE.relative_to(ROOT))+'/'
    expected={prefix+name for name in manifest['files']}|{prefix+'SOURCE.json'}
    workflow='.github/workflows/cp7-sku-current-parent-native6.yml'
    if manifest['active_workflow_added']:
        import sku_current_parent_runtime as runtime
        runtime.actual_inputs()
        active=ROOT/workflow
        require(active.is_file()and not active.is_symlink()
            and admission.pin(active.read_bytes())==manifest.get('active_workflow_source'),
            'SKU_COMPOSITE_EXACT_ACTIVE_WORKFLOW_PIN')
        expected.add(workflow)
    else:
        require(manifest.get('active_workflow_source')is None and not(ROOT/workflow).exists(),
            'SKU_COMPOSITE_NO_UNDECLARED_ACTIVE_WORKFLOW')
    paths={p.decode()for p in git('ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')if p}
    require(paths-set(base)==expected,'SKU_COMPOSITE_EXACT_OWN_NAMESPACE')
    if manifest['actual_parent_adopted']:
        import sku_current_parent_runtime as runtime
        _,_,receipt=runtime.actual_inputs()
        parent_state='EXACT_ROOT_ORIGINALS_BOUND_CURRENT_PARENT_RUNTIME_NOT_YET_QUALIFIED'
    else:receipt=None;parent_state='ALL_TEN_GATES_UNSET'
    return dict(status='SKU_CURRENT_PARENT_OWNING_SOURCE_FENCE_PASS_NOT_ERP',source_manifest=own,
        unchanged_base_files=len(base),own_files=len(expected),actual_parent_gate_state=parent_state,
        actual_parent_receipt=receipt,active_workflow_added=manifest['active_workflow_added'],actual_composite_cases=0,
        actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(source(),sort_keys=True))
