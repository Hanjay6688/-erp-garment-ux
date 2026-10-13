"""Lock this audit's evidence without converting any failed case to PASS.

Run after reconcile_evidence.py, summarize_evidence.py and write_report.py.
This checks evidence packaging, not ERP behavior, and never grants production GO.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import gzip
import hashlib
import json

P = Path(__file__).resolve().parent
ROOT = P.parents[1]

def read(name):
    return json.loads((P / name).read_text())

def save(name, value):
    (P / name).write_text(json.dumps(value, indent=2) + '\n')

summary = read('evidence/RESULT_SUMMARY.json')
assert summary['own_manifest_complete'] and not summary['own_cases_pending']
assert summary['own_status_counts'] == {'PASS': 76, 'COUNTEREXAMPLE': 1}
assert summary['product_cases_own_unique'] == 77 and summary['own_executions'] == 80
assert summary['writer_regression'] == dict(PASS=1760, smoke_executions=3, smoke_pass=3, reports=42)
assert summary['writer_product_unique_ids'] == 1174
assert not summary['pending_regression_reports'] and not summary['date_rollover_flags_in_case_reports']
assert len(summary['rehearsals']) == 2
assert all(x['status'] == 'PASS' and x['cp6_restored'] and x['advisor_gate'] for x in summary['rehearsals'])

runs = read('evidence/FINAL_EXECUTION_RECEIPT.json')
index = {str(x['id']): x for x in read('RUN_INDEX.json')['runs']}
assert set(runs) == set(index) and len(runs) == 9
jobs = []
for key, run in runs.items():
    assert run['control_sha'] == index[key]['control_commit']
    assert run['status'] == 'completed' and run['run_attempt'] == 1
    jobs.extend(run['jobs'])
assert len(jobs) == len({j['id'] for j in jobs}) == 68
assert all(j['status'] == 'completed' for j in jobs)
failed = {j['id'] for j in jobs if j['conclusion'] != 'success'}
assert failed == {114529226905, 114529226911, 114530570757}

source = read('evidence/FINAL_SOURCE_VERIFICATION.json')
assert source['product_unchanged'] and not source['changed_candidate_roots']
assert source['writer_ref_sha'] == read('SOURCE_RECEIPT.json')['documentation_sha']
identity = read('evidence/EXECUTION_IDENTITY_CHECK.json')
assert identity['all_same_candidate'] and identity['verified_archives'] == 64
for row in read('evidence/SAVED_ARCHIVES.json'):
    data = (P / row['path']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
for row in read('evidence/FIRST_FAILURE_LOGS.json')['logs']:
    data = (ROOT / row['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['gzip_sha256']
    decoded = gzip.decompress(data)
    assert len(decoded) == row['decoded_log_bytes']
    assert hashlib.sha256(decoded).hexdigest() == row['decoded_log_sha256']
visual = read('evidence/VISUAL_REVIEW.json')
assert len(visual['images']) == 11
for row in visual['images']:
    assert hashlib.sha256((ROOT / row['file']).read_bytes()).hexdigest() == row['sha256']

recon = read('evidence/RECONCILIATION.json')
counts = Counter()
known_flags = []
for archive in recon['archives']:
    for report in archive['reports']:
        initial_ui = archive['artifact_id'] == 11709906989
        assert report['case_budget_match'] or (initial_ui and report['observed'] == 0)
        assert not report['errors']
        assert report['cp6_restored'] is not False and report['advisor_gate'] is not False
        assert report['declared_group_keys_match'] is not False
        if isinstance(report['restore'], dict):
            assert all(v is True for v in report['restore'].values())
        for name, group in report['groups'].items():
            origin = 'own' if '-own-' in archive['artifact_name'] else 'writer'
            kind = 'smoke' if group['smoke'] else group['kind']
            counts[f'{origin}/{kind}'] += group['observed']
            if not initial_ui:
                assert group['planned_ids_match'] and group['counts_match']
                assert group['declared_ids_match'] is not False
                assert group['group_budget_match'] is not False
            flags = group['flags']
            faults = {k: v for k, v in flags.items() if k in (
                'error', 'missing', 'database_remaining', 'cleanup_failures',
                'auth_cleanup_failures', 'session_leaks', 'host_error', 'console_errors') and v}
            assert flags.get('complete_boundary_restored') is not False
            if faults:
                assert initial_ui and set(faults) <= {'error', 'host_error'}
                assert all('UI_INVENTORY.json' in v and 'ENOENT' in v for v in faults.values())
                known_flags.append(dict(artifact=archive['artifact_id'], group=name,
                    disposition='Auditor missing inventory before first case; recovery 38160527120, raw preserved'))

assert sum(v for k, v in counts.items() if k.startswith('own/')) == 80
assert sum(v for k, v in counts.items() if k.startswith('writer/') and k != 'writer/smoke') == 1760
assert counts['writer/smoke'] == 3
recon['complete'] = True
recon['note'] = ('Evidence collection and reconciliation complete. Repeated IDs are one canonical case. '
                 'Tool controls are separate. Known counterexample and pre-case tooling failure remain raw. '
                 'Complete audit does not mean independent acceptance or production GO.')
save('evidence/RECONCILIATION.json', recon)
finished = datetime.now(timezone.utc).isoformat()
save('evidence/FINAL_VALIDATION.json', dict(
    checked_at=finished, evidence_packaging='PASS', audit_verdict='HOLD', production_go=False,
    runs=9, jobs=68, successful_jobs=65, failed_jobs_preserved=sorted(failed),
    first_attempts_preserved=True, source_unchanged=True, verified_original_json_archives=64,
    visual_images=11, group_executions=dict(counts), known_raw_failure_flags=known_flags,
    note='Evidence validation only. ASF-F01 remains OPEN_TOOLING and PR44 needs non-author acceptance.'))

files = []
for path in sorted(P.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts:
        continue
    if path.name == 'LOCK.json' or path.name.startswith(('UPLOAD_', 'REMOTE_')):
        continue
    data = path.read_bytes()
    files.append(dict(path=str(path.relative_to(ROOT)), bytes=len(data),
                      sha256=hashlib.sha256(data).hexdigest()))
save('LOCK.json', dict(locked_at=finished, candidate=summary['candidate'],
    audit_complete=True, verdict='HOLD', independent_acceptance=False, production_go=False,
    same_round_peer_reports_read=False, files=files,
    scope='Report, handoff, manifests, harness and evidence files. LOCK itself and upload/remote bookkeeping excluded.'))
print(json.dumps(dict(locked_files=len(files), audit_complete=True, verdict='HOLD',
                     own_pass=76, own_known_boundary=1, regression_pass=1760, production_go=False)))
