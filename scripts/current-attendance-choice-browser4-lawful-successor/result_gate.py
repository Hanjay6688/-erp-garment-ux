"""Typed terminal gate over actual browser4 Original and all five package gates."""
from pathlib import Path
from hashlib import sha256
import gzip
import json
import math
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LABEL = 'CP7_S03_MOUNTED_FULL_APP_BROWSER4'
CASE = 'S03_MOUNTED_FULL_APP_AUTH_BROWSER4'
IDS = (
    'S03_BROWSER_OWNER_EXPENSE_CORRECT_REVERSE_DESKTOP',
    'S03_BROWSER_OWNER_CARRY_ALLOCATE_CANCEL_MOBILE390',
    'S03_BROWSER_ACTUAL_STALE_AND_LOST_REPLY_SAME_UUID',
    'S03_BROWSER_CURRENT_AUTH_RIGHTS_AND_DELAYED_CONTEXT',
)


def checked(report, package):
    if report.get('status') != 'PASS' or report.get('label') != LABEL:
        raise ValueError('S03_BROWSER4_ACTUAL_OUTER_PASS_REQUIRED')
    for key in ('cp6_restored', 'baseline_full22_all_rows_all_sequences_equal', 'baseline_advisors_equal',
            'advisor_gate', 'used_guard_refused_before_DDL', 'required_case_ids_pass', 'real_Auth_browser_claim'):
        if report.get(key) is not True:
            raise ValueError('S03_BROWSER4_FULL_ACTUAL_OUTER_GATE_REQUIRED:' + key)
    for key, value in dict(actual_browser_cases=4, actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_two_session_races=0).items():
        if type(report.get(key)) is not int or report[key] != value:
            raise ValueError('S03_BROWSER4_EXACT_TYPED_TERMINAL_COUNT_REQUIRED:' + key)
    component = report.get('committed', {}).get(CASE, {})
    browser = component.get('browser', {})
    if (component.get('actual_captured_originals') != 15 or component.get('actual_Native_clones') != 2
            or component.get('product_sources_override') is not False
            or component.get('canonical_backend_selected_from_qualified3c0') is not True
            or component.get('frozen_UI82_source_unchanged') is not True
            or component.get('backend_ROOT_or_method_override') is not False
            or component.get('canonical_qualified15_installed_proof', {}).get('actual_captured_originals') != 15
            or len(component.get('actual_backend_runtime_files', {})) != 7):
        raise ValueError('S03_BROWSER4_REAL_RUNTIME7_CAPTURE15_SOURCE_REQUIRED')
    if (set(report.get('committed', {})) != {CASE} or component.get('status') != 'PASS'
            or component.get('actual_browser_cases') != 4 or browser.get('status') != 'PASS'
            or browser.get('counts') != {'PASS': 4} or browser.get('planned_case_ids') != list(IDS)
            or set(browser.get('cases', {})) != set(IDS)
            or any(row.get('status') != 'PASS' for row in browser.get('cases', {}).values())):
        raise ValueError('S03_BROWSER4_EVERY_ACTUAL_CALLBACK_PASS_REQUIRED')
    for key, row in browser['cases'].items():
        if (row.get('actual_normal_App_real_Auth_public_RPC') is not True
                or row.get('fixture_screen_creation_claim') is not False
                or any(type(row.get(name)) is not int or row[name] != 0 for name in
                    ('actual_Native_cases', 'actual_Auth_HTTP_cases', 'actual_two_session_races'))
                or not row.get('shots') or not row.get('contrasts')):
            raise ValueError('S03_BROWSER4_ACTUAL_CALLBACK_EVIDENCE_REQUIRED:' + key)
        observed = [row.get('console_evidence', {})] + row.get('other_Auth_context_console', [])
        if 'delayed_context_console' in row:observed.append(row['delayed_context_console'])
        if any(item.get('unexpected') != [] or item.get('page_errors') != [] for item in observed):
            raise ValueError('S03_BROWSER4_NO_UNEXPECTED_CALLBACK_CONSOLE_REQUIRED:' + key)
        expected_width = 390 if key == IDS[1] else 1440
        for measurement in row['contrasts']:
            width, text = measurement.get('width', {}), measurement.get('measured', [])
            if (width.get('viewport') != expected_width or type(width.get('page')) is not int
                    or width['page'] > expected_width or not text
                    or any(type(item.get('ratio')) not in (int, float) or not math.isfinite(item['ratio'])
                        or item['ratio'] < 4.5 for item in text)):
                raise ValueError('S03_BROWSER4_STRICT_WIDTH_AND_CONTRAST_REQUIRED:' + key)
    if (browser.get('database_remaining') != 0 or browser.get('cleanup_failures')
            or browser.get('auth_counts', {}).get('restored') is not True or browser.get('console_errors') != 0
            or browser.get('session_leaks') or browser.get('real_auth') is not True
            or browser.get('jwt_signed_by_runtime') is not False or browser.get('test_only_usage_grant') is not False):
        raise ValueError('S03_BROWSER4_AUTH_COPY_AND_CONSOLE_CLEANUP_REQUIRED')
    admissions = component.get('copy_catalog_admissions', [])
    if len(admissions) != 1 or admissions[0].get('all22_groups_equal_original_install') is not True:
        raise ValueError('S03_BROWSER4_ACTUAL_COMPLETE22_COPY_ADMISSION_REQUIRED')
    if not component.get('actual_browser_host_originals'):
        raise ValueError('S03_BROWSER4_ACTUAL_HOST_ORIGINAL_RETENTION_REQUIRED')
    gates = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')
    if (package.get('status') != 'ALL_STAGES_INSTALLED' or set(package.get('gate', {})) != set(gates)
            or any(package['gate'][key] is not True for key in gates)):
        raise ValueError('S03_BROWSER4_ALL_FIVE_ACTUAL_PACKAGE_GATES_REQUIRED')
    return dict(status='PASS', qualified_actual_browser_cases=4, observed_browser_counts=browser['counts'],
        actual_Native_cases=0, actual_Auth_HTTP_cases=0, actual_two_session_races=0,
        real_Auth_observed_within_browser=True, all22_rows_sequences_Auth_full_outer_restore_required=True,
        production_go=False, independent_acceptance=False)


