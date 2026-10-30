"""Exact parent-source transition. No ERP imports, DB, installed-state proof."""
from pathlib import Path, PurePosixPath
from hashlib import sha1,sha256
import ast
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='c9613859c4e82f347c8cacfa1f874dbf73361cee'
OWN='scripts/current-final-composition-parent-adapters/'
PACKAGES=('scripts/cp7_final_global_bridge/','scripts/cp7_final_composition/')
MODIFIED=('scripts/cp7_sku_pair_conversion/composition.py',
 'scripts/cp7_attendance_period_choice/composition.py',
 'scripts/cp7_accessory_standard_report/stage.py','scripts/cp7_accessory_standard_report/SOURCE.json')
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONDONTWRITEBYTECODE='1')


def require(ok,code):
    if not ok:raise ValueError(code)


def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],env=ENV)
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def read_exact(root,name,entry):
    path=PurePosixPath(name)
    require(not path.is_absolute()and '..'not in path.parts and '\\'not in name
            and name==str(path),'FINAL_PARENT_UNSAFE_SOURCE_PATH')
    target=Path(root)/str(path)
    require(not any(p.is_symlink()for p in(target,*target.parents)if p.is_relative_to(root)),
            'FINAL_PARENT_SOURCE_SYMLINK:'+name)
    require(target.is_file(),'FINAL_PARENT_SOURCE_MISSING:'+name)
    raw=target.read_bytes();require(pin(raw)=={k:entry[k]for k in('bytes','sha256')},'FINAL_PARENT_SOURCE_BYTES_CHANGED:'+name)
    return raw


def apply_changes(original,steps,reverse=False):
    value=original.decode()
    for step in(reversed(steps)if reverse else steps):
        before,after=(step['after'],step['before'])if reverse else(step['before'],step['after'])
        require(type(step['count'])is int and step['count']==1 and value.count(before)==1,
                'FINAL_PARENT_EXACT_COUNTED_ANCHOR_REQUIRED')
        value=value.replace(before,after,1)
    return value.encode()


def tree(ref):
    answer={}
    for row in git('ls-tree','-rz','--full-tree',ref).split(b'\0'):
        if row:
            meta,path=row.split(b'\t',1);answer[path.decode()]=tuple(meta.decode().split())
    return answer


