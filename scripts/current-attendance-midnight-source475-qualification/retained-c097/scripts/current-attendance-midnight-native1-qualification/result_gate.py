"""One exact raw Native1, committed used witness and all five new package gates."""
import json
import subprocess
from midnight_common import HERE, ROOT, ID, LABEL, GROUP, CASE, document
import midnight_gate as gate
import midnight_admission as admission


def checked(outer, group, package, files, drill, parent_docs, cfg, expected_head):
    gate.selected(cfg)
    admission.exact_group(group, [ID])
    if group.get('business_day_retried') or group.get('business_day_attempts'):
        raise ValueError('MIDNIGHT_DAY_RETRY_FORBIDDEN')
    current = outer.get('source_declaration', {}).get('current_installation')
    admission.checked(parent_docs, cfg, current)
    if (outer.get('status') != 'PASS' or outer.get('label') != LABEL or outer.get('error')
            or outer.get('restore_error') or outer.get('qualification_commit') != expected_head
            or outer.get('required_case_ids') != [CASE] or set(outer.get('committed', {})) != {CASE}
            or outer.get('observed_case_count') != 1 or outer.get('expected_case_count') != 1):
        raise ValueError('MIDNIGHT_EXACT_NEW_OUTER_PASS_REQUIRED')
    for key in ('cp6_restored', 'baseline_full22_all_rows_all_sequences_equal',
                'baseline_advisors_equal', 'advisor_gate', 'used_guard_refused_before_DDL',
                'required_case_ids_pass'):
        if outer.get(key) is not True:
            raise ValueError('MIDNIGHT_FULL_OUTER_RESTORE_REQUIRED:' + key)
    if (not set(admission.RESTORE) <= set(outer.get('restore_components', {}))
            or any(v is not True for v in outer['restore_components'].values())
            or outer.get('baseline_role_cleanup', {}).get('baseline_roles_exact') is not True):
        raise ValueError('MIDNIGHT_ALL_RESTORE_COMPONENTS_AND_ROLES_REQUIRED')
    for key, value in dict(actual_Native_cases=1, actual_two_session_races=0,
                           actual_Auth_HTTP_cases=0, actual_browser_cases=0).items():
        if type(outer.get(key)) is not int or outer[key] != value:
            raise ValueError('MIDNIGHT_ONE_FRESH_CASE_AND_ZERO_OTHER_CREDIT_REQUIRED')
    component = outer['committed'][CASE]
    if (component.get('status') != 'PASS' or component.get('midnight_native1') != group
            or component.get('required_Native_case_ids') != [ID]
            or component.get('actual_Native_cases') != 1
            or component.get('single_attempt') is not True or component.get('day_rollover_retry') is not False
            or component.get('fresh_original11_or14_reexecuted') is not False
            or component.get('combined_strict15_fabricated') is not False):
        raise ValueError('MIDNIGHT_SEPARATE_EXACT_RAW1_NO_REEXECUTED14_REQUIRED')
    capture = component.get('actual_installed_capture', {})
    if (len(capture.get('originals', {})) != 15 or len(capture.get('clones', {})) != 2
            or len(capture.get('actual_all22', {})) != 22
            or capture.get('source_derived_local_ABI_used') is not False):
        raise ValueError('MIDNIGHT_ACTUAL15_CAPTURE_REQUIRED')
    if (not component.get('committed_choice_and_allocation')
            or not component.get('independent_Native_pool_oracle')
            or component.get('used_guard_refused_before_DDL') is not True
            or component.get('original_accrual_and_source_binding_unchanged') is not True
            or not component.get('used_inverse_refusal_before')
            or component['used_inverse_refusal_before'] != component.get('used_inverse_refusal_after')
            or component.get('committed_used_witness_additional_cases') != 0):
        raise ValueError('MIDNIGHT_UNCHANGED_ACTUAL_ALLOCATE_WITNESS_AND_FULL_NO_EFFECT_REQUIRED')
    fact = group['cases'][ID]
    previews = fact.get('previews', {})
    if (fact.get('source_cents') != 100003 or fact.get('exact_epoch_delta_us') != 1
            or fact.get('full_business_rows_and_sequences_unchanged_for_reads') is not True
            or fact.get('choice_waiting_without_allocation') is not True
            or fact.get('original_accrual_unchanged') is not True
            or {key: value.get('denominator') for key, value in previews.items()}
               != {'BEFORE': 5, 'AFTER': 5, 'BOTH': 10}):
        raise ValueError('MIDNIGHT_EXACT_ORIGINAL_100003_CENTS_5_5_10_ORACLES_REQUIRED')
    identity = package.get('run_identity', {})
    if (identity.get('tool_head') != expected_head or identity.get('github_sha') != expected_head
            or identity.get('workflow') != cfg['workflow_name'] or identity.get('job') != 'p21'
            or identity.get('mode') != 'install'
            or not isinstance(identity.get('run_id'), str) or not identity['run_id'].isdigit()):
        raise ValueError('MIDNIGHT_NEW_PACKAGE_CURRENT_RUN_IDENTITY_REQUIRED')
    if (package.get('status') != 'ALL_STAGES_INSTALLED' or set(package.get('gate', {})) != set(admission.FIVE)
            or any(package['gate'][k] is not True for k in admission.FIVE)
            or package.get('writer_runtime', {}).get('status') != 'PASS'
            or package.get('primary_unchanged') is not True
            or package.get('backup_restore_drill') != 'RESTORED_IDENTICAL'
            or package.get('auth_users_before') is None
            or package['auth_users_before'] != package.get('auth_users_after')):
        raise ValueError('MIDNIGHT_NEW_ALL5_PACKAGE_PRIMARY_AUTH_REQUIRED')
    rows = files.get('files', [])
    if (files.get('status') != 'ALL_FILES_INSTALLED' or len(rows) != 30
            or len({row.get('key') for row in rows}) != 30 or any(row.get('status') != 'PASS' for row in rows)):
        raise ValueError('MIDNIGHT_NEW_ALL30_PACKAGE_FILES_REQUIRED')
    if (drill.get('status') != 'RESTORED_IDENTICAL' or not drill.get('checks')
            or any(v is not True for v in drill['checks'].values())
            or drill.get('catalog', {}).get('differ') != {} or drill.get('data', {}).get('differ') != {}
            or drill.get('engine', {}).get('equal') is not True):
        raise ValueError('MIDNIGHT_NEW_COMPLETE_BACKUP_DRILL_REQUIRED')
    return dict(status='PASS', actual_Native_cases=1, retained_parent14_reexecuted=False,
        fresh_original11_or14_reexecuted=False, single_attempt=True,
        all_five_new_package_gates=True, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
        actual_two_session_races=0, production_go=False, independent_acceptance=False)


def main():
    out = ROOT / 'cp6-proof/t3'
    try:
        cfg = document((HERE / 'CONFIG.json').read_bytes())
        parent, _ = gate.selected(cfg)
        from midnight_common import read_original
        docs = {k: read_original(ROOT, v)['document'] for k, v in parent['originals'].items()}
        read = lambda name: document((out / name).read_bytes())
        result = checked(read(LABEL + '.json'), read(GROUP + '.json'),
            read('T3_PACKAGE_INSTALL.json'), read('T3_PACKAGE_FILES_INSTALL.json'),
            read('T3_BACKUP_RESTORE_DRILL.json'), docs, cfg,
            subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip())
    except Exception as error:
        result = dict(status='INCOMPLETE', error=str(error), actual_Native_cases=0,
                      production_go=False, independent_acceptance=False)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'MIDNIGHT_NATIVE1_FINAL_GATE.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
