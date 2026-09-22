"""Bound fresh transport proof to the qualified permanent AO/AP package."""
from pathlib import Path
import hashlib,json,subprocess
import cp6_aq_build as aq

BASE='c4ccecfdaadd20081923079c608f83ac494da87d'
CSS='src/initial-import.css'
CSS_SHA='29c7316c759fcf2ae017056d32a208e27df37c37967dc7ee3dc4e45b1f043eb9'
git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
assert git('merge-base',BASE,'HEAD')==BASE
assert not git('diff','--name-only','HEAD'),'FLOW_DIRTY_TRACKED_SOURCE'
changed=git('diff','--name-only',BASE,'HEAD').splitlines()
successor={str(aq.MIGRATION),str(aq.ROLLBACK),'scripts/cp6_aq_build.py','scripts/cp6_aq_runtime.py',str(aq.PINS),str(aq.PROVENANCE)}
allowed=lambda p:p.startswith('scripts/cp6_ap_flow_') or p in successor|{'.github/workflows/cp6-ap-flow.yml','docs/cp6-ap-flow.md',CSS}
assert all(allowed(p) for p in changed),[p for p in changed if not allowed(p)]
assert set(git('diff','--name-only',BASE,'HEAD','--','src','supabase','package.json','package-lock.json').splitlines())=={CSS,str(aq.MIGRATION),str(aq.ROLLBACK)},'UNADMITTED_PRODUCT_CHANGE'
assert hashlib.sha256(Path(CSS).read_bytes()).hexdigest()==CSS_SHA,'UNREVIEWED_CSS_CHANGE'
assert aq.sha(aq.PINS.read_bytes())=='2f58f2b3ef00367e04c4ed2aa2f9418642452220b15139936c30608f700f8f9a','AQ_SOURCE_PINS_DRIFT'
pin=json.loads(aq.PINS.read_text())
assert aq.sha(Path(aq.__file__).read_bytes())==pin['builder_sha256']
for key in ('migration','rollback'):assert aq.sha(Path(pin[key]).read_bytes())==pin[key+'_sha256']
aq.model()
root=Path('cp6-proof/ap-flow');root.mkdir(parents=True,exist_ok=True)
(root/'SOURCE.json').write_text(json.dumps(dict(head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),base=BASE,
 changed=changed,source_pins={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in changed},
 product_unchanged=False,product_changes=[CSS,str(aq.MIGRATION)],business_code_unchanged=False,prior_permanent_sql_unchanged=True,
 successor='AQ',changed_functions=[aq.IDENTITY],
 production_go=False,independent_acceptance=False),indent=2)+'\n')
print('AP flow source admitted; exact mobile CSS and AQ lock-order successor; prior SQL unchanged; CP6_HOLD')
