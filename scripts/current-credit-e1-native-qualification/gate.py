"""Closed exact parent admission. No runtime imports, network or database."""
from hashlib import sha256
import json
import re

NATIVE_CASE = 'CREDIT_DE_NATIVE13_AND_USED_INVERSE'
REJECTED_HEADS = ('0770541c94937ee5013c8ea9ae607c99260d2993',
                  '8a8dcb8509f1d6b33600239521a9b157c81bf9bc',
                  'a99463ca3ea2f1a71b22f0354df83f1b5a42b71b')
GATES = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')
FAILED_GROUP_SHA256 = '3274ce4c5684b77a82a8761638e3f78406ea164c503047446452c8eb3ea43525'
FAILED_GROUP_BYTES = 44099


def selected(cfg):
    pin, required = cfg.get('accepted_D1'), cfg.get('required_qualified_parent')
    if pin is None or required is None:
        raise ValueError('E1_CLOSED_EXACT_SUCCESSFUL_OWNING_D1_NATIVE13_ORIGINALS_REQUIRED')
    if pin.get('head') in REJECTED_HEADS:
        raise ValueError('E1_KNOWN_INCOMPLETE_D1_PREREQUISITE_REFUSED')
    failure = cfg.get('retained_failed_D1', {})
    if (failure.get('head') != REJECTED_HEADS[-1] or failure.get('status') != 'INCOMPLETE' or
            failure.get('case_counts') != {'PASS': 5, 'INCOMPLETE': 8} or
            failure.get('usable_prerequisite') is not False or failure.get('raw_bytes') != FAILED_GROUP_BYTES or
            failure.get('raw_sha256') != FAILED_GROUP_SHA256):
        raise ValueError('E1_RETAINED_FIRST_D1_FAILURE_MUST_REMAIN_EXPLICIT')
    if (required.get('status') != 'ROOT_VERIFIED_TERMINAL_NATIVE13_AND_COMPLETE_PACKAGE_PASS' or
            cfg.get('parent_status') != required.get('status') or
            pin.get('head') != required.get('head') or pin.get('tree') != required.get('tree') or
            pin.get('head') != cfg.get('frozen_parent_head') or pin.get('tree') != cfg.get('frozen_parent_tree')):
        raise ValueError('E1_EXPLICIT_SUCCESSOR_SOURCE_AND_PROOF_REBIND_REQUIRED')
    if not re.fullmatch('[a-f0-9]{40}', pin['head']) or not re.fullmatch('[a-f0-9]{40}', pin['tree']):
        raise ValueError('E1_CONCRETE_PARENT_HEAD_AND_TREE_REQUIRED')
    for key in ('run_id', 'job_id', 'artifact_id', 'zip_bytes'):
        if type(pin.get(key)) is not int or pin[key] <= 0:
            raise ValueError('E1_CONCRETE_PARENT_RUN_JOB_ARTIFACT_REQUIRED')
    if not re.fullmatch('[a-f0-9]{64}', pin.get('zip_sha256', '')):
        raise ValueError('E1_EXACT_ORIGINAL_ZIP_DIGEST_REQUIRED')
    for key in ('original', 'native_group', 'package'):
        item = pin.get(key, {})
        if (type(item.get('bytes')) is not int or item['bytes'] <= 0 or
                not re.fullmatch('[a-f0-9]{64}', item.get('sha256', '')) or
                item.get('name') != {'original': 'CP7_CREDIT_DE_NATIVE13.json',
                                    'native_group': 'CP7_CREDIT_DE_NATIVE13_CASES.json',
                                    'package': 'T3_PACKAGE_INSTALL.json'}[key]):
            raise ValueError('E1_EXACT_PARENT_RAW_REPORT_PINS_REQUIRED:' + key)
    return pin


def retained_failure(cfg, raw):
    item = cfg['retained_failed_D1']
    if len(raw) != FAILED_GROUP_BYTES or sha256(raw).hexdigest() != FAILED_GROUP_SHA256:
        raise ValueError('E1_RETAINED_FAILED_D1_ORIGINAL_BYTES_CHANGED')
    group = json.loads(raw)
    if group.get('status') != 'INCOMPLETE' or group.get('counts') != {'PASS': 5, 'INCOMPLETE': 8}:
        raise ValueError('E1_RETAINED_FAILED_D1_MUST_NOT_BE_RELABELLED')
    return dict(status='ACTUAL_FAILED_D1_FIVE_PASS_EIGHT_INCOMPLETE_RETAINED_ONLY', head=item['head'],
        raw_sha256=FAILED_GROUP_SHA256, usable_prerequisite=False, fresh_E_cases_credited=0)


