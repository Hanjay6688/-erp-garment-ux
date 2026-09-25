#!/usr/bin/env python3
"""list_runs.py <workflow file> [n]: latest runs of a workflow on the writer branch (id, head, status, conclusion, event, created)."""
import json,os,sys,urllib.request
wf=sys.argv[1];n=int(sys.argv[2]) if len(sys.argv)>2 else 5
req=urllib.request.Request(f'https://api.github.com/repos/Hanjay6688/-erp-garment-ux/actions/workflows/{wf}/runs?per_page={n}&branch=claude/new-session-deapao',
    headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
for r in json.loads(urllib.request.urlopen(req).read())['workflow_runs']:
    print(wf,r['id'],r['head_sha'][:7],r['status'],r['conclusion'],r['event'],r['created_at'])
