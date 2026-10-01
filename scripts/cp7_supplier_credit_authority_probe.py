"""Use the identical full F03 install/restoration gates for exact Native waits."""
import json,os
os.environ['CP7_F03_BUCKET']='supplier_credit'
import cp7_f03_full_probe as full

full.BUCKET='supplier_authority'
full.MANIFEST=full.bundle.ROOT/'scripts/cp7_supplier_credit_authority_manifest.json'
full.manifest=json.loads(full.MANIFEST.read_text())
full.spec=full.manifest['buckets'][full.BUCKET]
full.OUT=full.bundle.ROOT/'cp6-proof/t3/CP7_F03_FULL_SUPPLIER_AUTHORITY.json'
if __name__=='__main__':
 full.package._writer_runtime=lambda browser_mode=False:full.run()
 full.package.run('install')
