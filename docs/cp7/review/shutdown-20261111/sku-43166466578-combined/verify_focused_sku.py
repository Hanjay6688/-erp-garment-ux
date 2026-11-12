"""Verify original E4EA and fresh SKU case coverage without relabeling either run."""

import argparse
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

from verify_terminal_sku import (
    AREA, BACKUP, BOUNDARY, BRANCH, BROWSER, CASE, CATALOGUE, GATE, GATES,
    MAIN, NATIVE, PACKAGE, PARENT, PREFLIGHT, SUPERVISOR, WORKFLOW, catalogue,
    fields, files, member_pins, pin, require, strict,
)


ORIGIN = dict(id=43132617378, head_sha='e4eaaecebad1f0ba11ab1542b5df89a6423a8a1e',
              tree='ead4c59721d1fc1dc608a9f803dbaf2a076abbdd', job_id=130900171009)
CURRENT = dict(id=43158542850, head_sha='3f2a7748c7cfde2881b19dac853fef82e49b6885',
               tree='c7c53dd3678459ad6bd18f63a9fa8d9521eca140', job_id=130984047828)
PREFLIGHT_HEAD = '0de103b71b43a6581ff92378f0d69729f80fd91a'
SCOPE = AREA + 'E4EA_CONTINUATION_SCOPE.json'
SCOPE_PIN = dict(bytes=19120, sha256='ee12e4984040e6cafa5f1822e43d27c70842190f8fe3eb83bbc8e4383fd0f22c')
PLAN = AREA + 'PREPARED_NATIVE25_PLAN.json'
MANDOR_DECISION = AREA + 'CUMULATIVE_RUNTIME_BINDING.json'
SOURCE_DELTA = {AREA + name for name in ('E4EA_CONTINUATION_SCOPE.json', 'SOURCE.json',
    'assembly.py', 'component.py', 'context_timezone.py', 'continuation.py', 'final_gate.py',
    'package.py', 'qualification.py')}
FOCUSED_STATUS = 'CURRENT_MANDOR_PARENT_MONEY_AUTOMATIC_FRESH5_BROWSER2_AND_ALL5_PASS'
FOCUSED_COUNTS = dict(actual_Native_cases=5, actual_Auth_HTTP_cases=0,
                      actual_two_session_races=0, actual_browser_cases=2)
BROWSER_IDS = {
    'SKU_CURRENT_MOVAVG_DESKTOP_REAL_AUTH_PAIR_VALUE_RECOVERY_INVERSE',
    'SKU_CURRENT_MOVAVG_MOBILE390_REAL_AUTH_PAIR_VALUE_GUARDS_INVERSE',
}
BACKUP_CHECKS = dict(restore_errors_only_pg_cron=True, catalog_explained=True, data_identical=True,
                     engine_answer_present=True, engine_equal=True)
NATIVE_LOG_PREFIX = 'SKU_AUTOMATIC_CASE_STDOUT/'
OWNING_JOB = 'Actual Mandor parent, full money and automatic Native25; complete restoration'
OWNING_STEP = 'Run current-parent money automatic Native25 and real browser2 once with owning restoration'


def git(repo, *args):
    return subprocess.check_output(['git', '--no-lazy-fetch', '-C', str(repo), *args], timeout=60)


