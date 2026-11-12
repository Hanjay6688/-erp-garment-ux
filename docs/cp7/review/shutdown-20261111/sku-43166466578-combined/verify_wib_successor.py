"""Check the WIB correction, retained case evidence and the actual SKU catalogue."""

import argparse
import json
from pathlib import Path
import re
from zipfile import ZipFile

import verify_combined_sku as combined
import verify_cost_capture_successor as previous
from prepare_combined_sku_scope import install_failure
from verify_focused_sku import (
    MANDOR_DECISION, SCOPE, cases, current_result, git, load_inputs,
    restored, retained_origin, terminal,
)
from verify_terminal_sku import AREA, BACKUP, CATALOGUE, GATES, NATIVE, PACKAGE, PARENT, fields, pin, require, strict
from reviewed_sku_source import verify_cumulative_mandor


CANDIDATE = dict(id=43187520935, job_id=131078326983,
                 head_sha='ae0df1ef17b4d84478d50a2a144cf0382d662ad0',
                 tree='b8f534ba09226311c6eb83b967732dd7545db6ea')
AFTER_SCOPE_PIN = previous.SCOPE_PIN
DRIVER = AREA + 'continuation.py'
DRIVER_PIN = dict(bytes=4491, sha256='38800639c8cbf7bd5789380d7482b30e2037f77a5de8d44023a896647b81941c')
CHANGED = {AREA + name for name in ('SOURCE.json', 'continuation.py', 'test_runtime_receipt.py')}
WIB_ERROR = 'SKU_NON_PO_WIB_SESSION_REQUIRED'
WIB_FAILURE_ARCHIVE = dict(bytes=20962392, sha256='d2e642810bcc8424b48e685e2c498cff4e3db2edd4c279d9e588d033b938a535',
                           members=170)
WIB_DIAGNOSTIC_PIN = dict(bytes=16048295, sha256='7e1ba214f634afd822a7ef29e7a5731690aceb8d5afd7fb0f62f22fbd3ac0e55')
GUARD = 'cp7_credit.assert_source_native_trigger_census_v1()'
RUNTIME_LITERAL = re.compile(r"(?m)^ if actual_sha256 is distinct from '([0-9a-f]{64})'then$")


def source_review(repo):
    scope, shared = previous.source_review(repo)
    before, head = previous.CANDIDATE['head_sha'], CANDIDATE['head_sha']
    require(git(repo, 'rev-list', '--parents', '-n', '1', head).decode().split() == [head, before]
            and git(repo, 'rev-parse', head + '^{tree}').decode().strip() == CANDIDATE['tree'],
            'SKU_WIB_EXACT_PARENT_AND_TREE_REQUIRED')
    delta = set(git(repo, 'diff', '--no-renames', '--name-status', before, head, '--').decode().splitlines())
    require(delta == {'M\t' + path for path in CHANGED}, 'SKU_WIB_ONLY_DRIVER_TEST_AND_MANIFEST_CHANGED')
    require(pin(git(repo, 'show', head + ':' + SCOPE)) == AFTER_SCOPE_PIN
            and pin(git(repo, 'show', head + ':' + DRIVER)) == DRIVER_PIN,
            'SKU_WIB_EXACT_SCOPE_AND_DRIVER_REQUIRED')
    return scope, shared


