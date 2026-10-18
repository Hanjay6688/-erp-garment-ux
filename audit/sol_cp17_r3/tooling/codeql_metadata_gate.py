"""Existing SARIF gate with product identity separated from workflow identity.

Only identity binding is changed from scripts/cp6_codeql_artifact_gate.py.
No CodeQL query, scan invocation, application code or business oracle is run here.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

EXPECTED_PRODUCT_SHA = "b53b5acdf260b03ebac3474e9ae837fcef6f6eb1"
EXPECTED_PRODUCT_TREE = "32f54240a60e01ab8b1ffad7267d285a669be520"


def bind_identity(head, tree, workflow_sha):
    if head != EXPECTED_PRODUCT_SHA:
        raise ValueError("CODEQL_PRODUCT_HEAD_MISMATCH")
    if tree != EXPECTED_PRODUCT_TREE:
        raise ValueError("CODEQL_PRODUCT_TREE_MISMATCH")
    if not re.fullmatch(r"[0-9a-f]{40}", workflow_sha):
        raise ValueError("CODEQL_WORKFLOW_SHA_INVALID")
    return dict(head=head, tree=tree, workflow_sha=workflow_sha,
        expected_product_sha=EXPECTED_PRODUCT_SHA, expected_product_tree=EXPECTED_PRODUCT_TREE)


def main():
    root=Path('cp6-codeql')
    files=sorted((root/'sarif').glob('*.sarif'))
    if not files:raise SystemExit('CODEQL_SARIF_MISSING')
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()
    identity=bind_identity(head,tree,os.environ['GITHUB_SHA'])
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
            for finding in findings:
                location=(finding.get('locations') or [{}])[0].get('physicalLocation',{})
                print('CODEQL_FINDING '+json.dumps({'rule':finding.get('ruleId'),'file':location.get('artifactLocation',{}).get('uri'),
                    'line':location.get('region',{}).get('startLine'),'message':(finding.get('message') or {}).get('text','')[:300]}),flush=True)
            observations.append({'file':str(path.relative_to(root)),
                'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
                'tool':run['tool']['driver']['name'],'version':run['tool']['driver'].get('semanticVersion',run['tool']['driver'].get('version')),
                'rule_count':sum(len(component.get('rules',[])) for component in
                    [run['tool']['driver'],*run['tool'].get('extensions',[])]),
                'query_packs':[{'name':x['name'],'version':x.get('semanticVersion'),
                    'rule_count':len(x.get('rules',[]))} for x in run['tool'].get('extensions',[])],
                'result_count':len(findings),'execution_successful':True})
    result={**identity,'metadata_qualification':'SOL_METADATA_Q1','original_run_id':39146762479,
        'run_id':int(os.environ['GITHUB_RUN_ID']),'attempt':int(os.environ['GITHUB_RUN_ATTEMPT']),
        'language':os.environ['CP6_CODEQL_LANGUAGE'],'queries':'security-extended',
        'classification':'NATIVE_CODEQL_SARIF_ARTIFACT_NOT_CODE_SCANNING_UPLOAD',
        'observations':observations,'production_go':False,
        'status':'PASS' if all(x['result_count']==0 and x['rule_count']>0 for x in observations) else 'FAIL'}
    (root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'language':result['language'],
        'result_count':sum(x['result_count'] for x in observations),'production_go':False}))
    if result['status']!='PASS':raise SystemExit(1)


if __name__ == "__main__":
    main()
