"""Actual strict11 and strict3 originals plus complete outer/package restore only."""
from pathlib import Path
import importlib.util
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LABEL = 'CP7_S03_ATTENDANCE_CHOICE_NATIVE14'
CASE = 'S03_ATTENDANCE_NATIVE14_AND_USED_INVERSE'
FIVE = ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')


def checked(report, original11, reader3, package, files, drill, cfg, expected_head=None):
    spec = importlib.util.spec_from_file_location('s03_native14_actual_group_result_gate', HERE / 'reader_group.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    helper.exact_group(original11, cfg['original_Native11_ids'])
    helper.exact_group(reader3, cfg['reader_Native3_ids'])
    if (report.get('status') != 'PASS' or report.get('label') != LABEL or report.get('error') or report.get('restore_error')
            or report.get('required_case_ids') != [CASE] or report.get('expected_case_count') != 1
            or report.get('observed_case_count') != 1 or set(report.get('committed', {})) != {CASE}):
        raise ValueError('S03_NATIVE14_EXACT_OUTER_PASS_AND_ONE_COMMITTED_COMPONENT_REQUIRED')
    for key in ('cp6_restored', 'baseline_full22_all_rows_all_sequences_equal', 'baseline_advisors_equal',
                'advisor_gate', 'used_guard_refused_before_DDL', 'required_case_ids_pass'):
        if report.get(key) is not True:
            raise ValueError('S03_NATIVE14_FULL_OUTER_RESTORE_REQUIRED:' + key)
    restore = report.get('restore_components', {})
    if not restore or any(v is not True for v in restore.values()):
        raise ValueError('S03_NATIVE14_EVERY_RESTORE_COMPONENT_REQUIRED')
    if report.get('baseline_role_cleanup', {}).get('baseline_roles_exact') is not True:
        raise ValueError('S03_NATIVE14_BASELINE_ROLES_EXACT_REQUIRED')
    for key, count in dict(actual_Native_cases=14, actual_two_session_races=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0).items():
        if type(report.get(key)) is not int or report[key] != count:
            raise ValueError('S03_NATIVE14_HONEST_EXACT_COUNTS_REQUIRED:' + key)
    component = report['committed'][CASE]
    if (component.get('status') != 'PASS' or component.get('native') != original11 or component.get('reader_native3') != reader3
            or component.get('actual_Native_cases') != 14 or component.get('required_Native_case_ids') != cfg['Native_case_ids']
            or component.get('both_groups_same_actual_installation') is not True
            or component.get('reader3_requires_actual_fresh_original11') is not True
            or component.get('combined_strict14_fabricated') is not False):
        raise ValueError('S03_NATIVE14_BOTH_EXACT_RAW_GROUPS_SAME_CURRENT_INSTALLATION_REQUIRED')
    capture = component.get('actual_installed_capture', {})
    if (len(capture.get('originals', {})) != 15 or len(capture.get('clones', {})) != 2
            or len(capture.get('actual_all22', {})) != 22 or capture.get('source_derived_local_ABI_used') is not False):
        raise ValueError('S03_NATIVE14_REAL_CAPTURE15_CLONES2_ALL22_REQUIRED')
    if (component.get('used_guard_refused_before_DDL') is not True
            or component.get('original_accrual_and_source_binding_unchanged') is not True
            or component.get('used_inverse_refusal_before') != component.get('used_inverse_refusal_after')
            or not component.get('used_inverse_refusal_before')
            or not component.get('committed_choice_and_allocation') or not component.get('independent_Native_pool_oracle')):
        raise ValueError('S03_NATIVE14_ACTUAL_COMMITTED_ALLOCATE_USED_WITNESS_AND_NO_EFFECT_GUARD_REQUIRED')
    source = report.get('source_declaration', {})
    if source.get('current_installation', {}).get('files') != cfg['runtime_files']:
        raise ValueError('S03_NATIVE14_ACTUAL_CURRENT_RUNTIME7_REQUIRED')
    head = report.get('qualification_commit', '')
    identity = package.get('run_identity', {})
    if (not re.fullmatch('[a-f0-9]{40}', head) or expected_head is not None and head != expected_head
            or identity.get('tool_head') != head or identity.get('github_sha') != head
            or identity.get('workflow') != 'CP7 A S03 attendance choice plus owning readers Native14'
            or identity.get('job') != 'p21' or identity.get('mode') != 'install'
            or not isinstance(identity.get('run_id'), str) or not identity['run_id'].isdigit()):
        raise ValueError('S03_NATIVE14_SAME_CURRENT_OUTER_PACKAGE_RUN_SOURCE_REQUIRED')
    if (package.get('status') != 'ALL_STAGES_INSTALLED' or set(package.get('gate', {})) != set(FIVE)
            or any(package['gate'][key] is not True for key in FIVE)
            or package.get('primary_unchanged') is not True or package.get('backup_restore_drill') != 'RESTORED_IDENTICAL'
            or package.get('auth_users_before') is None or package['auth_users_before'] != package.get('auth_users_after')
            or package.get('writer_runtime', {}).get('status') != 'PASS'):
        raise ValueError('S03_NATIVE14_ALL5_PACKAGE_GATES_PRIMARY_AUTH_RESTORE_REQUIRED')
    rows = files.get('files', [])
    if (files.get('status') != 'ALL_FILES_INSTALLED' or len(rows) != 30
            or len({r.get('key') for r in rows}) != 30 or any(r.get('status') != 'PASS' for r in rows)):
        raise ValueError('S03_NATIVE14_COMPLETE_THIRTY_PACKAGE_FILES_REQUIRED')
    if (drill.get('status') != 'RESTORED_IDENTICAL' or not drill.get('checks') or any(v is not True for v in drill['checks'].values())
            or drill.get('data', {}).get('differ') != {} or drill.get('catalog', {}).get('differ') != {}
            or drill.get('engine', {}).get('equal') is not True):
        raise ValueError('S03_NATIVE14_COMPLETE_BACKUP_DRILL_REQUIRED')
    return dict(status='PASS', actual_Native_cases=14, actual_groups=[11, 3], combined_strict14_fabricated=False,
        actual_Auth_HTTP_cases=0, actual_two_session_races=0, actual_browser_cases=0,
        all_five_package_gates=True, complete_outer_restore_required=True,
        full_S03_acceptance=False, independent_acceptance=False, production_go=False)


def main():
    out = ROOT / 'cp6-proof/t3'
    try:
        read = lambda name: json.loads((out / name).read_bytes())
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        result = checked(read(LABEL + '.json'), read('CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json'),
            read('CP7_S03_ATTENDANCE_CHOICE_READER_NATIVE3_CASES.json'), read('T3_PACKAGE_INSTALL.json'),
            read('T3_PACKAGE_FILES_INSTALL.json'), read('T3_BACKUP_RESTORE_DRILL.json'), cfg,
            expected_head=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip())
    except Exception as error:
        result = dict(status='INCOMPLETE', error=str(error), actual_Native_cases=0, production_go=False, independent_acceptance=False)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'S03_NATIVE14_FINAL_GATE.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
