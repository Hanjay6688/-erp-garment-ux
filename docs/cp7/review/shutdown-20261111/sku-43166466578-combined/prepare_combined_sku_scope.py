"""Bind the next SKU scope to both terminal Originals and the reviewed SQL changes."""

import argparse
import json
from pathlib import Path

from prepare_non_po_followup import ADAPTER, ADAPTER_PIN, IMPACT_PIN, expected_catalogue
from verify_focused_sku import (
    CURRENT, ORIGIN, load_inputs, restored, retained_origin, source, terminal,
)
from verify_terminal_sku import BACKUP, CASE, MAIN, PACKAGE, catalogue, fields, pin, require, strict


CONTRACT = 'cp7.sku.e4ea-combined-timezone-scope.v1'
INSTALL_FAILURE = 'syntax error at or near "$"'
ORIGINAL_3F2A = dict(bytes=1731575, sha256='8614e42069a7a14b9e2fd3a79b08598d9d4c6207c44b5f72c0f03459d8dff1d1', members=137)
FIXES = {
    'cp7_sku_conversion.automatic_valid_v5()': (
        'fe1afe2958c0582d3d858f7d567af3f1dc619cc97af92137527fe41665cab502',
        'c7366933a6bcf9b70859e28fd625fbe5988b28cb49f4c5febdeef4c8e3080db8'),
    'cp7_sku_conversion.automatic_enter_v5(uuid,text,uuid)': (
        '114ea066e9db7ff770b733f65f8087fafe3703a18aa39089b84df564eebe8cdc',
        '37c945673bcb5fc3643d6bdaf0f7f9bae58c354bcc7f077ed78bff6fc29921a9'),
}


def projection(raw, old_observation, reviewed):
    value = strict(raw)
    catalogue(raw, old_observation, ORIGIN['head_sha'], ORIGIN['id'])
    changed = set()
    before, after = " SET search_path TO ''\nAS $function$", " SET search_path TO ''\n SET \"TimeZone\" TO 'UTC'\nAS $function$"
    for index, (sig, row) in enumerate(value['functions']):
        if sig not in FIXES:
            continue
        prior, current = FIXES[sig]
        require(len(row) == 19 and pin(row[0].encode())['sha256'] == prior
                and row[12] == ['search_path=""'] and row[0].count(before) == 1,
                'SKU_COMBINED_EXACT_AUTOMATIC_PREIMAGE_REQUIRED:' + sig)
        definition = row[0].replace(before, after, 1)
        require(pin(definition.encode())['sha256'] == current, 'SKU_COMBINED_AUTOMATIC_POSTIMAGE_CHANGED:' + sig)
        value['functions'][index] = [sig, [definition, *row[1:12], row[12] + ['TimeZone=UTC'], *row[13:]]]
        changed.add(sig)
    require(changed == set(FIXES), 'SKU_COMBINED_EXACT_TWO_AUTOMATIC_FUNCTIONS_REQUIRED')
    encode = lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    prior_groups = {name: pin(encode(group)) for name, group in value.items()}
    require(prior_groups == reviewed, 'SKU_COMBINED_MATCH_EXISTING_TWO_FUNCTION_PROJECTION_REQUIRED')
    projected = encode(value)
    return expected_catalogue(projected, dict(original=dict(name=old_observation['original']['name'], **pin(projected))))


def install_failure(inputs):
    receipt, reports, _, cases, raw, _ = terminal(CURRENT, *inputs)
    fields(receipt, dict(conclusion='failure', artifact_id=13919701197, archive=ORIGINAL_3F2A,
                         all_member_crc_verified=True, first_case_error=None), 'SKU_3F2A_EXACT_TERMINAL_FAILURE')
    fields(reports[MAIN], dict(status='INCOMPLETE', installation_failed_before_commit=True,
                              observed_case_count=0, committed={}, native={}, real_Auth_browser_claim=False),
           'SKU_3F2A_FAILED_BEFORE_CASES')
    first_error = reports[MAIN]['error'].splitlines()[0]
    require(not cases and raw is None and first_error == INSTALL_FAILURE, 'SKU_3F2A_EXACT_INSTALL_ERROR_REQUIRED')
    restored(receipt, reports, 1)
    return dict(receipt, first_error=first_error, actual_Native_cases=0, actual_browser_cases=0,
                package=reports[PACKAGE]['gate'], backup_tables=reports[BACKUP]['data']['tables'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('repo', 'origin', 'failed', 'impact', 'adapter', 'ddl-reproduction', 'scope', 'receipt'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    scope, _ = source(args.repo)
    origin = load_inputs(args.origin)
    old, _, retained = retained_origin(scope, *origin)
    _, reports, _, _, raw, _ = terminal(ORIGIN, *origin)
    failed = install_failure(load_inputs(args.failed))
    impact_raw, adapter_raw, ddl_raw = (path.read_bytes() for path in (args.impact, args.adapter, args.ddl_reproduction))
    require(pin(impact_raw)['sha256'] == IMPACT_PIN and pin(adapter_raw)['sha256'] == ADAPTER_PIN,
            'SKU_COMBINED_EXACT_NON_PO_PATCH_AND_IMPACT_REQUIRED')
    fields(strict(ddl_raw), dict(status='EXACT_AUTOMATIC_OWNING_DDL_INSTALLS_IN_POSTGRESQL_17_6',
                                 actual_ERP_cases=0, restored=True, prior_first_error=INSTALL_FAILURE + ' at character 6447'),
           'SKU_COMBINED_EXACT_INSTALL_REPRODUCTION')
    affected = strict(impact_raw)['impacted_old_sku_passes']
    require(len(affected) == len(set(affected)) == 8 and set(affected) <= set(retained),
            'SKU_COMBINED_EXACT_EIGHT_PREVIOUSLY_PASSING_CASES_REQUIRED')
    planned = scope['planned_case_ids']
    fresh = set(scope['fresh_case_ids']) | set(affected)
    expected = projection(raw, reports[MAIN]['committed'][CASE]['Global_parent_catalogue'],
                          scope['expected_fixed_catalogue_group_pins'])
    combined = dict(scope, contract=CONTRACT, caller_timezone='Asia/Jakarta',
                    fresh_case_ids=[case for case in planned if case in fresh],
                    retained_case_ids=[case for case in planned if case not in fresh],
                    non_po_affected_case_ids=affected, expected_fixed_catalogue_group_pins=expected,
                    intervening_install_failure=failed,
                    non_po_scope=pin(impact_raw), non_po_source=dict(path=ADAPTER, **pin(adapter_raw)),
                    exact_ddl_reproduction=pin(ddl_raw))
    for path, item in ((args.scope, combined), (args.receipt, failed)):
        with path.open('x') as stream:
            stream.write(json.dumps(item, indent=2) + '\n')
    print(json.dumps(dict(fresh_native=len(fresh), retained_native=len(planned) - len(fresh),
                          fresh_browser=2, restored=failed['actual_outer_restore'], original_run=old['run_id'],
                          catalogue_groups=len(expected), scope=pin(args.scope.read_bytes()))))


if __name__ == '__main__':
    main()
