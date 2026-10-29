"""Closed prerequisite; pure raw-byte/report admission and no runtime imports."""
from hashlib import sha256
import json
import re

REJECTED_HEADS = ('0770541c94937ee5013c8ea9ae607c99260d2993',
                  '8a8dcb8509f1d6b33600239521a9b157c81bf9bc',
                  'a99463ca3ea2f1a71b22f0354df83f1b5a42b71b')
GATES = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')
ORIGINALS = dict(original='CP7_CREDIT_DE_NATIVE13.json', strict_native13='CP7_CREDIT_DE_NATIVE13_CASES.json',
                 package='T3_PACKAGE_INSTALL.json', package_files='T3_PACKAGE_FILES_INSTALL.json',
                 backup_drill='T3_BACKUP_RESTORE_DRILL.json')
NATIVE13_CASE = 'CREDIT_DE_NATIVE13_AND_USED_INVERSE'
FAILED_SHA = '3274ce4c5684b77a82a8761638e3f78406ea164c503047446452c8eb3ea43525'


def selected(cfg):
    pin, required = cfg.get('accepted_native13'), cfg.get('required_qualified_parent')
    if pin is None or required is None:
        raise ValueError('D1_CONT_CLOSED_EXACT_SUCCESSFUL_NATIVE13_AND_COMPLETE_PACKAGE_REQUIRED')
    if pin.get('head') in REJECTED_HEADS:
        raise ValueError('D1_CONT_KNOWN_FAILED_PREREQUISITE_REFUSED')
    failure = cfg.get('retained_failed_a994', {})
    if (failure.get('head') != REJECTED_HEADS[-1] or failure.get('counts') != {'PASS':5,'INCOMPLETE':8}
            or failure.get('raw_sha256') != FAILED_SHA or failure.get('raw_bytes') != 44099 or failure.get('usable_prerequisite') is not False):
        raise ValueError('D1_CONT_FIRST_FAILED_NATIVE13_MUST_REMAIN_EXPLICIT')
    if (required.get('status') != 'ROOT_VERIFIED_TERMINAL_NATIVE13_AND_COMPLETE_PACKAGE_PASS'
            or cfg.get('parent_status') != required.get('status')
            or pin.get('head') != required.get('head') or pin.get('tree') != required.get('tree')
            or pin.get('head') != cfg.get('frozen_parent_head') or pin.get('tree') != cfg.get('frozen_parent_tree')):
        raise ValueError('D1_CONT_EXPLICIT_SUCCESSFUL_SOURCE_AND_PROOF_REBIND_REQUIRED')
    if any(not re.fullmatch('[a-f0-9]{40}', pin.get(key,'')) for key in ('head','tree')):
        raise ValueError('D1_CONT_EXACT_PUBLIC_PARENT_HEAD_AND_TREE_REQUIRED')
    if any(type(pin.get(key)) is not int or pin[key] <= 0 for key in ('run_id','job_id','artifact_id','zip_bytes')):
        raise ValueError('D1_CONT_EXACT_TERMINAL_RUN_JOB_ARTIFACT_REQUIRED')
    if not re.fullmatch('[a-f0-9]{64}', pin.get('zip_sha256','')):
        raise ValueError('D1_CONT_ORIGINAL_ZIP_DIGEST_REQUIRED')
    for key, name in ORIGINALS.items():
        item = pin.get(key,{})
        if (item.get('name') != name or type(item.get('bytes')) is not int or item['bytes'] <= 0
                or not re.fullmatch('[a-f0-9]{64}', item.get('sha256',''))):
            raise ValueError('D1_CONT_EXACT_RAW_REPORT_PIN_REQUIRED:'+key)
    return pin


def retained_failure(cfg, raw):
    failure = cfg['retained_failed_a994']
    if len(raw) != 44099 or sha256(raw).hexdigest() != FAILED_SHA:
        raise ValueError('D1_CONT_FAILED_A994_RAW_BYTES_CHANGED')
    group = json.loads(raw)
    if group.get('status') != 'INCOMPLETE' or group.get('counts') != {'PASS':5,'INCOMPLETE':8} or failure['usable_prerequisite'] is not False:
        raise ValueError('D1_CONT_FAILED_A994_MUST_NOT_BECOME_PASS')
    return dict(status='RETAINED_FAILED_A994_NOT_A_PREREQUISITE',actual_cases_credited=0)


def exact_group(group, ids, count):
    if (len(ids) != count or len(set(ids)) != count or group.get('status') != 'PASS' or group.get('error')
            or group.get('counts') != {'PASS':count} or group.get('planned_case_ids') != list(ids)
            or set(group.get('cases',{})) != set(ids) or group.get('complete_boundary_restored') is not True):
        raise ValueError('D1_CONT_COMPLETE_EXACT_NATIVE_GROUP_REQUIRED')
    for name, row in group['cases'].items():
        if any(row.get(key) is not True for key in ('full_boundary_restored','public_schema_unchanged')) or row.get('status') != 'PASS':
            raise ValueError('D1_CONT_NATIVE_CASE_OR_RESTORE_FAILED:'+name)


