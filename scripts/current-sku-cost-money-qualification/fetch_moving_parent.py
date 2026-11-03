"""Verify exact accepted moving Native6 archive and every required Original."""
from hashlib import sha256
from pathlib import Path
import io
import json
import os
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent

def main():
    pin=json.loads((HERE/'CONFIG.json').read_bytes())['qualified_moving']
    raw=subprocess.check_output(['gh','api',f"repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{pin['artifact_id']}/zip"])
    if len(raw)!=pin['archive']['bytes']or sha256(raw).hexdigest()!=pin['archive']['sha256']:raise ValueError('SKU_MONEY_MOVING_PARENT_ARCHIVE_CHANGED')
    destination=Path(os.environ['RUNNER_TEMP'])/'sku-money-moving-parent-originals';destination.mkdir()
    with zipfile.ZipFile(io.BytesIO(raw))as archive:
        if archive.testzip()is not None or len(archive.namelist())!=pin['archive']['members']:raise ValueError('SKU_MONEY_MOVING_PARENT_MEMBERS_CHANGED')
        for name,expected in pin['originals'].items():
            if archive.namelist().count(name)!=1:raise ValueError('SKU_MONEY_EXACT_TOP_LEVEL_PARENT_ORIGINAL_REQUIRED:'+name)
            value=archive.read(name)
            if len(value)!=expected['bytes']or sha256(value).hexdigest()!=expected['sha256']:raise ValueError('SKU_MONEY_MOVING_ORIGINAL_CHANGED:'+name)
            (destination/name).write_bytes(value)
    with open(os.environ['GITHUB_ENV'],'a')as env:env.write('CP7_SKU_MOVING_PARENT_ORIGINALS='+str(destination)+'\n')
    print(json.dumps(dict(status='EXACT_MOVING_NATIVE6_ORIGINALS_BOUND',artifact_id=pin['artifact_id'],originals=sorted(pin['originals'])),sort_keys=True))

if __name__=='__main__':main()
