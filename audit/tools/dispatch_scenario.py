#!/usr/bin/env python3
"""Dispatch an auditor scenario file to cp6-auditor-scenario.yml on claude/new-session-deapao via the GitHub REST API.
Prints the scenario sha256 (the runner prints the same first line) and records the dispatch in SP/out/dispatch_ledger.jsonl.
Usage: dispatch_scenario.py <scenario.py> <after|before> [note]
Refuses when the branch head is not 9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc at dispatch time."""
import base64,hashlib,json,os,subprocess,sys,time,urllib.request
FROZEN='9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc'
SP='/tmp/claude-0/-home-user--erp-garment-ux/2a0eb6c3-bb79-5f14-b9f8-6487e74e773f/scratchpad'
path,phase=sys.argv[1],sys.argv[2]; note=sys.argv[3] if len(sys.argv)>3 else ''
assert phase in ('after','before')
data=open(path,'rb').read(); sha=hashlib.sha256(data).hexdigest()
compile(data,path,'exec')  # syntax check
tok=os.environ['GITHUB_TOKEN']
def api(method,url,body=None):
    req=urllib.request.Request('https://api.github.com'+url,method=method,data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+tok,'Accept':'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req) as r: return r.status,(r.read().decode() or '')
st,head=api('GET','/repos/Hanjay6688/-erp-garment-ux/git/ref/heads/claude/new-session-deapao')
head_sha=json.loads(head)['object']['sha']
assert head_sha==FROZEN,('BRANCH_MOVED',head_sha)
before=json.loads(api('GET','/repos/Hanjay6688/-erp-garment-ux/actions/workflows/cp6-auditor-scenario.yml/runs?per_page=1')[1])['workflow_runs']
before_id=before[0]['id'] if before else 0
st,_=api('POST','/repos/Hanjay6688/-erp-garment-ux/actions/workflows/cp6-auditor-scenario.yml/dispatches',
         {'ref':'claude/new-session-deapao','inputs':{'scenario_b64':base64.b64encode(data).decode(),'phase':phase}})
assert st==204,st
run_id=None
for _ in range(30):
    time.sleep(4)
    runs=json.loads(api('GET','/repos/Hanjay6688/-erp-garment-ux/actions/workflows/cp6-auditor-scenario.yml/runs?per_page=5')[1])['workflow_runs']
    newer=[r for r in runs if r['id']>before_id and r['event']=='workflow_dispatch']
    if newer:
        run_id=max(r['id'] for r in newer); run=[r for r in newer if r['id']==run_id][0]; break
rec=dict(scenario=os.path.basename(path),scenario_sha256=sha,bytes=len(data),phase=phase,note=note,run_id=run_id,head_sha=run['head_sha'] if run_id else None,
         created_at=run['created_at'] if run_id else None,dispatched_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
open(SP+'/out/dispatch_ledger.jsonl','a').write(json.dumps(rec)+'\n')
print(json.dumps(rec))
