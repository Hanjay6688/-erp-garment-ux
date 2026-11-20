"""Verify the audited child installer and fingerprints through fresh database connections."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import psycopg
from common import db, first, save, PARENT_PRODUCT, PARENT_TREE, PARENT_SEAL, PRODUCT, TREE, SEAL

PIN='faa6a2edf23e52daa42fd268b2effc7374315e52'
BLOBS={'README.md':'083ee3912101304ceb637ad32d9214a92b6b8626','definitions.patch':'73cba3c8e32aef7254a8be78e17a19a43d1bb5d7','install.py':'77cc2c35a78c1fde725e37199a80f87a5f9965e3','manifest.json':'87959104d1a4989aabb1fbe8ad3167fdf8e7fe76'}
def seal():
    with psycopg.connect(**db()) as conn:
        return conn.execute('select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()').fetchone()[0]
def run():
    repo=Path(os.environ['GITHUB_WORKSPACE'])/'installer'
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    assert head==PIN
    path=repo/'qualification/close12/product'
    for name,digest in BLOBS.items():
        raw=(path/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==digest,name
    spec=importlib.util.spec_from_file_location('candidate_g14_install',path/'install.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    origin=json.loads((Path(os.environ['RUNNER_TEMP'])/'cp7-global-auditor'/'installed.json').read_bytes())
    base=seal();assert base==origin['server_catalogue_fingerprint'] and origin['product']==PARENT_PRODUCT and origin['tree']==PARENT_TREE and base['sha256']==PARENT_SEAL
    events=[]
    for direction,changed,expected in [('up',True,SEAL),('up',False,SEAL),('down',True,PARENT_SEAL),('up',True,SEAL)]:
        with psycopg.connect(**db()) as c:result=mod.apply(c,direction)
        observed=seal()
        events.append(dict(operation=direction,changed=result['changed'],groups=observed['groups'],sha256=observed['sha256']))
        assert result['changed']==changed and expected==observed['sha256'] and observed['groups']==25,(direction,events)
        if direction=='down':assert observed==base
    save('candidate-install',dict(outcome='PASS',parent=PARENT_PRODUCT,parent_tree=PARENT_TREE,parent_seal=base['sha256'],child_seal=SEAL,source_checkout=PIN,installer_blobs=BLOBS,events=events,public_functions=origin['public_functions']))
if __name__=='__main__':run()
