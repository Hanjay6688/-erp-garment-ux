"""Build a source-bound index of complete retained writer evidence, no ERP access."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(value).hexdigest()


def check_receipt(path):
    raw = path.read_bytes()
    receipt = json.loads(raw)
    roots = receipt.get('root_originals', {})
    if isinstance(roots, list):
        roots = {name: dict(receipt['all_zip_members'][name], file=name + '.gz') for name in roots}
    for name, info in roots.items():
        compressed = (path.parent / info['file']).read_bytes()
        value = gzip.decompress(compressed)
        if 'gzip_sha256' in info:
            assert digest(compressed) == info['gzip_sha256'], 'GZIP_HASH'
        assert len(value) == info['bytes'] and digest(value) == info['sha256'], 'ORIGINAL_UTF8_HASH'
    if 'original_reports_gzip_sha256' in receipt:
        compressed = (path.parent / 'ORIGINAL_REPORTS.json.gz').read_bytes()
        assert digest(compressed) == receipt['original_reports_gzip_sha256'], 'ENVELOPE_HASH'
        envelope = json.loads(gzip.decompress(compressed))
        assert set(envelope['root_json_utf8']) == set(receipt['original_root_reports']), 'ORIGINAL_MEMBERS'
        for name, text in envelope['root_json_utf8'].items():
            value = text.encode('utf8')
            expected = receipt['original_root_reports'][name]
            assert len(value) == expected['bytes'] and digest(value) == expected['sha256'], 'ENVELOPE_UTF8_HASH'
        roots = receipt['original_root_reports']
    return dict(path=str(path), sha256=digest(raw), status=receipt.get('status'),
                source_commit=receipt.get('source_commit'), run_id=receipt.get('run_id'),
                artifact_id=receipt.get('id', receipt.get('artifact_id')),
                complete_Original_roots=len(roots), report_checks=receipt.get('report_checks', {}))


def build(run_metadata, artifact_metadata, destination):
    request = json.loads(Path('docs/cp7/MERGE_QUALIFICATION_REQUEST.json').read_text())
    runs = json.loads(Path(run_metadata).read_text())
    artifacts = json.loads(Path(artifact_metadata).read_text())
    source = 'ab4d8fa5a1ba640dc2fe03167aa2cabb92337cd5'
    tree = '262eae67469b28d62caa456660a1e94f2b299046'
    expected = {row['path'] for row in request['workflow_inventory']}
    assert len(runs) == len(expected) == 63 and {row['path'] for row in runs} == expected, 'FROZEN_INVENTORY'
    assert all(row['head_sha'] == source and row['status'] == 'completed' and row['conclusion'] == 'success'
               for row in runs), 'EXACT_SOURCE_RUN_OUTCOME'
    receipts = []
    for root in ('docs/cp7/evidence/integration-ab4', 'docs/cp7/evidence/p19'):
        receipts.extend(check_receipt(p) for p in sorted(Path(root).rglob('RECEIPT.json')))
    for row in runs:
        row['receipt_paths'] = [r['path'] for r in receipts if r['run_id'] == row['id'] and r['source_commit'] == source]
        row['artifact_pins'] = [{key: a[key] for key in ('id', 'name', 'size_in_bytes', 'digest')}
                                for a in artifacts if a['run_id'] == row['id']]
        if row['path'] == '.github/workflows/ci.yml':
            row['receipt_paths'].append('docs/cp7/evidence/build-ux/qualified-ab4/RECEIPT.json')
            row['scope_limit'] = 'CP45 log-only; reporter overwrote its Original. PreCP5/CP5/CP6 Originals complete. Successor preserves separate CP45 output.'
        if row['path'] == '.github/workflows/cp7-retain-existing-artifact.yml':
            row['retention_receipt'] = 'docs/cp7/evidence/integration-ab4/legacy-retention-11391124350/RETENTION_RECEIPT.json'
            row['Native_execution_credit'] = 0
        if row['path'] == '.github/workflows/cp7-native-artifact-projection.yml':
            row['retention_receipt'] = 'docs/cp7/evidence/integration-ab4/legacy-projection-11391852016/RETENTION_RECEIPT.json'
            row['Native_execution_credit'] = 0
        assert row['receipt_paths'] or row.get('retention_receipt'), 'WORKFLOW_WITHOUT_EVIDENCE:' + row['path']
        if row.get('retention_receipt'):
            value = Path(row['retention_receipt']).read_bytes()
            proof = json.loads(value)
            assert proof['run_id'] == row['id'] and proof['retainer_source'] == source
            row['retention_receipt_sha256'] = digest(value)
    result = dict(contract='cp7.checkpoint-evidence-index.v1', status='VERIFIED_SOURCE_BOUND_WRITER_CHECKPOINT',
                  canonical_merge_source=source, canonical_merge_tree=tree,
                  frozen_inventory_sha256=digest(Path('docs/cp7/MERGE_QUALIFICATION_REQUEST.json').read_bytes()),
                  requested_workflows=63, successful_workflows=63, workflows=sorted(runs, key=lambda r: r['path']),
                  retained_receipts=receipts, Native_cases_reexecuted_by_index=0,
                  case_counts_are_overlapping_not_unique=True, full_CP7_acceptance=False,
                  independent_acceptance=False, installed_P21_acceptance=False, production_go=False)
    Path(destination).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], successful_workflows=63, verified_receipts=len(receipts),
                         retained_Original_roots=sum(r['complete_Original_roots'] for r in receipts),
                         Native_execution_credit=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_metadata')
    parser.add_argument('artifact_metadata')
    parser.add_argument('destination')
    args = parser.parse_args()
    build(args.run_metadata, args.artifact_metadata, args.destination)
