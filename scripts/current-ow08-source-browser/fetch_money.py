"""Exact accepted money UI originals, once, before the next disposable DB."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
cfg=json.loads((Path(__file__).resolve().parent/'CONFIG.json').read_bytes())
pin=cfg['accepted_money_browser2']
if pin is None:raise ValueError('OW08_SOURCE_BROWSER_CLOSED_ACTUAL_MONEY_BROWSER2_REQUIRED')
root=Path(os.environ['RUNNER_TEMP'])/'ow08-money-browser-prerequisite';root.mkdir(exist_ok=False)
prefix='repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(pin['artifact_id'])
meta=json.loads(subprocess.check_output(['gh','api',prefix]))
assert meta['workflow_run']['id']==pin['run_id']and meta['workflow_run']['head_sha']==pin['head']and not meta['expired']
raw=subprocess.check_output(['gh','api',prefix+'/zip'])
assert len(raw)==meta['size_in_bytes']==pin['zip_bytes']
assert 'sha256:'+sha256(raw).hexdigest()==meta['digest']=='sha256:'+pin['zip_sha256']
with zipfile.ZipFile(io.BytesIO(raw))as z:
    assert z.testzip()is None and len(z.namelist())==len(set(z.namelist()))
    for kind in ('original','package'):
        p=pin[kind];assert Path(p['name']).name==p['name'];value=z.read(p['name'])
        assert len(value)==p['bytes']and sha256(value).hexdigest()==p['sha256']
        (root/p['name']).write_bytes(value)
(root/'ARTIFACT_METADATA.json').write_text(json.dumps(meta,indent=2)+'\n')
with open(os.environ['GITHUB_ENV'],'a')as out:out.write('CP7_OW08_MONEY_BROWSER_ORIGINALS='+str(root)+'\n')
print(json.dumps(dict(status='EXACT_MONEY_BROWSER_AND_PACKAGE_ORIGINALS_FETCHED',head=pin['head'],fresh_DB_cases=0)))
