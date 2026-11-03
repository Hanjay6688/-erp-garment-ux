"""Exact old Native27 plus moving Native6 originals; no inherited case credit."""
from hashlib import sha256
from pathlib import Path
import json

FIVE_GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)

def expected_fields(report,expected,label):
    failures=[key for key,value in expected.items()if type(report.get(key))is not type(value)or report[key]!=value]
    if failures:raise ValueError(label+':'+','.join(failures))

def read_exact(directory,pin):
    values={};proofs={}
    for name,expected in pin['originals'].items():
        raw=(Path(directory)/name).read_bytes();proof=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
        if proof!=expected:raise ValueError('SKU_MONEY_PARENT_ORIGINAL_CHANGED:'+name)
        values[name]=json.loads(raw);proofs[name]=proof
    package=values['T3_PACKAGE_INSTALL.json']
    if package.get('gate')!=FIVE_GATES:raise ValueError('SKU_MONEY_PARENT_ALL_FIVE_REQUIRED')
    files=values['T3_PACKAGE_FILES_INSTALL.json']
    keys=['A'+chr(n)for n in range(ord('C'),ord('Z')+1)]+['B'+chr(n)for n in range(ord('A'),ord('F')+1)]
    if files.get('status')!='ALL_FILES_INSTALLED'or files.get('files')!=[dict(key=key,status='PASS')for key in keys]:
        raise ValueError('SKU_MONEY_PARENT_ALL_FILES_REQUIRED')
    backup=values['T3_BACKUP_RESTORE_DRILL.json']
    if backup.get('status')!='RESTORED_IDENTICAL'or not backup.get('checks')or not all(backup['checks'].values())or backup.get('data',{}).get('differ')!={}:
        raise ValueError('SKU_MONEY_PARENT_COMPLETE_BACKUP_REQUIRED')
    return values,proofs

def check(native_directory,moving_directory,config):
    old,old_proofs=read_exact(native_directory,config['qualified_native27'])
    report=old['CP7_SKU_MANAGED_RECOVERY_NATIVE27.json']
    expected_fields(report,dict(status='PASS',qualification_commit=config['qualified_native27']['head'],required_case_ids_pass=True,
        actual_Native_cases=12,base_Native_cases=7,cost_Native_cases=5,actual_two_session_races=3,
        actual_Native_session_permission_waits=7,actual_Native_nonblocking_busy_cases=1,actual_Auth_HTTP_cases=0,
        actual_browser_cases=4,actual_business_cases=27,real_Auth_browser_claim=True,
        baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
        baseline_advisors_equal=True,advisor_gate=True,production_go=False,independent_acceptance=False),'SKU_MONEY_NATIVE27_PARENT_NOT_TERMINAL')
    for name,count in(('CP7_SKU_PAIR_CONVERSION_NATIVE7.json',7),('CP7_SKU_GROUP_COST_NATIVE5.json',5)):
        expected_fields(old[name],dict(status='PASS',counts={'PASS':count},complete_boundary_restored=True),'SKU_MONEY_NATIVE27_COMPONENT:'+name)
    current,current_proofs=read_exact(moving_directory,config['qualified_moving'])
    report=current['CP7_SKU_MOVING_AVERAGE_QUALIFICATION.json']
    expected_fields(report,dict(status='PASS',qualification_commit=config['qualified_moving']['head'],required_case_ids_pass=True,
        actual_Native_cases=6,actual_two_session_races=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,actual_business_cases=6,
        baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
        baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
        production_go=False,independent_acceptance=False),'SKU_MONEY_MOVING_PARENT_NOT_TERMINAL')
    native=current['CP7_SKU_MOVING_AVERAGE_NATIVE6.json']
    expected_fields(native,dict(status='PASS',counts={'PASS':6},complete_boundary_restored=True),'SKU_MONEY_MOVING_COMPONENT')
    if set(native.get('cases',{}))!=set(config['retained_native_case_ids']):raise ValueError('SKU_MONEY_MOVING_CASE_IDS_CHANGED')
    for name,row in native['cases'].items():
        expected_fields(row,dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True),'SKU_MONEY_MOVING_CASE_BOUNDARY:'+name)
        leaks=row.get('session_leaks',{})
        if leaks.get('advisory_locks')!=0 or leaks.get('other_sessions')!=[]:raise ValueError('SKU_MONEY_MOVING_CASE_SESSION_LEAK:'+name)
    return dict(status='EXACT_NATIVE27_AND_MOVING_NATIVE6_PARENTS',native27=old_proofs,moving=current_proofs,
        moving_source=report['source_declaration']['current_installation'],actual_new_cases=0,
        unresolved_parent_cost_gap_requires_this_successor=True,production_go=False)
