"""Admit a read-only product probe against the immutable qualified AQ runtime."""
from pathlib import Path
import hashlib,json,subprocess
import cp6_aq_build as aq

BASE='34b03848b03192845ab44dc43c8e28706099397c'
ALLOWED={'scripts/cp6_opening_overlap_scope.py','scripts/cp6_opening_overlap_probe.py',
         '.github/workflows/cp6-opening-overlap.yml','docs/cp6-opening-overlap.md'}
git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
assert git('merge-base',BASE,'HEAD')==BASE
assert not git('diff','--name-only','HEAD'),'OVERLAP_DIRTY_SOURCE'
changed=set(git('diff','--name-only',BASE,'HEAD').splitlines())
assert changed<=ALLOWED,sorted(changed-ALLOWED)
assert not git('diff','--name-only',BASE,'HEAD','--','src','supabase','package.json','package-lock.json')
assert aq.sha(aq.PINS.read_bytes())=='2f58f2b3ef00367e04c4ed2aa2f9418642452220b15139936c30608f700f8f9a'
pin=json.loads(aq.PINS.read_text())
for key in ('migration','rollback'):assert aq.sha(Path(pin[key]).read_bytes())==pin[key+'_sha256']
aq.model()
out=Path('cp6-proof/opening-overlap');out.mkdir(parents=True,exist_ok=True)
(out/'SOURCE.json').write_text(json.dumps(dict(head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),
 base=BASE,changed=sorted(changed),source_pins={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(changed)},
 product_unchanged=True,phase='COUNTEREXAMPLE_PROBE',production_go=False,independent_acceptance=False),indent=2)+'\n')
print('Exact AQ product unchanged; opening overlap probe admitted; CP6_HOLD')
