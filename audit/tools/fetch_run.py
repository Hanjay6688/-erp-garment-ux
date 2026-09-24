#!/usr/bin/env python3
"""Fetch the auditor-scenario run's job log, save it, and summarize per-case JSON lines.
Usage: fetch_run.py <run_id>  -> writes SP/logs/auditor_<run_id>.log and SP/out/auditor_<run_id>.json"""
import json,os,re,sys,time,urllib.request,collections
SP='/tmp/claude-0/-home-user--erp-garment-ux/2a0eb6c3-bb79-5f14-b9f8-6487e74e773f/scratchpad'
tok=os.environ['GITHUB_TOKEN']; run_id=int(sys.argv[1])
def api(url,raw=False):
    req=urllib.request.Request('https://api.github.com'+url,headers={'Authorization':'Bearer '+tok,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req) as r: return r.read() if raw else json.loads(r.read().decode())
while True:
    run=api(f'/repos/Hanjay6688/-erp-garment-ux/actions/runs/{run_id}')
    if run['status']=='completed': break
    time.sleep(20)
jobs=api(f'/repos/Hanjay6688/-erp-garment-ux/actions/runs/{run_id}/jobs')['jobs']
job=jobs[0]
log=api(f'/repos/Hanjay6688/-erp-garment-ux/actions/jobs/{job["id"]}/logs',raw=True).decode(errors='replace')
open(f'{SP}/logs/auditor_{run_id}.log','w').write(log)
objs=[]
for line in log.split('\n'):
    m=re.match(r'^\S+\s(.*)$',line); body=m.group(1) if m else line
    if body.startswith('{'):
        try: objs.append(json.loads(body))
        except Exception: pass
cases=[o for o in objs if 'group' in o and 'case' in o]
meta=[o for o in objs if 'auditor_scenario_sha256' in o or 'auditor_setup' in o or 'auditor_phase' in o]
summary=dict(run_id=run_id,head_sha=run['head_sha'],conclusion=run['conclusion'],job_id=job['id'],job_conclusion=job['conclusion'],
             meta=meta,counts=dict(collections.Counter(c.get('status') for c in cases)),planned=None,cases=cases)
for o in objs:
    if 'planned_case_ids' in o: summary['planned']=o['planned_case_ids']
json.dump(summary,open(f'{SP}/out/auditor_{run_id}.json','w'),default=str,indent=1)
print(json.dumps({k:summary[k] for k in ('run_id','head_sha','conclusion','job_id','job_conclusion','counts')}))
for m in meta: print(json.dumps(m,default=str)[:600])
for c in cases: print(c['case'],'|',c.get('status'),'|',json.dumps({k:v for k,v in c.items() if k not in ('group','case','status','traceback')},default=str)[:400])
