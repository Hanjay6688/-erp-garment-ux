"""Read retained Originals independently; preserve catalog multiplicity and fields.

This review performs no SQL and awards no new Native case credit. It cannot
reconstruct per-case catalog snapshots missing from a historical failed run.
"""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path


def canonical(raw):
    result = deepcopy(raw)
    assert isinstance(result['functions'], list)
    assert all(isinstance(pair, list) and len(pair) == 2 and
               all(isinstance(value, str) for value in pair)
               for pair in result['functions'])
    # Sort the complete list, including duplicates; never convert it to a set.
    result['functions'] = sorted(result['functions'])
    return result


def moved_members(before, after):
    assert canonical(before) == canonical(after)
    b, a = before['functions'], after['functions']
    # Existing catalog signatures are unique. Equality above still preserves
    # multiplicity if future diagnostic inputs contain duplicates.
    assert len({pair[0] for pair in b}) == len(b)
    positions = {tuple(pair): i + 1 for i, pair in enumerate(a)}
    return [dict(signature=pair[0], definition_md5=pair[1],
                 before_position=i + 1, after_position=positions[tuple(pair)])
            for i, pair in enumerate(b) if positions[tuple(pair)] != i + 1]


def review(retained_path, report_name):
    archive = Path(retained_path).read_bytes()
    envelope = json.loads(gzip.decompress(archive))
    r = json.loads(envelope['root_json_utf8'][report_name])
    group = r.get('native', {})
    audit = r.get('native_public_catalog_comparison', {})
    snapshots = audit.get('raw_snapshots', [])
    result = dict(contract='cp7.catalog.retained-independent-review.v1',
                  source_commit=envelope['source_commit'], report=report_name,
                  retained_gzip_sha256=hashlib.sha256(archive).hexdigest(),
                  original_status=r['status'], native_case_ids=group.get('planned_case_ids', []),
                  historical_missing_raws_reconstructed=False, new_Native_execution_credit=0,
                  independent_P20_acceptance=False, production_go=False)
    if snapshots:
        planned = group['planned_case_ids']
        assert group['status'] == 'PASS' and len(set(planned)) == len(planned)
        assert group['counts'] == {'PASS': len(planned)}
        assert set(group['cases']) == set(planned)
        assert len(snapshots) == audit['snapshots_checked'] == 2 + 2 * len(planned)
        baseline = canonical(snapshots[0]['raw'])
        assert baseline['functions']
        rows = []
        for i, item in enumerate(snapshots, 1):
            assert item['snapshot'] == i
            state = canonical(item['raw'])
            assert state == baseline, ('CATALOG_FULL_MEMBER_DELTA', i)
            fingerprint = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            assert fingerprint == item['exact_canonical_state_sha256']
        for i, case_id in enumerate(planned):
            before, after = snapshots[1 + 2 * i]['raw'], snapshots[2 + 2 * i]['raw']
            case = group['cases'][case_id]
            assert case['status'] == 'PASS'
            assert case['public_schema_unchanged'] and case['full_boundary_restored']
            assert not case['session_leaks']['advisory_locks'] and not case['session_leaks']['other_sessions']
            rows.append(dict(case_id=case_id, status='PASS', before_snapshot=2 + 2 * i,
                             after_snapshot=3 + 2 * i, raw_order_equal=before == after,
                             all_original_fields_and_members_equal=True,
                             functions=len(before['functions']), moved_members=moved_members(before, after)))
        assert all(audit['read_only_preservation_controls'].values())
        result.update(status='EVERY_RETAINED_NATIVE_CATALOG_EXACT', raw_snapshots_checked=len(snapshots),
                      functions_per_snapshot=len(baseline['functions']), cases=rows,
                      original_sensitivity_controls=audit['read_only_preservation_controls'],
                      OID_or_storage_identity_captured=False,
                      no_inference_of_historical_DDL_from_pair_order=True)
    else:
        result.update(status='HISTORICAL_PER_CASE_RAW_CATALOGS_UNAVAILABLE',
                      exact_failed_case_catalog_delta='UNPROVED', OID_or_storage_identity_captured=False)
    difference = r.get('restore_raw_public_difference')
    if difference:
        assert canonical(difference['before']) == canonical(difference['after'])
        result['final_restore'] = dict(all_original_fields_and_members_equal=True,
                                      function_members=len(difference['before']['functions']),
                                      moved_members=moved_members(difference['before'], difference['after']),
                                      witness_is_final_restore_not_individual_failed_case=True)
    else:
        assert r['restore_raw_public_equal'] is True
        result['final_restore'] = dict(raw_equal=True, moved_members=[])
    assert r['cp6_restored'] and all(r['restore_components'].values()) and r['advisor_gate']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_reports_gzip')
    parser.add_argument('report_name')
    parser.add_argument('output_json')
    args = parser.parse_args()
    result = review(args.original_reports_gzip, args.report_name)
    Path(args.output_json).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'source_commit', 'original_status', 'new_Native_execution_credit')}))


if __name__ == '__main__':
    main()
