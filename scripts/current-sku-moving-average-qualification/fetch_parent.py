"""Fetch and pin the exact Root-accepted SKU27 report and package originals."""
from hashlib import sha256
from pathlib import Path
import io
import json
import os
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/'CONFIG.json').read_bytes());pin=cfg['qualified_parent']
raw=subprocess.check_output(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{pin['artifact_id']}/zip"])
if len(raw)!=pin['archive']['bytes']or sha256(raw).hexdigest()!=pin['archive']['sha256']:raise ValueError('SKU_MOVAVG_PARENT_ARCHIVE_CHANGED')
out=Path(os.environ['RUNNER_TEMP'])/'sku27-parent-originals';out.mkdir()
with zipfile.ZipFile(io.BytesIO(raw))as archive:
    if archive.testzip()is not None or len(archive.namelist())!=pin['archive']['members']:raise ValueError('SKU_MOVAVG_PARENT_ARCHIVE_MEMBERS_CHANGED')
    for name,expected in pin['originals'].items():
        matches=[member for member in archive.namelist()if Path(member).name==name]
        if len(matches)!=1:raise ValueError('SKU_MOVAVG_PARENT_ORIGINAL_COUNT:'+name)
        data=archive.read(matches[0])
        if len(data)!=expected['bytes']or sha256(data).hexdigest()!=expected['sha256']:raise ValueError('SKU_MOVAVG_PARENT_ORIGINAL_CHANGED:'+name)
        (out/name).write_bytes(data)
with open(os.environ['GITHUB_ENV'],'a')as env:env.write('CP7_SKU_PARENT_ORIGINALS='+str(out)+'\n')
print(json.dumps(dict(status='EXACT_SKU27_PARENT_ORIGINALS_BOUND',artifact_id=pin['artifact_id'],originals=sorted(pin['originals'])),sort_keys=True))
