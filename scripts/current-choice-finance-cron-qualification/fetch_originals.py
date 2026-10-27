from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
HERE=Path(__file__).resolve().parent
pins=json.loads((HERE/'SOURCE.json').read_bytes())
for kind,proof in pins['actual_originals'].items():
    raw=subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(proof['artifact_id'])+'/zip'])
    assert len(raw)==proof['zip_bytes']and sha256(raw).hexdigest()==proof['zip_sha256'],kind
    directory=Path(os.environ['RUNNER_TEMP'])/('choice-finance-cron-'+kind);directory.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw))as archive:
        for row in proof['preserved_files']:
            if not row['path'].endswith('.json'):continue
            basename=Path(row['path']).name;names=[n for n in archive.namelist()if Path(n).name==basename]
            assert len(names)==1,(kind,basename)
            data=archive.read(names[0]);assert len(data)==row['bytes']and sha256(data).hexdigest()==row['sha256']
            (directory/basename).write_bytes(data)
    with Path(os.environ['GITHUB_ENV']).open('a')as stream:stream.write(proof['directory_variable']+'='+str(directory)+'\n')
    print(json.dumps(dict(kind=kind,actual_original_verified=True,head=proof['head'],production_go=False)))
