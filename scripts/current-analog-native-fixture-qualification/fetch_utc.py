"""Preserve and admit the first failed composed Original before successor execution."""
from pathlib import Path
from hashlib import sha256
import io,json,os,subprocess,zipfile
p=json.loads(Path(__file__).with_name('SOURCE.json').read_bytes())['actual_qualification_originals']['ANALOG_UTC_ORIGINAL_REPORT']
raw=subprocess.check_output(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{p['artifact_id']}/zip"])
assert len(raw)==p['zip_bytes']and sha256(raw).hexdigest()==p['zip_sha256']
with zipfile.ZipFile(io.BytesIO(raw))as z:
    assert z.testzip()is None
    raw=z.read(p['name'])
assert len(raw)==p['bytes']and sha256(raw).hexdigest()==p['sha256']
d=json.loads(raw);assert d['status']=='INCOMPLETE'and d['cp6_restored']and d['baseline_advisors_equal']
target=Path(os.environ['RUNNER_TEMP'])/'UTC_CP7_CURRENT_ANALOG_INSTALLATION_RESTORE.json';target.write_bytes(raw)
with open(os.environ['GITHUB_ENV'],'a')as out:out.write('ANALOG_UTC_ORIGINAL_REPORT='+str(target)+'\n')
print('UTC_SEVEN_STEPS_INCOMPLETE_ORIGINAL_PRESERVED_AND_VERIFIED')
