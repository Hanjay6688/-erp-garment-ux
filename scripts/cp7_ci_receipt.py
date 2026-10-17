"""CI receipt for one commit: every workflow run and job on that SHA, plus the business-day lines of each job.

usage: python3 scripts/cp7_ci_receipt.py SHA OUT.json   (needs `gh api` access to this repository)

When the WIB business day changes during a group, the auditor runtime (scripts/cp6_auditor_business_day.py
with_retry) prints a JSON line and, on GitHub Actions, a warning annotation titled
AUDITOR_BUSINESS_DAY_RERUN_FROM_FRESH_COPY (the group ran again; the first attempt is kept) or
AUDITOR_BUSINESS_DAY_KEPT_FIRST_RESULT (no rerun; the rolled cases need a person). Fable F-TOOL-01 asked for
these in the receipt, so a status that came from a second attempt is visible without reading every log. The
annotations are read through the API (check run id = job id), which needs no log download.
"""
import json, subprocess, sys

REPO = 'repos/Hanjay6688/-erp-garment-ux'
PREFIX = 'AUDITOR_BUSINESS_DAY_'


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path]))


def pages(path, key=None):
    """Every page of a GitHub list (r3, Sol KNOWN-RECEIPT-FIRST100: the first page alone held 100 of 115 runs)."""
    rows, page = [], 1
    while True:
        batch = api(f'{path}{"&" if "?" in path else "?"}per_page=100&page={page}')
        batch = batch[key] if key else batch
        rows += batch
        if len(batch) < 100: return rows
        page += 1


def markers(job_id):
    notes = pages(f'{REPO}/check-runs/{job_id}/annotations')
    return [dict(kind=n['title'][len(PREFIX):], message=n['message']) for n in notes if (n.get('title') or '').startswith(PREFIX)]


def main(sha, out):
    runs = pages(f'{REPO}/actions/runs?head_sha={sha}', 'workflow_runs')
    rows = []
    for r in sorted(runs, key=lambda r: r['name']):
        jobs = pages(f"{REPO}/actions/runs/{r['id']}/jobs", 'jobs')
        rows.append(dict(workflow=r['name'], run_id=r['id'], attempt=r['run_attempt'], event=r['event'], status=r['status'],
                         conclusion=r['conclusion'],
                         jobs=[dict(name=j['name'], job_id=j['id'], conclusion=j['conclusion'], business_day=markers(j['id']))
                               for j in jobs]))
    seen = [dict(workflow=r['workflow'], job=j['name'], **m) for r in rows for j in r['jobs'] for m in j['business_day']]
    summary = dict(sha=sha, workflows=len(rows), workflows_success=sum(r['conclusion'] == 'success' for r in rows),
                   jobs=sum(len(r['jobs']) for r in rows),
                   jobs_success=sum(j['conclusion'] == 'success' for r in rows for j in r['jobs']),
                   not_success=[(r['workflow'], j['name'], j['conclusion']) for r in rows for j in r['jobs'] if j['conclusion'] != 'success'],
                   first_attempt_only=all(r['attempt'] == 1 for r in rows),
                   business_day_reruns=[m for m in seen if m['kind'] == 'RERUN_FROM_FRESH_COPY'],
                   business_day_kept_first=[m for m in seen if m['kind'] == 'KEPT_FIRST_RESULT'])
    json.dump(dict(summary=summary, runs=rows), open(out, 'w'), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:3])
