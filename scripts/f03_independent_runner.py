"""Reuse installation/cleanup machinery; run only auditor-owned case providers."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

os.environ['CP7_F03_BUCKET']='p09'
import cp7_f03_full_probe as runtime

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'scripts/f03_independent_manifest.json'
manifest=json.loads(MANIFEST.read_text())
assert manifest['candidate']=='eb6b8682e97e94c95f89d431ab81974c54ddcbaf'
subprocess.run(['git','diff','--exit-code',manifest['candidate'],'--','src','scripts/cp7-src','scripts/cp7*bundle.py','package.json','package-lock.json'],cwd=ROOT,check=True)
assert hashlib.sha256(runtime.bundle.bundle().encode()).hexdigest()==manifest['f03_bundle_sha256']
runtime.BUCKET='independent'
runtime.MANIFEST=MANIFEST
runtime.manifest=manifest
runtime.spec=manifest['spec']
runtime.OUT=ROOT/'cp6-proof/t3/F03_INDEPENDENT.json'
runtime.package._writer_runtime=lambda browser_mode=False:runtime.run()
runtime.package.run('install')
