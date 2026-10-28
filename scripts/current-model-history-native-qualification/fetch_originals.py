"""Fetch immutable actual reports, never a reconstructed PASS summary."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
pins=json.loads(Path(__file__).with_name('SOURCE.json').read_bytes())
for variable,proof in pins['actual_qualification_originals'].items():
    raw=subprocess.check_output(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{proof['artifact_id']}/zip"])
    assert len(raw)==proof['zip_bytes']and sha256(raw).hexdigest()==proof['zip_sha256'],variable
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        assert z.testzip()is None
        names=[n for n in z.namelist()if Path(n).name==proof['name']];assert len(names)==1
        original=z.read(names[0])
        packages=[n for n in z.namelist()if Path(n).name=='T3_PACKAGE_INSTALL.json'];assert len(packages)==1
        gate=json.loads(z.read(packages[0]))['gate']
        assert set(gate)=={'installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime'}
        assert gate==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=proof['status']=='PASS'),(variable,gate)
    assert len(original)==proof['bytes']and sha256(original).hexdigest()==proof['sha256'],variable
    actual=json.loads(original);assert actual['status']==proof['status']and actual['cp6_restored'],variable
    # PASS and all preserved first-failure Originals share a basename. Preserve each
    # exact artifact independently so later fetches cannot overwrite its input.
    target=Path(os.environ['RUNNER_TEMP'])/(variable+'-'+proof['name']);target.write_bytes(original)
    with open(os.environ['GITHUB_ENV'],'a')as out:out.write(variable+'='+str(target)+'\n')
    print(variable+' actual raw '+proof['status']+' Original verified',flush=True)
