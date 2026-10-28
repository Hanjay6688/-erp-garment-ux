"""Download only the retained first diagnostic bytes; a failed result stays failed."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
from admission import check_gate

here=Path(__file__).resolve().parent
config=json.loads((here/'CONFIG.json').read_bytes())
check_gate(config,json.loads((here/'PREPARED.json').read_bytes()))
proof=config['first_diagnostic']
raw=subprocess.check_output(['gh','api',
    'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/'+str(proof['artifact_id'])+'/zip'])
assert len(raw)==proof['zip_bytes'] and sha256(raw).hexdigest()==proof['zip_sha256']
directory=Path(os.environ['RUNNER_TEMP'])/'finance-consistency-first-diagnostics';directory.mkdir()
with zipfile.ZipFile(io.BytesIO(raw))as archive:
    assert archive.testzip()is None and len(archive.namelist())==len(set(archive.namelist()))
    for member,name,size,digest in (
        (proof['archive_member'],proof['name'],proof['bytes'],proof['sha256']),
        (proof['package_member'],proof['package_name'],proof['package_bytes'],proof['package_sha256'])):
        assert Path(name).name==name and name.endswith('.json')
        assert archive.namelist().count(member)==1
        data=archive.read(member);assert len(data)==size and sha256(data).hexdigest()==digest
        (directory/name).write_bytes(data)
with Path(os.environ['GITHUB_ENV']).open('a')as stream:
    stream.write(config['original_directory_variable']+'='+str(directory)+'\n')
print(json.dumps(dict(head=proof['head'],first_actual_diagnostic_preserved=True,
    first_status='INCOMPLETE',runtime_acceptance_requires_admission=True)))
