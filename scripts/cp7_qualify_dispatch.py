"""Dispatch every qualification workflow that has no run yet on SHA, on a branch whose head is SHA (or docs-only beyond it).

usage: python3 scripts/cp7_qualify_dispatch.py SHA BRANCH [WORKFLOWS.json] [--dry]
WORKFLOWS.json defaults to docs/cp7/audit-candidate/cp1-7-r6-20261019/QUALIFICATION_WORKFLOWS.json (the 116 workflow files
of the r6 qualification). The full CP6 writer scenario is a second CP6 Auditor Scenario run with inputs and is dispatched
separately (see the r6 README, E25w): scenario_path=scripts/cp6_bf_combined_modes.py,
browser_path=scripts/cp6_bf_vendor_browser.mjs, phase=after.
"""
import json
import subprocess
import sys

import yaml

REPO = 'repos/Hanjay6688/-erp-garment-ux'


def api(path, *a):
    return json.loads(subprocess.check_output(['gh', 'api', path, *a]))


def main():
    args = [a for a in sys.argv[1:] if a != '--dry']
    dry = '--dry' in sys.argv
    sha, branch = args[0], args[1]
    files = json.load(open(args[2] if len(args) > 2 else
                           'docs/cp7/audit-candidate/cp1-7-r6-20261019/QUALIFICATION_WORKFLOWS.json'))
    runs, page = [], 1
    while True:
        rs = api(f'{REPO}/actions/runs?head_sha={sha}&per_page=100&page={page}')['workflow_runs']
        runs += rs
        if len(rs) < 100:
            break
        page += 1
    have = {r['path'] for r in runs}
    todo = [f for f in files if f not in have]
    print(json.dumps(dict(total=len(files), have=len(have & set(files)), todo=len(todo), runs_on_sha=len(runs))))
    for f in todo:
        on = yaml.safe_load(open(f)).get(True) or {}
        if isinstance(on, dict) and 'workflow_dispatch' not in on:
            print('NO DISPATCH', f)
            continue
        if dry:
            print('would dispatch', f)
            continue
        subprocess.check_call(['gh', 'api', '-X', 'POST', f'{REPO}/actions/workflows/{f.split("/")[-1]}/dispatches',
                               '-f', f'ref={branch}'])
        print('dispatched', f, flush=True)


if __name__ == '__main__':
    main()
