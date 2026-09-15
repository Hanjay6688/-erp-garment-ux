#!/usr/bin/env python3
"""Bind completed AD gates to immutable input evidence and lossless output."""
from pathlib import Path
import hashlib,json,os,subprocess,tarfile
import cp6_v2620ad_runtime as runtime

ROOT=Path('cp6-proof');WRITER=ROOT/'writer-ad'

def run():
    head,tree=runtime.verify_audit_source()
    required={'predecessor':'PASS_PREDECESSOR_NEGATIVE_CONTROL_QUALIFIED','successor':'PASS_55_FAMILY_CASES',
      'admission_ATOMIC_CONTROLS':'PASS','rollback_ATOMIC_CONTROLS':'PASS','DETECTOR_NEGATIVE_CONTROLS':'PASS','AD_EXACT_AC_RESTORE':'PASS'}
    gates={}
    for name,status in required.items():
        report=json.loads((WRITER/(name+'.json')).read_text());assert report['status']==status,(name,report['status']);gates[name]=report['status']
    matrix=json.loads((ROOT/'AD_MAINTENANCE_ROLLBACK/manifest.json').read_text())
    assert matrix['status']=='PASS' and matrix['completed_case_count']==20
    gates['AD_MAINTENANCE_20']=matrix['status']
    cleanup=json.loads((ROOT/'AD_FINAL_BOUNDARY.json').read_text());assert cleanup['auth_users']==cleanup['app_users']==cleanup['remaining_clone_databases']==0
    physical=(ROOT/'AD_PHYSICAL_CLEANUP.txt').read_text();assert 'remaining_database_container=0' in physical
    # The complete original AC ZIP is retained once. Its exact digest binds
    # inherited Code/Auth/browser/rollback evidence, not a new execution claim.
    incoming=ROOT/'incoming/AC_NATIVE200.zip'
    assert hashlib.sha256(incoming.read_bytes()).hexdigest()=='eeb76d0c63e5e78514e44a3acd958177a0d39810b89663c538dd93ffef29ae04'
    files={}
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():files[p.relative_to(ROOT).as_posix()]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    changed=subprocess.check_output(['git','diff','--name-only',runtime.AC_HEAD,'HEAD'],text=True).splitlines()
    source_pins={p:{'bytes':Path(p).stat().st_size,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in changed}
    r={'format':'CP6_AD_WRITER_MANIFEST_V1','status':'WRITER_PASS_INDEPENDENT_AUDIT_PENDING','head':head,'tree':tree,
       'run_id':os.environ['GITHUB_RUN_ID'],'run_attempt':os.environ['GITHUB_RUN_ATTEMPT'],'predecessor':runtime.AC_HEAD,
       'new_native_gates':gates,'new_family_cases':55,'new_predecessor_cases':55,'maintenance_cases':20,
       'reused_evidence':{'native_run':34956212157,'matrix_460':'REUSED only; unchanged predecessor schedules',
          'ac_runtime_objects_272':'Reverified on the new engine; AC behavior evidence reused',
          'older_rollback_ladder':'RECONCILED through new exact AD -> AC edge; older AC -> CP4.5 evidence reused',
          'signed_auth_http_browser':'REUSED for unchanged facades; new posting tests are synthetic JWT SQL'},
       'source_pins':source_pins,'payload_files':files,'production_go':False}
    manifest=ROOT/'AD_WRITER_MANIFEST.json';manifest.write_text(json.dumps(r,indent=2)+'\n')
    out=Path('cp6-ad-transfer');out.mkdir(exist_ok=True)
    archive=out/'CP6_AD_NATIVE_PROOF.tar.xz'
    with tarfile.open(archive,'w:xz',preset=6) as t:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file():t.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
    transfer={'status':'WRITER_PASS_INDEPENDENT_AUDIT_PENDING','head':head,'tree':tree,'run_id':os.environ['GITHUB_RUN_ID'],
      'archive':{'name':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},
      'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'payload_files':len(files),'production_go':False}
    (out/'CP6_AD_NATIVE_TRANSFER.json').write_text(json.dumps(transfer,indent=2)+'\n')
    print(json.dumps(transfer));return transfer

if __name__=='__main__':run()
