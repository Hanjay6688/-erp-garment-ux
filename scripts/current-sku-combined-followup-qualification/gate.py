"""Closed prerequisite and complete-group oracles. No runtime operations."""
from hashlib import sha256
import json

BASE = '21c69cf25defcee854beb08e998062d7e883d968'
TREE = 'a0d2c0da83bf5dc29f2c6b2e02abe6d7ed68f89e'
NATIVE_CASE = 'SKU_PAIR_CONVERSION_NATIVE_AND_USED_INVERSE'
MIXED_CASE = 'SKU29_MIXED_PO_NONPO_NATIVE_LINEAGE_VALUE_CONSERVATION'
CALLER_ZONES = ['Asia/Jakarta', 'UTC', 'Asia/Tokyo', 'Pacific/Kiritimati', 'Etc/GMT+12']


def selected(cfg):
    pin = cfg.get('accepted_native7')
    if pin is None:
        raise ValueError('SKU_COMBINED_CLOSED_TERMINAL_21C_NATIVE7_ORIGINAL_AND_PACKAGE_REQUIRED')
    run_id = cfg.get('pending_run_id')
    if (type(run_id) is not int or run_id <= 0 or pin.get('head') != BASE or
            pin.get('tree') != TREE or pin.get('run_id') != run_id):
        raise ValueError('SKU_COMBINED_OTHER_NATIVE_PREREQUISITE_REFUSED')
    for key in ('original', 'package'):
        item = pin[key]
        if not isinstance(item['bytes'], int) or item['bytes'] <= 0 or len(item['sha256']) != 64:
            raise ValueError('SKU_COMBINED_CONCRETE_ORIGINAL_PIN_REQUIRED')
    return pin


def admitted(cfg, raw, package_raw, current_sources, ids):
    pin = selected(cfg)
    for key, value in (('original', raw), ('package', package_raw)):
        if len(value) != pin[key]['bytes'] or sha256(value).hexdigest() != pin[key]['sha256']:
            raise ValueError('SKU_COMBINED_RETAINED_BYTES_CHANGED:' + key)
    actual, package = json.loads(raw), json.loads(package_raw)
    if actual.get('label') != 'CP7_SKU_PAIR_CONVERSION_NATIVE' or actual.get('status') != 'PASS' or actual.get('qualification_commit') != BASE:
        raise ValueError('SKU_COMBINED_RETAINED_NATIVE7_NOT_PASS')
    for key in ('cp6_restored', 'advisor_gate', 'baseline_full22_all_rows_all_sequences_equal', 'baseline_advisors_equal',
                'used_guard_refused_before_DDL', 'required_case_ids_pass'):
        if actual.get(key) is not True:
            raise ValueError('SKU_COMBINED_RETAINED_BOUNDARY_FAILED:' + key)
    if actual.get('expected_case_count') != 1 or actual.get('observed_case_count') != 1 or actual.get('required_case_ids') != [NATIVE_CASE]:
        raise ValueError('SKU_COMBINED_RETAINED_OUTER_CASE_REQUIRED')
    if actual.get('focused_preuse_removal', {}).get('used_guard_before_DDL') is not True:
        raise ValueError('SKU_COMBINED_RETAINED_PREUSE_INVERSE_REQUIRED')
    bundle = actual.get('committed', {}).get(NATIVE_CASE, {})
    group = bundle.get('native', {})
    if (bundle.get('status') != 'PASS' or bundle.get('used_guard_refused_before_DDL') is not True or
            group.get('counts') != {'PASS': 7} or set(group.get('cases', {})) != set(ids) or
            any(row.get('status') != 'PASS' or row.get('full_boundary_restored') is not True for row in group['cases'].values())):
        raise ValueError('SKU_COMBINED_RETAINED_EXACT_SEVEN_NATIVE_BOUNDARIES_REQUIRED')
    if actual.get('source_declaration', {}).get('current_installation') != current_sources:
        raise ValueError('SKU_COMBINED_CURRENT_PRODUCT_DIFFERS_FROM_RETAINED_21C')
    canonical_mixed(group)
    required = {key: True for key in ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')}
    if (package.get('gate') != required or package.get('run_identity', {}).get('tool_head') != BASE or
            package.get('writer_runtime', {}).get('status') != 'PASS' or 'auth_users_before' not in package or
            'auth_users_after' not in package or package['auth_users_before'] is None or package['auth_users_before'] != package['auth_users_after']):
        raise ValueError('SKU_COMBINED_RETAINED_PACKAGE_OR_AUTH_RESTORE_FAILED')
    return dict(status='EXACT_TERMINAL_21C_NATIVE7_AND_FIVE_PACKAGE_GATES_ADMITTED', head=BASE,
                original_sha256=pin['original']['sha256'], package_sha256=pin['package']['sha256'],
                retained_base_Native_cases=7, fresh_cases_credited=0)


def canonical_mixed(group):
    """The same repaired Native case must retain its five-zone observation."""
    mixed = group.get('cases', {}).get(MIXED_CASE, {})
    if (mixed.get('preview_caller_zones_checked') != CALLER_ZONES or
            mixed.get('all_preview_fields_equal_across_zones') is not True or
            mixed.get('preview_caller_setting_restored') is not True or
            mixed.get('posting_function_timezone') != 'UTC'):
        raise ValueError('SKU_COMBINED_NATIVE7_EXACT_FIVE_ZONE_PREVIEW_PROOF_REQUIRED')


def exact_native(group, ids, count):
    if (len(ids) != count or group.get('error') or group.get('counts') != {'PASS': count} or set(group.get('cases', {})) != set(ids) or
            any(row.get('status') != 'PASS' or row.get('full_boundary_restored') is not True for row in group['cases'].values())):
        raise ValueError('SKU_COMBINED_FRESH_NATIVE_GROUP_OR_BOUNDARY_FAILED')
    if count == 7:
        canonical_mixed(group)


def browser(group, ids):
    if (group.get('status') != 'RUN_COMPLETE' or group.get('error') or group.get('host_exit') != 0 or group.get('counts') != {'PASS': 4} or set(group.get('cases', {})) != set(ids) or
            group.get('planned_case_ids') != list(ids) or group.get('host_status') != 'RUN_COMPLETE' or
            group.get('real_auth') is not True or group.get('jwt_signed_by_runtime') is not False or
            group.get('test_only_usage_grant') is not False or group.get('database_remaining') != 0 or
            group.get('cleanup_failures') or group.get('session_leaks') or group.get('console_errors') != 0 or
            group.get('auth_counts', {}).get('restored') is not True or group.get('auth_cleanup_failures')):
        raise ValueError('SKU_COMBINED_REAL_AUTH_BROWSER4_OR_CLEANUP_FAILED')
    if any(row.get('status') != 'PASS' for row in group['cases'].values()):
        raise ValueError('SKU_COMBINED_PARTIAL_BROWSER_REFUSED')
    return dict(real_Auth_browser_cases=4, Native_permission_waits_are_real_Auth=False)
