"""Check Global authority against the scoped SKU successor before database setup."""

import argparse
import json
from pathlib import Path
from zipfile import ZipFile

from compare_sku_catalogue import checked_catalogue
from prepare_combined_sku_scope import FIXES
from prepare_non_po_followup import NEW, OLD, SIGNATURE
from review_native_authority import ROUTES, compare, load_source, references
from verify_cost_capture_successor import CANDIDATE, SCOPE_PIN, source_review
from verify_focused_sku import ORIGIN
from verify_terminal_sku import CATALOGUE, catalogue, fields, pin, require, strict


SETTING_BEFORE = " SET search_path TO ''\nAS $function$"
SETTING_AFTER = " SET search_path TO ''\n SET \"TimeZone\" TO 'UTC'\nAS $function$"
SOURCE_PINS = {
    'context_timezone.py': 'd5727277f393ca5bf673d9d5dfaf695af045945e285030d66ace2354b0217f44',
    'cost_source_timezone.py': '71e7eadb126f7128c06961f31df8b548b2bdf249779f19e97959f8511e59cc90',
}


def normalized(row, before, after, signature):
    require(len(row) == 19 and pin(row[0].encode())['sha256'] == before
            and row[0].count(SETTING_BEFORE) == 1 and row[1] == 'postgres' and row[4] is True
            and row[12] == ['search_path=""'] and row[18] == [['postgres', 'postgres', 'EXECUTE', False]],
            'GLOBAL_COMBINED_EXACT_PRIVATE_FUNCTION_PREIMAGE_REQUIRED:' + signature)
    definition = row[0].replace(SETTING_BEFORE, SETTING_AFTER, 1)
    require(pin(definition.encode())['sha256'] == after, 'GLOBAL_COMBINED_EXACT_FUNCTION_POSTIMAGE_REQUIRED:' + signature)
    return [definition, *row[1:12], row[12] + ['TimeZone=UTC'], *row[13:]]


def expected_references(checkout, origin):
    expected, reasons = references(checkout, origin)
    functions = expected['functions']
    before = {}
    for signature, (old, new) in FIXES.items():
        before[signature] = functions[signature]
        functions[signature] = normalized(functions[signature], old, new, signature)
        reasons[('functions', signature)].append('reviewed_automatic_context_timezone')
    profile, _ = load_source(checkout / ROUTES).prior.sources()
    before[SIGNATURE] = profile['groups']['functions'][SIGNATURE]
    require(SIGNATURE not in functions or functions[SIGNATURE] == before[SIGNATURE],
            'GLOBAL_COMBINED_CONFLICTING_CAPTURE_AUTHORITY')
    functions[SIGNATURE] = normalized(before[SIGNATURE], OLD['sha256'], NEW['sha256'], SIGNATURE)
    reasons.setdefault(('functions', SIGNATURE), []).append('reviewed_non_po_cost_capture_timezone')
    return expected, reasons, before


