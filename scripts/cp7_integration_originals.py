"""Verify and retain complete integration-run Originals; execute no ERP work.

Input is the GitHub artifact metadata plus an authorized local ZIP path. Native
catalogue probes, diagnostics, kernel fixtures and writer cases remain distinct.
This is writer evidence retention, never independent or installed acceptance.
"""
import argparse
import gzip
import hashlib
import json
import zipfile
from pathlib import Path


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'DUPLICATE_JSON_MEMBER'
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def groups(report):
    candidates = list(report.items())
    if isinstance(report.get('groups'), dict):
        candidates += [('groups/' + k, v) for k, v in report['groups'].items()]
    return {key: value for key, value in candidates if isinstance(value, dict)
            and ('planned_case_ids' in value or 'planned_race_ids' in value)}


def check_group(group):
    planned = group.get('planned_case_ids', group.get('planned_race_ids'))
    rows = group.get('cases', group.get('races'))
    assert isinstance(planned, list) and planned and all(isinstance(v, str) for v in planned)
    assert len(set(planned)) == len(planned), 'DUPLICATE_CASE_ID'
    assert isinstance(rows, dict) and set(rows) == set(planned), 'CASE_ID_SET'
    assert all(row.get('status') == 'PASS' for row in rows.values()), 'CASE_FAILURE'
    assert group['counts'] == {'PASS': len(planned)}, 'CASE_COUNTS'
    assert group['status'] in ('PASS', 'RUN_COMPLETE'), 'GROUP_STATUS'
    assert group.get('database_remaining', 0) == 0, 'DATABASE_CLEANUP'
    for key in ('missing', 'cleanup_failures', 'auth_cleanup_failures', 'session_leaks', 'host_error'):
        assert not group.get(key), 'GROUP_' + key.upper()
    if 'console_errors' in group:
        assert group['console_errors'] == 0, 'BROWSER_CONSOLE'
    if 'real_auth' in group:
        # GoTrue-issued tokens are real Auth. A fixture-signed JWT must not
        # substitute for the actual sign-in and runtime verification.
        assert group['real_auth'] is True and group['jwt_signed_by_runtime'] is False, 'REAL_AUTH_REQUIRED'
        counts = group['auth_counts']
        assert counts['restored'] and counts['before'] == counts['after'], 'GROUP_AUTH_CLEANUP'
    return dict(case_count=len(planned), case_ids=planned, counts=group['counts'],
                console_errors=group.get('console_errors'), actual_auth=group.get('real_auth'))