def source(repo):
    origin, head = ORIGIN['head_sha'], CURRENT['head_sha']
    trees = git(repo, 'rev-parse', origin + '^{tree}', head + '^{tree}',
                PREFLIGHT_HEAD + '^{tree}').decode().splitlines()
    require(trees == [ORIGIN['tree'], CURRENT['tree'], CURRENT['tree']], 'SKU_EXACT_REVIEWED_TREES_REQUIRED')
    delta = set(git(repo, 'diff', '--no-renames', '--name-only', origin, head, '--').decode().splitlines())
    require(delta == SOURCE_DELTA, 'SKU_EXACT_FOCUSED_SOURCE_DELTA_REQUIRED')
    stable = (PLAN, PARENT, MANDOR_DECISION, WORKFLOW, AREA + 'native_preflight.py',
              AREA + 'browser_gate.py', AREA + 'global_parent_catalogue.py')
    shared = {name: git(repo, 'show', head + ':' + name) for name in stable}
    for name, raw in shared.items():
        require(git(repo, 'show', origin + ':' + name) == raw, 'SKU_RETAINED_SOURCE_CHANGED:' + name)
    raw = git(repo, 'show', head + ':' + SCOPE)
    require(pin(raw) == SCOPE_PIN, 'SKU_EXACT_REVIEWED_SCOPE_REQUIRED')
    scope = strict(raw)
    plan = strict(shared[PLAN])['case_ids']
    fresh, retained = scope['fresh_case_ids'], scope['retained_case_ids']
    require(plan == scope['planned_case_ids'] and len(plan) == len(set(plan)) == 25
            and len(fresh) == 5 and len(retained) == 20 and set(fresh).isdisjoint(retained)
            and fresh == [case for case in plan if case not in retained]
            and retained == [case for case in plan if case not in fresh], 'SKU_EXACT_DISJOINT_CASE_PLAN_REQUIRED')
    return scope, {name: pin(raw) for name, raw in shared.items()}


def metadata(identity, run, job, artifact):
    run_id, head = identity['id'], identity['head_sha']
    fields(run, dict(id=run_id, head_sha=head, head_branch=BRANCH, event='push', path=WORKFLOW,
                     run_attempt=1, status='completed'), 'SKU_EXACT_TERMINAL_RUN')
    conclusion = run['conclusion']
    require(conclusion in ('success', 'failure', 'cancelled', 'timed_out'), 'SKU_TERMINAL_CONCLUSION_REQUIRED')
    fields(job, dict(id=identity['job_id'], head_sha=head, run_id=run_id, run_attempt=1,
                     status='completed', conclusion=conclusion, name=OWNING_JOB), 'SKU_EXACT_OWNING_JOB')
    name = ('cp7-sku-current-parent-money-automatic-native25-1' if conclusion == 'success'
            else f'cp7-sku-failure-{run_id}-1')
    fields(artifact, dict(name=name, expired=False), 'SKU_EXACT_OWNING_ARCHIVE')
    fields(artifact['workflow_run'], dict(id=run_id, head_sha=head, head_branch=BRANCH), 'SKU_SAME_RUN_ARCHIVE')


def terminal(identity, archive, run, job, artifact):
    metadata(identity, run, job, artifact)
    archive_pin = files(archive, artifact)
    expected_names = (MAIN, NATIVE, PREFLIGHT, BROWSER, GATE, PACKAGE, BACKUP, SUPERVISOR, CATALOGUE)
    with ZipFile(archive) as bundle:
        pins = member_pins(bundle)
        archive_pin['members'] = len(bundle.infolist())
        reports = {name: strict(bundle.read(name)) for name in expected_names if name != CATALOGUE and name in pins}
        original_catalogue = bundle.read(CATALOGUE) if CATALOGUE in pins else None
        case_rows = {}
        for name in pins:
            if name.startswith(NATIVE_LOG_PREFIX) and name.endswith('.jsonl'):
                for line in bundle.read(name).splitlines():
                    row = strict(line)
                    if row.get('group') == NATIVE.removesuffix('.json'):
                        case = row['case']
                        require(case not in case_rows, 'SKU_DUPLICATE_NATIVE_CASE_ORIGINAL:' + case)
                        case_rows[case] = (name, row)
    run_id, head = str(identity['id']), identity['head_sha']
    if MAIN in reports:
        fields(reports[MAIN], dict(qualification_commit=head), 'SKU_SAME_RUN_QUALIFICATION')
    if PACKAGE in reports:
        fields(reports[PACKAGE]['run_identity'], dict(tool_head=head, github_sha=head, run_id=run_id, run_attempt='1'),
               'SKU_SAME_RUN_PACKAGE')
    if SUPERVISOR in reports:
        fields(reports[SUPERVISOR], dict(qualification_commit=head, github_run_id=run_id, github_run_attempt='1'),
               'SKU_SAME_RUN_SUPERVISOR')
    failure = next((step for step in job['steps'] if step['conclusion'] in ('failure', 'cancelled', 'timed_out')), None)
    done = {step['name'] for step in job['steps'] if step['conclusion'] == 'success'}
    case_order = reports.get(NATIVE, {}).get('planned_case_ids', tuple(case_rows))
    first_case_error = None
    for case in case_order:
        if case in case_rows and case_rows[case][1].get('error'):
            name, row = case_rows[case]
            first_case_error = dict(case=case, original=name, message=row['error'].splitlines()[0])
            break
    main_error = reports.get(MAIN, {}).get('error')
    error_pin = pin(main_error.encode()) if isinstance(main_error, str) else None
    receipt = dict(head=head, tree=identity['tree'], run_id=identity['id'], job_id=identity['job_id'], attempt=1,
                   conclusion=run['conclusion'], artifact_id=artifact['id'], archive=archive_pin,
                   all_member_crc_verified=True, first_failed_step=failure,
                   first_case_error=first_case_error, main_error_pin=error_pin,
                   cleanup='Remove disposable database' in done)
    return receipt, reports, pins, case_rows, original_catalogue, done


