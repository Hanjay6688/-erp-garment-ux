"""Admit exact actual Native7+package Originals before any followup DB work."""
from hashlib import sha256
import json

def checked(config,original,package,current,case_ids):
    expected=config.get('accepted_native7')
    if expected is None:raise ValueError('VENDOR_FOLLOWUP_CLOSED_NATIVE7_ACTUAL_PASS_REQUIRED')
    for key,raw in (('original',original),('package',package)):
        pin=expected[key]
        if len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('VENDOR_FOLLOWUP_ORIGINAL_BYTES_CHANGED:'+key)
    actual=json.loads(original);pkg=json.loads(package)
    if actual.get('label')!='CP7_VENDOR_RECEIVABLE_NATIVE7'or actual.get('status')!='PASS'or actual.get('qualification_commit')!=expected['head']:
        raise ValueError('VENDOR_FOLLOWUP_NATIVE7_NOT_QUALIFIED')
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','used_guard_refused_before_DDL'):
        if actual.get(key)is not True:raise ValueError('VENDOR_FOLLOWUP_NATIVE7_BOUNDARY_FAILED:'+key)
    if actual.get('required_case_ids_pass')is not True or actual.get('expected_case_count')!=1 or actual.get('observed_case_count')!=1:
        raise ValueError('VENDOR_FOLLOWUP_NATIVE7_OUTER_CASE_REQUIRED')
    if actual.get('focused_preuse_removal',{}).get('used_guard_before_DDL')is not True:
        raise ValueError('VENDOR_FOLLOWUP_NATIVE7_PREUSE_INVERSE_REQUIRED')
    bundle=actual.get('committed',{}).get('VENDOR_RECEIVABLE_NATIVE7_AND_USED_INVERSE',{})
    group=bundle.get('native',{})
    if bundle.get('status')!='PASS'or group.get('counts')!={'PASS':7}or set(group.get('cases',{}))!=set(case_ids):
        raise ValueError('VENDOR_FOLLOWUP_EXACT_NATIVE7_CASES_REQUIRED')
    if any(v.get('status')!='PASS'for v in group['cases'].values()):raise ValueError('VENDOR_FOLLOWUP_PARTIAL_NATIVE7_REFUSED')
    if actual['source_declaration']['current_installation']!=current:raise ValueError('VENDOR_FOLLOWUP_OTHER_BACKEND_REFUSED')
    keys=('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')
    if pkg.get('gate')!={key:True for key in keys}or pkg['run_identity']['tool_head']!=expected['head']:
        raise ValueError('VENDOR_FOLLOWUP_NATIVE7_PACKAGE_NOT_QUALIFIED')
    if pkg.get('writer_runtime',{}).get('status')!='PASS'or pkg.get('auth_users_before')!=pkg.get('auth_users_after'):
        raise ValueError('VENDOR_FOLLOWUP_NATIVE7_PACKAGE_RUNTIME_OR_AUTH_RESTORE_FAILED')
    return dict(status='EXACT_ACTUAL_NATIVE7_AND_PACKAGE_PASS_ADMITTED',head=expected['head'],
        original_binding=expected,retained_Native_case_count=7,fresh_followup_cases=0,
        retained_preuse_inverse=True,production_go=False,independent_acceptance=False)
