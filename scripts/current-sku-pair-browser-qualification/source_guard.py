"""Read-only source/case admission. It grants no Native or browser PASS."""
from hashlib import sha256
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
IDS=('SKU29_BROWSER_DESKTOP_REAL_AUTH_PAIR_FIFO_RECOVERY_INVERSE','SKU29_BROWSER_MOBILE390_REAL_AUTH_PAIR_FIFO_GUARDS_INVERSE')

def admitted(root=ROOT):
    pins=json.loads((root/'scripts/current-sku-pair-browser-qualification/SOURCE.json').read_bytes())
    assert pins['case_ids']==list(IDS)and len(set(IDS))==2,'SKU29_BROWSER_CASE_IDS_CHANGED'
    assert pins['backend_candidate']==dict(commit='21c69cf25defcee854beb08e998062d7e883d968',tree='a0d2c0da83bf5dc29f2c6b2e02abe6d7ed68f89e'),'SKU29_BROWSER_BACKEND_PIN_CHANGED'
    assert pins['normal_full_App']is True and pins['response_fixtures']is False,'SKU29_REAL_APPLICATION_REQUIRED'
    required=('scripts/cp6_auditor_browser_host.mjs','scripts/cp7_ow04_restore_bundle.py','src/App.tsx',
      'src/ConnectedSkuMasterPage.tsx','src/ConnectedProductConversionPage.tsx','src/productionRecovery.ts',
      'scripts/current-sku-pair-conversion-qualification/fixture.py','scripts/cp7_sku_pair_conversion/conversion.sql')
    assert all(path in pins['files']for path in required),'SKU29_REQUIRED_SOURCE_PIN_MISSING'
    for path,digest in pins['files'].items():
        assert sha256((root/path).read_bytes()).hexdigest()==digest,('SKU29_BROWSER_SOURCE_CHANGED',path)
    return dict(status='SKU29_PREPARED_SOURCE_ADMITTED_NOT_RUNTIME_PASS',backend_candidate=pins['backend_candidate'],case_ids=list(IDS),
      source_file_count=len(pins['files']),source_manifest_sha256=sha256((root/'scripts/current-sku-pair-browser-qualification/SOURCE.json').read_bytes()).hexdigest(),
      actual_runtime_execution=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':print(json.dumps(admitted(),indent=2))
