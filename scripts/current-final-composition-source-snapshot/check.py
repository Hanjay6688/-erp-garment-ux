"""Verify only a selective source snapshot. Never import ERP, SQL, Auth or HTTP."""
from pathlib import Path, PurePosixPath
from hashlib import sha256
import ast
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='3fdbffe3f41da6dc1004d2179ac1fe81fe05b609'
NAMESPACE='scripts/current-final-composition-source-snapshot/'
REFS={
 'D1':'cde78b2cc82e0a286174098458dab9815fdfd072',
 'E':'fe2ae370c00e68437c4951c28c3a1038ce35fb38',
 'SKU':'f3d014648d12279dfa89ca8593f25585430a5efe',
 'S03':'73ad6d323099e1d5384a94477043c01db8989106',
 'S05':'52eedc88e9aa2cd7470894c1f38ff9eb22f9cc60',
}
RUNTIME={
 'D1':('scripts/cp7_credit_correction_de/',('review.sql','facts.sql','owning.sql','proof.sql','posting.sql','materialize.sql','closure.sql','native_delta.py','composition.py')),
 'E':('scripts/cp7_credit_correction_de/',tuple('note_carry/'+x for x in('01_facts.sql','02_plan.sql','03_readers.sql','04_basis.sql','05_effect.sql','06_owning.sql','07_profile_closure.sql'))+('e_native_delta.py','e_composition.py')),
 'SKU':('scripts/cp7_sku_pair_conversion/',('pairs.sql','conversion.sql','native_delta.py','composition.py','ri_catalog.py','recovery.sql','recovery_delta.py','recovery_profile.json','recovery_before/erp.bc_value_custody_v1.sql','recovery_before/erp.save_accessory_service_action_v1.sql')),
 'S03':('scripts/cp7_attendance_period_choice/',('choice.sql','readers.sql','native_delta.py','catalog_contract.py','NEW_CATALOG_IDENTITIES.json','composition.py','installer_ddl.py')),
 'S05':('scripts/cp7_accessory_standard_report/',('stage.py','report.sql','SOURCE.json')),
}
EXTRA=(
 'scripts/cp7_accessory_standard_report/README.md',
 'scripts/cp7_accessory_standard_report/cases.py',
 'scripts/cp7_accessory_standard_report/preflight.py',
 'src/ConnectedAccessoryStandardReportPage.tsx','src/accessoryStandardReport.ts',
 'src/accessory-standard-report.css','src/accessoryStandardReport.test.ts',
 'src/AccessoryStandardReport.dom.test.tsx','tests/fixtures/accessoryStandardReport.ts',
)
OWN=('PLAN.json','SNAPSHOT.json','README.md','check.py','test_source.py')
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1',PYTHONDONTWRITEBYTECODE='1')


def require(ok,code):
    if not ok:raise ValueError(code)


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args],env=ENV)


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def safe_path(name):
    p=PurePosixPath(name)
    require(isinstance(name,str)and not p.is_absolute()and '..'not in p.parts
            and '\\'not in name and name==str(p),'SNAPSHOT_UNSAFE_PATH')
    return p


def expected_selection():
    expected={}
    for domain,(prefix,names)in RUNTIME.items():
        for name in names:expected[prefix+name]=REFS[domain]
        if domain!='E':expected[prefix+'__init__.py']=REFS[domain]
    expected.update({path:REFS['S05']for path in EXTRA})
    require(len(expected)==51,'SNAPSHOT_CLOSED_SELECTION_COUNT')
    return expected


def validate_manifest(value):
    require(value['contract']=='cp7.final-composition-source-snapshot.v1','SNAPSHOT_CONTRACT')
    require(value['base_head']==BASE,'SNAPSHOT_EXACT_BASE_REQUIRED')
    expected=expected_selection()
    rows=value['selected_files'];actual={row['path']:row for row in rows}
    require(len(rows)==len(actual)==51 and set(actual)==set(expected),'SNAPSHOT_EXACT_SELECTION_REQUIRED')
    for path,row in actual.items():
        safe_path(path)
        require(row['source_commit']==expected[path],'SNAPSHOT_COMPONENT_SOURCE_CHANGED')
        require(row['git_mode']in('100644','100755'),'SNAPSHOT_REGULAR_GIT_MODE_REQUIRED')
        require(type(row['bytes'])is int and row['bytes']>=0,'SNAPSHOT_TYPED_BYTES')
    require(value['runtime_entry']is None and value['global_parent_binding']is None
            and value['accepted_component_bindings']==dict.fromkeys(REFS),'SNAPSHOT_RUNTIME_MUST_REMAIN_CLOSED')
    for key in('actual_execution_authorized','default_installer_changed','parent_adapters_changed',
               'global_8hooks_changed','App_or_registry_or_menu_changed','production_go'):
        require(value[key]is False,'SNAPSHOT_FORBIDDEN_RUNTIME_OR_SCOPE_CHANGE:'+key)
    require(type(value['actual_Native_Auth_HTTP_browser_races'])is int and value['actual_Native_Auth_HTTP_browser_races']==0,'SNAPSHOT_ZERO_ACTUAL_CREDIT')
    return actual


def verify_bytes(raw,row):
    require(pin(raw)=={k:row[k]for k in('bytes','sha256')},'SNAPSHOT_BYTES_CHANGED:'+row.get('path','double'))


