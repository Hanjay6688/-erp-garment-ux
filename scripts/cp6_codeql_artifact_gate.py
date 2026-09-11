"""Persist complete SARIF and reject findings or incomplete CodeQL execution.

No Code Scanning upload or repository setting change: these are separate,
commit-bound competition artifacts. SQL/business proof is provided by native CI.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

root=Path('cp6-codeql')
files=sorted((root/'sarif').glob('*.sarif'))
if not files:raise SystemExit('CODEQL_SARIF_MISSING')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if head!=os.environ['GITHUB_SHA']:raise SystemExit('CODEQL_HEAD_MISMATCH')
observations=[]
for path in files:
    data=path.read_bytes();document=json.loads(data)
    runs=document.get('runs',[])
    if not runs:raise SystemExit('CODEQL_RUNS_MISSING')
    for run in runs:
        invocations=run.get('invocations',[])
        if not invocations or any(i.get('executionSuccessful') is not True for i in invocations):
            raise SystemExit('CODEQL_EXECUTION_INCOMPLETE')
        findings=run.get('results',[])
        observations.append({'file':str(path.relative_to(root)),
            'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
            'tool':run['tool']['driver']['name'],'version':run['tool']['driver'].get('semanticVersion',run['tool']['driver'].get('version')),
            'rule_count':sum(len(component.get('rules',[])) for component in
                [run['tool']['driver'],*run['tool'].get('extensions',[])]),
            'query_packs':[{'name':x['name'],'version':x.get('semanticVersion'),
                'rule_count':len(x.get('rules',[]))} for x in run['tool'].get('extensions',[])],
            'result_count':len(findings),'execution_successful':True})
result={'head':head,'tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip(),
    'run_id':int(os.environ['GITHUB_RUN_ID']),'attempt':int(os.environ['GITHUB_RUN_ATTEMPT']),
    'language':os.environ['CP6_CODEQL_LANGUAGE'],'queries':'security-extended',
    'classification':'NATIVE_CODEQL_SARIF_ARTIFACT_NOT_CODE_SCANNING_UPLOAD',
    'observations':observations,'production_go':False,
    'status':'PASS' if all(x['result_count']==0 and x['rule_count']>0 for x in observations) else 'FAIL'}
(root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'language':result['language'],
    'result_count':sum(x['result_count'] for x in observations),'production_go':False}))
if result['status']!='PASS':raise SystemExit(1)
