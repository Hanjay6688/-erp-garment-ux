#!/usr/bin/env python3
"""Run all 23 AA oracles before and after AB; retain every failed observation."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

GROUPS = {
    'invoice_partial': ('scripts/cp6_aa_invoice_partial_audit.py', 'AA_INVOICE_PARTIAL_AUDIT.json', 16),
    'revocation': ('scripts/cp6_aa_revocation_audit.py', 'revocation/AA_REVOCATION_AUDIT.json', 3),
    'midnight': ('scripts/cp6_aa_midnight_audit.py', 'midnight/AA_MIDNIGHT_AUDIT.json', 4),
}
ZONES = ('Asia/Jakarta', 'UTC', 'Etc/GMT+12', 'Pacific/Kiritimati')


def validate_wave(phase, reports, head):
    assert phase in ('AA_AUDIT', 'AB_REGRESSION')
    generation = 'AA' if phase == 'AA_AUDIT' else 'AB'
    for group, (_, _, count) in GROUPS.items():
        r = reports[group]
        assert r['head'] == head and r['phase'] == phase and r['runtime_generation'] == generation
        assert r['expected_cases'] == len(r['cases']) == count
        assert r['incomplete'] == 0 and r['controls'] + r['counterexamples'] == count
        assert sum(c['status'] == 'CONTROL_PASS' for c in r['cases'].values()) == r['controls']
        assert sum(c['status'] == 'COUNTEREXAMPLE' for c in r['cases'].values()) == r['counterexamples']
        assert r['synthetic_fixture_only'] and not r['hosted_database_used']
        assert r['production_go'] is False and r['independent_acceptance_complete'] is False
        assert r['status'] == ('FAIL_NEW_COUNTEREXAMPLE' if r['counterexamples'] else 'PASS_BOUNDED_AUDIT')
        if phase == 'AB_REGRESSION':
            assert r['controls'] == count and r['counterexamples'] == 0
    invoice = reports['invoice_partial']
    expected_names = {f'{kind}:{zone}:{cost}' for kind in ('ESTIMATED_RECEIPT', 'PARTIAL_CHAIN')
                      for zone in ZONES for cost in ('20', '20.003')}
    assert set(invoice['cases']) == expected_names
    assert invoice['entire_unseeded_runtime_restored'] and invoice['schema_usage_restored']
    assert len(invoice['installed_functions']) == 2
    assert len(invoice['verified_ab_functions']) == (0 if phase == 'AA_AUDIT' else 5)
    expected_failures = set()
    for name, c in invoice['cases'].items():
        assert c['full_boundary_restored']
        assert c.get('replay_boundary_exact') or c.get('rejection_boundary_exact')
        kind, zone, _ = name.split(':')
        clock = datetime.fromisoformat(c['invocation_clocks']['transaction'])
        assert clock.tzinfo is not None
        different_day = clock.astimezone(ZoneInfo(zone)).date() != clock.astimezone(ZoneInfo('Asia/Jakarta')).date()
        if phase == 'AA_AUDIT' and kind == 'PARTIAL_CHAIN' and different_day:
            expected_failures.add(name)
        if c['status'] == 'COUNTEREXAMPLE':
            assert c['severity'] == 'P2' and c['partial'] is True
            if c['stage'] == 'AFTER_INVOICE':
                assert c['mismatches'] and all(k.endswith('.business_day') for k in c['mismatches'])
            else:
                assert c['stage'] == 'LAWFUL_LATE_INVOICE_REFUSED_BY_CALLER_ZONE'
                assert invoice['cases'][c['paired_control']]['status'] == 'CONTROL_PASS'
                assert c['rejection_boundary_exact'] and c['invoice_call_error']['sqlstate'] == 'P0001'
        else:
            assert c['replay_boundary_exact'] and not c['mismatches']
    assert {n for n, c in invoice['cases'].items() if c['status'] == 'COUNTEREXAMPLE'} == expected_failures
    if phase == 'AA_AUDIT':
        # Current_date depends on runner time. Require precisely the affected
        # caller dates, not a fixed count that only works during one UTC hour.
        assert 2 <= len(expected_failures) <= 4
    revocation = reports['revocation']
    assert set(revocation['cases']) == {'ACTIVE_CONTROL', 'REVOKED_AFTER_TRANSACTION_START', 'REVOKED_WHILE_POST_WAITS'}
    assert revocation['controls'] == 3 and revocation['counterexamples'] == 0
    assert revocation['source_boundary_unchanged']
    assert all(c['status'] == 'CONTROL_PASS' and c['remaining_clone_databases'] == 0 for c in revocation['cases'].values())
    midnight = reports['midnight']
    assert set(midnight['cases']) == {f'{tx}:{source}' for tx in ('FRESH', 'LONG')
                                    for source in ('PRIOR_DAY_SOURCE', 'CURRENT_DAY_SOURCE')}
    assert midnight['physical_copy_boundary_exact'] and midnight['application_function_modifications'] == 0
    assert not midnight['cleanup_errors'] and midnight['remaining_clock_containers'] == 0
    assert midnight['source_boundary_unchanged'] and midnight['source_clock_still_real']
    assert midnight['source_postgres_sha256'] == midnight['copy_postgres_sha256']
    assert all(c['full_boundary_restored'] for c in midnight['cases'].values())
    expected_midnight = {'LONG:PRIOR_DAY_SOURCE', 'LONG:CURRENT_DAY_SOURCE'} if phase == 'AA_AUDIT' else set()
    assert {n for n, c in midnight['cases'].items() if c['status'] == 'COUNTEREXAMPLE'} == expected_midnight
    if phase == 'AA_AUDIT':
        prior = midnight['cases']['LONG:PRIOR_DAY_SOURCE']
        current = midnight['cases']['LONG:CURRENT_DAY_SOURCE']
        assert prior['severity'] == current['severity'] == 'P2'
        assert 'reverse_business_day' in prior['mismatches']
        assert all(k == 'reverse_business_day' or k.startswith('daily_cash.') for k in prior['mismatches'])
        assert current['classification'] == 'LAWFUL_POST_REJECTED_AFTER_MIDNIGHT_IN_LONG_TRANSACTION'
    return dict(cases=23, controls=sum(r['controls'] for r in reports.values()),
                counterexamples=sum(r['counterexamples'] for r in reports.values()), incomplete=0)


def capture_inputs(root, phase):
    paths = [v[0] for v in GROUPS.values()] + [
        'scripts/cp6_v2620ab_audit_wave.py', 'scripts/cp6_v2620ab_proof.py', 'scripts/cp6_v2620ab_runtime.py',
        'scripts/cp6_v2620ab_install_qualification.py', 'scripts/cp6_v2620ab_rollback_guards.py',
        'supabase/migrations/20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.sql',
        'supabase/rollbacks/20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.rollback.sql',
        'supabase/tests/support/cp6_clock_offset.c', '.github/workflows/cp6-full-schema-validation.yml',
        'docs/cp6-competition-mode-audit-protocol.md', 'docs/evidence/cp6-aa185-writer-verification.json',
        'docs/evidence/cp6-aa186-audit-verification.json', 'docs/evidence/cp6-aa186-qualified-audit.json',
        'docs/evidence/cp6-aa187-audit-verification.json', 'docs/evidence/cp6-aa187-midnight-audit.json',
    ]
    writer = json.loads(Path('docs/evidence/cp6-aa185-writer-verification.json').read_text())
    assert writer['head'] == '7d824f780fa06fc16385c347759a9b96d0138e9d' and writer['native_run_id'] == 34873186373
    assert writer['status'] == 'WRITER_PASS_PENDING_EXPANDED_INDEPENDENT_AUDIT' and writer['native_conclusion'] == 'success'
    assert writer['all_payload_hashes_verified'] and writer['all_source_pins_verified_against_exact_git_commit']
    pins = {}
    for name in paths:
        data = Path(name).read_bytes()
        out = root / ('workflows/' + Path(name).name if name.startswith('.github/') else name)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        pins[name] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), payload=str(out.relative_to(root)))
    result = dict(head=os.environ['GITHUB_SHA'], tree=subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], text=True).strip(),
                  run_id=os.environ['GITHUB_RUN_ID'], phase=phase, source_pins=pins,
                  expected_cases={k:v[2] for k,v in GROUPS.items()}, status='INPUTS_CAPTURED_NOT_A_RUNTIME_PASS', production_go=False)
    (root / 'INPUTS.json').write_text(json.dumps(result, indent=2) + '\n')


def main():
    phase = os.environ['CP6_AB_PHASE']
    assert phase in ('AA_AUDIT', 'AB_REGRESSION')
    root = Path('cp6-proof') / ('independent-aa' if phase == 'AA_AUDIT' else 'independent-ab')
    root.mkdir(parents=True, exist_ok=True)
    result = dict(head=os.environ['GITHUB_SHA'], phase=phase, status='INCOMPLETE', production_go=False,
                  independent_acceptance_complete=False, groups={})
    capture_inputs(root / 'audit-source', phase)
    reports = {}
    for group, (script, report, _) in GROUPS.items():
        with (root / (group + '.log')).open('w') as log:
            code = subprocess.run([sys.executable, script], stdout=log, stderr=subprocess.STDOUT, check=False).returncode
        path = root / report
        try:
            reports[group] = json.loads(path.read_text())
            status = reports[group].get('status', 'INCOMPLETE')
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            status = 'INCOMPLETE'
            result['groups'][group] = dict(error=str(exc))
        result['groups'].setdefault(group, {}).update(exit_code=code, status=status, report=report)
        (root / 'AB_AUDIT_WAVE.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(dict(group=group, phase=phase, status=status, exit_code=code)), flush=True)
    try:
        result.update(validate_wave(phase, reports, os.environ['GITHUB_SHA']))
        for group, report in reports.items():
            assert result['groups'][group]['exit_code'] == (1 if report['counterexamples'] else 0)
        result['status'] = 'EXPECTED_PREDECESSOR_COUNTEREXAMPLES_REPRODUCED' if phase == 'AA_AUDIT' else 'PASS_BOUNDED_REGRESSION'
    except Exception as exc:
        import traceback
        result.update(status='FAIL', error=str(exc), traceback=traceback.format_exc())
    (root / 'AB_AUDIT_WAVE.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    raise SystemExit(1 if result['status'] == 'FAIL' else 0)


if __name__ == '__main__':
    main()
