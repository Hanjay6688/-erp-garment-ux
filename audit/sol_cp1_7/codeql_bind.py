"""Qualify the original Sol SARIF without rescanning or changing its gate."""
import hashlib, json, os, shutil, subprocess, urllib.request, zipfile
from pathlib import Path

SOURCE = '0b7049d9203bac52b47a4c89f3e0d75646067a8f'
SCAN_RUN = 38560025889
SCAN_WORKFLOW_SHA = '2e6fbf92d4669f09fa78ef389fa5523a524ebf93'
ARTIFACTS = {
 11891678417: '73de06f9d968cc29b094be4eff65da9ff5301edc9db458b45b555e3368c8c3f1',
 11891618647: 'ae8adadf758008234c35fe65b6e0d5a3f297f9b0db238c236f50d04041b2028d',
 11891573392: 'ef37b7e1cf800c897494dc9c03ab3a88c6f4201335560964a1353e7e5ef8bcaa',
 11891203768: 'db732754aad11ad98e11b38fca3f8fb0d035f67dce27e416828541e5ee81bdc5',
 11891848406: '49d97058abd39c9ad692309433ad51f5483e52b1dd7c56b02368a81f9e02895e',
 11891688684: '49d97058abd39c9ad692309433ad51f5483e52b1dd7c56b02368a81f9e02895e',
 11891678421: '54aca7a0232ef34092e761fe2f93cddc8519bd96f5dfc65a24ffa46c366002fd',
 11891503530: '49d97058abd39c9ad692309433ad51f5483e52b1dd7c56b02368a81f9e02895e',
}
ROOT = Path('cp6-codeql')
(ROOT/'original').mkdir(parents=True, exist_ok=True)
(ROOT/'sarif').mkdir(exist_ok=True)
def api(path):
    req = urllib.request.Request('https://api.github.com/repos/Hanjay6688/-erp-garment-ux/'+path,
          headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'], 'Accept':'application/vnd.github+json'})
    return urllib.request.urlopen(req).read()

assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == SOURCE
inventory=[]
for aid, digest in ARTIFACTS.items():
    meta=json.loads(api(f'actions/artifacts/{aid}'))
    assert meta['workflow_run']['id']==SCAN_RUN
    assert meta['workflow_run']['head_sha']==SCAN_WORKFLOW_SHA
    assert meta['digest']=='sha256:'+digest
    data=api(f'actions/artifacts/{aid}/zip')
    assert hashlib.sha256(data).hexdigest()==digest
    path=ROOT/'original'/f'{aid}.zip'; path.write_bytes(data)
    with zipfile.ZipFile(path) as z:
        members=[]
        for name in z.namelist():
            if name.endswith('.sarif'):
                raw=z.read(name)
                (ROOT/'sarif'/f'{aid}-{Path(name).name}').write_bytes(raw)
                members.append({'name':name,'sha256':hashlib.sha256(raw).hexdigest()})
            elif name.endswith('SOL_SOURCE_IDENTITY.json'):
                raw=z.read(name); ident=json.loads(raw)
                # Require both identities; key names are recorded by the routing wrapper.
                encoded=json.dumps(ident)
                assert SOURCE in encoded and SCAN_WORKFLOW_SHA in encoded
                (ROOT/'original'/f'{aid}-identity.json').write_bytes(raw)
                members.append({'name':name,'sha256':hashlib.sha256(raw).hexdigest(),'identity':ident})
        assert members
    inventory.append({'artifact':aid,'name':meta['name'],'zip_sha256':digest,'members':members})
assert len(list((ROOT/'sarif').glob('*.sarif')))==4
binding={'source_sha':SOURCE,'scan_run':SCAN_RUN,'scan_workflow_sha':SCAN_WORKFLOW_SHA,
 'qualification_workflow_sha':os.environ['GITHUB_SHA'], 'qualification_run':os.environ['GITHUB_RUN_ID'],
 'initial_failure':'AUDITOR_TOOL: source SHA compared with routing workflow SHA before SARIF validation',
 'change':'Run the unchanged source gate with GITHUB_SHA explicitly bound to its product checkout; preserve the actual workflow identity separately.',
 'rescanned':False,'weakened_oracle':False,'artifacts':inventory,'production_go':False}
(ROOT/'SOL_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
env=dict(os.environ,GITHUB_SHA=SOURCE,CP6_CODEQL_LANGUAGE='all-four-original-languages')
code=subprocess.call(['python','scripts/cp6_codeql_artifact_gate.py'],env=env)
binding['gate_exit']=code
binding['status']='PASS' if code==0 else 'FAIL'
(ROOT/'SOL_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
raise SystemExit(code)