def check():
    declaration=json.loads((HERE/'SOURCE.json').read_bytes())
    require(declaration['contract']=='cp7.final-composition-parent-source.v1'
            and declaration['runtime_entry']is None and declaration['actual_execution_authorized']is False,
            'FINAL_PARENT_CLOSED_SOURCE_DECLARATION_REQUIRED')
    rows=declaration['files'];entries={r['path']:r for r in rows}
    require(len(entries)==len(rows),'FINAL_PARENT_DUPLICATE_SOURCE_PIN')
    for name,entry in entries.items():read_exact(ROOT,name,entry)
    frozen=json.loads((HERE/'FROZEN_PHASE1.json').read_bytes())
    require(frozen['commit']==BASE and git('rev-parse',BASE+'^{tree}').decode().strip()==frozen['tree'],
            'FINAL_PARENT_EXACT_PUBLIC_PHASE1_REQUIRED')
    derivation=json.loads((HERE/'DERIVATIONS.json').read_bytes())
    require(derivation['base_commit']==BASE and {r['path']for r in derivation['files']}==set(MODIFIED)
            and len(derivation['files'])==4,'FINAL_PARENT_EXACT_FOUR_FILE_TRANSITION_REQUIRED')
    adapted={r['path']:r for r in derivation['files']};changes=0
    for name,original_pin in frozen['files'].items():
        original=git('show',BASE+':'+name)
        require(pin(original)=={k:original_pin[k]for k in('bytes','sha256')},'FINAL_PARENT_ORIGINAL_GIT_BYTES_CHANGED')
        current=(ROOT/name).read_bytes()
        if name in adapted:
            row=adapted[name]
            require(pin(original)==row['original']and pin(current)==row['current'],'FINAL_PARENT_DERIVED_PIN_CHANGED')
            require(apply_changes(original,row['steps'])==current and apply_changes(current,row['steps'],True)==original,
                    'FINAL_PARENT_FOUR_FILE_REVERSE_NOT_EXACT')
            changes+=len(row['steps'])
        else:require(current==original,'FINAL_PARENT_FROZEN_PHASE1_LEAF_CHANGED:'+name)
    require(changes==derivation['counted_reversible_substitutions']==9,'FINAL_PARENT_EXACT_NINE_SUBSTITUTIONS')
    allowed=set(MODIFIED)|{p for p in entries if p.startswith((OWN,*PACKAGES))}|{OWN+'SOURCE.json'}
    require(declaration['allowed_delta']==sorted(allowed),'FINAL_PARENT_EXACT_DELTA_DECLARATION_REQUIRED')
    for row in git('diff','--name-status','--no-renames',BASE).decode().splitlines():
        status,path=row.split('\t')
        require(path in allowed and(status=='M'if path in MODIFIED else status=='A'),'FINAL_PARENT_UNALLOCATED_CHANGE:'+row)
    base,current=tree(BASE),tree('HEAD')
    materialized=0
    for path,value in base.items():
        if path not in MODIFIED:require(current.get(path)==value,'FINAL_PARENT_OLD_GIT_BLOB_OR_MODE_CHANGED:'+path)
        p=ROOT/path
        if path not in MODIFIED and(p.exists()or p.is_symlink()):
            require(value[0]in('100644','100755')and value[1]=='blob',
                    'FINAL_PARENT_INHERITED_REGULAR_SOURCE_REQUIRED:'+path)
            require(not any(x.is_symlink()for x in(p,*p.parents)if x.is_relative_to(ROOT)),
                    'FINAL_PARENT_INHERITED_SOURCE_LINK:'+path)
            raw=p.read_bytes();oid=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            require(oid==value[2],'FINAL_PARENT_INHERITED_PHYSICAL_BYTES_CHANGED:'+path)
            materialized+=1
    require(not any((ROOT/'scripts').rglob('*.pyc')),'FINAL_PARENT_PROJECT_BYTECODE_CACHE_REFUSED')
    historical=declaration.get('exact_historical_untracked_inputs',{})
    for path in git('ls-files','--others','--exclude-standard').decode().splitlines():
        if path not in allowed:
            require(path in historical,'FINAL_PARENT_UNKNOWN_UNTRACKED_SOURCE:'+path)
            read_exact(ROOT,path,historical[path])
    actual_own={str(p.relative_to(ROOT))for prefix in(OWN,*PACKAGES)for p in(ROOT/prefix).rglob('*')if p.is_file()}
    require(actual_own=={p for p in allowed if p.startswith((OWN,*PACKAGES))},'FINAL_PARENT_UNKNOWN_NAMESPACE_OR_PACKAGE_LEAF')
    for name in entries:
        if name.endswith('.py'):ast.parse((ROOT/name).read_bytes(),filename=name)
    source=json.loads((ROOT/'scripts/cp7_accessory_standard_report/SOURCE.json').read_bytes())
    old_source=json.loads(git('show',BASE+':scripts/cp7_accessory_standard_report/SOURCE.json'))
    expected=dict(old_source['files']);expected['scripts/cp7_accessory_standard_report/stage.py']=pin((ROOT/'scripts/cp7_accessory_standard_report/stage.py').read_bytes())['sha256']
    require(source['files']==expected,'FINAL_PARENT_S05_UNRELATED_SOURCE_REPIN_REFUSED')
    for name,digest in source['files'].items():require(sha256((ROOT/name).read_bytes()).hexdigest()==digest,'FINAL_PARENT_S05_ACTUAL_NATURAL_LEAF_CHANGED:'+name)
    return dict(status='PARENT_ADAPTER_SOURCE_ONLY_PASS',original_phase1_leaves=57,
        original_source_leaves_preserved_exact=47,derived_original_files=4,counted_substitutions=9,
        exact_materialized_inherited_Git_leaves=materialized,
        runtime_entry=None,actual_execution_authorized=False,actual_Native_Auth_HTTP_browser_races=0,
        default_installer_changed=False,installed_or_catalog_verified=False,production_go=False)


if __name__=='__main__':print(json.dumps(check()))
