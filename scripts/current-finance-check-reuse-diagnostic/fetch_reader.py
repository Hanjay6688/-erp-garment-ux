"""Verify the immutable actual paired reader diagnostic Original and all package gates."""
from hashlib import sha256
from pathlib import Path
import io,json,os,subprocess,zipfile

proof=json.loads(Path(__file__).with_name('SOURCE.json').read_bytes())['actual_reader']
raw=subprocess.check_output(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{proof['artifact_id']}/zip"])
assert len(raw)==proof['zip_bytes']and sha256(raw).hexdigest()==proof['zip_sha256']
with zipfile.ZipFile(io.BytesIO(raw))as z:
    assert z.testzip()is None and z.namelist().count(proof['archive_member'])==1
    original=z.read(proof['archive_member'])
    packages=[n for n in z.namelist()if Path(n).name=='T3_PACKAGE_INSTALL.json'];assert len(packages)==1
    assert json.loads(z.read(packages[0]))['gate']==dict(installed=True,primary_unchanged=True,
        backup_restore_drill=True,security_advisors=True,writer_runtime=True)
assert len(original)==proof['bytes']and sha256(original).hexdigest()==proof['sha256']
path=Path(os.environ['RUNNER_TEMP'])/('D17_18_FINANCE_READER-'+proof['name']);path.write_bytes(original)
with open(os.environ['GITHUB_ENV'],'a')as out:out.write('D17_18_FINANCE_READER_ORIGINAL='+str(path)+'\n')
print(json.dumps(dict(artifact_id=proof['artifact_id'],status='PASS',exact_original_verified=True)))
