#!/usr/bin/env python3
"""G-01: rebuild the disposable test chain only up to the hosted-equivalent point.

Hosted Enteng carries 70 platform migrations ending with v2.6.20. The CP6 test
chain starts from the CP4.5a read-only catalog bootstrap and replays the local
migration files. This runner executes exactly the same admitted bootstrap and
apply commands that cp6_ac_audit_bootstrap.py executes, from the same frozen
workflow at 1bdca37, but stops right after v2.6.20 instead of continuing to AC.
It then captures the shared read-only catalog fingerprint.

Label: G01_BASELINE (construction plus measurement; no test is claimed).
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys
import yaml

sys.path.insert(0,str(Path(__file__).resolve().parent))
import cp6_ac_audit_bootstrap as ac
import cp6_g01_fingerprint as fp

STOP='Apply v2.6.20 authoritative Laundry-QC-FG bridge once and reject replay'

def run(out):
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==ac.HEAD
    assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()==ac.TREE
    assert os.environ.get('PGURL')=='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
    workflow=Path('.github/workflows/cp6-full-schema-validation.yml').read_bytes()
    assert workflow==subprocess.check_output(['git','show',ac.HEAD+':.github/workflows/cp6-full-schema-validation.yml'])
    w=yaml.safe_load(workflow);steps=w['jobs']['validate-full-schema']['steps']
    names={
        'Verify immutable CP4.5a catalog/config bootstrap',
        'Restore exact CP4.5a schema and allowlisted configuration',
        'Capture exact pre-Cutting and pre-CP5 boundary',
        'Prove exact recorded and unused v2.6.18 boundary',
        'Capture exact v2.6.19c predecessor before CP6',
    }
    proof=Path('cp6-proof');proof.mkdir(exist_ok=True)
    reused=ac.reuse_bootstrap_input(proof)
    report={'label':'G01_BASELINE','status':'INCOMPLETE','frozen_head':ac.HEAD,
        'frozen_workflow_sha256':hashlib.sha256(workflow).hexdigest(),'stop_after':STOP,
        'reused_bootstrap_input':reused,'production_go':False,'steps':[]}
    env=os.environ.copy();env.update(w['env']);env['GITHUB_SHA']=ac.HEAD;env['PYTHONPATH']='scripts'
    for step in steps:
        name=step.get('name','')
        if name not in names and not name.startswith('Apply '):continue
        code=step['run'].split('\nset +e\n',1)[0]
        script=proof/('g01-bootstrap-'+str(len(report['steps']))+'.sh');script.write_text(code+'\n')
        log=script.with_suffix('.log')
        print('RESTORE '+name,flush=True)
        with log.open('wb') as f:completed=subprocess.run(['bash',str(script)],env=env,stdout=f,stderr=subprocess.STDOUT)
        report['steps'].append({'name':name,'code_sha256':hashlib.sha256(code.encode()).hexdigest(),'exit_code':completed.returncode})
        if completed.returncode:
            print(log.read_text()[-6000:]);Path(out).write_text(json.dumps(report,indent=2)+'\n');return completed.returncode
        if name==STOP:break
    assert report['steps'][-1]['name']==STOP
    report['status']='PASS_HOSTED_EQUIVALENT_POINT_RESTORED'
    Path(out).write_text(json.dumps(report,indent=2)+'\n')
    return 0

if __name__=='__main__':raise SystemExit(run(sys.argv[1]))
