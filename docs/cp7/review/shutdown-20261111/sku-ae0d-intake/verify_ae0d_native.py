"""Verify reusable Native case observations from two original SKU archives."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile

from reviewed_sku_source import verify_cumulative_mandor
from verify_combined_sku import write_json
from verify_focused_sku import (
    BROWSER_IDS, MANDOR_DECISION, NATIVE_LOG_PREFIX, cases, git, load_inputs,
    restored, retained_origin, terminal,
)
from verify_terminal_sku import (
    BACKUP, BROWSER, CASE, CATALOGUE, GATE, GATES, MAIN, NATIVE, PACKAGE,
    PARENT, PREFLIGHT, catalogue, fields, pin, require, strict,
)
from verify_wib_successor import AFTER_SCOPE_PIN, CANDIDATE, compare_catalogue, source_review


ARCHIVE = dict(bytes=87993330, sha256='a47ee57b6a36cf68eaff78dc24aa30cbe5b07f1279502795c0b827f53fc43754',
               members=186)
AUDIT = 'sequence:erp.audit_logs_id_seq'
FROZEN_RECEIPT = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FROZEN_EXECUTION_RECEIPT.json'
FROZEN_PREFIX = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FROZEN_EXECUTION/qualified-sku-money/'
BROWSER_PREREQUISITES = 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER_PREREQUISITES.json'
FIRST_CASE = 'SKU_MONEY_NATIVE_LEGACY_PHYSICAL_OPENING_LATE_INVOICE_CURRENT_INVERSE'
FIRST_ERROR = str(('SKU_MONEY_UNATTRIBUTED_SEQUENCE_BEFORE_CASE', FIRST_CASE))


def original_cases(archive, report, observations):
    evidence = {}
    with ZipFile(archive) as bundle:
        frozen = strict(bundle.read(FROZEN_RECEIPT))['frozen']['qualified-sku-money']['files']
        for case, receipt in observations.items():
            row = report['cases'][case]
            lines = bundle.read(receipt['original']).splitlines()
            require(len(lines) == 1 and receipt['original'].startswith(NATIVE_LOG_PREFIX),
                    'SKU_NATIVE_SINGLE_COMPLETE_CASE_ORIGINAL:' + case)
            exact = strict(lines[0])
            require(exact == dict(row, group=NATIVE.removesuffix('.json'), case=case),
                    'SKU_NATIVE_ORIGINAL_CASE_BODY_CHANGED:' + case)
            day = row['business_day']
            require(day['planned'] == day['before'] == day['after'],
                    'SKU_NATIVE_ACTUAL_CASE_DAY_CHANGED:' + case)
            reference = row['complete_case_sequence_raw']
            path = PurePosixPath(reference['path'])
            require(path.parts[:2] == ('cp6-proof', 't3') and len(path.parts) == 3
                    and re.fullmatch('SKU27_SEQUENCE_PREFIX_' + case + r'_[a-f0-9]{32}\.json', path.name),
                    'SKU_NATIVE_EXACT_SEQUENCE_ORIGINAL_PATH:' + case)
            raw = bundle.read(FROZEN_PREFIX + path.name)
            require(pin(raw) == frozen[path.name] == {key: reference[key] for key in ('bytes', 'sha256')},
                    'SKU_NATIVE_EXACT_SEQUENCE_ORIGINAL_BYTES:' + case)
            prefix = row['complete_case_sequence_prefix']
            require(len(prefix['before']) == len(prefix['after']) == 15
                    and set(prefix['before']) == set(prefix['after']),
                    'SKU_NATIVE_COMPLETE_SEQUENCE_SET_REQUIRED:' + case)
            require(strict(raw) == dict(case_id=case, before=prefix['before'], after=prefix['after'],
                                        first_failure=None, observation_error=None,
                                        per_savepoint_sequence_restore_claim=False, full_restore_required=True),
                    'SKU_NATIVE_EXACT_SEQUENCE_OBSERVATION:' + case)
            evidence[case] = dict(receipt, business_day=day['planned'],
                                  sequence_original=dict(member=FROZEN_PREFIX + path.name, **pin(raw)))
            if 'caller_timezone' in row:
                evidence[case]['caller_timezone'] = row['caller_timezone']
    return evidence


def checked_chain(native, boundary):
    fields(boundary, dict(all22_equal=True, all_current_table_rows_equal=True), 'SKU_NATIVE_OUTER_GROUP_ROWS')
    whole = boundary['sequence_prefix']
    planned = native['planned_case_ids']
    require(planned[0] == FIRST_CASE, 'SKU_NATIVE_FIRST_CASE_CHANGED')
    first = native['cases'][FIRST_CASE]['complete_case_sequence_prefix']['before']
    require(set(first) == set(whole['before']) == set(whole['after']) and len(first) == 15,
            'SKU_NATIVE_OUTER_GROUP_COMPLETE_SEQUENCE_SET')
    gap = {name: dict(before=whole['before'][name], after=value) for name, value in first.items()
           if value != whole['before'][name]}
    require(gap == {AUDIT: dict(before=['1', False], after=['222', True])},
            'SKU_NATIVE_RECORDED_SEQUENCE_GAP_CHANGED')
    expected = first
    for case in planned:
        observed = native['cases'][case]['complete_case_sequence_prefix']
        require(observed['before'] == expected, 'SKU_NATIVE_CASE_SEQUENCE_CHAIN_BROKEN:' + case)
        expected = observed['after']
    require(expected == whole['after'], 'SKU_NATIVE_POST_GROUP_SEQUENCE_CHAIN_BROKEN')
    return dict(observed_pre_case_gap=gap, case_links=len(planned), last_case_matches_post_group=True,
                sequence_count=len(first), setup_attribution_required=True)


def fixture_match(previous, actual, scope):
    fields(actual, dict(status='PASS', errors=[], all_prerequisites_checked_before_first_case=True,
                       all22_rows_and_all_sequences_unchanged=True,
                       supplier_account_mappings=dict(AP_SUPPLIER=[[True, True]])),
           'SKU_NATIVE_EXACT_AE0D_PREFLIGHT')
    fields(actual, {key: previous[key] for key in ('automatic_functions', 'automatic_actors', 'natural_callers')},
           'SKU_NATIVE_FIXTURE_CALLERS_AND_AUTHORITY_CHANGED')
    old_money, money = previous['retained_money19'], actual['retained_money19']
    fields(money, {key: value for key, value in old_money.items() if key != 'observed_WIB'},
           'SKU_NATIVE_MONEY_FIXTURE_OR_BUSINESS_DAY_CHANGED')
    require(scope['caller_timezone'] == 'Asia/Jakarta', 'SKU_NATIVE_WIB_SCOPE_REQUIRED')


def clone_audit_anchor(bundle, native):
    initial = b"SELECT pg_catalog.setval('erp.audit_logs_id_seq', 1, false);"
    with bundle.open('CLONE_install.clone-erp.sql') as source:
        rows = [line.strip() for line in source if b"setval('erp.audit_logs_id_seq'" in line]
    require(rows == [initial], 'SKU_NATIVE_ORIGINAL_CLONE_AUDIT_SEQUENCE_CHANGED')
    first = native['cases'][native['planned_case_ids'][0]]['complete_case_sequence_prefix']['before']
    require(first[AUDIT] == ['222', True], 'SKU_NATIVE_ORIGINAL_FIRST_AUDIT_SEQUENCE_CHANGED')
    return dict(clone=['1', False], before_first_case=first[AUDIT])


def browser_preflight(repo, bundle):
    raw = bundle.read(BROWSER_PREREQUISITES)
    result = strict(raw)
    fields(result, dict(status='EXACT_BOTH_CHECKOUT_PACKAGES_AND_REAL_DESKTOP_MOBILE_BROWSER_READY',
                        phase='COMPLETE', candidate_disposable_build='PASS', candidate_browser_module_import='PASS',
                        actual_SQL_executed=0, actual_Auth_requests=0, actual_browser_case_credit=0,
                        production_go=False), 'SKU_EXACT_ARCHIVED_BROWSER_PREREQUISITES')
    head = CANDIDATE['head_sha']
    manifest = git(repo, 'show', head + ':package.json')
    lock = git(repo, 'show', head + ':package-lock.json')
    version = strict(lock)['packages']['node_modules/@playwright/test']['version']
    checkouts = ('auditor', 'writer')
    require(result['pins'] == [dict(checkout=name, package_manifest=pin(manifest), lockfile=pin(lock),
                                    playwright_version=version) for name in checkouts],
            'SKU_BROWSER_PREREQUISITES_EXACT_PACKAGE_AND_LOCK')
    observations = [dict(checkout=name, width=width, timezone=zone, external_requests=0, status='PASS')
                    for name in checkouts for width, zone in ((1440, 'Asia/Jakarta'), (390, 'America/Los_Angeles'))]
    require(result['observations'] == observations, 'SKU_BROWSER_PREREQUISITES_EXACT_VIEWPORTS_AND_TIMEZONES')
    return dict(original=dict(name=BROWSER_PREREQUISITES, **pin(raw)),
                candidate_build='PASS', candidate_browser_module_import='PASS',
                offline_browser_setup_observations=len(observations), actual_business_browser_cases=0)


def verify(repo, origin_source, e4ea, ae0d):
    scope, shared = source_review(repo)
    old_inputs, current_inputs = load_inputs(e4ea), load_inputs(ae0d)
    old, old_preflight, retained = retained_origin(scope, *old_inputs)
    current, reports, pins, rows, raw, _ = terminal(CANDIDATE, *current_inputs)
    fields(current, dict(conclusion='failure', artifact_id=13940756296, archive=ARCHIVE,
                        all_member_crc_verified=True, first_case_error=None), 'SKU_NATIVE_EXACT_AE0D_ORIGINAL')
    restored(current, reports, 1)
    require(reports[BACKUP]['data']['tables'] == 407
            and reports[PACKAGE]['gate'] == dict(GATES, writer_runtime=False)
            and BROWSER not in reports and GATE not in reports, 'SKU_NATIVE_EXACT_FOUR_GATES_AND_PENDING_BROWSER')
    native, main, preflight = (reports[name] for name in (NATIVE, MAIN, PREFLIGHT))
    fields(main, dict(status='INCOMPLETE', error=FIRST_ERROR, cp6_restored=True,
                     baseline_full22_all_rows_all_sequences_equal=True, advisor_gate=True),
           'SKU_NATIVE_EXACT_AE0D_FIRST_FAILURE_AND_RESTORE')
    fields(native, dict(status='PASS', counts={'PASS': 13}), 'SKU_NATIVE_ALL_THIRTEEN_OBSERVED_PASS')
    part = main['committed'][CASE]
    fields(part, dict(status='INCOMPLETE', native=native, native_prerequisites=preflight,
                     actual_Native_cases=0, actual_Auth_browser=False,
                     strict_group_originals=[dict(name=NATIVE, **{key: pins[NATIVE][key]
                                                                 for key in ('bytes', 'sha256')})]),
           'SKU_NATIVE_EXACT_COMPLETE_NESTED_REPORTS')
    fixture_match(old_preflight, preflight, scope)
    fresh = cases(native, rows, pins, scope['fresh_case_ids'])
    require(all(fresh[name]['status'] == 'PASS' for name in fresh)
            and len(retained) == 12 and len(fresh) == 13
            and not set(retained) & set(fresh)
            and set(retained) | set(fresh) == set(scope['planned_case_ids']), 'SKU_NATIVE_EXACT_DISJOINT_25_CASES')
    for name in scope['non_po_affected_case_ids']:
        fields(rows[name][1], dict(caller_timezone=scope['caller_timezone']), 'SKU_NATIVE_ACTUAL_WIB:' + name)
    fresh = original_cases(current_inputs[0], native, fresh)
    with ZipFile(old_inputs[0]) as bundle:
        old_native = strict(bundle.read(NATIVE))
        old_catalogue = bundle.read(CATALOGUE)
        old_anchor = clone_audit_anchor(bundle, old_native)
    with ZipFile(current_inputs[0]) as bundle:
        current_anchor = clone_audit_anchor(bundle, native)
        prerequisites = browser_preflight(repo, bundle)
    retained = original_cases(old_inputs[0], old_native, retained)
    sequence = checked_chain(native, part['all22_rows_and_sequence_prefix'])
    observed = catalogue(raw, part['Global_parent_catalogue'], current['head'], current['run_id'])
    groups = {key: pin(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
              for key, value in strict(raw).items()}
    equivalence = compare_catalogue(old_catalogue, raw, scope, groups)
    mandor_raw = git(repo, 'show', CANDIDATE['head_sha'] + ':' + PARENT)
    mandor = verify_cumulative_mandor(origin_source, scope['origin']['head'], mandor_raw)
    require(mandor['decision'] == shared[MANDOR_DECISION], 'SKU_NATIVE_ACTUAL_MANDOR_17_REQUIRED')
    return dict(status='SKU_NATIVE25_ORIGINAL_OBSERVATIONS_REVIEWED', source_scope=AFTER_SCOPE_PIN,
                original_e4ea=old, original_ae0d=current, retained_e4ea=retained, observed_ae0d=fresh,
                observed_native_passes=25, observed_browser_passes=0, qualification_credit=0,
                actual_first_failure=FIRST_ERROR, current_archive_restore_tables=407,
                native_sequence_review=dict(sequence, clone_audit_anchor_e4ea=old_anchor,
                                            clone_audit_anchor_ae0d=current_anchor),
                original_browser_prerequisites=prerequisites, actual_diagnostic_full25=observed,
                catalogue_equivalence=equivalence, mandor_root=shared[PARENT],
                mandor_cumulative_decision=shared[MANDOR_DECISION],
                pending=dict(setup_sequence_attribution=True, final_candidate_equivalence=True,
                             committed_used_inverse=True, browser_cases=sorted(BROWSER_IDS),
                             full_five_gates_and_outer_restore=True),
                global_admitted=False, production_go=False, independent_acceptance=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'origin-source', 'e4ea', 'ae0d', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.repo, args.origin_source, args.e4ea, args.ae0d)
    print(json.dumps(write_json(args.output, result)))


if __name__ == '__main__':
    main()
