"""Admit only the explicit AR successor of the immutable AQ defect probe."""
from pathlib import Path
import hashlib,json,subprocess,re
import cp6_ar_build as build

BASE='3ddf32fde459ab437afb07b762bc6246f97744d5'
ALLOWED={
 'scripts/cp6_ar_definitions.py','scripts/cp6_ar_build.py','scripts/cp6_ar_runtime.py',
 'scripts/cp6_ar_trial.py','scripts/cp6_ar_scope.py','.github/workflows/cp6-ar.yml',
 'docs/cp6-ar-opening-overlap.md','docs/evidence/cp6-ar-cli-provenance.json','docs/evidence/cp6-ar-pins.json',
 'supabase/migrations/20260922185015_erp_v2_6_20ar_cp6_opening_overlap.sql',
 'supabase/rollbacks/20260922185015_erp_v2_6_20ar_cp6_opening_overlap.rollback.sql'}
git=lambda *a:subprocess.check_output(['git',*a],text=True).strip()
assert git('merge-base',BASE,'HEAD')==BASE
assert not git('diff','--name-only','HEAD'),'AR_DIRTY_TRACKED_SOURCE'
changed=set(git('diff','--name-only',BASE,'HEAD').splitlines())
assert changed<=ALLOWED,sorted(changed-ALLOWED)
assert ALLOWED<=changed,'AR_PACKAGE_INCOMPLETE'
pin=json.loads(build.PINS.read_text())
assert build.sha(build.PINS.read_bytes())==re.search("EXPECTED_PINS='([0-9a-f]+)'",Path('scripts/cp6_ar_runtime.py').read_text())[1]
assert build.sha(Path(build.__file__).read_bytes())==pin['builder_sha256']
assert build.sha(Path('scripts/cp6_ar_definitions.py').read_bytes())==pin['definitions_sha256']
for key in ('migration','rollback'):assert build.sha(Path(pin[key]).read_bytes())==pin[key+'_sha256']
base,capture,before,after,pin=build.model()
assert {k for k in before['objects'] if before['objects'][k]!=after['objects'][k]}=={'FUNCTION:'+i for i in build.FUNCTIONS}
assert set(before['objects'])==set(after['objects'])
out=Path('cp6-proof/ar');out.mkdir(parents=True,exist_ok=True)
(out/'SOURCE.json').write_text(json.dumps(dict(head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),
 base=BASE,changed=sorted(changed),source_pins={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(changed)},
 inherited_sources_unchanged=True,changed_functions=list(build.FUNCTIONS),catalog_objects=len(after['objects']),
 production_go=False,hosted_migration_installed=False,independent_acceptance=False),indent=2)+'\n')
print('AR three-function successor admitted; inherited gates unchanged; CP6_HOLD')
