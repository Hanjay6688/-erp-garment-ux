"""Fetch exact PASS Native15 and exact first INCOMPLETE transport plus package gates."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
pins=json.loads(Path(__file__).with_name('SOURCE.json').read_bytes())
for variable,p in pins['actual_qualification_originals'].items():
    raw=subprocess.check_output(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{p['artifact_id']}/zip"])
    assert len(raw)==p['zip_bytes']and sha256(raw).hexdigest()==p['zip_sha256']
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        assert z.testzip()is None
        names=[n for n in z.namelist()if Path(n).name==p['name']];assert len(names)==1;original=z.read(names[0])
        packages=[n for n in z.namelist()if Path(n).name=='T3_PACKAGE_INSTALL.json'];assert len(packages)==1
        gate=json.loads(z.read(packages[0]))['gate']
    assert len(original)==p['bytes']and sha256(original).hexdigest()==p['sha256']
    actual=json.loads(original);assert actual['status']==p['status']and actual['cp6_restored']and actual['advisor_gate']
    assert gate==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=p['status']=='PASS')
    out=Path(os.environ['RUNNER_TEMP'])/p['name'];out.write_bytes(original)
    with open(os.environ['GITHUB_ENV'],'a')as f:f.write(variable+'='+str(out)+'\n')
    print(variable+' exact '+p['status']+' Original and package gates verified')
