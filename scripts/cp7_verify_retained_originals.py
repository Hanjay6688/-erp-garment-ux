"""Read-only validation of qualified retained Originals; execute no ERP case."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'DUPLICATE_JSON_MEMBER'
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique_object)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(directory, expected_manifest=None, projection_head=None):
    directory = Path(directory)
    receipt_raw = (directory / 'RECEIPT.json').read_bytes()
    receipt = decode(receipt_raw)
    compressed = (directory / 'ORIGINAL_REPORTS.json.gz').read_bytes()
    assert digest(compressed) == receipt['original_reports_gzip_sha256'], 'ORIGINAL_ENVELOPE_HASH'
    envelope = decode(gzip.decompress(compressed))
    assert envelope['contract'] == 'cp7.retained-originals.v1'
    assert envelope['source_commit'] == receipt['source_commit'], 'ORIGINAL_SOURCE'
    originals = envelope['root_json_utf8']
    assert set(originals) == set(receipt['original_root_reports']), 'ROOT_REPORT_MEMBERS'
    for name, value in originals.items():
        assert '/' not in name and name.endswith('.json') and isinstance(value, str)
        raw = value.encode('utf-8')
        expected = receipt['original_root_reports'][name]
        assert len(raw) == expected['bytes'] and digest(raw) == expected['sha256'], 'ROOT_REPORT_HASH'
        assert expected == receipt['all_zip_members'][name], 'ARCHIVE_ROOT_REPORT_HASH'
    report = decode(originals[receipt['runtime_report']])
    package = decode(originals['T3_PACKAGE_INSTALL.json'])
    assert receipt['expected_status'] == report['status'] == 'PASS', 'QUALIFIED_STATUS_REQUIRED'
    assert report['source_sha256'] == receipt['source_bundle_sha256'], 'SOURCE_BUNDLE_HASH'
    assert package['run_identity']['tool_head'] == receipt['source_commit'], 'PACKAGE_SOURCE'
    assert str(package['run_identity']['run_id']) == str(receipt['run_id']), 'PACKAGE_RUN'
    if report.get('source_commit') is not None:
        assert report['source_commit'] == receipt['source_commit'], 'RUNTIME_SOURCE'
    if report.get('source_tree') is not None:
        assert report['source_tree'] == receipt['source_tree'], 'RUNTIME_TREE'
    assert receipt['observed_case_count'] == report['observed_case_count'] == report['expected_case_count'] == receipt['expected_case_count']
    assert report['cp6_restored'] and receipt['cp6_restored']
    assert report['restore_components'] == receipt['restore_components'] and all(report['restore_components'].values())
    assert report['advisor_gate'] and receipt['advisor_gate']
    assert receipt['package_gate'] == package['gate'] and all(package['gate'].values())
    assert package['primary_unchanged'] and receipt['primary_unchanged']
    assert package['auth_users_before'] == package['auth_users_after'] == receipt['auth_users_before'] == receipt['auth_users_after'] == 0
    diagnostic = report.get('diagnostic_only', False)
    assert receipt['status'] == ('DIAGNOSTIC_EMISSION_COMPLETE' if diagnostic else 'NATIVE_WRITER_QUALIFIED')
    if diagnostic:
        assert report['product_qualification'] is False
        assert report['Native_product_exit_case_credit'] == 0 and receipt['Native_product_exit_case_credit'] == 0
        assert report['full_family_acceptance'] is False and receipt['full_P19_acceptance'] is False
    budget = receipt['required_case_counts']
    if budget is None:
        assert expected_manifest is not None, 'EXTERNAL_BUDGET_REQUIRED'
        budget = expected_manifest['required_case_counts']
    assert set(budget).issubset({'native', 'races', 'http', 'browser'})
    assert all(type(value) is int and value >= 0 for value in budget.values())
    assert sum(budget.values()) == receipt['expected_case_count'], 'CASE_BUDGET'
    counts = {}
    for group in ['native', 'races', 'http', 'browser']:
        expected = budget.get(group, 0)
        actual = report.get(group)
        if expected == 0:
            assert actual in (None, {}), 'UNDECLARED_GROUP'
            continue
        assert isinstance(actual, dict)
        rows = actual.get('cases', actual.get('races', {}))
        assert len(rows) == expected and all(row['status'] == 'PASS' for row in rows.values()), 'CASE_RESULTS'
        assert actual['counts'] == receipt['counts'][group] == {'PASS': expected}, 'GROUP_COUNTS'
        planned = actual.get('planned_case_ids', actual.get('planned_race_ids'))
        assert planned is not None and len(planned) == expected and len(set(planned)) == expected and set(planned) == set(rows), 'PLANNED_CASE_IDS'
        counts[group] = expected
    if report.get('browser'):
        assert report['browser']['console_errors'] == 0, 'BROWSER_CONSOLE'
    if expected_manifest is not None:
        for field in ['source_commit', 'source_tree', 'run_id', 'job_id', 'artifact_id', 'zip_bytes', 'zip_sha256', 'runtime_report', 'source_bundle_sha256', 'expected_status', 'expected_case_count']:
            assert receipt[field] == expected_manifest[field], 'PINNED_' + field.upper()
        assert budget == expected_manifest['required_case_counts'], 'PINNED_CASE_BUDGET'
    projection_path = directory / 'PROJECTION.json'
    if projection_path.exists():
        projection = decode(projection_path.read_bytes())
        assert projection['report_receipt_sha256'] == digest(receipt_raw), 'PROJECTION_RECEIPT_HASH'
        assert projection['original_reports_gzip_sha256'] == digest(compressed)
        for field in ['source_commit', 'source_tree', 'zip_sha256', 'run_id', 'artifact_id']:
            assert projection['original_' + field] == receipt[field], 'PROJECTION_SOURCE'
        assert projection['Native_product_cases_reexecuted'] == 0 and projection['Native_database_access'] is False
        if projection_head is not None:
            assert projection['projection_source_commit'] == projection_head, 'PROJECTION_HEAD'
    elif projection_head is not None:
        raise AssertionError('PROJECTION_REQUIRED')
    assert receipt['full_family_acceptance'] is False and receipt['independent_acceptance'] is False and receipt['production_go'] is False
    return {'status': 'VERIFIED_QUALIFIED_ORIGINALS_RETENTION_ONLY',
            'source_commit': receipt['source_commit'], 'source_tree': receipt['source_tree'],
            'original_run_id': receipt['run_id'], 'observed_case_count': receipt['observed_case_count'],
            'groups': counts, 'root_reports': len(originals), 'diagnostic_only': diagnostic,
            'validation_new_Native_execution_credit': 0, 'Native_database_access': False,
            'full_family_acceptance': False, 'independent_acceptance': False, 'production_go': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    parser.add_argument('--manifest')
    parser.add_argument('--projection-head')
    args = parser.parse_args()
    manifest = decode(Path(args.manifest).read_bytes()) if args.manifest else None
    print(json.dumps(verify(args.directory, manifest, args.projection_head)))


if __name__ == '__main__':
    main()
