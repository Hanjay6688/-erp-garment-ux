"""Fetch the own combined PASS Original/package only after its exact binding."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
from evidence import gate

HERE=Path(__file__).resolve().parent


def fetch():
    config=json.loads((HERE/'CONFIG.json').read_bytes());proof=gate(config)
    raw=subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(proof['artifact_id'])+'/zip'])
    assert len(raw)==proof['zip_bytes']and sha256(raw).hexdigest()==proof['zip_sha256']
    directory=Path(os.environ['RUNNER_TEMP'])/'combined-finance-accepted-runtime';directory.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw))as archive:
        assert archive.testzip()is None and len(archive.namelist())==len(set(archive.namelist()))
        for member,name,size,digest in ((proof['archive_member'],proof['name'],proof['bytes'],proof['sha256']),
            (proof['package_member'],proof['package_name'],proof['package_bytes'],proof['package_sha256'])):
            assert Path(name).name==name and name.endswith('.json')and archive.namelist().count(member)==1
            value=archive.read(member);assert len(value)==size and sha256(value).hexdigest()==digest
            (directory/name).write_bytes(value)
    with Path(os.environ['GITHUB_ENV']).open('a')as stream:
        stream.write(config['original_directory_variable']+'='+str(directory)+'\n')
    print(json.dumps(dict(head=proof['head'],own_combined_original_fetched=True,
        full_source_and_runtime_verification_still_required=True,Auth_browser_executed=False)))


if __name__=='__main__':fetch()
