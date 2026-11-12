"""Verify the cost capture successor and preserve both intervening failures."""

import argparse
import json
from pathlib import Path

import verify_combined_sku as combined
from prepare_combined_sku_scope import install_failure
from verify_focused_sku import MANDOR_DECISION, SCOPE, current_result, git, load_inputs, retained_origin, terminal
from verify_terminal_sku import AREA, BACKUP, CATALOGUE, MAIN, PARENT, SUPERVISOR, fields, pin, require, strict
from reviewed_sku_source import verify_cumulative_mandor


CANDIDATE = dict(id=43174323175, job_id=131034780958,
                 head_sha='882fdd376387f66e607cce62152eba9732654211',
                 tree='f73ca6844d8a7facda5fc8526a43da697d72417a')
SCOPE_PIN = dict(bytes=22999, sha256='91a74eeda82feace3cfdc27488841306edb05ff40311c38cda6201af7215a760')
REPLAY_PIN = dict(bytes=1353, sha256='0f28a8a592cbb9f34540a25d1162b5e53f74d1c7ff9d244be22105bf33cb1518')
CHANGED = {AREA + name for name in (
    'E4EA_CONTINUATION_SCOPE.json', 'SOURCE.json', 'continuation.py',
    'cost_source_timezone.py', 'test_runtime_receipt.py',
)}
REVIEWED_SCOPE_CHANGES = {'non_po_source', 'intervening_cost_capture_install_failure',
                          'exact_final_cost_capture_ddl_reproduction'}
FAILURE = 'SKU_MONEY_EXACT_CATALOG_ADDITION_CHANGED:functions:cp7_sku_conversion.capture_cost_source_v3(uuid)'


def source_review(repo):
    prior, shared = combined.source_review(repo)
    head, previous = CANDIDATE['head_sha'], combined.CANDIDATE['head_sha']
    require(git(repo, 'rev-list', '--parents', '-n', '1', head).decode().split() == [head, previous]
            and git(repo, 'rev-parse', head + '^{tree}').decode().strip() == CANDIDATE['tree'],
            'SKU_COST_CAPTURE_EXACT_PARENT_AND_TREE_REQUIRED')
    changes = set(git(repo, 'diff', '--no-renames', '--name-status', previous, head, '--').decode().splitlines())
    require(changes == {'M\t' + path for path in CHANGED}, 'SKU_COST_CAPTURE_EXACT_FIVE_SOURCE_MODIFICATIONS')
    raw = git(repo, 'show', head + ':' + SCOPE)
    require(pin(raw) == SCOPE_PIN, 'SKU_COST_CAPTURE_EXACT_SCOPE_PIN_REQUIRED')
    scope = strict(raw)
    require(set(scope) == set(prior) | REVIEWED_SCOPE_CHANGES
            and all(scope[key] == value for key, value in prior.items() if key not in REVIEWED_SCOPE_CHANGES),
            'SKU_COST_CAPTURE_ONLY_REVIEWED_SCOPE_METADATA_CHANGED')
    source_path = AREA + 'cost_source_timezone.py'
    fields(scope, dict(non_po_source=dict(path=source_path, **pin(git(repo, 'show', head + ':' + source_path))),
                       exact_final_cost_capture_ddl_reproduction=REPLAY_PIN),
           'SKU_COST_CAPTURE_EXACT_ADAPTER_AND_REPRODUCTION')
    return scope, shared


def failed_capture(scope, shared, origin, directory):
    current = terminal(combined.CANDIDATE, *load_inputs(directory))
    reports = current[1]
    fields(reports[MAIN], dict(status='INCOMPLETE', observed_case_count=0, committed={}, native={},
                              real_Auth_browser_claim=False),
           'SKU_AF6E_FAILED_BEFORE_CASES')
    require(not current[3] and reports[BACKUP]['data']['tables'] == 407
            and reports[SUPERVISOR]['worker_exit'] == 1, 'SKU_AF6E_ZERO_CASES_AND_COMPLETE_RESTORATION_REQUIRED')
    receipt, raw = current_result(scope, shared, origin, current, scope_pin=combined.SCOPE_PIN,
                                  expected_status=combined.STATUS)
    fields(receipt, dict(status='SKU_FOCUSED_ORIGINAL_FAILURE_RETAINED', actual_case_credit=0,
                         first_reported_error=[FAILURE], first_case_error=None,
                         actual_outer_restore=True, actual_worker_reaped=True),
           'SKU_AF6E_ORIGINAL_FAILURE_AND_RESTORATION_REQUIRED')
    require(raw is None, 'SKU_AF6E_UNQUALIFIED_CATALOGUE_MUST_BE_ABSENT')
    expected = scope['intervening_cost_capture_install_failure']
    fields(receipt, expected, 'SKU_AF6E_EXACT_BOUND_ORIGINAL_FAILURE')
    return expected


def verify(repo, origin_source, original, delimiter_failure, capture_failure, candidate, output):
    scope, shared = source_review(repo)
    fields(scope, dict(intervening_install_failure=install_failure(load_inputs(delimiter_failure))),
           'SKU_COST_CAPTURE_EXACT_3F2A_FAILURE')
    origin = retained_origin(scope, *load_inputs(original))
    af6e = failed_capture(scope, shared, origin, capture_failure)
    mandor_raw = git(repo, 'show', CANDIDATE['head_sha'] + ':' + PARENT)
    mandor = verify_cumulative_mandor(origin_source, scope['origin']['head'], mandor_raw)
    require(mandor['decision'] == shared[MANDOR_DECISION], 'SKU_COST_CAPTURE_ACTUAL_MANDOR_17_REQUIRED')
    current = terminal(CANDIDATE, *load_inputs(candidate))
    receipt, raw = current_result(scope, shared, origin, current, scope_pin=SCOPE_PIN,
                                  expected_status=combined.STATUS)
    receipt['retained_install_failures'] = [scope['intervening_install_failure'], af6e]
    output.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        with (output / CATALOGUE).open('xb') as stream:
            stream.write(raw)
        root = combined.root(receipt, current[1], current[2])
        receipt['root_pin'] = combined.write_json(output / 'SKU_COMBINED_ROOT.json', root)
    combined.write_json(output / 'SKU_COMBINED_TERMINAL_RECEIPT.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'origin-source', 'original', 'delimiter-failure', 'capture-failure', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    receipt = verify(args.repo, args.origin_source, args.original, args.delimiter_failure,
                     args.capture_failure, args.candidate, args.output)
    print(json.dumps({key: receipt.get(key) for key in (
        'status', 'head', 'run_id', 'conclusion', 'actual_case_credit', 'actual_outer_restore',
        'first_reported_error', 'first_case_error', 'covered_Native_cases')}))


if __name__ == '__main__':
    main()
