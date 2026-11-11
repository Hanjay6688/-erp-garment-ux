"""Prioritize the Global review from the verified SKU catalogue, without granting admission."""
from pathlib import Path
import argparse
import json

from verify_terminal_sku import CATALOGUE, CATALOGUE_GROUPS, fields, pin, require, strict


HISTORICAL_CATALOGUE = dict(bytes=14755737, sha256='80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb')
PARSER_CACHE = dict(bytes=341039, sha256='d5cc550150de36a82abcea050f7a3a2fcc8ba47343d83b2fe738ff4a644be649')


def checked_catalogue(raw):
    groups = strict(raw)
    require(set(groups) == CATALOGUE_GROUPS, 'GLOBAL_EXACT_TWENTY_FIVE_CATALOGUE_GROUPS_REQUIRED')
    result = {}
    for group, rows in groups.items():
        require(type(rows) is list and all(type(row) is list and len(row) == 2 and type(row[0]) is str for row in rows),
                'GLOBAL_EXPECTED_KEYED_CATALOGUE_ROWS:' + group)
        result[group] = dict(rows)
        require(len(result[group]) == len(rows), 'GLOBAL_DUPLICATE_CATALOGUE_IDENTITY:' + group)
    return result


def exact_differences(before, current):
    changes = {}
    for name in sorted(CATALOGUE_GROUPS):
        left, right = before[name], current[name]
        changed = (key for key in left.keys() & right.keys()
                   if json.dumps(left[key], sort_keys=True) != json.dumps(right[key], sort_keys=True))
        changes[name] = dict(added=sorted(right.keys() - left.keys()), removed=sorted(left.keys() - right.keys()),
                             changed=sorted(changed))
    return changes


def reuse_candidates(functions, cache):
    reusable, requires_parse = [], []
    for key, row in sorted(functions.items()):
        require(type(row) is list and len(row) == 19 and type(row[0]) is str and type(row[2]) is str,
                'GLOBAL_FULL19_FUNCTION_ROW_REQUIRED:' + key)
        fact = cache.get(key)
        if fact and fact['definition'] == pin(row[0].encode()) and fact['language'] == row[2]:
            reusable.append(key)
        else:
            requires_parse.append(key)
    return dict(parser_facts_reusable=reusable, no_matching_cached_parser_fact=requires_parse)


def review(receipt_raw, root_raw, catalogue_raw, historic_raw, cache_raw):
    receipt, root = strict(receipt_raw), strict(root_raw)
    fields(root, dict(head='980c22890cda4ced9aaecfc37390da77d5718e00', tree='e49d13044d4304525c8a73da3fee3dfbc81cff51',
                      mandor_evidence_mode='CUMULATIVE_15_PLUS_2'),
           'GLOBAL_CURRENT_SKU_CUMULATIVE_PARENT_REQUIRED')
    fields(receipt, dict(status='SKU_TERMINAL_ORIGINAL_BYTES_VERIFIED', conclusion='success', attempt=1,
                         root_pin=pin(root_raw), actual_case_credit=27, actual_all_five=True,
                         all_member_crc_verified=True, actual_outer_restore=True, actual_worker_reaped=True,
                         github_disposable_cleanup_success=True),
           'GLOBAL_REQUIRES_VERIFIED_OWNING_SKU_ORIGINAL')
    fields(root, dict(status='ROOT_VERIFIED_CURRENT_SKU_NATIVE25_BROWSER2_ALL5', head=receipt['head'],
                      run_id=receipt['run_id'], job_id=receipt['job_id'], artifact_id=receipt['artifact_id'],
                      actual_business_cases=27, package_all_five=True, prior_runs_aggregated=False,
                      actual_outer_restore=True, complete_global_input_review=False, production_go=False),
           'GLOBAL_REQUIRES_EXACT_ACTUAL_SKU_ROOT')
    observation = root['global_parent_catalogue']
    current_pin = pin(catalogue_raw)
    require(receipt['global_parent_catalogue'] == observation
            and observation['original'] == dict(name=CATALOGUE, **current_pin)
            and root['originals'][CATALOGUE] == current_pin
            and {key: receipt['members'][CATALOGUE][key] for key in current_pin} == current_pin,
            'GLOBAL_REQUIRES_EXACT_CATALOGUE_ORIGINAL_BYTES')
    require(pin(historic_raw) == HISTORICAL_CATALOGUE and pin(cache_raw) == PARSER_CACHE,
            'GLOBAL_REUSE_REQUIRES_EXACT_RETAINED_INPUTS')
    current, historic = checked_catalogue(catalogue_raw), checked_catalogue(historic_raw)
    fields(observation['fingerprint'], dict(groups=25, counts={group: len(rows) for group, rows in current.items()}),
           'GLOBAL_COMPLETE_CURRENT_CATALOGUE_COUNTS')
    return dict(status='ACTUAL_SKU_CATALOGUE_DELTA_REVIEW_INPUT_ONLY', parent_root=pin(root_raw),
                current_original=current_pin, historical_original=HISTORICAL_CATALOGUE,
                postgres_fingerprint=observation['fingerprint'], exact_row_changes=exact_differences(historic, current),
                **reuse_candidates(current['functions'], strict(cache_raw)['facts']),
                complete_input_review=False, actual_ERP_cases=0, production_go=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('receipt', 'root', 'catalogue', 'historical', 'cache', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    result = review(*(p.read_bytes() for p in (a.receipt, a.root, a.catalogue, a.historical, a.cache)))
    with a.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
