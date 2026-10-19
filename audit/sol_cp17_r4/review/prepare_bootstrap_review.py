"""Verify exact captured job logs and retain the one pre-case startup failure."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = ROOT / 'ci_receipts'
    index_path = base / 'OWN_JOB_LOG_INDEX.json'
    index = json.loads(index_path.read_text())
    jobs = []
    for row in index['jobs']:
        data = (base / row['log_path']).read_bytes()
        assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256']
        text = data.decode()
        assert len(text) == row['decoded_codepoints'] and row['run_attempt'] == 1
        lines = text.splitlines()
        marks = [(i + 1, int(m.group(1)), m.group(2)) for i, line in enumerate(lines)
                 for m in [re.search(r'supabase start succeeded on attempt (\d+) from (\S+)', line)] if m]
        assert [r[1] for r in marks] == [r['attempt'] for r in row['bootstrap_markers']]
        # The collector retains its broad step-name list. Later workflows name
        # their case entrypoint "Qualify/Execute/Observe", so disclose rather
        # than relabel those failed business/qualification steps as setup PASS.
        qualification_steps = [s for s in row['setup_steps'] if s['name'].startswith(('Qualify ', 'Execute ', 'Observe '))]
        install_steps = [s for s in row['setup_steps'] if s not in qualification_steps]
        assert all(s['conclusion'] == 'success' for s in install_steps)
        failed_qualification = [s for s in qualification_steps if s['conclusion'] == 'failure']
        assert all(s['conclusion'] in ('success','failure') for s in qualification_steps)
        cases = []
        for i, line in enumerate(lines):
            start = line.find('{"group":')
            if start < 0:
                continue
            try:
                parsed = json.JSONDecoder().raw_decode(line[start:])[0]
            except ValueError:
                continue
            if 'case' in parsed and 'status' in parsed:
                cases.append((i + 1, parsed))
        startup = None
        if marks and marks[0][1] > 1:
            assert row['job_id'] == 117846167103 and marks[0][1] == 2
            failed = [(i + 1, line) for i, line in enumerate(lines) if 'failed to bind host port' in line]
            assert len(failed) == 1 and failed[0][0] < marks[0][0] < cases[0][0]
            startup = {'classification': 'INFRA_RACE_RERUN_PASSED',
                       'first_failure_line': failed[0][0], 'first_failure': failed[0][1],
                       'successful_bootstrap_line': marks[0][0], 'successful_bootstrap': lines[marks[0][0] - 1],
                       'first_case_line': cases[0][0], 'first_case_id': cases[0][1]['case'],
                       'github_run_attempt': 1, 'github_job_rerun': False,
                       'disposition': 'The local database container could not bind port54322 before any case/admission output. Existing bootstrap stopped containers and retried once with registry fallback. Start succeeded at02:00:54Z; first case at02:02:12Z. Guide1.9/16.3 permits one pre-case prerequisite retry; no product result or case failure was retried.',
                       'limitation': 'Copied workflow bootstrap loop allows up to4 attempts; only2 occurred. Future auditor harness should enforce the guide limit directly. No product change requested.'}
        else:
            assert all(mark[1] == 1 for mark in marks)
        jobs.append({'run_id': row['run_id'], 'job_id': row['job_id'], 'workflow_sha': row['workflow_sha'],
                     'run_attempt': 1, 'log_path': row['log_path'], 'sha256': row['sha256'], 'bytes': row['bytes'],
                     'bootstrap_success_attempts': [m[1] for m in marks], 'installation_bootstrap_steps_all_success': True,
                     'collector_setup_list_includes_qualification_entrypoint': bool(qualification_steps),
                     'failed_qualification_entrypoints_preserved': failed_qualification,
                     'case_log_rows': len(cases), 'case_log_status_counts': dict(Counter(r['status'] for _, r in cases)),
                     'precase_startup_retry': startup})
    result = {'state': 'FINAL_ALL60_REGISTERED_RUNS_TERMINAL_LOGS_REVIEWED',
              'source_index_path': 'ci_receipts/OWN_JOB_LOG_INDEX.json', 'source_index_sha256': sha256(index_path.read_bytes()).hexdigest(),
              'exact_decoded_text_not_provider_zip_bytes': True, 'job_count': len(jobs),
              'jobs_with_database_bootstrap': sum(bool(r['bootstrap_success_attempts']) for r in jobs),
              'bootstrap_attempt_counts': dict(Counter(a for r in jobs for a in r['bootstrap_success_attempts'])),
              'failed_installation_bootstrap_steps_at_provider_step_level': 0,
              'failed_qualification_steps_in_collector_setup_name_list': sum(len(r['failed_qualification_entrypoints_preserved']) for r in jobs),
              'precase_startup_failures_retained': sum(bool(r['precase_startup_retry']) for r in jobs),
              'any_github_run_attempt_above_one': False, 'missing_or_hash_mismatch': 0, 'jobs': jobs,
              'limitation': 'Bootstrap retry is separate from GitHub attempt and business-day/case retry. Business outcomes require per-case review; no acceptance inferred from job success.'}
    (ROOT / 'OWN_BOOTSTRAP_REVIEW.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f"{len(jobs)} exact logs verified; bootstrap counts{result['bootstrap_attempt_counts']}; one original pre-case port failure retained, no GitHub rerun.")


if __name__ == '__main__':
    main()
