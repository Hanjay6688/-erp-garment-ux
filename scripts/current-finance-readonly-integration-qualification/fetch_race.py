"""Fetch accepted source-race bytes and package gates, without a second DB run."""
from hashlib import sha256
from pathlib import Path
import io
import json
import os
import subprocess
import zipfile

proof = json.loads(Path(__file__).with_name('PREREQUISITES.json').read_bytes())['source_race']
assert proof is not None and proof['status'] == 'PASS'
raw = subprocess.check_output(['gh', 'api', 'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/' + str(proof['artifact_id']) + '/zip'])
assert len(raw) == proof['zip_bytes'] and sha256(raw).hexdigest() == proof['zip_sha256']
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist()))
    assert z.namelist().count(proof['archive_member']) == 1
    original = z.read(proof['archive_member'])
    assert len(original) == proof['bytes'] and sha256(original).hexdigest() == proof['sha256']
    matches = [n for n in z.namelist() if Path(n).name == 'T3_PACKAGE_INSTALL.json']
    assert len(matches) == 1
    package = z.read(matches[0])
    assert json.loads(package)['gate'] == proof['package_gate'] == {k: True for k in (
        'installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')}
directory = Path(os.environ['RUNNER_TEMP']) / 'readonly-composition-accepted-source-race'
directory.mkdir()
(directory / proof['name']).write_bytes(original)
(directory / 'T3_PACKAGE_INSTALL.json').write_bytes(package)
with Path(os.environ['GITHUB_ENV']).open('a') as output:
    output.write('D17_18_COMPOSED_RACE_DIRECTORY=' + str(directory) + '\n')
print(json.dumps(dict(head=proof['head'], exact_original_verified=True, all_package_gates=True)))
