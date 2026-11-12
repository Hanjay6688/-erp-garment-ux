"""Read the exact SKU sequence successor's canonical terminal archive."""

import argparse
from datetime import datetime, timedelta
import json
from math import isfinite
from pathlib import Path
from zipfile import ZipFile
from zoneinfo import ZoneInfo

from verify_ae0d_native import AUDIT, original_cases
from verify_combined_sku import STATUS, root, write_json
from verify_focused_sku import (
    BACKUP_CHECKS, MANDOR_DECISION, OWNING_STEP, cases, current_result, git, load_inputs,
    retained_origin, terminal,
)
from verify_terminal_sku import (
    AREA, BACKUP, BOUNDARY, BROWSER, CASE, CATALOGUE, MAIN, NATIVE, PACKAGE, PARENT,
    SUPERVISOR, WORKFLOW, fields, pin, require,
)
from verify_wib_successor import (
    AFTER_SCOPE_PIN, CANDIDATE as PRIOR, compare_catalogue, source_review as prior_source_review,
)
from reviewed_sku_source import verify_cumulative_mandor


CANDIDATE = dict(id=43211990138, job_id=131161671229,
                 head_sha='beda75853d9cb698ec912639002b3e4bd1ec52cf',
                 tree='108f843ddaa96571436e7f54f8cd9770612ae6cd')
MODIFIED = (WORKFLOW, *(AREA + name for name in (
    'SOURCE.json', 'component.py', 'execution.py', 'run_window.py', 'runtime_receipt.py',
    'sku-current-parent-money-automatic-native25-83.workflow.yml.txt', 'test_native25.py',
    'test_run_window.py', 'test_runtime_receipt.py', 'workflow.py',
)))
ADDED = (AREA + 'setup_sequences.py', AREA + 'test_setup_sequences.py')
WIB = ZoneInfo('Asia/Jakarta')


def source_review(repo):
    scope, shared = prior_source_review(repo)
    head = CANDIDATE['head_sha']
    prior = PRIOR['head_sha']
    require(git(repo, 'rev-parse', head + '^{tree}').decode().strip() == CANDIDATE['tree'],
            'SKU_BEDA_EXACT_TREE')
    require(git(repo, 'rev-list', '--parents', '-n', '1', head).decode().split() == [head, prior],
            'SKU_BEDA_EXACT_PARENT')
    names = set(git(repo, 'diff', '--no-renames', '--name-status', prior, head, '--').decode().splitlines())
    require(names == {'M\t' + name for name in MODIFIED} | {'A\t' + name for name in ADDED},
            'SKU_BEDA_EXACT_SEQUENCE_WINDOW_AND_SUPERVISOR_DELTA')
    return scope, shared


def checked_setup(part):
    setup = part['native_fixture_seed_sequence_prefix']
    require(setup.get('status') == 'SEED_ALLOCATIONS_VERIFIED', 'SKU_BEDA_ACTUAL_FIXTURE_SEED_REQUIRED')
    change = setup['prefix']
    group = part['all22_rows_and_sequence_prefix']
    fields(group, dict(all22_equal=True, all_current_table_rows_equal=True), 'SKU_BEDA_ALL_GROUP_ROWS_RESTORED')
    sequence = group['sequence_prefix']
    before, after = change['before'], change['after']
    require(before == sequence['before'] == setup['observed_before'] and after == setup['observed_after']
            and len(before) == 15 and set(before) == set(after) == set(sequence['after'])
            and {key for key in before if before[key] != after[key]} == {AUDIT},
            'SKU_BEDA_ONLY_SETUP_AUDIT_SEQUENCE_MOVED')
    value, is_called = before[AUDIT]
    end, called_after = after[AUDIT]
    require(type(value) is str and value.isdecimal() and type(end) is str and end.isdecimal()
            and type(is_called) is bool and called_after is True, 'SKU_BEDA_TYPED_AUDIT_SEQUENCE_STATE')
    start, last = int(value) + int(is_called), int(end)
    allocations = setup['audit_row_ids']
    require(0 < start <= last and last - start + 1 <= 100001
            and allocations == [str(number) for number in range(start, last + 1)]
            and setup['audit_allocation_count'] == len(allocations),
            'SKU_BEDA_EVERY_SETUP_AUDIT_ID_ACCOUNTED_FOR')
    fields(change, dict(changed={AUDIT: dict(before=before[AUDIT], after=after[AUDIT],
                                            last_value_delta=str(last - int(value)))},
                        all_current_sequences_recorded=True, per_case_sequence_restore_claim=False),
           'SKU_BEDA_EXACT_SETUP_TRANSITION')
    native = part['native']
    expected = after
    for case in native['planned_case_ids']:
        observed = native['cases'][case]['complete_case_sequence_prefix']
        require(observed['before'] == expected and set(observed['after']) == set(before),
                'SKU_BEDA_UNATTRIBUTED_SEQUENCE_BEFORE_CASE:' + case)
        expected = observed['after']
    require(expected == sequence['after'], 'SKU_BEDA_UNATTRIBUTED_SEQUENCE_AFTER_CASES')
    return dict(verified_audit_allocations=len(allocations), first_id=allocations[0], last_id=allocations[-1],
                native_cases=len(native['planned_case_ids']), all_15_sequences_accounted_for=True)


