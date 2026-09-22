#!/usr/bin/env python3
"""Narrow source admission for the proposed import trial; no historic PASS claim."""
from pathlib import Path
import hashlib,json,subprocess
BASE='3767458fa571f3a6f8e20945ccd01bd7ce1ab47c'
ALLOWED={
 '.github/workflows/cp6-initial-import-review.yml',
 'scripts/cp6_ai_audit_router.py',
 'scripts/check-access-catalog.mjs','scripts/check-production-recovery.mjs','scripts/check-source-ownership.mjs',
 'scripts/cp6_initial_import_ao_trial.py','scripts/cp6_v2620ao_definitions.py','docs/evidence/cp6-ao-predecessor-input.json',
 'scripts/cp6_pocket_fabric.py','scripts/cp6_pocket_fabric_trial.py',
 'scripts/cp6_pocket_periods.py','scripts/cp6_pocket_period_trial.py','docs/evidence/cp6-pocket-period-predecessor.json',
 'src/ConnectedPocketFabricPage.tsx','src/ConnectedPocketFabricPage.dom.test.tsx',
 'scripts/cp6_initial_import_scope.py','scripts/cp6_initial_import_trial.py','scripts/cp6_initial_import_masters.py','scripts/cp6_initial_import_financial_sources.py','scripts/cp6_v2620ap_definitions.py',
 'src/App.tsx','src/auth/accessCatalog.ts','src/productionRecovery.ts','src/types/database.preconnect.ts',
 'src/ConnectedInitialImportPage.tsx','src/ConnectedInitialImportPage.dom.test.tsx','src/initial-import.css',
 'src/initialImport.ts','src/initialImport.test.ts','src/initialImportCatalog.json',
 'docs/evidence/cp6-initial-import-predecessor.json','docs/evidence/cp6-initial-import-source-pins.json',
 'docs/cp6-initial-import-progress.md',
 'scripts/cp6_initial_import_receipts.py','scripts/cp6_initial_import_receipt_trial.py',
 'docs/evidence/cp6-initial-import-receipt-predecessor.json',
 'scripts/cp6_initial_import_advances.py','scripts/cp6_initial_import_advance_trial.py',
 'docs/evidence/cp6-initial-import-advance-predecessor.json',
 'scripts/cp6_initial_import_prepayments.py','scripts/cp6_initial_import_prepayment_trial.py',
 'docs/evidence/cp6-initial-import-prepayment-predecessor.json',
}
git=lambda *args:subprocess.check_output(['git',*args],text=True).strip()
assert git('merge-base',BASE,'HEAD')==BASE,'IMPORT_NON_SUCCESSOR'
changed=set(git('diff','--name-only',BASE,'HEAD').splitlines())
assert changed<=ALLOWED,sorted(changed-ALLOWED)
assert not git('diff','--name-only','HEAD'),'IMPORT_DIRTY_SOURCE'
pins=json.loads(Path('docs/evidence/cp6-initial-import-source-pins.json').read_text())
for path,digest in pins.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
assert set(pins)==ALLOWED-{'docs/evidence/cp6-initial-import-source-pins.json','docs/cp6-initial-import-progress.md'}
root=Path('cp6-proof/initial-import');root.mkdir(parents=True,exist_ok=True)
(root/'SOURCE.json').write_text(json.dumps(dict(status='TRIAL_SOURCE_ADMITTED',head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),changed=sorted(changed),base=BASE,production_go=False,independent_acceptance=False,historical_matrix_reexecuted=False),indent=2)+'\n')
print('Import trial source admitted; historical SQL remains unchanged; CP6_HOLD')