def host_originals(root, component):
    """Hash real retained host bytes and require the final case objects unchanged."""
    originals, matched = component['actual_browser_host_originals'], False
    for item in originals:
        name = item['name']
        if not re.fullmatch(r'S03_BROWSER4_HOST_ORIGINAL_cp6-auditor-browser-[A-Za-z0-9_-]+\.json\.gz', name):
            raise ValueError('S03_BROWSER4_SAFE_FIRST_HOST_ORIGINAL_NAME_REQUIRED')
        packed = (root / 'cp6-proof/t3' / name).read_bytes();raw = gzip.decompress(packed)
        if (len(raw) != item['raw_bytes'] or sha256(raw).hexdigest() != item['raw_sha256']
                or len(packed) != item['gzip_bytes'] or sha256(packed).hexdigest() != item['gzip_sha256']):
            raise ValueError('S03_BROWSER4_ACTUAL_HOST_ORIGINAL_BYTES_CHANGED')
        host = json.loads(raw)
        if host.get('phase') != 'S03_CHOICE_MOUNTED4' or host.get('ui_mode') != 'DISPOSABLE':
            raise ValueError('S03_BROWSER4_NORMAL_APP_HOST_ORIGINAL_REQUIRED')
        if (host.get('status') == 'RUN_COMPLETE' and host.get('planned') == list(IDS)
                and host.get('cases') == component['browser']['cases'] and host.get('real_auth') is True
                and host.get('product_responses_mocked') is False and host.get('blocked_requests') == 0
                and host.get('auth_cleanup_failures') == [] and host.get('console_errors') == []):
            matched = True
    if not matched:
        raise ValueError('S03_BROWSER4_EXACT_FINAL_HOST_ORIGINAL_REQUIRED')
    return dict(retained_actual_host_originals=len(originals), exact_final_host_cases_equal=True)


def main():
    report, package = {}, {}
    try:
        report = json.loads((ROOT / 'cp6-proof/t3' / (LABEL + '.json')).read_bytes())
        package = json.loads((ROOT / 'cp6-proof/t3/T3_PACKAGE_INSTALL.json').read_bytes())
        result = checked(report, package)
        result['host_originals'] = host_originals(ROOT, report['committed'][CASE])
    except Exception as error:
        result = dict(status='INCOMPLETE', error=str(error), qualified_actual_browser_cases=0,
            observed_browser_counts=report.get('committed', {}).get(CASE, {}).get('browser', {}).get('counts', {}),
            production_go=False, independent_acceptance=False)
    output = ROOT / 'cp6-proof/t3/S03_BROWSER4_FINAL_GATE.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