def retain(metadata, destination, expected_source, expected_tree):
    run = metadata['workflow_run']
    assert run['head_sha'] == expected_source and run['id'] == metadata['run_id'], 'ARTIFACT_RUN_SOURCE'
    assert metadata['expired'] is False, 'EXPIRED_ARTIFACT'
    raw = Path(metadata['local_path']).read_bytes()
    assert len(raw) == metadata['size_in_bytes'], 'ZIP_BYTES'
    assert 'sha256:' + sha(raw) == metadata['digest'], 'ZIP_HASH'
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    originals, members = {}, {}
    with zipfile.ZipFile(Path(metadata['local_path'])) as archive:
        assert len(set(archive.namelist())) == len(archive.namelist()), 'DUPLICATE_ZIP_MEMBER'
        assert archive.testzip() is None, 'ZIP_CRC'
        for name in sorted(archive.namelist()):
            if name.endswith('/'):
                continue
            value = archive.read(name)
            members[name] = dict(bytes=len(value), sha256=sha(value))
            if '/' not in name and name.endswith(('.json', '.sarif')):
                originals[name] = value
    assert originals, 'NO_COMPLETE_ROOT_ORIGINALS'
    decoded = {name: decode(value) for name, value in originals.items()}
    package = decoded.get('T3_PACKAGE_INSTALL.json')
    if package is not None:
        identity = package['run_identity']
        assert identity['tool_head'] == expected_source and str(identity['run_id']) == str(metadata['run_id']), 'PACKAGE_SOURCE'
        assert all(package['gate'].values()) and package['primary_unchanged'], 'PACKAGE_GATE'
        assert package['auth_users_before'] == package['auth_users_after'] == 0, 'AUTH_CLEANUP'
        assert decoded['T3_BACKUP_RESTORE_DRILL.json']['status'] == 'RESTORED_SAME_MEANING', 'BACKUP_RESTORE'
        assert decoded['T3_PACKAGE_FILES_INSTALL.json']['status'] == 'ALL_FILES_INSTALLED', 'INSTALL_FILES'
    checks = {}
    for name, report in decoded.items():
        if name.endswith('.sarif'):
            assert report['runs'] and all(not r.get('results') and r.get('invocations')
                and all(v.get('executionSuccessful') is True for v in r['invocations']) for r in report['runs']), 'CODEQL_GATE'
            checks[name] = dict(kind='CODEQL', findings=0)
            continue
        if name.startswith('CP7_') and 'status' in report:
            assert report['status'] == 'PASS', 'RUNTIME_STATUS:' + name
            assert report.get('production_go') is False, 'RUNTIME_PRODUCTION_FLAG'
            if 'source_commit' in report:
                assert report['source_commit'] == expected_source, 'RUNTIME_SOURCE'
            if 'source_tree' in report:
                assert report['source_tree'] == expected_tree, 'RUNTIME_TREE'
            if 'cp6_restored' in report:
                assert report['cp6_restored'] and report['advisor_gate'], 'RESTORE_ADVISOR_GATE'
                if 'restore_components' in report:
                    assert report['restore_components'] and all(report['restore_components'].values()), 'EXACT_RESTORE'
            checked = {key: check_group(value) for key, value in groups(report).items()}
            no_credit = {key for key in checked if report.get(key.removeprefix('groups/') + '_required_case_credit') == 0}
            smoke = {key for key in checked if key.removeprefix('groups/') == 'smoke' or key.endswith('_smoke')}
            if 'expected_smoke_count' in report:
                assert report['expected_smoke_count'] == report['observed_smoke_count'] == sum(checked[key]['case_count'] for key in smoke), 'SMOKE_BUDGET'
                no_credit |= smoke
            observed = sum(value['case_count'] for key, value in checked.items() if key not in no_credit)
            if 'expected_case_count' in report:
                assert report['expected_case_count'] == report['observed_case_count'] == observed, 'FULL_CASE_BUDGET'
            if 'expected_group_executions' in report:
                assert report['groups_complete'] and report['expected_group_executions'] == {
                    key.removeprefix('groups/'): value['case_count'] for key, value in checked.items()}, 'DECLARED_GROUP_BUDGET'
            if 'required_case_counts' in report:
                for key, value in report['required_case_counts'].items():
                    assert (checked.get(key, {}).get('case_count', 0)) == value, 'REQUIRED_GROUP_BUDGET'
            diagnostic = report.get('diagnostic_only', False)
            if diagnostic:
                assert report['product_qualification'] is False and report.get('Native_product_exit_case_credit', 0) == 0
            checks[name] = dict(kind='DIAGNOSTIC_ONLY' if diagnostic else 'WRITER_NATIVE_CASES' if checked else 'CATALOGUE_OR_LEGACY_PROBE',
                                observed_planned_executions=observed, declared_case_count=report.get('expected_case_count'),
                                source_bundle_sha256=report.get('source_sha256'), groups=checked,
                                extra_zero_exit_credit_groups=sorted(no_credit),
                                diagnostic_only=diagnostic, unique_full_CP7_credit=0)
        elif name == 'results.json':
            assert not report['errors'] and report['stats']['unexpected'] == report['stats']['flaky'] == report['stats']['skipped'] == 0
            checks[name] = dict(kind='FIXTURE_BROWSER', expected=report['stats']['expected'], Native_credit=0)
    retained = {}
    for name, value in originals.items():
        target = destination / (name + '.gz')
        compressed = gzip.compress(value, mtime=0)
        target.write_bytes(compressed)
        retained[name] = dict(members[name], file=target.name, gzip_sha256=sha(compressed), original_bytes_unchanged=True)
    receipt = {key: metadata[key] for key in ('id', 'name', 'run_id', 'workflow_name', 'workflow_path', 'size_in_bytes', 'digest')}
    receipt.update(contract='cp7.integration-original-retention.v1', source_commit=expected_source,
                   source_tree=expected_tree, status='VERIFIED_COMPLETE_ORIGINALS_RETAINED',
                   package_gate=package['gate'] if package else None, all_zip_members=members,
                   root_originals=retained, report_checks=checks, Native_cases_reexecuted_by_retainer=0,
                   full_CP7_acceptance=False, independent_acceptance=False, installed_P21_acceptance=False, production_go=False)
    (destination / 'RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata')
    parser.add_argument('destination')
    parser.add_argument('--source', required=True)
    parser.add_argument('--tree', required=True)
    args = parser.parse_args()
    result = retain(decode(Path(args.metadata).read_bytes()), args.destination, args.source, args.tree)
    print(json.dumps(dict(status=result['status'], artifact_id=result['id'], reports=list(result['root_originals']))))


if __name__ == '__main__':
    main()
