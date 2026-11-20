import json
import os
from pathlib import Path
import re
from .source import PRODUCT,TREE

work=Path(os.environ['GITHUB_WORKSPACE']); evidence=work/'close11-evidence';evidence.mkdir(exist_ok=True)
scratch=Path(os.environ['RUNNER_TEMP'])/'cp7-live-parent';t3=work/'global-candidate/cp6-proof/t3'
def read(path):
    return json.loads(path.read_bytes()) if path.exists() else {}
proof=read(evidence/'installed.json')
writer=read(t3/'CP7_GLOBAL_FIRST_SNAPSHOTS.json')
supervisor=read(scratch/'ordinary-supervision.json')
first=read(evidence/'first-failure.json') or read(scratch/'ordinary-preflight-failure.json') or read(scratch/'ordinary-worker-failure.json')
# Retain safe first installation diagnostics on the very first failure, including metadata emitted by Postgres.
phases=[]
for log in (scratch/'ordinary-worker.log',scratch/'ordinary-preflight.log'):
    if log.exists():
        for line in log.read_text(errors='replace').splitlines():
            if re.fullmatch(r'GLOBAL_ORDINARY_PHASE [A-Z0-9_]+ (STARTED|FAILED|COMPLETED)',line):phases.append(line)
            if not first and re.fullmatch(r'(?:ValueError|RuntimeError|AssertionError): [A-Z][A-Z0-9_]{5,100}',line):
                first={'reason':line}
ok=bool(proof and proof.get('status')=='COMMITTED' and proof.get('product')==PRODUCT and proof.get('tree')==TREE
        and proof.get('catalogue_verified_after_scheduler') is True and len(proof.get('catalogue_groups',{}))==25 and proof.get('checkpoint',{}).get('sha256')
        and os.environ['CLEANUP']=='success' and os.environ['RUNTIME']=='success'
        and os.environ['PRIOR_JOB']=='success' and supervisor.get('status')=='WORKER_COMPLETED_AND_REAPED' and writer.get('status')=='PASS')
result=dict(status='INSTALLED_AND_PRESERVED' if ok else 'INCOMPLETE',product=PRODUCT,tree=TREE,run=os.environ['GITHUB_RUN_ID'],
            writer_installed=bool(read(evidence/'committed.json')),auditor_environment_preserved=bool(proof.get('catalogue_verified_after_scheduler')),runner=os.environ['GITHUB_SHA'],cleanup=os.environ['CLEANUP'],runtime=os.environ['RUNTIME'],
            supervisor=supervisor.get('status'),owning_report=writer.get('status'),first_failure=first,last_phases=phases[-12:],
            checkpoint=proof.get('checkpoint'),auditor_cases_run=0,production_go=False)
(evidence/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if ok else 1)