def admitted(cfg, originals, current_sources, frozen_source, ids):
    pin = selected(cfg)
    parsed = {}
    for key in ORIGINALS:
        raw, item = originals[key], pin[key]
        if len(raw) != item['bytes'] or sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('D1_CONT_PARENT_ORIGINAL_BYTES_CHANGED:'+key)
        parsed[key] = json.loads(raw)
    outer, group, package, files, drill = (parsed[key] for key in ORIGINALS)
    if (outer.get('label') != 'CP7_CREDIT_DE_NATIVE13' or outer.get('status') != 'PASS' or outer.get('error') or outer.get('restore_error')
            or outer.get('qualification_commit') != pin['head'] or outer.get('required_case_ids') != [NATIVE13_CASE]
            or outer.get('expected_case_count') != 1 or outer.get('observed_case_count') != 1):
        raise ValueError('D1_CONT_TERMINAL_EXACT_NATIVE13_OUTER_REQUIRED')
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal',
                'used_guard_refused_before_DDL','required_case_ids_pass'):
        if outer.get(key) is not True:
            raise ValueError('D1_CONT_PARENT_FULL_RESTORE_FAILED:'+key)
    restore = outer.get('restore_components',{})
    if not restore or any(value is not True for value in restore.values()):
        raise ValueError('D1_CONT_PARENT_COMPLETE_RESTORE_COMPONENTS_REQUIRED')
    if (outer.get('baseline_role_cleanup',{}).get('baseline_roles_exact') is not True
            or outer.get('focused_preuse_removal',{}).get('used_guard_before_DDL') is not True
            or outer.get('actual_Native_cases') != 13 or outer.get('actual_Auth_HTTP_cases') != 0 or outer.get('actual_two_session_races') != 0):
        raise ValueError('D1_CONT_PARENT_ROLE_PREUSE_AND_HONEST_COUNTS_REQUIRED')
    exact_group(group, ids, 13)
    witness = outer.get('committed',{}).get(NATIVE13_CASE,{})
    if (set(outer.get('committed',{})) != {NATIVE13_CASE} or witness.get('status') != 'PASS' or witness.get('native') != group
            or witness.get('actual_Native_cases') != 13 or witness.get('used_guard_refused_before_DDL') is not True
            or witness.get('unchanged_physical_stock_HPP_cost_GL_and_original_sale_payment') is not True
            or witness.get('committed_source_truth') != dict(I='250.00',available='250.00',net='750.00',AR='0.00')):
        raise ValueError('D1_CONT_PARENT_COMMITTED_FINANCIAL_WRITER_WITNESS_REQUIRED')
    declaration = outer.get('source_declaration',{})
    if declaration.get('current_installation') != current_sources or declaration.get('qualification') != frozen_source:
        raise ValueError('D1_CONT_ACTUAL_PARENT_SOURCE_OR_DECLARATION_DIFFERS')
    if (package.get('status') != 'ALL_STAGES_INSTALLED' or package.get('gate') != {key:True for key in GATES}
            or package.get('writer_runtime',{}).get('status') != 'PASS' or package.get('backup_restore_drill') != 'RESTORED_IDENTICAL'
            or package.get('primary_unchanged') is not True or package.get('auth_users_before') is None
            or package['auth_users_before'] != package.get('auth_users_after')):
        raise ValueError('D1_CONT_ALL_FIVE_PACKAGE_GATES_AND_PRIMARY_AUTH_RESTORE_REQUIRED')
    identity = package.get('run_identity',{})
    if identity.get('tool_head') != pin['head'] or identity.get('github_sha') != pin['head'] or str(identity.get('run_id')) != str(pin['run_id']):
        raise ValueError('D1_CONT_EXACT_PARENT_PACKAGE_RUN_REQUIRED')
    rows = files.get('files',[])
    if (files.get('status') != 'ALL_FILES_INSTALLED' or len(rows) != 30 or len({row.get('key')for row in rows}) != 30
            or any(row.get('status') != 'PASS'for row in rows)):
        raise ValueError('D1_CONT_ALL_THIRTY_PACKAGE_FILES_REQUIRED')
    if (drill.get('status') != 'RESTORED_IDENTICAL' or not drill.get('checks') or any(value is not True for value in drill['checks'].values())
            or drill.get('data',{}).get('differ') != {} or drill.get('catalog',{}).get('differ') != {} or drill.get('engine',{}).get('equal') is not True):
        raise ValueError('D1_CONT_COMPLETE_BACKUP_RESTORE_DRILL_REQUIRED')
    return dict(status='EXACT_TERMINAL_D1_NATIVE13_COMPLETE_PACKAGE_AND_RESTORE_ADMITTED',head=pin['head'],tree=pin['tree'],
        run_id=pin['run_id'],job_id=pin['job_id'],retained_Native_cases=13,fresh_cases_credited=0,
        original_sha256=pin['original']['sha256'],strict_native13_sha256=pin['strict_native13']['sha256'],
        package_sha256=pin['package']['sha256'],production_go=False,independent_acceptance=False), parsed
