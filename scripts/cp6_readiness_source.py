"""Bind readiness evidence to the checkout; refuse any CP6 SQL/package change."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE='10a834712e515af86c6d8baa89bbe40cff9793e3'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()
def main():
    assert git('merge-base',BASE,'HEAD')==BASE,'READINESS_NOT_BASED_ON_ACCEPTED_CP6'
    assert not git('diff',BASE,'HEAD','--name-only','--','supabase'),'READINESS_SQL_CHANGED'
    assert not git('diff','HEAD','--name-only'),'READINESS_TRACKED_SOURCE_DIRTY'
    manifest=ROOT/'supabase/release/cp6-t3/MANIFEST.json'
    package=json.loads(manifest.read_text());assert len(package['files'])==30
    hashes={}
    for row in package['files']:
        digest=hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()
        assert digest==row['package_sha256'],('READINESS_PACKAGE_HASH_CHANGED',row['key'])
        hashes[row['key']]=digest
    changed=git('diff',BASE,'HEAD','--name-only').splitlines()
    allowed_scripts={'cp6_bf_combined_modes.py','cp6_bf_free_browser.mjs','cp6_bf_free_browser_fixture.py','cp6_bf_free_modes.py','cp6_bf_free_probe.py','cp6_bf_vendor_browser.mjs'}
    assert all(p.startswith(('src/','docs/cp6-readiness/')) or p in {'.github/workflows/cp6-release-readiness.yml','.github/workflows/cp6-readiness-shell.yml'} or
      p.startswith('scripts/cp6_readiness_') or (p.startswith('scripts/') and Path(p).name in allowed_scripts) for p in changed),('READINESS_SCOPE',changed)
    result=dict(label='CP6_READINESS_SOURCE',head=git('rev-parse','HEAD'),tree=git('rev-parse','HEAD^{tree}'),accepted_cp6_base=BASE,
      cp7_changes_included=False,sql_bytes_unchanged=True,package_files=30,package_hashes=hashes,
      changed_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in changed},production_go=False,independent_acceptance=False)
    out=ROOT/'cp6-proof/t3/READINESS_SOURCE.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
