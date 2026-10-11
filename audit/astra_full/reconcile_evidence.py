"""Independently count Original case rows, declared IDs, first attempts and restore gates.
This never changes a raw verdict and never treats a green workflow as a case result.
"""
from collections import Counter
from pathlib import Path
import hashlib, json

HERE = Path(__file__).resolve().parent
ARCHIVES = Path('/workspace/scratch/eeb89eca3f58/audit-artifacts')
INDEX = json.loads((HERE / 'evidence/ARTIFACT_INDEX.json').read_text())
RESULTS = []
ALL = {}

def first_attempts(value, path=''):
    found = []
    if isinstance(value, dict):
        if value.get('business_day_retried') or value.get('business_day_rollover'):
            found.append(dict(path=path, status=value.get('status'), retried=value.get('business_day_retried'),
                              rollover=value.get('business_day_rollover'), error=value.get('error')))
        for k, v in value.items(): found += first_attempts(v, path + '/' + k)
    elif isinstance(value, list):
        for i, v in enumerate(value): found += first_attempts(v, path + '/' + str(i))
    return found

for item in INDEX:
    directory = ARCHIVES / str(item['id'])
    if not directory.is_dir() or not item['name'].endswith('-json'): continue
    z = directory.with_suffix('.zip')
    assert hashlib.sha256(z.read_bytes()).hexdigest() == item['digest'].removeprefix('sha256:')
    record = dict(artifact_id=item['id'], artifact_name=item['name'], run_id=item['run_id'],
                  archive_digest_verified=True, reports=[])
    for p in sorted(directory.glob('*.json')):
        d = json.loads(p.read_text())
        if not isinstance(d, dict): continue
        if p.name == 'T3_PACKAGE_INSTALL.json':
            record['package'] = {k: d.get(k) for k in ('status', 'run_identity', 'gate', 'primary_unchanged', 'auth_users_before', 'auth_users_after')}
        if p.name == 'T3_BACKUP_RESTORE_DRILL.json':
            record['backup'] = dict(status=d.get('status'), checks=d.get('checks'), data=d.get('data'),
                                    unexplained=d.get('restore', {}).get('unexplained'))
        if not ('expected_case_count' in d or 'expected_cases' in d): continue
        result = dict(file=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), reported_status=d.get('status'),
                      expected=d.get('expected_case_count', d.get('expected_cases')), observed=0, groups={},
                      restore=d.get('restore', d.get('restore_components')), cp6_restored=d.get('cp6_restored'),
                      advisor_gate=d.get('advisor_gate'), errors={k: d[k] for k in ('error', 'restore_error', 'traceback') if d.get(k)},
                      first_attempt_and_date_flags=first_attempts(d))
        for name in ('native', 'races', 'http', 'browser'):
            if name not in d: continue
            g = d[name]
            rows = g.get('races', g.get('cases', {}))
            if not isinstance(rows, dict): continue
            planned = g.get('planned_race_ids', g.get('planned_case_ids'))
            declared = d.get('required_case_ids', {}).get(name)
            counts = Counter(r.get('status', 'NO_STATUS') for r in rows.values())
            group = dict(case_ids={k: r.get('status') for k, r in rows.items()}, observed=len(rows), counts=dict(counts),
                         planned_ids_match=planned is not None and set(planned) == set(rows) and len(planned) == len(set(planned)),
                         declared_ids_match=None if declared is None else set(declared) == set(rows) and len(declared) == len(rows),
                         counts_match=g.get('counts') == dict(counts),
                         flags={k: g.get(k) for k in ('status', 'error', 'missing', 'complete_boundary_restored', 'database_remaining',
                                                     'cleanup_failures', 'auth_cleanup_failures', 'session_leaks', 'host_error', 'console_errors') if k in g})
            result['groups'][name] = group
            result['observed'] += len(rows)
            for key, row in rows.items():
                origin = 'ASTRA_CONTRACT' if '-own-' in item['name'] else 'WRITER_ORACLE_RERUN_BY_ASTRA'
                ALL.setdefault(origin + '/' + key, []).append(dict(artifact_id=item['id'], file=p.name, group=name, status=row.get('status'),
                                                                   business_day=row.get('business_day'), first_attempt_flags=first_attempts(row)))
        result['case_budget_match'] = result['observed'] == result['expected']
        record['reports'].append(result)
    RESULTS.append(record)

summary = dict(candidate_sha='d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0', production_go=False,
               complete=False, archives=RESULTS, canonical_case_observations=ALL,
               unique_counts=dict(Counter(k.split('/')[0] for k in ALL)),
               note='Work in progress. Repeated case IDs are one canonical case. Tool controls are reported separately. No raw FAIL is overwritten by adjudication.')
(HERE / 'evidence/RECONCILIATION.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(dict(archives=len(RESULTS), unique_counts=summary['unique_counts'],
                      reports=[dict(artifact=r['artifact_name'], file=s['file'], observed=s['observed'], expected=s['expected'],
                                    status=s['reported_status'], budget_match=s['case_budget_match'],
                                    bad=[k for g in s['groups'].values() for k, v in g['case_ids'].items() if v != 'PASS'],
                                    date_flags=len(s['first_attempt_and_date_flags'])) for r in RESULTS for s in r['reports']]), indent=2))
