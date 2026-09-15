#!/usr/bin/env python3
"""Restore immutable AC using its admitted bootstrap/apply commands only.

This is runtime construction for new independent tests. It makes no claim to
re-execute inherited regression or maintenance matrices. Those are separately
verified and reused from Native200/AB189.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys
import yaml

HEAD='1bdca3766f7c9800d68295ff5122798060b8a05d'
TREE='334629c626257b8b713826f491cdf62385d5299b'

def run():
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==HEAD
    assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()==TREE
    assert os.environ.get('PGURL')=='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
    assert os.environ.get('CP6_AC_INDEPENDENT_CONFIRM')=='postgres'
    workflow=Path('.github/workflows/cp6-full-schema-validation.yml').read_bytes()
    assert workflow==subprocess.check_output(['git','show',HEAD+':.github/workflows/cp6-full-schema-validation.yml'])
    w=yaml.safe_load(workflow);steps=w['jobs']['validate-full-schema']['steps']
    names={
        'Verify immutable CP4.5a catalog/config bootstrap',
        'Restore exact CP4.5a schema and allowlisted configuration',
        'Capture exact pre-Cutting and pre-CP5 boundary',
        'Prove exact recorded and unused v2.6.18 boundary',
        'Capture exact v2.6.19c predecessor before CP6',
    }
    proof=Path('cp6-proof');proof.mkdir(exist_ok=True)
    report={'status':'INCOMPLETE','candidate_head':HEAD,'candidate_tree':TREE,'audit_harness_head':os.environ['CP6_AUDIT_HARNESS_HEAD'],'frozen_workflow_sha256':hashlib.sha256(workflow).hexdigest(),'production_go':False,'steps':[]}
    env=os.environ.copy();env.update(w['env']);env['GITHUB_SHA']=HEAD;env['PYTHONPATH']='scripts'
    for step in steps:
        name=step.get('name','')
        if name not in names and not name.startswith('Apply '):continue
        code=step['run'].split('\nset +e\n',1)[0]
        # Replay refusal and historic test commands are not needed to construct
        # the runtime. Preserve the exact apply/ledger/installation commands.
        script=proof/('audit-bootstrap-'+str(len(report['steps']))+'.sh');script.write_text(code+'\n')
        log=script.with_suffix('.log')
        print('RESTORE '+name,flush=True)
        with log.open('wb') as f:completed=subprocess.run(['bash',str(script)],env=env,stdout=f,stderr=subprocess.STDOUT)
        report['steps'].append({'name':name,'code_sha256':hashlib.sha256(code.encode()).hexdigest(),'exit_code':completed.returncode,'log':str(log)})
        (proof/'AC_AUDIT_RUNTIME_BOOTSTRAP.json').write_text(json.dumps(report,indent=2)+'\n')
        if completed.returncode:
            print(log.read_text()[-6000:]);return completed.returncode
        if name=='Apply exact AC temporal surface closure and verify 272 runtime objects':break
    assert report['steps'][-1]['name']=='Apply exact AC temporal surface closure and verify 272 runtime objects'
    report['status']='PASS_EXACT_AC_RUNTIME_RESTORED'
    (proof/'AC_AUDIT_RUNTIME_BOOTSTRAP.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0

if __name__=='__main__':raise SystemExit(run())