def restored(receipt, reports, worker_exit):
    fields(reports[MAIN], dict.fromkeys(BOUNDARY, True), 'SKU_RESTORED_ALL_BOUNDARIES')
    fields(reports[BACKUP], dict(status='RESTORED_IDENTICAL', checks=BACKUP_CHECKS), 'SKU_RESTORED_BACKUP')
    fields(reports[BACKUP]['data'], dict(differ={}), 'SKU_RESTORED_DATA')
    fields(reports[SUPERVISOR], dict(worker_exit=worker_exit, deadline_reached=False, external_signal=None,
                                   process_group_empty=True, process_tree_empty=True, orphaned_child=False),
           'SKU_WORKER_EXIT_AND_REAP')
    require(receipt['cleanup'], 'SKU_DISPOSABLE_DATABASE_CLEANUP_REQUIRED')
    receipt.update(actual_outer_restore=True, actual_worker_reaped=True)


def cases(report, rows, pins, planned):
    fields(report, dict(planned_case_ids=planned, missing=[], complete_boundary_restored=True), 'SKU_NATIVE_CASE_PLAN')
    require(set(rows) == set(report['cases']) == set(planned), 'SKU_EXACT_NATIVE_ORIGINALS_REQUIRED')
    observations = {}
    for case in planned:
        name, row = rows[case]
        fields(row, dict(status=report['cases'][case]['status'], full_boundary_restored=True,
                         public_schema_unchanged=True,
                         session_leaks=dict(advisory_locks=0, advisory_lock_keys=[], other_sessions=[])),
               'SKU_NATIVE_ORIGINAL_BOUNDARY:' + case)
        observations[case] = dict(status=row['status'], original=name,
                                  **{key: pins[name][key] for key in ('bytes', 'sha256')})
    return observations


def retained_origin(scope, archive, run, job, artifact):
    receipt, reports, pins, rows, _, _ = terminal(ORIGIN, archive, run, job, artifact)
    origin = scope['origin']
    fields(receipt, dict(conclusion='failure', artifact_id=origin['artifact_id'],
                         archive=dict(bytes=origin['bytes'], sha256=origin['sha256'], members=origin['crc_members'])),
           'SKU_EXACT_E4EA_ORIGINAL')
    fields(reports[MAIN], dict(status='INCOMPLETE'), 'SKU_ORIGINAL_FAILURE_PRESERVED')
    restored(receipt, reports, 1)
    observed = cases(reports[NATIVE], rows, pins, scope['planned_case_ids'])
    require(observed == scope['original_case_receipts'], 'SKU_EXACT_E4EA_CASE_BYTES_REQUIRED')
    kept = {name: observed[name] for name in scope['retained_case_ids']}
    require(all(row['status'] == 'PASS' for row in kept.values()), 'SKU_RETAINED_CASES_MUST_HAVE_PASSED')
    return receipt, reports[PREFLIGHT], kept


