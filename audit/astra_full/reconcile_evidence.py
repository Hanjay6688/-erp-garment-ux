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

# These retained P12 reports predate an aggregate expected_case_count field.
# Budgets come from the frozen source group lists, not the observed PASS count:
# cp7_p12_nota_probe.py run()/finally group_keys, and referenced case modules.
P12_BASE = dict(native=5, http=1, notes=7, note_races=3, note_http=1,
                admission_regression=1, browser=2, payroll_review=4,
                payroll_review_http=1, payroll_review_browser=2, settlement=7,
                settlement_races=4, settlement_http=1, settlement_browser=3)
P12_ROSTER = dict(P12_BASE, attendance_read=6, attendance_read_http=1,
                  attendance_read_browser=2, roster=6, roster_races=3,
                  roster_http=1, roster_browser=2)
P12_WRITE = dict(P12_ROSTER, attendance_write=10, attendance_write_races=4,
                 attendance_write_http=1, attendance_write_browser=2)
LEGACY = {'CP7_P12_SETTLEMENT.json': P12_BASE, 'CP7_P12_ROSTER.json': P12_ROSTER,
          'CP7_P12_ATTENDANCE_WRITE.json': P12_WRITE}

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
                  archive_digest_verified=True, reports=[], rehearsals=[])
    for p in sorted(directory.glob('*.json')):
        d = json.loads(p.read_text())
        if not isinstance(d, dict): continue
        if p.name == 'T3_PACKAGE_INSTALL.json':
            record['package'] = {k: d.get(k) for k in ('status', 'run_identity', 'gate', 'primary_unchanged', 'auth_users_before', 'auth_users_after')}
        if p.name == 'T3_BACKUP_RESTORE_DRILL.json':
            record['backup'] = dict(status=d.get('status'), checks=d.get('checks'), data=d.get('data'),
                                    unexplained=d.get('restore', {}).get('unexplained'))
        if p.name in ('CP7_P21_REHEARSAL.json', 'CP7_P21_FULL_REHEARSAL.json'):
            record['rehearsals'].append(dict(file=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                status=d.get('status'), steps=d.get('steps', d.get('phases')),
                cp6_restored=d.get('cp6_restored'), advisor_gate=d.get('advisor_gate'),
                errors={k: d[k] for k in ('error', 'restore_error', 'traceback') if d.get(k)},
                note='Rehearsal phases, not counted as product case executions; committed rows remain only in disposable clone until dropped.'))
        legacy = LEGACY.get(p.name)
        if not ('expected_case_count' in d or 'expected_cases' in d or legacy): continue
        result = dict(file=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), reported_status=d.get('status'),
                      expected=sum(legacy.values()) if legacy else d.get('expected_case_count', d.get('expected_cases')), observed=0, groups={},
                      budget_origin='FROZEN_SOURCE_GROUP_LISTS' if legacy else 'REPORT_PREDECLARED',
                      restore=d.get('restore', d.get('restore_components')), cp6_restored=d.get('cp6_restored'),
                      advisor_gate=d.get('advisor_gate'), errors={k: d[k] for k in ('error', 'restore_error', 'traceback') if d.get(k)},
                      first_attempt_and_date_flags=first_attempts(d))
        specs = {g['key']: g for g in d.get('predeclared_groups', [])}
        if legacy:
            specs = {k: dict(expected_executions=v, smoke=False,
                     kind='browser' if 'browser' in k else 'http' if 'http' in k or k == 'admission_regression' else 'races' if 'races' in k else 'native') for k, v in legacy.items()}
            supplied = {k: v for k, v in d.items() if isinstance(v, dict) and ('cases' in v or 'races' in v)}
        else:
            supplied = d.get('groups') if specs else {k: d[k] for k in ('native', 'races', 'http', 'browser') if k in d}
        result['expected_smoke'] = d.get('expected_smoke_count', 0)
        result['observed_smoke'] = 0
        result['declared_group_keys_match'] = None if not specs else set(supplied) == set(specs)
        for name, g in (supplied or {}).items():
            rows = g.get('races', g.get('cases', {}))
            if not isinstance(rows, dict): continue
            spec = specs.get(name, {})
            planned = g.get('planned_race_ids', g.get('planned_case_ids', g.get('planned')))
            declared = d.get('required_case_ids', {}).get(name)
            counts = Counter(r.get('status', 'NO_STATUS') for r in rows.values())
            group = dict(case_ids={k: r.get('status') for k, r in rows.items()}, observed=len(rows), counts=dict(counts),
                         planned_ids_match=planned is not None and set(planned) == set(rows) and len(planned) == len(set(planned)),
                         declared_ids_match=None if declared is None else set(declared) == set(rows) and len(declared) == len(rows),
                         counts_match=g.get('counts') == dict(counts), kind=spec.get('kind', name),
                         smoke=spec.get('smoke', False), expected_group_executions=spec.get('expected_executions'),
                         group_budget_match=None if not spec else len(rows) == spec['expected_executions'],
                         flags={k: g.get(k) for k in ('status', 'error', 'missing', 'complete_boundary_restored', 'database_remaining',
                                                     'cleanup_failures', 'auth_cleanup_failures', 'session_leaks', 'host_error', 'console_errors') if k in g})
            result['groups'][name] = group
            result['observed_smoke' if spec.get('smoke') else 'observed'] += len(rows)
            for key, row in rows.items():
                origin = 'ASTRA_CONTRACT' if '-own-' in item['name'] else 'WRITER_ORACLE_RERUN_BY_ASTRA'
                ALL.setdefault(origin + '/' + key, []).append(dict(artifact_id=item['id'], file=p.name, group=name, status=row.get('status'),
                                                                   smoke=spec.get('smoke', False), business_day=row.get('business_day'), first_attempt_flags=first_attempts(row)))
        result['case_budget_match'] = result['observed'] == result['expected'] and result['observed_smoke'] == result['expected_smoke']
        result['runtime_diagnostics'] = d.get('runtime_diagnostics')
        result['additional_source_admission_controls'] = None if 'source_admission' not in d else {
            'counts': d['source_admission'].get('counts'), 'status': d['source_admission'].get('status'),
            'declared_case_credit': d.get('source_admission_required_case_credit'),
            'note': 'Outside declared product case budget; not added to product totals.'}
        record['reports'].append(result)
    RESULTS.append(record)

summary = dict(candidate_sha='d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0', production_go=False,
               complete=False, archives=RESULTS, canonical_case_observations=ALL,
               unique_counts=dict(Counter(k.split('/')[0] for k in ALL)),
               note='Work in progress. Repeated case IDs are one canonical case. Tool controls are reported separately. No raw FAIL is overwritten by adjudication.')
(HERE / 'evidence/RECONCILIATION.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(dict(archives=len(RESULTS), unique_counts=summary['unique_counts'],
    reports=Counter(s['reported_status'] for a in RESULTS for s in a['reports']),
    budget_issues=[dict(artifact=a['artifact_id'],file=s['file']) for a in RESULTS for s in a['reports'] if not s['case_budget_match']],
    date_flags=sum(len(s['first_attempt_and_date_flags']) for a in RESULTS for s in a['reports'])), indent=2))