def actual_inputs(path, scope):
    raw = (path / CATALOGUE).read_bytes()
    root_raw = (path / 'SKU_COMBINED_ROOT.json').read_bytes()
    root = strict(root_raw)
    receipt = strict((path / 'SKU_COMBINED_TERMINAL_RECEIPT.json').read_bytes())
    identity = dict(head=CANDIDATE['head_sha'], tree=CANDIDATE['tree'], run_id=CANDIDATE['id'],
                    job_id=CANDIDATE['job_id'], attempt=1, scope=SCOPE_PIN)
    fields(receipt, dict(status='SKU_CUMULATIVE_ORIGINALS_VERIFIED', **identity, conclusion='success',
                         actual_case_credit=15, actual_all_five=True, actual_outer_restore=True,
                         actual_worker_reaped=True, all_member_crc_verified=True, cleanup=True, root_pin=pin(root_raw),
                         retained_install_failures=[scope['intervening_install_failure'],
                                                    scope['intervening_cost_capture_install_failure']]),
           'GLOBAL_COMBINED_VERIFIED_SKU_ORIGINAL_REQUIRED')
    fields(root, dict(status='ROOT_VERIFIED_CURRENT_SKU_CUMULATIVE_NATIVE25_BROWSER2_ALL5', **identity,
                      covered_Native_cases=25, actual_Native_cases=13, retained_Native_cases=12, actual_browser_cases=2,
                      actual_business_cases=15, prior_runs_aggregated=True, package_all_five=True,
                      actual_outer_restore=True, complete_global_input_review=False, production_go=False,
                      independent_acceptance=False, prior_run=receipt['original_run'],
                      retained_native=receipt['retained_native'], fresh_native=receipt['fresh_native'],
                      artifact_id=receipt['artifact_id'], archive=receipt['archive']), 'GLOBAL_COMBINED_SKU_ROOT_REQUIRED')
    require(set(root['fresh_native']) == set(scope['fresh_case_ids']) and
            set(root['retained_native']) == set(scope['retained_case_ids']) and
            root['prior_run']['head'] == ORIGIN['head_sha'] and root['prior_run']['run_id'] == ORIGIN['id'],
            'GLOBAL_COMBINED_EXACT_SCOPED_NATIVE_COVERAGE_REQUIRED')
    observation = root['global_parent_catalogue']
    require(observation == receipt['actual_full25'] and root['originals'][CATALOGUE] == pin(raw),
            'GLOBAL_COMBINED_CANONICAL_FULL25_REQUIRED')
    catalogue(raw, dict(status='ACTUAL_FULL25_SKU_CATALOGUE_OBSERVED', head=root['head'], run_id=str(root['run_id']),
                        attempt=1, original=observation['original'], readers=observation['exact_query_sources'],
                        fingerprint=observation['fingerprint'], actual_ERP_case_credit=0, complete_input_review=False,
                        production_go=False), root['head'], root['run_id'])
    return raw


def replay(raw, scope, expected, before):
    groups = strict(raw)
    changed = set()
    for index, (name, row) in enumerate(groups['functions']):
        if name in before:
            require(row == before[name], 'GLOBAL_COMBINED_DIAGNOSTIC_ORIGINAL_FUNCTION_DRIFT:' + name)
            groups['functions'][index] = [name, expected['functions'][name]]
            changed.add(name)
    require(changed == set(before), 'GLOBAL_COMBINED_EXACT_THREE_PROJECTED_FUNCTIONS_REQUIRED')
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    require({group: pin(encode(rows)) for group, rows in groups.items()} == scope['expected_fixed_catalogue_group_pins'],
            'GLOBAL_COMBINED_ALL25_PROJECTED_GROUPS_REQUIRED')
    return encode(groups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('global-checkout', 'origin-sku-checkout', 'repo', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--origin-archive', type=Path)
    mode.add_argument('--terminal', type=Path)
    args = parser.parse_args()
    from verify_focused_sku import AREA, git
    scope, _ = source_review(args.repo)
    for name, digest in SOURCE_PINS.items():
        raw = git(args.repo, 'show', CANDIDATE['head_sha'] + ':' + AREA + name)
        require(pin(raw)['sha256'] == digest, 'GLOBAL_COMBINED_EXACT_ADAPTER_REQUIRED:' + name)
    expected, reasons, before = expected_references(args.global_checkout, args.origin_sku_checkout)
    if args.origin_archive is not None:
        with ZipFile(args.origin_archive) as bundle:
            raw = bundle.read(CATALOGUE)
        require(pin(raw) == dict(bytes=16048163, sha256='5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07'),
                'GLOBAL_COMBINED_EXACT_E4EA_DIAGNOSTIC_CATALOGUE_REQUIRED')
        raw = replay(raw, scope, expected, before)
    else:
        raw = actual_inputs(args.terminal, scope)
    value = compare(checked_catalogue(raw), expected, reasons)
    value.update(status='GLOBAL_COMBINED_AUTHORITY_DIFFERENCES' if value['problems'] else 'GLOBAL_COMBINED_AUTHORITY_ROWS_MATCH',
                 reviewed_functions=list(before), candidate=CANDIDATE['head_sha'], catalogue=pin(raw),
                 actual_terminal_original=args.terminal is not None, actual_new_erp_cases=0,
                 complete_global_input_review=False, runtime_admission=False, production_go=False)
    with args.output.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value, separators=(',', ':')))
    return 1 if value['problems'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
