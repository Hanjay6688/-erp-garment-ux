"""Bound fresh transport proof to the qualified permanent AO/AP package."""
from pathlib import Path
import hashlib,json,subprocess

BASE='c4ccecfdaadd20081923079c608f83ac494da87d'
git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
assert git('merge-base',BASE,'HEAD')==BASE
assert not git('diff','--name-only','HEAD'),'FLOW_DIRTY_TRACKED_SOURCE'
changed=git('diff','--name-only',BASE,'HEAD').splitlines()
allowed=lambda p:p.startswith('scripts/cp6_ap_flow_') or p in {'.github/workflows/cp6-ap-flow.yml','docs/cp6-ap-flow.md'}
assert all(allowed(p) for p in changed),[p for p in changed if not allowed(p)]
assert not git('diff','--name-only',BASE,'HEAD','--','src','supabase','package.json','package-lock.json'),'QUALIFIED_PRODUCT_CHANGED'
root=Path('cp6-proof/ap-flow');root.mkdir(parents=True,exist_ok=True)
(root/'SOURCE.json').write_text(json.dumps(dict(head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),base=BASE,
 changed=changed,source_pins={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in changed},
 product_unchanged=True,production_go=False,independent_acceptance=False),indent=2)+'\n')
print('AP flow source admitted; qualified product unchanged; CP6_HOLD')