def exact_group(group, ids, count):
    if (group.get('status') != 'PASS' or group.get('error') or group.get('counts') != {'PASS': count} or
            len(ids) != len(set(ids)) or len(ids) != count or group.get('planned_case_ids') != list(ids) or
            set(group.get('cases', {})) != set(ids) or group.get('complete_boundary_restored') is not True):
        raise ValueError('E1_COMPLETE_EXACT_NATIVE_GROUP_REQUIRED')
    for name, row in group['cases'].items():
        if row.get('status') != 'PASS' or row.get('full_boundary_restored') is not True or row.get('public_schema_unchanged') is not True:
            raise ValueError('E1_NATIVE_CASE_OR_BOUNDARY_FAILED:' + name)


def admitted(cfg, originals, current_D1, frozen_D1_source, ids):
    pin = selected(cfg)
    parsed = {}
    for key in ('original', 'native_group', 'package'):
        raw, item = originals[key], pin[key]
        if len(raw) != item['bytes'] or sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('E1_RETAINED_ORIGINAL_BYTES_CHANGED:' + key)
        parsed[key] = json.loads(raw)
    actual, group, package = (parsed[key] for key in ('original', 'native_group', 'package'))
    if (actual.get('label') != 'CP7_CREDIT_DE_NATIVE13' or actual.get('status') != 'PASS' or
            actual.get('qualification_commit') != pin['head'] or actual.get('error') or actual.get('restore_error') or
            actual.get('expected_case_count') != 1 or actual.get('observed_case_count') != 1 or
            actual.get('required_case_ids') != [NATIVE_CASE]):
        raise ValueError('E1_PARENT_ACTUAL_NATIVE13_TERMINAL_PASS_REQUIRED')
    for key in ('cp6_restored', 'advisor_gate', 'baseline_full22_all_rows_all_sequences_equal',
                'baseline_advisors_equal', 'used_guard_refused_before_DDL', 'required_case_ids_pass'):
        if actual.get(key) is not True:
            raise ValueError('E1_PARENT_FULL_RESTORE_OR_USED_GUARD_FAILED:' + key)
    if (actual.get('baseline_role_cleanup', {}).get('baseline_roles_exact') is not True or
            actual.get('focused_preuse_removal', {}).get('used_guard_before_DDL') is not True):
        raise ValueError('E1_PARENT_ROLE_RESTORE_AND_PREUSE_INVERSE_REQUIRED')
    bundle = actual.get('committed', {}).get(NATIVE_CASE, {})
    if (set(actual.get('committed', {})) != {NATIVE_CASE} or bundle.get('status') != 'PASS' or
            bundle.get('native') != group or bundle.get('actual_Native_cases') != 13 or
            bundle.get('used_guard_refused_before_DDL') is not True or
            bundle.get('unchanged_physical_stock_HPP_cost_GL_and_original_sale_payment') is not True):
        raise ValueError('E1_PARENT_EXACT_NATIVE13_AND_COMMITTED_FINANCIAL_WITNESS_REQUIRED')
    exact_group(group, ids, 13)
    declaration = actual.get('source_declaration', {})
    if declaration.get('current_installation') != current_D1 or declaration.get('qualification') != frozen_D1_source:
        raise ValueError('E1_CURRENT_D1_OR_FROZEN_PARENT_SOURCE_DIFFERS_FROM_ORIGINAL')
    if (package.get('gate') != {key: True for key in GATES} or package.get('run_identity', {}).get('tool_head') != pin['head'] or
            package.get('writer_runtime', {}).get('status') != 'PASS' or
            'auth_users_before' not in package or 'auth_users_after' not in package or
            package['auth_users_before'] is None or package['auth_users_before'] != package['auth_users_after']):
        raise ValueError('E1_PARENT_FIVE_PACKAGE_GATES_AND_AUTH_RESTORE_REQUIRED')
    return dict(status='EXACT_SUCCESSFUL_D1_NATIVE13_AND_FIVE_PACKAGE_GATES_ADMITTED', head=pin['head'],
                retained_Native_cases=13, fresh_E_cases_credited=0,
                original_sha256=pin['original']['sha256'], native_group_sha256=pin['native_group']['sha256'],
                package_sha256=pin['package']['sha256'], production_go=False, independent_acceptance=False)
