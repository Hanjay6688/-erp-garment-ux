#!/usr/bin/env python3
"""Restore immutable AC using its admitted bootstrap/apply commands only.

This is runtime construction for new independent tests. It makes no claim to
re-execute inherited regression or maintenance matrices. Those are separately
verified and reused from Native200/AB189.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,zipfile
import yaml

HEAD='1bdca3766f7c9800d68295ff5122798060b8a05d'
TREE='334629c626257b8b713826f491cdf62385d5299b'

def reuse_bootstrap_input(proof):
    """Supply X's original pre-U table inventory, with frozen transport pins.

    This is an input to construction, never a newly executed test result. X's
    unchanged commands compare the entire old table-name set with the live DB.
    No archived SQL, scripts or catalog definitions are executed here.
    """
    archive=Path(os.environ['CP6_AC_WRITER_ARTIFACT'])
    assert archive.stat().st_size==6881232
    assert hashlib.sha256(archive.read_bytes()).hexdigest()=='eeb76d0c63e5e78514e44a3acd958177a0d39810b89663c538dd93ffef29ae04'
    name='CP6_V2620U_FAILED150_PREDICATES.json'
    expected='5413e679617a5e1edca8d95669d0d11140e94828478f9f4b08f22abfa34b1b88'
    found=None
    with zipfile.ZipFile(archive) as outer:
        assert outer.testzip() is None
        transfer=json.loads(outer.read('CP6_NATIVE_TRANSFER.json'))
        assert transfer['identity']['head_sha']==HEAD and transfer['identity']['head_tree']==TREE
        assert transfer['identity']['run_id']==34956212157
        assert transfer['status']=='PASS' and transfer['production_go'] is False
        assert hashlib.sha256(outer.read('CP6_NATIVE_PROOF.tar.xz')).hexdigest()=='14e692626892f0a9614d2389cc728513758d6e37f511b8d2d630079c93f3f69e'
        with outer.open('CP6_NATIVE_PROOF.tar.xz') as stream,tarfile.open(fileobj=stream,mode='r|xz') as tar:
            for member in tar:
                if member.name!=name:
                    # Drain bounded chunks: tarfile's implicit stream skip can
                    # repeatedly concatenate a very large archived log.
                    if member.isfile():
                        with tar.extractfile(member) as unused:
                            while unused.read(1024*1024):pass
                    continue
                assert member.isfile() and member.size==157463
                found=tar.extractfile(member).read()
                break
    assert found is not None and hashlib.sha256(found).hexdigest()==expected
    assert len(json.loads(found)['baseline']['tables'])==208
    assert not (proof/name).exists()
    (proof/name).write_bytes(found)
    reuse={'status':'REUSED_VERIFIED_BOOTSTRAP_INPUT','run_id':34956212157,
           'artifact_id':10392910720,'candidate_head':HEAD,'path':name,
           'sha256':expected,'bytes':len(found),'historical_test_reexecuted':False,
           'purpose':'Exact pre-U table names consumed by unchanged X admission commands',
           'production_go':False}
    (proof/'AC_AUDIT_REUSED_BOOTSTRAP_INPUT.json').write_text(json.dumps(reuse,indent=2)+'\n')
    return reuse

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
    reused=reuse_bootstrap_input(proof)
    report={'status':'INCOMPLETE','candidate_head':HEAD,'candidate_tree':TREE,'audit_harness_head':os.environ['CP6_AUDIT_HARNESS_HEAD'],'frozen_workflow_sha256':hashlib.sha256(workflow).hexdigest(),'production_go':False,'steps':[]}
    report['reused_bootstrap_input']=reused
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
