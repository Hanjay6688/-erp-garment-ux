"""Auditor re-execution of retained extended journeys; never label as own oracles."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

os.environ['CP7_F03_BUCKET']='p09'
import cp7_f03_full_probe as runtime

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'scripts/f03_additional_manifest.json'
manifest=json.loads(MANIFEST.read_text())
assert manifest['candidate']=='eb6b8682e97e94c95f89d431ab81974c54ddcbaf'
subprocess.run(['git','diff','--exit-code',manifest['candidate'],'--','src','scripts/cp7-src','scripts/cp7*bundle.py','package.json','package-lock.json'],cwd=ROOT,check=True)
assert hashlib.sha256(runtime.bundle.bundle().encode()).hexdigest()==manifest['f03_bundle_sha256']
bucket='additional'
runtime.BUCKET='retained_'+bucket
runtime.MANIFEST=MANIFEST
runtime.manifest=manifest
runtime.spec=manifest['buckets'][bucket]
runtime.OUT=ROOT/'cp6-proof/t3'/('F03_RETAINED_'+bucket.upper()+'.json')
runtime.package._writer_runtime=lambda browser_mode=False:runtime.run()
runtime.package.run('install')
