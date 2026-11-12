"""Prepare the next native case scope from verified SKU Originals and impact review."""

import argparse
import json
from pathlib import Path

from verify_focused_sku import CURRENT, ORIGIN, SCOPE_PIN, source
from verify_terminal_sku import CATALOGUE, fields, pin, require, strict


IMPACT_PIN = '255850a7c34687e46ca22544aed499b0a0b7364f095ba759ed8c226ac55b8552'
ADAPTER = 'scripts/current-sku-automatic-composite-preparation/cost_source_timezone.py'
ADAPTER_PIN = 'c747f1980099a1cf81e9ff5817dc54a56cc8be8b8d1978de4a8680e9dbe1b4bd'
SIGNATURE = 'cp7_sku_conversion.capture_cost_source_v3(uuid)'
OLD = dict(bytes=1556, sha256='d34b88ae943c49c5061d1c2116e9fc337dfbada17a81fcc5f5933fbe8627a02c')
NEW = dict(bytes=1581, sha256='44aba20d060d3a7eed11f7118c3cffa9289ec9306511e9ed3fb15ea8eaa28ae2')


def expected_catalogue(raw, observation):
    require(observation['original'] == dict(name=CATALOGUE, **pin(raw)), 'SKU_NON_PO_FOLLOWUP_ACTUAL_FULL25_REQUIRED')
    value = strict(raw)
    rows = value['functions']
    target = [i for i, (signature, _) in enumerate(rows) if signature == SIGNATURE]
    require(len(target) == 1 and len(value) == 25, 'SKU_NON_PO_FOLLOWUP_EXACT_FULL25_AND_FUNCTION_REQUIRED')
    index, = target
    signature, previous = rows[index]
    require(len(previous) == 19 and pin(previous[0].encode()) == OLD and previous[1] == 'postgres'
            and previous[4] is True and previous[12] == ['search_path=""']
            and previous[18] == [['postgres', 'postgres', 'EXECUTE', False]],
            'SKU_NON_PO_FOLLOWUP_EXACT_FUNCTION_PREIMAGE_REQUIRED')
    anchor = " SET search_path TO ''\nAS $function$"
    require(previous[0].count(anchor) == 1, 'SKU_NON_PO_FOLLOWUP_ONE_CONFIGURATION_ROUTE_REQUIRED')
    revised = list(previous)
    revised[0] = previous[0].replace(anchor, " SET search_path TO ''\n SET \"TimeZone\" TO 'UTC'\nAS $function$", 1)
    require(pin(revised[0].encode()) == NEW, 'SKU_NON_PO_FOLLOWUP_EXACT_POSTIMAGE_REQUIRED')
    revised[12] = previous[12] + ['TimeZone=UTC']
    rows[index] = [signature, revised]
    return {name: pin(json.dumps(group, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
            for name, group in value.items()}


def prepare(sku_scope, receipt, impact_raw, catalogue_raw, adapter_raw):
    fields(receipt, dict(status='SKU_CUMULATIVE_ORIGINALS_VERIFIED', head=CURRENT['head_sha'],
                        tree=CURRENT['tree'], run_id=CURRENT['id'], job_id=CURRENT['job_id'],
                        attempt=1, conclusion='success', actual_case_credit=7, retained_Native_cases=20,
                        covered_Native_cases=25, actual_outer_restore=True, actual_worker_reaped=True,
                        actual_all_five=True, cleanup=True, all_member_crc_verified=True, scope=SCOPE_PIN),
           'SKU_NON_PO_FOLLOWUP_REQUIRES_VERIFIED_3F2A_ORIGINAL')
    old = receipt['original_run']
    fields(old, dict(head=ORIGIN['head_sha'], run_id=ORIGIN['id'], job_id=ORIGIN['job_id'],
                     conclusion='failure', actual_outer_restore=True), 'SKU_NON_PO_FOLLOWUP_E4EA_PROVENANCE')
    require(pin(impact_raw)['sha256'] == IMPACT_PIN and pin(adapter_raw)['sha256'] == ADAPTER_PIN,
            'SKU_NON_PO_FOLLOWUP_EXACT_REVIEW_AND_PATCH_REQUIRED')
    impact = strict(impact_raw)['impacted_old_sku_passes']
    retained, fresh = receipt['retained_native'], receipt['fresh_native']
    order = sku_scope['planned_case_ids']
    require(set(retained) == set(sku_scope['retained_case_ids']) and set(fresh) == set(sku_scope['fresh_case_ids'])
            and len(impact) == len(set(impact)) == 8 and set(impact) <= set(retained),
            'SKU_NON_PO_FOLLOWUP_EXACT_EIGHT_AFFECTED_CASES_REQUIRED')
    require(all(retained[name] == sku_scope['original_case_receipts'][name] for name in retained)
            and all(item['status'] == 'PASS' for item in (retained | fresh).values()),
            'SKU_NON_PO_FOLLOWUP_ONLY_VERIFIED_NATIVE_CASES_REQUIRED')
    kept = [name for name in order if name not in impact]
    originals = {name: dict((retained | fresh)[name], run_id=ORIGIN['id'] if name in retained else CURRENT['id'])
                 for name in order}
    return dict(contract='cp7.sku.non-po-timezone-followup-source-scope.v1', planned_case_ids=order,
                fresh_case_ids=[name for name in order if name in impact], retained_case_ids=kept,
                caller_timezone='Asia/Jakarta', original_case_receipts=originals,
                browser_original_run=CURRENT['id'], browser_case_ids=receipt['fresh_browser_ids'],
                browser_source_impact_review_required=True,
                prior_evidence={str(row['run_id']): {key: row[key] for key in ('head', 'tree', 'run_id', 'job_id',
                    'conclusion', 'artifact_id', 'archive', 'actual_outer_restore')} for row in (old, receipt)},
                expected_fixed_catalogue_group_pins=expected_catalogue(catalogue_raw, receipt['actual_full25']),
                source_adapter=dict(path=ADAPTER, **pin(adapter_raw)), source_impact_review=pin(impact_raw),
                actual_new_erp_cases=0, runtime_admitted=False, production_go=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('repo', 'receipt', 'impact', 'catalogue', 'adapter', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    scope, _ = source(args.repo)
    value = prepare(scope, strict(args.receipt.read_bytes()), args.impact.read_bytes(),
                    args.catalogue.read_bytes(), args.adapter.read_bytes())
    with args.output.open('x') as out:
        out.write(json.dumps(value, indent=2) + '\n')
    print(json.dumps(dict(fresh_native=len(value['fresh_case_ids']), retained_native=len(value['retained_case_ids']),
                          catalogue_groups=len(value['expected_fixed_catalogue_group_pins']))))


if __name__ == '__main__':
    main()
