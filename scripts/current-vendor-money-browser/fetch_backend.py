"""Fetch exact complete backend11 Original and package bytes before DB work."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile

HERE=Path(__file__).resolve().parent
config=json.loads((HERE/'CONFIG.json').read_bytes())
selected=config.get('accepted_backend11')
if selected is None:raise ValueError('VENDOR_MONEY_BROWSER_CLOSED_COMPLETE_BACKEND11_REQUIRED')
root=Path(os.environ['RUNNER_TEMP'])/'vendor-backend11-browser-prerequisite'
root.mkdir(exist_ok=False)
prefix='repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(selected['artifact_id'])
metadata=json.loads(subprocess.check_output(['gh','api',prefix]))
assert metadata['workflow_run']['id']==selected['run_id']and metadata['workflow_run']['head_sha']==selected['head']and not metadata['expired']
raw=subprocess.check_output(['gh','api',prefix+'/zip'])
assert len(raw)==metadata['size_in_bytes']==selected['zip_bytes']
assert 'sha256:'+sha256(raw).hexdigest()==metadata['digest']=='sha256:'+selected['zip_sha256']
with zipfile.ZipFile(io.BytesIO(raw))as archive:
    assert archive.testzip()is None
    for kind in ('original','package'):
        pin=selected[kind];assert Path(pin['name']).name==pin['name']
        value=archive.read(pin['name'])
        assert len(value)==pin['bytes']and sha256(value).hexdigest()==pin['sha256']
        (root/pin['name']).write_bytes(value)
(root/'ARTIFACT_METADATA.json').write_text(json.dumps(metadata,indent=2)+'\n')
with open(os.environ['GITHUB_ENV'],'a')as env:env.write('CP7_VENDOR_BACKEND11_ORIGINALS='+str(root)+'\n')
print(json.dumps(dict(status='EXACT_BACKEND11_AND_PACKAGE_BYTES_FETCHED',head=selected['head'],run_id=selected['run_id'],fresh_DB_cases=0)))