def checked_window(run, job, supervisor):
    started = datetime.fromisoformat(run['run_started_at']).astimezone(WIB)
    finished = datetime.fromisoformat(job['completed_at']).astimezone(WIB)
    midnight = (started + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    work_step, = [row for row in job['steps'] if row['name'] == OWNING_STEP]
    work_started = datetime.fromisoformat(work_step['started_at']).astimezone(WIB)
    require(started <= work_started < finished < midnight,
            'SKU_BEDA_SAME_WIB_DAY_FOR_SETUP_RUNTIME_AND_RESTORE')
    window = supervisor['wib_window']
    fields(window, dict(mode='SHORT_WIB_WINDOW', business_day=started.date().isoformat(),
                        recovery_reserve_seconds=1200, artifact_reserve_seconds=600,
                        termination_buffer_seconds=35, setup_reserve_seconds=1800,
                        automatic_group_retry=False, product_clock_changed=False),
           'SKU_BEDA_ACTUAL_WIB_RESERVES_REQUIRED')
    worker, available, midnight_seconds, elapsed = (
        window['effective_worker_seconds'], window['work_seconds_remaining'],
        window['seconds_to_midnight'], supervisor['elapsed_seconds'])
    require(all(type(value) in (int, float) and isfinite(value)
                for value in (worker, available, midnight_seconds, elapsed, window['work_cutoff_monotonic']))
            and 0 < elapsed < worker <= available - 1 <= 19800
            and available <= midnight_seconds - 1835 + 0.001
            and midnight_seconds <= (midnight - work_started).total_seconds() + 1,
            'SKU_BEDA_EFFECTIVE_RUNTIME_MUST_FIT_ACTUAL_WIB_WINDOW')
    return dict(window, actual_worker_elapsed_seconds=elapsed, job_completed_wib=finished.isoformat())


def failure_observations(scope, result, archive):
    receipt, reports, pins, rows, _, _ = result
    observation = dict(disposable_database_cleanup=receipt['cleanup'])
    if MAIN in reports:
        observation['first_main_error'] = (reports[MAIN].get('error') or '').splitlines()[:1]
        observation['restore_boundaries'] = {name: reports[MAIN].get(name) for name in BOUNDARY}
    if BACKUP in reports:
        backup = reports[BACKUP]
        data = backup.get('data', {})
        observation['backup_restore'] = dict(status=backup.get('status'), checks=backup.get('checks'),
            row_diff=data.get('differ'), restored_table_count=data.get('tables'))
        observation['full_database_restore_verified'] = (
            backup.get('status') == 'RESTORED_IDENTICAL' and backup.get('checks') == BACKUP_CHECKS
            and data.get('differ') == {}
            and all(value is True for value in observation.get('restore_boundaries', {}).values())
            and MAIN in reports)
    if SUPERVISOR in reports:
        supervisor = reports[SUPERVISOR]
        observation['worker'] = {name: supervisor.get(name) for name in (
            'status', 'worker_exit', 'deadline_reached', 'external_signal', 'process_group_empty',
            'process_tree_empty', 'orphaned_child', 'wib_window')}
    if PACKAGE in reports:
        observation['package_gate'] = reports[PACKAGE].get('gate')
    if BROWSER in reports:
        observation['browser_original'] = {key: pins[BROWSER][key] for key in ('bytes', 'sha256')}
        observation['browser_case_observations'] = {name: row.get('status')
            for name, row in reports[BROWSER].get('cases', {}).items()}
    if NATIVE in reports and reports[NATIVE].get('status') == 'PASS':
        try:
            observations = cases(reports[NATIVE], rows, pins, scope['fresh_case_ids'])
            observation['native_original_observations'] = original_cases(archive, reports[NATIVE], observations)
        except (KeyError, ValueError) as error:
            observation['native_original_review_failure'] = str(error)
    return observation


def verify(repo, origin_source, e4ea, current, output):
    scope, shared = source_review(repo)
    e4ea_inputs, current_inputs = load_inputs(e4ea), load_inputs(current)
    origin = retained_origin(scope, *e4ea_inputs)
    with ZipFile(e4ea_inputs[0]) as bundle:
        old_catalogue = bundle.read(CATALOGUE)
    parent = git(repo, 'show', CANDIDATE['head_sha'] + ':' + PARENT)
    mandor = verify_cumulative_mandor(origin_source, scope['origin']['head'], parent)
    require(mandor['decision'] == shared[MANDOR_DECISION], 'SKU_BEDA_ACTUAL_MANDOR_17_REQUIRED')
    result = terminal(CANDIDATE, *current_inputs)
    output.mkdir(parents=True, exist_ok=True)
    if result[0]['conclusion'] != 'success':
        observation = failure_observations(scope, result, current_inputs[0])
        receipt = dict(result[0], status='SKU_FOCUSED_ORIGINAL_FAILURE_RETAINED', actual_case_credit=0,
                       actual_outer_restore=observation.get('full_database_restore_verified'),
                       terminal_failure_observations=observation)
        write_json(output / 'SKU_COMBINED_TERMINAL_RECEIPT.json', receipt)
        return receipt
    receipt, raw = current_result(scope, shared, origin, result, scope_pin=AFTER_SCOPE_PIN,
                                  expected_status=STATUS, review_catalogue=lambda data, scope, groups:
                                  compare_catalogue(old_catalogue, data, scope, groups))
    reports = result[1]
    main = reports[MAIN]
    part = main['committed'][CASE]
    fields(main, dict(used_guard_refused_before_DDL=True), 'SKU_BEDA_ACTUAL_COMMITTED_USED_INVERSE')
    fields(part, dict(used_guard_refused_before_DDL=True), 'SKU_BEDA_COMMITTED_USED_INVERSE_ORIGINAL')
    require(raw is not None and reports[BACKUP]['data']['tables'] == 407, 'SKU_BEDA_FULL_RESTORE_AND_CATALOGUE')
    receipt['fixture_setup'] = checked_setup(part)
    receipt['actual_window'] = checked_window(current_inputs[1], current_inputs[2], reports[SUPERVISOR])
    receipt['fresh_native'] = original_cases(current_inputs[0], reports[NATIVE], receipt['fresh_native'])
    with (output / CATALOGUE).open('xb') as stream:
        stream.write(raw)
    root_receipt = root(receipt, reports, result[2])
    root_receipt.update(fixture_setup=receipt['fixture_setup'], actual_window=receipt['actual_window'])
    if 'catalogue_equivalence' in receipt:
        root_receipt['catalogue_equivalence'] = receipt['catalogue_equivalence']
    receipt['root_pin'] = write_json(output / 'SKU_COMBINED_ROOT.json', root_receipt)
    write_json(output / 'SKU_COMBINED_TERMINAL_RECEIPT.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'origin-source', 'e4ea', 'current', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.repo, args.origin_source, args.e4ea, args.current, args.output)
    print(json.dumps({key: result.get(key) for key in (
        'run_id', 'conclusion', 'status', 'covered_Native_cases', 'actual_case_credit', 'actual_outer_restore')}))


if __name__ == '__main__':
    main()
