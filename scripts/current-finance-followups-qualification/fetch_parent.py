"""Fetch only the declared accepted Original; never infer PASS from a green job."""
from hashlib import sha256
from pathlib import Path
import io
import json
import os
import subprocess
import zipfile

config = json.loads(Path(__file__).with_name('CONFIG.json').read_bytes())
proof = config['parent']
if not config['allow_database_execution'] or proof['status'] != 'PASS':
    raise ValueError('FOLLOWUP_PARENT_NOT_ACCEPTED_DATABASE_GATE_CLOSED')
raw = subprocess.check_output(['gh', 'api',
    'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/' + str(proof['artifact_id']) + '/zip'])
assert len(raw) == proof['zip_bytes'] and sha256(raw).hexdigest() == proof['zip_sha256']
directory = Path(os.environ['RUNNER_TEMP']) / 'finance-followups-accepted-readonly'
directory.mkdir()
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist()) == len(set(archive.namelist()))
    for member, name, size, digest in (
        (proof['archive_member'], proof['name'], proof['bytes'], proof['sha256']),
        (proof['package_member'], proof['package_name'], proof['package_bytes'], proof['package_sha256'])):
        assert Path(name).name == name and name.endswith('.json')
        assert archive.namelist().count(member) == 1
        data = archive.read(member)
        assert len(data) == size and sha256(data).hexdigest() == digest
        (directory / name).write_bytes(data)
with Path(os.environ['GITHUB_ENV']).open('a') as stream:
    stream.write(config['original_directory_variable'] + '=' + str(directory) + '\n')
print(json.dumps(dict(head=proof['head'], exact_originals_downloaded=True,
                     runtime_acceptance_requires_admission=True)))
