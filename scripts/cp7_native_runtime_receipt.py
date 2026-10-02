"""Retain exact Native runtime Originals, including every failed gate."""
import gzip
import hashlib
import json
import sys
import zipfile
from pathlib import Path


def retain(archive, metadata, destination):
    archive, destination = Path(archive), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    raw = archive.read_bytes()
    assert len(raw) == metadata['zip_bytes']
    assert hashlib.sha256(raw).hexdigest() == metadata['zip_sha256']
    with zipfile.ZipFile(archive) as z:
        originals, members = {}, {}
        for name in sorted(z.namelist()):
            if name.endswith('/'):
                continue
            data = z.read(name)
            members[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            if '/' not in name and name.endswith('.json'):
                originals[name] = data.decode('UTF8')
        report = json.loads(originals[metadata['runtime_report']])
        package = json.loads(originals['T3_PACKAGE_INSTALL.json'])
        identity = package['run_identity']
        assert identity['tool_head'] == metadata['source_commit']
        assert str(identity['run_id']) == str(metadata['run_id'])
        assert report['status'] == metadata['expected_status']
        assert report['expected_case_count'] == metadata['expected_case_count']
        diagnostic = metadata.get('diagnostic_only', False)
        if diagnostic:
            assert report['diagnostic_only'] is True and report['product_qualification'] is False
            assert report['full_family_acceptance'] is False and report['full_P19_acceptance'] is False
        counts = {g: report.get(g, {}).get('counts') for g in ('native', 'races', 'http', 'browser')}
        failures = {}
        for group in counts:
            rows = report.get(group, {}).get('cases', report.get(group, {}).get('races', {}))
            failures[group] = {key: value['status'] for key, value in rows.items()
                               if value.get('status') != 'PASS'}
        if report['status'] == 'PASS':
            assert report['observed_case_count'] == report['expected_case_count']
            assert all(set(c or {}) == {'PASS'} for c in counts.values() if c is not None or not diagnostic)
            assert all(package['gate'].values())
            assert report['cp6_restored'] and all(report['restore_components'].values())
            assert report['advisor_gate']
            assert package['auth_users_after'] == package['auth_users_before']
        envelope = dict(contract='cp7.retained-originals.v1',
                        source_commit=identity['tool_head'], root_json_utf8=originals)
        original_bytes = json.dumps(envelope, ensure_ascii=False, separators=(',', ':')).encode('UTF8')
        original_path = destination / 'ORIGINAL_REPORTS.json.gz'
        original_path.write_bytes(gzip.compress(original_bytes, mtime=0))
        receipt_status = ('DIAGNOSTIC_EMISSION_COMPLETE' if report['status'] == 'PASS' else 'DIAGNOSTIC_INCOMPLETE') if diagnostic else (
            'NATIVE_WRITER_QUALIFIED' if report['status'] == 'PASS' else 'NATIVE_WRITER_INCOMPLETE')
        receipt = dict(metadata,
                       status=receipt_status,
                       source_bundle_sha256=report['source_sha256'],
                       observed_case_count=report['observed_case_count'],
                       required_case_counts=report.get('required_case_counts'), counts=counts,
                       failures=failures, restore_components=report['restore_components'],
                       cp6_restored=report['cp6_restored'], advisor_gate=report['advisor_gate'],
                       package_gate=package['gate'], primary_unchanged=package['primary_unchanged'],
                       auth_users_before=package['auth_users_before'], auth_users_after=package['auth_users_after'],
                       original_reports_gzip_sha256=hashlib.sha256(original_path.read_bytes()).hexdigest(),
                       original_root_reports={n: members[n] for n in originals}, all_zip_members=members,
                       full_family_acceptance=False, independent_acceptance=False, production_go=False)
        (destination / 'RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('status', 'run_id', 'counts', 'package_gate',
                                             'auth_users_before', 'auth_users_after')}))
    return receipt


if __name__ == '__main__':
    retain(sys.argv[1], json.loads(Path(sys.argv[2]).read_text()), sys.argv[3])