def compare_catalogue(origin_raw, raw, scope, actual_groups):
    expected = scope['expected_fixed_catalogue_group_pins']
    require(set(actual_groups) == set(expected) and len(expected) == 25
            and [name for name in actual_groups if actual_groups[name] != expected[name]] == ['functions'],
            'SKU_ONLY_CREDIT_RUNTIME_SEAL_GROUP_MAY_DIFFER')
    original = dict(strict(origin_raw)['functions'])[GUARD]
    value = strict(raw)
    matches = [index for index, (sig, _) in enumerate(value['functions']) if sig == GUARD]
    require(len(matches) == 1, 'SKU_ONE_CREDIT_RUNTIME_SEAL_REQUIRED')
    index, = matches
    row = value['functions'][index][1]
    require(len(original) == len(row) == 19 and row[1:] == original[1:]
            and row[1] == 'postgres' and row[4] is True and row[12] == ['search_path=""', 'TimeZone=UTC'],
            'SKU_CREDIT_RUNTIME_SEAL_METADATA_CHANGED')
    original_token = RUNTIME_LITERAL.findall(original[0])
    actual_token = RUNTIME_LITERAL.findall(row[0])
    require(len(original_token) == len(actual_token) == 1 and actual_token != original_token,
            'SKU_EXACT_RUNTIME_SEAL_LITERAL_REQUIRED')
    restored_body, count = RUNTIME_LITERAL.subn(
        " if actual_sha256 is distinct from '" + original_token[0] + "'then", row[0])
    require(count == 1 and restored_body == original[0], 'SKU_CREDIT_RUNTIME_GUARD_BODY_CHANGED')
    value['functions'][index][1] = [restored_body, *row[1:]]
    normalized = pin(json.dumps(value['functions'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
    require(normalized == expected['functions'], 'SKU_OTHER_FUNCTIONS_DIFFER_FROM_REVIEWED_REPAIR')
    return dict(status='ALL25_EQUAL_EXCEPT_OW04_DATABASE_LOCAL_SEAL',
                actual_catalogue=pin(raw), original_guard_definition=pin(original[0].encode()),
                actual_guard_definition=pin(row[0].encode()), observed_runtime_literal=actual_token[0],
                reference_runtime_literal=original_token[0], normalized_functions=normalized,
                live_guard_verification_for_global_pending=True, production_go=False)


def case_failure(scope, directory, origin_raw):
    current = terminal(previous.CANDIDATE, *load_inputs(directory))
    receipt, reports, pins, rows, raw, _ = current
    fields(receipt, dict(conclusion='failure', artifact_id=13927899180, archive=WIB_FAILURE_ARCHIVE,
                         all_member_crc_verified=True), 'SKU_882F_EXACT_ORIGINAL')
    restored(receipt, reports, 1)
    require(reports[BACKUP]['data']['tables'] == 407 and reports[PACKAGE]['gate'] == dict(GATES, writer_runtime=False),
            'SKU_882F_PACKAGE_RESTORATION_REQUIRED')
    native = cases(reports[NATIVE], rows, pins, scope['fresh_case_ids'])
    errors = set(scope['non_po_affected_case_ids'])
    require(all(native[case]['status'] == ('INCOMPLETE' if case in errors else 'PASS') for case in native)
            and all(rows[case][1]['error'] == WIB_ERROR for case in errors),
            'SKU_882F_EXACT_FIVE_PASSES_EIGHT_SESSION_REFUSALS_REQUIRED')
    fields(receipt['first_case_error'], dict(case=scope['fresh_case_ids'][0], message=WIB_ERROR),
           'SKU_882F_FIRST_CASE_ERROR_REQUIRED')
    require(raw is not None and pin(raw) == WIB_DIAGNOSTIC_PIN, 'SKU_882F_EXACT_DIAGNOSTIC_CATALOGUE_REQUIRED')
    groups = {name: pin(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
              for name, value in strict(raw).items()}
    comparison = compare_catalogue(origin_raw, raw, scope, groups)
    return dict(receipt, actual_Native_pass=5, actual_Native_incomplete=8, actual_browser_cases=0,
                observed_native=native, diagnostic_catalogue_equivalence=comparison)


def verify(repo, origin_source, original, delimiter_failure, capture_failure, wib_failure, candidate, output):
    scope, shared = source_review(repo)
    fields(scope, dict(intervening_install_failure=install_failure(load_inputs(delimiter_failure))),
           'SKU_WIB_EXACT_DELIMITER_FAILURE')
    origins = load_inputs(original)
    origin = retained_origin(scope, *origins)
    with ZipFile(origins[0]) as bundle:
        origin_raw = bundle.read(CATALOGUE)
    require(pin(origin_raw) == dict(bytes=16048163, sha256='5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07'),
            'SKU_WIB_EXACT_E4EA_CATALOGUE_ORIGINAL_REQUIRED')
    af6 = previous.failed_capture(scope, shared, origin, capture_failure)
    failed = case_failure(scope, wib_failure, origin_raw)
    mandor_raw = git(repo, 'show', CANDIDATE['head_sha'] + ':' + PARENT)
    mandor = verify_cumulative_mandor(origin_source, scope['origin']['head'], mandor_raw)
    require(mandor['decision'] == shared[MANDOR_DECISION], 'SKU_WIB_ACTUAL_MANDOR_17_REQUIRED')
    current = terminal(CANDIDATE, *load_inputs(candidate))
    receipt, raw = current_result(scope, shared, origin, current, scope_pin=AFTER_SCOPE_PIN,
                                  expected_status=combined.STATUS,
                                  review_catalogue=lambda actual, scope, groups:
                                      compare_catalogue(origin_raw, actual, scope, groups))
    receipt['retained_install_failures'] = [scope['intervening_install_failure'], af6]
    receipt['retained_wib_case_failure'] = failed
    output.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        with (output / CATALOGUE).open('xb') as stream:
            stream.write(raw)
        root = combined.root(receipt, current[1], current[2])
        if 'catalogue_equivalence' in receipt:
            root['catalogue_equivalence'] = receipt['catalogue_equivalence']
        receipt['root_pin'] = combined.write_json(output / 'SKU_COMBINED_ROOT.json', root)
    combined.write_json(output / 'SKU_COMBINED_TERMINAL_RECEIPT.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'origin-source', 'original', 'delimiter-failure', 'capture-failure',
                 'wib-failure', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.repo, args.origin_source, args.original, args.delimiter_failure,
                    args.capture_failure, args.wib_failure, args.candidate, args.output)
    print(json.dumps({key: result.get(key) for key in (
        'status', 'run_id', 'conclusion', 'actual_case_credit', 'actual_outer_restore',
        'first_case_error', 'covered_Native_cases')}))


if __name__ == '__main__':
    main()
