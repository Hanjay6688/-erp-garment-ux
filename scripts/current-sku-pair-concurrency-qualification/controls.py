"""Pure orchestration oracles; local doubles cannot confer Native/Auth credit."""
from copy import deepcopy
import traceback

RESTORE_GATES = ('complete_database_dump_restored', 'all22_all_rows_all_sequences_roles_exact',
                 'cp6_restored', 'advisors_equal', 'only_pg_cron_errors')


def prerequisite(native7, expected_ids, installed_sources, current_sources):
    if installed_sources != current_sources:
        raise ValueError('SKU_CONCURRENCY_EXACT_CURRENT_INSTALLATION_REQUIRED')
    if not isinstance(native7, dict) or native7.get('status') != 'PASS':
        raise ValueError('SKU_CONCURRENCY_FRESH_NATIVE7_PASS_REQUIRED')
    group = native7.get('native', {})
    rows = group.get('cases', {})
    if (len(expected_ids) != 7 or len(set(expected_ids)) != 7 or
            group.get('counts') != {'PASS': 7} or set(rows) != set(expected_ids) or
            any(row.get('status') != 'PASS' for row in rows.values()) or
            native7.get('actual_Native_cases') != 7):
        raise ValueError('SKU_CONCURRENCY_EXACT_SEVEN_NATIVE_CASES_REQUIRED')
    if native7.get('used_guard_refused_before_DDL') is not True:
        raise ValueError('SKU_CONCURRENCY_FRESH_USED_GUARD_REQUIRED')
    return dict(status='SAME_CALL_NATIVE7_AND_USED_GUARD_ADMITTED', Native_case_ids=list(expected_ids),
                fresh_Native_cases_in_this_followup=0, real_Auth_claim=False)


def restored(proof):
    if not isinstance(proof, dict) or any(proof.get(key) is not True for key in RESTORE_GATES):
        raise ValueError('SKU_CONCURRENCY_COMPLETE_RESTORE_PROOF_REQUIRED')
    if proof.get('selected_table_cleanup') is not False:
        raise ValueError('SKU_CONCURRENCY_SELECTED_TABLE_CLEANUP_REFUSED')
    return proof


def execute(operation, boundary):
    """Retain the first business error; always attempt full dump restoration.

    boundary.always is the existing current-factory-initial-stage restoration
    control. A restore failure cannot erase the original business result.
    """
    row = dict(status='INCOMPLETE')
    try:
        value = operation()
        row['original_case_result'] = deepcopy(value)
        if not isinstance(value, dict) or value.get('status') not in ('PASS', 'FAIL', 'COUNTEREXAMPLE', 'INCOMPLETE'):
            raise ValueError('SKU_CONCURRENCY_CASE_RESULT_INVALID')
        row.update(value)
    except Exception as error:
        row.update(status='INCOMPLETE', error=str(error), traceback=traceback.format_exc())
    try:
        observed, restore, proof, observation_failure = boundary.always(
            boundary.observe, boundary.restore, boundary.verify)
        row['installed_baseline_restoration'] = dict(restored(proof), observation=observed, restore=restore)
        if observation_failure:
            row.update(status='INCOMPLETE', observation_error=str(observation_failure[0]),
                       observation_traceback=observation_failure[1])
    except Exception as error:
        row.update(status='INCOMPLETE', restore_error=str(error), restore_traceback=traceback.format_exc())
        row['failed_restore_observation'] = deepcopy(boundary.observed)
    return row


def complete(group, ids):
    rows = group.get('races', {})
    if (group.get('status') != 'RUN_COMPLETE' or group.get('counts') != {'PASS': len(ids)} or
            set(rows) != set(ids) or group.get('planned_race_ids') != list(ids) or
            group.get('database_remaining') != 0 or group.get('cleanup_failures')):
        raise ValueError('SKU_CONCURRENCY_EXACT_NINE_CASES_AND_CLEANUP_REQUIRED')
    for row in rows.values():
        if row.get('status') != 'PASS' or row.get('session_leaks') or row.get('observation_error') or row.get('restore_error'):
            raise ValueError('SKU_CONCURRENCY_FAILED_OR_LEAKING_CASE')
        restored(row.get('installed_baseline_restoration'))
    return dict(status='PASS', actual_two_session_conversion_races=3,
                actual_Native_session_permission_waits=6, actual_Native_cases=0,
                same_call_prerequisite_Native_cases=7, actual_Auth_HTTP_cases=0,
                actual_browser_cases=0, administrative_actor_fixtures=True,
                real_Auth_claim=False, production_go=False, independent_acceptance=False)
