"""Retain exact AF incomplete bytes before the corrected qualification."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
from retained_d3 import gate

HERE=Path(__file__).resolve().parent


def fetch():
    config=json.loads((HERE/'D3_PREREQUISITE.json').read_bytes());proof=gate(config)
    raw=subprocess.check_output(['gh','api','repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(proof['artifact_id'])+'/zip'])
    assert len(raw)==proof['zip_bytes']and sha256(raw).hexdigest()==proof['zip_sha256']
    directory=Path(os.environ['RUNNER_TEMP'])/'retained-D3-first-factory-cutoff';directory.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw))as archive:
        assert archive.testzip()is None and len(archive.namelist())==len(set(archive.namelist()))
        for member,name,size,digest in ((proof['archive_member'],proof['name'],proof['bytes'],proof['sha256']),
            (proof['package_member'],proof['package_name'],proof['package_bytes'],proof['package_sha256'])):
            assert Path(name).name==name and name.endswith('.json')and archive.namelist().count(member)==1
            value=archive.read(member);assert len(value)==size and sha256(value).hexdigest()==digest
            (directory/name).write_bytes(value)
    with Path(os.environ['GITHUB_ENV']).open('a')as stream:stream.write(config['original_directory_variable']+'='+str(directory)+'\n')
    print(json.dumps(dict(head=proof['head'],retained_whole_status='INCOMPLETE',new_runtime_credit=0)))


if __name__=='__main__':fetch()
