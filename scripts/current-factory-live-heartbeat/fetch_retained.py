from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/'CONFIG.json').read_bytes());proof=cfg['retained']
assert cfg['allow_database_execution']is True
raw=subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(proof['artifact_id'])+'/zip'])
assert len(raw)==proof['zip_bytes']and sha256(raw).hexdigest()==proof['zip_sha256']
directory=Path(os.environ['RUNNER_TEMP'])/'factory-live-retained11c';directory.mkdir()
with zipfile.ZipFile(io.BytesIO(raw))as z:
    assert z.testzip()is None and len(z.namelist())==len(set(z.namelist()))
    for member,name,size,digest in ((proof['name'],proof['name'],proof['bytes'],proof['sha256']),
        (proof['package_name'],proof['package_name'],proof['package_bytes'],proof['package_sha256'])):
        assert Path(name).name==name and z.namelist().count(member)==1
        data=z.read(member);assert len(data)==size and sha256(data).hexdigest()==digest
        (directory/name).write_bytes(data)
with Path(os.environ['GITHUB_ENV']).open('a')as f:f.write(cfg['original_directory_variable']+'='+str(directory)+'\n')
print(json.dumps(dict(retained_backend_head=proof['head'],retained_pass_groups=6,historical_factory_status='INCOMPLETE',backend_unlock=False)))
