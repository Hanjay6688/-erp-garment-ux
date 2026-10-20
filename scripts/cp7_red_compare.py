"""Every red run on SHA against the red run of the same workflow in the previous package: failing jobs and steps.

usage: python3 scripts/cp7_red_compare.py SHA PREVIOUS_RED.json OUT.json
PREVIOUS_RED.json is a list of {"workflow": name, "run_id": id} (e.g. the previous package's RED_RUNS_VS_*.json). A run is
"same" only when its failing jobs and failing steps equal the previous run's; anything else is listed as new (never hidden).
"""
import json
import subprocess
import sys

REPO = 'repos/Hanjay6688/-erp-garment-ux'


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path]))


def failing(run_id):
    jobs = api(f'{REPO}/actions/runs/{run_id}/jobs?per_page=100')['jobs']
    return sorted([j['name'], j['conclusion'], sorted(s['name'] for s in j.get('steps', []) if s['conclusion'] == 'failure')]
                  for j in jobs if j['conclusion'] not in ('success', 'skipped'))


def main():
    sha, prev_path, out_path = sys.argv[1:4]
    runs, page = [], 1
    while True:
        rs = api(f'{REPO}/actions/runs?head_sha={sha}&per_page=100&page={page}')['workflow_runs']
        runs += rs
        if len(rs) < 100:
            break
        page += 1
    prev = {x['workflow']: x for x in json.load(open(prev_path))}
    out = []
    for r in sorted(runs, key=lambda r: r['name']):
        if r['conclusion'] == 'success':
            continue
        jobs = failing(r['id'])
        e = dict(workflow=r['name'], run_id=r['id'], conclusion=r['conclusion'], run_attempt=r['run_attempt'], jobs=jobs)
        if r['name'] in prev:
            pj = failing(prev[r['name']]['run_id'])
            e['previous_red_run'] = prev[r['name']]['run_id']
            e['same_jobs_steps_as_previous'] = pj == jobs
            if pj != jobs:
                e['previous_jobs'] = pj
        else:
            e['previous_red_run'] = None
            e['same_jobs_steps_as_previous'] = False
        out.append(e)
    json.dump(out, open(out_path, 'w'), indent=1)
    print(len(runs), 'runs;', len(out), 'red;', sum(e['same_jobs_steps_as_previous'] for e in out), 'same as previous;',
          [e['workflow'] for e in out if not e['same_jobs_steps_as_previous']])


if __name__ == '__main__':
    main()