def current_result(scope, shared, origin, current, *, scope_pin=SCOPE_PIN, expected_status=FOCUSED_STATUS,
                   review_catalogue=None):
    old_receipt, old_preflight, retained = origin
    receipt, reports, pins, rows, raw, done = current
    if receipt['conclusion'] != 'success':
        # A preflight failure may have no database reports to verify.
        if {MAIN, BACKUP, SUPERVISOR} <= reports.keys():
            try:
                restored(receipt, reports, reports[SUPERVISOR]['worker_exit'])
            except ValueError as error:
                receipt['restore_verification_failure'] = str(error)
        return dict(receipt, status='SKU_FOCUSED_ORIGINAL_FAILURE_RETAINED', actual_case_credit=0,
                    observed_native={name: row['status'] for name, (_, row) in rows.items()},
                    first_reported_error=(reports.get(MAIN, {}).get('error') or '').splitlines()[:1]), None
    counts = dict(FOCUSED_COUNTS, actual_Native_cases=len(scope['fresh_case_ids']))
    business_count = counts['actual_Native_cases'] + counts['actual_browser_cases']
    require(not receipt['first_failed_step'] and OWNING_STEP in done, 'SKU_OWNING_RUNTIME_SUCCESS_REQUIRED')
    restored(receipt, reports, 0)
    fields(reports[SUPERVISOR], dict(status='WORKER_COMPLETED_AND_REAPED', job_budget_seconds=21600,
                                   work_budget_seconds=19800, recovery_reserve_seconds=1200,
                                   artifact_reserve_seconds=600), 'SKU_SAME_OWNING_RUNTIME_RESERVES')
    require(reports[PACKAGE]['gate'] == GATES, 'SKU_ALL_FIVE_PACKAGE_GATES_REQUIRED')
    fields(reports[MAIN], dict(status='PASS', actual_business_cases=business_count, real_Auth_browser_claim=True,
                              **counts), 'SKU_ACTUAL_FOCUSED_NATIVE_AND_BROWSER2')
    gate = reports[GATE]
    fields(gate, dict(status=expected_status, head=receipt['head'], run_id=str(receipt['run_id']),
                      package_all_five=True, prior_parent_cases_not_counted_as_fresh=True,
                      parent_root=shared[PARENT], complete_native_plan=shared[PLAN], **counts),
           'SKU_EXACT_FRESH_FINAL_GATE')
    gate_members = (MAIN, NATIVE, PREFLIGHT, BROWSER, PACKAGE, BACKUP, SUPERVISOR)
    require(gate['originals'] == {name: {key: pins[name][key] for key in ('bytes', 'sha256')} for name in gate_members},
            'SKU_FINAL_GATE_MUST_BIND_EXACT_ORIGINALS')
    preflight = reports[PREFLIGHT]
    for key in ('automatic_functions', 'automatic_actors', 'natural_callers'):
        require(preflight[key] == old_preflight[key], 'SKU_RETAINED_PREFLIGHT_CHANGED:' + key)
    comparable = lambda value: {key: row for key, row in value['retained_money19'].items() if key != 'observed_WIB'}
    require(comparable(preflight) == comparable(old_preflight), 'SKU_RETAINED_MONEY_FIXTURE_AUTHORITY_OR_DAY_CHANGED')
    fresh = cases(reports[NATIVE], rows, pins, scope['fresh_case_ids'])
    require(all(row['status'] == 'PASS' for row in fresh.values()), 'SKU_ALL_FRESH_CASES_MUST_PASS')
    if 'non_po_affected_case_ids' in scope:
        fields(preflight, dict(supplier_account_mappings=dict(AP_SUPPLIER=[[True, True]])),
               'SKU_COMBINED_ACTUAL_SUPPLIER_PREFLIGHT')
        for case in scope['non_po_affected_case_ids']:
            fields(rows[case][1], dict(caller_timezone=scope['caller_timezone']), 'SKU_COMBINED_ACTUAL_WIB:' + case)
    browser = reports[BROWSER]['cases']
    require(set(browser) == BROWSER_IDS and all(row['status'] == 'PASS' for row in browser.values()),
            'SKU_BOTH_EXACT_CURRENT_BROWSER_ORIGINALS_REQUIRED')
    checks = gate['current_browser2']
    fields(checks, dict(actual_browser_cases=2, primary_Auth_counts_restored=True), 'SKU_CURRENT_AUTH_RESTORED')
    assets = dict(checks['complete_census_originals'],
                  **{row['name']: row for row in checks['screenshots']})
    require(len(checks['screenshots']) == 16 and bool(checks['complete_census_originals']) and all(
        {key: pins[name][key] for key in ('bytes', 'sha256')} == {key: row[key] for key in ('bytes', 'sha256')}
        for name, row in assets.items()), 'SKU_EXACT_CURRENT_BROWSER_ASSET_BYTES_REQUIRED')
    observed = catalogue(raw, reports[MAIN]['committed'][CASE]['Global_parent_catalogue'],
                         receipt['head'], receipt['run_id'])
    groups = {name: pin(json.dumps(group, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
              for name, group in strict(raw).items()}
    expected_groups = scope['expected_fixed_catalogue_group_pins']
    differing_groups = sorted(name for name in groups if groups[name] != expected_groups[name])
    exact = not differing_groups
    catalogue_equivalence = None
    if not exact:
        require(review_catalogue is not None, 'SKU_ACTUAL_FULL25_DIFFERS_FROM_REVIEWED_REPAIR')
        catalogue_equivalence = review_catalogue(raw, scope, groups)
    fields(gate['continuation'], dict(origin=scope['origin'], scope=scope_pin, fresh_case_ids=list(fresh),
                                    retained_case_ids=list(retained), cumulative_acceptance_pending=True),
           'SKU_EXACT_CUMULATIVE_SCOPE_BINDING')
    fields(gate['continuation']['catalogue'], dict(actual=groups, differing_groups=differing_groups,
                                                 exact_expected_groups=exact),
           'SKU_GATE_ACTUAL_FULL25_GROUPS')
    receipt.update(status='SKU_CUMULATIVE_ORIGINALS_VERIFIED', actual_case_credit=business_count,
                   retained_Native_cases=len(retained), covered_Native_cases=len(retained) + len(fresh), actual_all_five=True,
                   original_run=old_receipt, retained_native=retained, fresh_native=fresh,
                   fresh_browser_ids=sorted(browser), actual_full25=observed, scope=scope_pin,
                   mandor_root=shared[PARENT], mandor_cumulative_decision=shared[MANDOR_DECISION],
                   production_go=False, independent_acceptance=False, complete_global_input_review=False)
    if catalogue_equivalence is not None:
        receipt['catalogue_equivalence'] = catalogue_equivalence
    return receipt, raw


def load_inputs(directory):
    return [directory / 'canonical.zip', *(strict((directory / f'{name}.json').read_bytes())
            for name in ('run', 'job', 'artifact'))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'origin', 'current', 'output'):
        parser.add_argument('--' + name, type=Path, required=name in ('repo', 'origin'))
    args = parser.parse_args()
    if (args.current is None) != (args.output is None):
        parser.error('--current and --output must be provided together')
    scope, shared = source(args.repo)
    origin = retained_origin(scope, *load_inputs(args.origin))
    if args.current is None:
        print(json.dumps(dict(status='RETAINED_E4EA_ORIGINAL_VERIFIED', original=origin[0], retained=len(origin[2]))))
        return
    receipt, catalogue_raw = current_result(scope, shared, origin, terminal(CURRENT, *load_inputs(args.current)))
    args.output.mkdir()
    (args.output / 'SKU_CUMULATIVE_TERMINAL_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if catalogue_raw is not None:
        (args.output / CATALOGUE).write_bytes(catalogue_raw)
    print(json.dumps({key: receipt[key] for key in ('status', 'run_id', 'conclusion', 'actual_case_credit')}))


if __name__ == '__main__':
    main()
