"""Fetch exact six-retained/one-fresh Originals; never relabel historical11c."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
from composition import gate
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def fetch():
    gate(json.loads((HERE/'CONFIG.json').read_bytes()))
    cfg=json.loads((ROOT/'scripts/current-backend-acceptance-3194/CONFIG.json').read_bytes())
    directory=Path(os.environ['RUNNER_TEMP'])/'B-browser3194-originals';directory.mkdir()
    for label in ('retained','fresh'):
        proof=cfg[label]
        run=json.loads(subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/actions/runs/'+str(proof['run_id'])]))
        assert run['head_sha']==proof['head']and run['status']=='completed'
        assert run['conclusion']==('success'if label=='fresh'else'failure')
        job=json.loads(subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/actions/jobs/'+str(proof['job_id'])]))
        assert job['run_id']==proof['run_id']and job['head_sha']==proof['head']and job['status']=='completed'and job['conclusion']==run['conclusion']
        meta=json.loads(subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(proof['artifact_id'])]))
        assert not meta['expired']and meta['workflow_run']['id']==proof['run_id']and meta['workflow_run']['head_sha']==proof['head']
        raw=subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(proof['artifact_id'])+'/zip'])
        assert len(raw)==proof['zip_bytes']and sha256(raw).hexdigest()==proof['zip_sha256']
        target=directory/label;target.mkdir()
        with zipfile.ZipFile(io.BytesIO(raw))as archive:
            assert archive.testzip()is None and len(archive.namelist())==len(set(archive.namelist()))
            for key,size,digest in (('name','bytes','sha256'),('package_name','package_bytes','package_sha256')):
                name=proof[key];members=[p for p in archive.namelist()if Path(p).name==name]
                assert len(members)==1 and Path(name).name==name
                value=archive.read(members[0]);assert len(value)==proof[size]and sha256(value).hexdigest()==proof[digest]
                (target/name).write_bytes(value)
        print(json.dumps(dict(component=label,head=proof['head'],run=proof['run_id'],artifact=proof['artifact_id'],zip_sha256=proof['zip_sha256'],historical_status_preserved=True)))
    with Path(os.environ['GITHUB_ENV']).open('a')as stream:stream.write('D17_18_BROWSER_BACKEND_ORIGINALS='+str(directory)+'\n')
if __name__=='__main__':fetch()
