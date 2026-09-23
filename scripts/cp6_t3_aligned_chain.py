#!/usr/bin/env python3
"""T3 preparation: rebuild the disposable chain to v2.6.20, align it with hosted Enteng (G-01 option 1), then continue
the frozen upgrade path to AC exactly as the AC bootstrap does.

Owner (23 Sep 2026): T3 stays HOLD until every G-01 difference is explained and the AO-AV install passes. This runner
only builds the hosted-faithful starting point and replays the frozen AC path on it; the later stages (AD..AN from
the workflow, AO..AX from scripts/cp6_t3_aligned_install.py) record PASS or the exact refusal. No guard is changed.
Label: T3_PREP (not release evidence).
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys
import yaml

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(AUDITOR/'scripts'))
import cp6_ac_audit_bootstrap as ac
import cp6_g01_baseline as g01

AC_STEP='Apply exact AC temporal surface closure and verify 272 runtime objects'
# The frozen AC refuses on the aligned chain (run 35911530080); the T3 release package starts after AB.
AB_STEP='Apply AB statement-time Jakarta business dates before every final-runtime proof'


def run(out,stop=AC_STEP):
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==ac.HEAD
    assert os.environ.get('PGURL')=='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
    workflow=Path('.github/workflows/cp6-full-schema-validation.yml').read_bytes()
    assert workflow==subprocess.check_output(['git','show',ac.HEAD+':.github/workflows/cp6-full-schema-validation.yml'])
    w=yaml.safe_load(workflow);steps=w['jobs']['validate-full-schema']['steps']
    names={'Verify immutable CP4.5a catalog/config bootstrap','Restore exact CP4.5a schema and allowlisted configuration',
           'Capture exact pre-Cutting and pre-CP5 boundary','Prove exact recorded and unused v2.6.18 boundary',
           'Capture exact v2.6.19c predecessor before CP6'}
    proof=Path('cp6-proof');proof.mkdir(exist_ok=True)
    report={'label':'T3_PREP','status':'INCOMPLETE','frozen_head':ac.HEAD,'frozen_workflow_sha256':hashlib.sha256(workflow).hexdigest(),
            'reused_bootstrap_input':ac.reuse_bootstrap_input(proof),'aligned_after':g01.STOP,'stop_after':stop,'steps':[],
            'production_go':False,'release_evidence':False}
    env=os.environ.copy();env.update(w['env']);env['GITHUB_SHA']=ac.HEAD;env['PYTHONPATH']='scripts'
    aligned=False
    for step in steps:
        name=step.get('name','')
        if name not in names and not name.startswith('Apply '):continue
        code=step['run'].split('\nset +e\n',1)[0]
        script=proof/('t3-chain-'+str(len(report['steps']))+'.sh');script.write_text(code+'\n')
        log=script.with_suffix('.log')
        print('APPLY '+name,flush=True)
        with log.open('wb') as f:completed=subprocess.run(['bash',str(script)],env=env,stdout=f,stderr=subprocess.STDOUT)
        report['steps'].append({'name':name,'code_sha256':hashlib.sha256(code.encode()).hexdigest(),'exit_code':completed.returncode,
                                'after_alignment':aligned})
        if completed.returncode:
            report['status']='REFUSED_AT_STEP';report['refused_step']=name;report['refusal_log_tail']=log.read_text()[-6000:]
            print(report['refusal_log_tail']);Path(out).write_text(json.dumps(report,indent=2)+'\n');return completed.returncode
        if name==g01.STOP:
            # Hosted-faithful point: align the differing definitions from read-only hosted metadata, verified per object.
            align=subprocess.run([sys.executable,str(AUDITOR/'scripts/cp6_g01_align.py'),'apply',str(proof/'T3_ALIGN_PER_OBJECT.json')],
                                 env=env,capture_output=True,text=True)
            report['alignment']=json.loads((proof/'T3_ALIGN_PER_OBJECT.json').read_text()) if (proof/'T3_ALIGN_PER_OBJECT.json').exists() else None
            print(align.stdout[-2000:],align.stderr[-2000:],flush=True)
            if align.returncode:
                report['status']='ALIGNMENT_FAILED';Path(out).write_text(json.dumps(report,indent=2)+'\n');return align.returncode
            aligned=True
        if name==stop:break
    assert report['steps'][-1]['name']==stop and aligned
    report['status']='PASS_ALIGNED_CHAIN_TO_'+('AC' if stop==AC_STEP else 'AB')
    Path(out).write_text(json.dumps(report,indent=2)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(run(sys.argv[1],AB_STEP if sys.argv[2:]==['--stop-after-ab'] else AC_STEP))
