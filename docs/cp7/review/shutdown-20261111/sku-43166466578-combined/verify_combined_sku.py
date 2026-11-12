"""Verify the terminal SKU candidate and its scoped cumulative Native evidence."""

import argparse
import json
from pathlib import Path

from prepare_combined_sku_scope import CONTRACT, install_failure
from verify_focused_sku import (
    CURRENT, MANDOR_DECISION, PLAN, SCOPE, current_result, git, load_inputs,
    retained_origin, source, terminal,
)
from verify_terminal_sku import AREA, BACKUP, BROWSER, CATALOGUE, GATE, MAIN, NATIVE, PACKAGE, PARENT, PREFLIGHT, SUPERVISOR, fields, pin, require, strict
from reviewed_sku_source import verify_cumulative_mandor


CANDIDATE = dict(id=43166466578, job_id=131009386319,
                 head_sha='af6e5710c0a3265daeb14c8ccd078ea82c99c482',
                 tree='41aa56dc3247e7a802e8b2f48d55e15ff933954b')
SCOPE_PIN = dict(bytes=21621, sha256='f99119c78a886f98045cc99599c8885c0b40d1414359ee493dfc219bcc306161')
STATUS = 'CURRENT_MANDOR_PARENT_MONEY_AUTOMATIC_FRESH13_BROWSER2_AND_ALL5_PASS'
REVIEWED_DELTA = {AREA + name for name in (
    'E4EA_CONTINUATION_SCOPE.json', 'SOURCE.json', 'assembly.py', 'component.py',
    'context_timezone.py', 'continuation.py', 'cost_source_timezone.py', 'final_gate.py',
    'native_preflight.py', 'package.py', 'test_final_gate.py', 'test_runtime_receipt.py',
)}


def source_review(repo):
    prior, shared = source(repo)
    head = CANDIDATE['head_sha']
    require(git(repo, 'rev-parse', head + '^{tree}').decode().strip() == CANDIDATE['tree'],
            'SKU_COMBINED_EXACT_OWNING_TREE_REQUIRED')
    names = set(git(repo, 'diff', '--no-renames', '--name-only', CURRENT['head_sha'], head, '--').decode().splitlines())
    require(names == REVIEWED_DELTA, 'SKU_COMBINED_EXACT_REVIEWED_TWELVE_PATHS_REQUIRED')
    raw = git(repo, 'show', head + ':' + SCOPE)
    require(pin(raw) == SCOPE_PIN, 'SKU_COMBINED_EXACT_SCOPE_PIN_REQUIRED')
    scope = strict(raw)
    fields(scope, dict(contract=CONTRACT, origin=prior['origin'], planned_case_ids=prior['planned_case_ids'],
                       original_case_receipts=prior['original_case_receipts']), 'SKU_COMBINED_EXACT_ORIGIN_COVERAGE')
    expected = set(prior['fresh_case_ids']) | set(scope['non_po_affected_case_ids'])
    require(len(expected) == 13 and scope['fresh_case_ids'] == [case for case in scope['planned_case_ids'] if case in expected]
            and scope['retained_case_ids'] == [case for case in scope['planned_case_ids'] if case not in expected],
            'SKU_COMBINED_EXACT_FRESH_AND_RETAINED_SPLIT_REQUIRED')
    for name in (PARENT, PLAN, MANDOR_DECISION):
        require(pin(git(repo, 'show', head + ':' + name)) == shared[name], 'SKU_COMBINED_MANDOR_OR_PLAN_CHANGED:' + name)
    return scope, shared


def root(receipt, reports, pins):
    originals = {name: {key: pins[name][key] for key in ('bytes', 'sha256')}
                 for name in (MAIN, NATIVE, PREFLIGHT, BROWSER, GATE, PACKAGE, BACKUP, SUPERVISOR, CATALOGUE)}
    return dict(status='ROOT_VERIFIED_CURRENT_SKU_CUMULATIVE_NATIVE25_BROWSER2_ALL5',
                **{key: receipt[key] for key in ('head', 'tree', 'run_id', 'job_id', 'attempt', 'artifact_id', 'archive',
                    'mandor_root', 'mandor_cumulative_decision', 'scope', 'retained_native', 'fresh_native', 'fresh_browser_ids')},
                originals=originals, prior_run=receipt['original_run'], prior_runs_aggregated=True,
                actual_Native_cases=13, retained_Native_cases=12, covered_Native_cases=25,
                actual_browser_cases=2, actual_Auth_HTTP_cases=0, actual_two_session_races=0,
                actual_business_cases=15, actual_outer_restore=True, package_all_five=True,
                mandor_evidence_mode='CUMULATIVE_15_PLUS_2',
                qualified_combined_SKU_sources=reports[MAIN]['source_declaration']['complete_combined_sources'],
                global_parent_catalogue=receipt['actual_full25'], complete_global_input_review=False,
                production_go=False, independent_acceptance=False)


def write_json(path, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    return pin(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'origin-source', 'origin', 'failed', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    scope, shared = source_review(args.repo)
    fields(scope, dict(intervening_install_failure=install_failure(load_inputs(args.failed))), 'SKU_COMBINED_EXACT_3F2A_FAILURE')
    origin = retained_origin(scope, *load_inputs(args.origin))
    mandor_raw = git(args.repo, 'show', CANDIDATE['head_sha'] + ':' + PARENT)
    mandor = verify_cumulative_mandor(args.origin_source, scope['origin']['head'], mandor_raw)
    require(mandor['decision'] == shared[MANDOR_DECISION], 'SKU_COMBINED_ACTUAL_MANDOR_17_REQUIRED')
    current = terminal(CANDIDATE, *load_inputs(args.candidate))
    receipt, raw = current_result(scope, shared, origin, current, scope_pin=SCOPE_PIN, expected_status=STATUS)
    args.output.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        with (args.output / CATALOGUE).open('xb') as stream:
            stream.write(raw)
        receipt['root_pin'] = write_json(args.output / 'SKU_COMBINED_ROOT.json', root(receipt, current[1], current[2]))
    write_json(args.output / 'SKU_COMBINED_TERMINAL_RECEIPT.json', receipt)
    print(json.dumps({key: receipt.get(key) for key in ('status', 'head', 'run_id', 'conclusion', 'actual_case_credit',
        'actual_outer_restore', 'first_reported_error', 'first_case_error', 'covered_Native_cases')}))


if __name__ == '__main__':
    main()