def physical(name):
    p=ROOT/str(safe_path(name))
    require(not any(x.is_symlink()for x in(p,*p.parents)if x.is_relative_to(ROOT)),
            'SNAPSHOT_SOURCE_LINK_REFUSED:'+name)
    require(p.is_file(),'SNAPSHOT_SOURCE_MISSING:'+name)
    return p.read_bytes()


def git_tree(ref):
    result={}
    for row in git('ls-tree','-rz','--full-tree',ref).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode().split()
        result[name.decode()]=(mode,kind,oid)
    return result


def check():
    value=json.loads((HERE/'SNAPSHOT.json').read_bytes());selection=validate_manifest(value)
    require(git('rev-parse',BASE+'^{tree}').decode().strip()==value['base_tree'],'SNAPSHOT_BASE_TREE_CHANGED')
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    require(source['contract']=='cp7.final-composition-source-pins.v1','SNAPSHOT_SOURCE_PIN_CONTRACT')
    require(source['base_head']==BASE and source['runtime_entry']is None
            and source['global_parent_binding']is None
            and source['accepted_component_bindings']==dict.fromkeys(REFS)
            and source['actual_execution_authorized']is False
            and type(source['actual_Native_Auth_HTTP_browser_races'])is int
            and source['actual_Native_Auth_HTTP_browser_races']==0
            and source['production_go']is False,'SNAPSHOT_SOURCE_METADATA_MUST_REMAIN_CLOSED')
    entries={r['path']:r for r in source['files']}
    expected=set(selection)|{NAMESPACE+name for name in OWN}
    require(len(entries)==len(source['files'])==56 and set(entries)==expected,'SNAPSHOT_EXACT_56_SOURCE_PINS')
    for path,row in entries.items():verify_bytes(physical(path),row)
    actual_own={str(x.relative_to(ROOT))for x in HERE.rglob('*')if x.is_file()}
    require(actual_own=={NAMESPACE+n for n in(*OWN,'SOURCE.json')},'SNAPSHOT_UNKNOWN_NAMESPACE_LEAF')
    original,current=git_tree(BASE),git_tree('HEAD')
    for path,entry in original.items():require(current.get(path)==entry,'SNAPSHOT_OLD_BASE_GIT_BYTES_OR_MODE_CHANGED:'+path)
    allowed=expected|{NAMESPACE+'SOURCE.json'}
    for line in git('diff','--name-status','--no-renames',BASE).decode().splitlines():
        status,path=line.split('\t');require(status=='A'and path in allowed,'SNAPSHOT_UNALLOCATED_TRACKED_DELTA:'+line)
    for path in git('ls-files','--others','--exclude-standard').decode().splitlines():
        require(path in allowed,'SNAPSHOT_UNALLOCATED_UNTRACKED_SOURCE:'+path)
    for path,row in selection.items():
        data=git('show',row['source_commit']+':'+path);verify_bytes(data,row)
        require((ROOT/path).stat().st_mode&0o777==(0o755 if row['git_mode']=='100755'else 0o644),
                'SNAPSHOT_PHYSICAL_MODE_CHANGED:'+path)
        mode,kind,oid=git('ls-tree',row['source_commit'],'--',path).split(b'\t')[0].decode().split()
        require((mode,kind,oid)==(row['git_mode'],'blob',row['git_blob']),'SNAPSHOT_ORIGINAL_GIT_IDENTITY_CHANGED:'+path)
        require(git('rev-parse',row['source_commit']+'^{tree}').decode().strip()==row['source_tree'],'SNAPSHOT_SOURCE_TREE_CHANGED')
        require(path not in original,'SNAPSHOT_EXISTING_BASE_OVERWRITE_NOT_AUTHORIZED:'+path)
        if path in current:require(current[path]==(mode,kind,oid),'SNAPSHOT_SELECTED_COMMITTED_BYTES_CHANGED:'+path)
        if path.endswith('.py'):ast.parse(physical(path),filename=path)
    s05=json.loads(physical('scripts/cp7_accessory_standard_report/SOURCE.json'))
    for path,digest in s05['files'].items():require(sha256(physical(path)).hexdigest()==digest,'SNAPSHOT_S05_NATURAL_DEPENDENCY_MISSING_OR_CHANGED:'+path)
    sku=physical('scripts/cp7_sku_pair_conversion/composition.py').decode()
    attendance=physical('scripts/cp7_attendance_period_choice/composition.py').decode()
    report=physical('scripts/cp7_accessory_standard_report/stage.py').decode()
    require('import cp7_vendor_receivable.composition as vendor_parent'in sku
            and 'from cp7_vendor_receivable import composition as predecessor'in attendance
            and "'VENDOR_RECEIVABLE_EXACT_SOURCE_AND_ALL22'"in report,'SNAPSHOT_PARENT_LIMITATIONS_MUST_STAY_ORIGINAL')
    return dict(status='SOURCE_SNAPSHOT_PIN_CHECK_PASS',selected_exact_original_files=51,
        exact_source_pins=56,unchanged_base_Git_paths=len(original),
        S05_original_declared_dependencies_present=len(s05['files']),
        proposed_composition_runnable=False,parent_adapters_changed=False,runtime_entry=None,
        accepted_component_bindings=dict.fromkeys(REFS),actual_Native_Auth_HTTP_browser_races=0,
        default_installer_changed=False,production_go=False)


if __name__=='__main__':print(json.dumps(check()))
