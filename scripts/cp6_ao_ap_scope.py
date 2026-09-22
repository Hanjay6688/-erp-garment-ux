"""Bound permanent-package work to the verified accessory checkpoint."""
from pathlib import Path
import hashlib,json,subprocess

BASE='4dcc950fb8cd2a102cc11c8f6545af2865cafa6c'
git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
assert git('merge-base',BASE,'HEAD')==BASE
assert not git('diff','--name-only','HEAD'),'PACKAGE_DIRTY_TRACKED_SOURCE'
changed=git('diff','--name-only',BASE,'HEAD').splitlines()
allowed=lambda p:p.startswith(('scripts/cp6_ao_ap_','docs/evidence/cp6-ao-ap-')) or p in {
 '.github/workflows/cp6-ao-ap-package.yml','docs/cp6-ao-ap-package.md',
 'supabase/migrations/20260922135612_erp_v2_6_20ao_cp6_invoice_retail.sql',
 'supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql',
 'supabase/rollbacks/20260922135612_erp_v2_6_20ao_cp6_invoice_retail.rollback.sql',
 'supabase/rollbacks/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.rollback.sql',
}
assert all(allowed(p) for p in changed),[p for p in changed if not allowed(p)]
pins=json.loads(git('show',BASE+':docs/evidence/cp6-initial-import-source-pins.json'))
for p,h in pins.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,'VERIFIED_PROPOSAL_CHANGED:'+p
root=Path('cp6-proof/ao-ap-package');root.mkdir(parents=True,exist_ok=True)
(root/'SOURCE.json').write_text(json.dumps(dict(head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),base=BASE,changed=changed,
 source_pins={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in changed},proposal_pins_unchanged=True,
 production_go=False,independent_acceptance=False,migration_installed=False),indent=2)+'\n')
print('Permanent package source admitted; verified proposal unchanged; CP6_HOLD')
