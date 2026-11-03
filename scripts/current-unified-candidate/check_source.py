"""Source fence for the explicitly prepared Afui/Global/Mandor composition.

The Mandor source fence includes the exact new private command guards. Global
source and all financial admission remain unchanged. This fence verifies the
combined source candidate only; it neither imports an installer
nor executes a database, browser, model or financial scenario.
"""
from pathlib import Path
from hashlib import sha256
import json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MANIFEST=HERE/'SOURCE.json'


def require(value,message):
    if not value:raise ValueError(message)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])


def entries(ref):
    result={}
    for item in git('ls-tree','-rz',ref).split(b'\0'):
        if not item:continue
        meta,path=item.split(b'\t',1);mode,kind,blob=meta.decode().split()
        require(kind=='blob'and mode in('100644','100755'),'UNIFIED_REGULAR_SOURCE_ENTRY')
        result[path.decode()]=dict(mode=mode,blob=blob)
    return result


def source():
    m=json.loads(MANIFEST.read_bytes())
    require(m['contract']=='cp7.unified-source-candidate.v1'and m['status']=='PREPARED_UNQUALIFIED','UNIFIED_SOURCE_ONLY_CONTRACT')
    require(m['integrator']=='WRITER_A'and m['runtime_admission']is False and m['production_go']is False,'UNIFIED_CLOSED_RUNTIME_GATE')
    base=entries(m['base']['head'])
    require(git('rev-parse',m['base']['head']+'^{tree}').decode().strip()==m['base']['tree'],'UNIFIED_EXACT_AFUI_BASE_TREE')
    changed=set(m['parent_overrides'])
    shared=set(json.loads((ROOT/'scripts/cp7_mandor_shop/UI_SOURCE.json').read_bytes())['files'])&set(base)
    appearance=m.get('appearance_derivations',{})
    require(len(shared)==8 and set(appearance)=={'src/accessory-workspace.css'}and changed==shared|set(appearance),'UNIFIED_EXACT_SHARED_UI_AND_APPEARANCE_PATHS')
    for name,row in base.items():
        f=ROOT/name;require(f.is_file()and not f.is_symlink(),'UNIFIED_MISSING_OR_SYMLINK_PARENT:'+name)
        if name in changed:continue
        raw=f.read_bytes();blob=__import__('hashlib').sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(blob==row['blob'],'UNIFIED_UNDECLARED_PARENT_CHANGE:'+name)
    for name,expected in m['files'].items():
        f=ROOT/name;require(f.is_file()and not f.is_symlink()and pin(f.read_bytes())==expected,'UNIFIED_DECLARED_FILE_CHANGED:'+name)
    for component in m['components'].values():
        require(git('rev-parse',component['head']+'^{tree}').decode().strip()==component['tree'],'UNIFIED_EXACT_COMPONENT_TREE')
        for name,expected in component['exact_files'].items():
            original=git('show',component['head']+':'+name)
            require(pin(original)==expected and(ROOT/name).read_bytes()==original,'UNIFIED_COMPONENT_SOURCE_CHANGED:'+name)
    for name,route in(m['validator_derivations']|appearance).items():
        before=git('show',m['base']['head']+':'+name);require(pin(before)==route['before'],'UNIFIED_VALIDATOR_BASE_PIN')
        lines=before.decode().splitlines(keepends=True)
        for h in reversed(route['hunks']):
            require(''.join(lines[h['start']:h['end']])==h['before'],'UNIFIED_EXACT_VALIDATOR_HUNK')
            lines[h['start']:h['end']]=h['after'].splitlines(keepends=True)
        after=''.join(lines).encode()
        require(after==(ROOT/name).read_bytes()and pin(after)==route['after'],'UNIFIED_COMPLETE_VALIDATOR_DERIVATION')
    all_paths={n.decode()for n in git('ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')if n}
    actual_new=all_paths-set(base)
    require(actual_new==set(m['new_paths']),'UNIFIED_EXACT_NEW_NAMESPACE_PATHS')
    require(len(m['components']['GLOBAL']['exact_files'])==42 and len(m['components']['MANDOR']['exact_files'])==107,'UNIFIED_COMPLETE_COMPONENT_AND_UI_FILE_COUNTS')
    preparation=m.get('Mandor_native9_preparation')
    if preparation is not None:
        import ast
        prefix='scripts/current-mandor-shop-native-qualification/'
        expected={prefix+n for n in('admission.py','native_fixture.py','oracle.py','cases.py','additional_cases.py','preflight.py',
            'assembly.py','component.py','package_engine.py','qualification.py','runtime_supervisor.py','final_gate.py',
            'SOURCE_READINESS.json','READINESS.txt')}
        require(set(preparation['files'])==expected and all(n in m['files']for n in expected),'UNIFIED_EXACT_PREPARED_NATIVE9_NAMESPACE')
        require(preparation['actual_Native_cases']==0 and preparation['parent_root_adopted']is False,'UNIFIED_NATIVE9_PREPARATION_IS_NOT_ACCEPTANCE')
        tree=ast.parse((ROOT/prefix/'admission.py').read_bytes())
        values={t.id:ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and isinstance(n.value,ast.Constant)for t in n.targets if isinstance(t,ast.Name)}
        require(values['PARENT_HEAD']==m['base']['head']and values['PARENT_ROOT_PIN']is None and values['RUNTIME_ENTRY']is None,'UNIFIED_PREPARED_NATIVE9_PARENT_GATE_MUST_STAY_CLOSED')
    return dict(status='UNIFIED_AFUI_GLOBAL_MANDOR_SOURCE_FENCE_PASS_NOT_RUNTIME_OR_BUSINESS',base=m['base'],
        unchanged_parent_blobs=len(base)-len(changed),shared_UI_parent_paths=len(shared),appearance_parent_paths=len(appearance),parent_modified_paths=len(changed),new_paths=len(actual_new),
        Global_module_files=42,Mandor_module_and_exact_UI_files=107,validator_files_composed=2,
        Global_standalone_source_fence_unchanged=True,Mandor_source_fence_includes_new_command_guards=True,
        actual_SQL_executed=0,actual_Native_cases=0,
        runtime_admission=False,CP7_complete=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(source(),sort_keys=True))
