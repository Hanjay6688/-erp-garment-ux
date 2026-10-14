"""New qualification: original CP6 source charter superseded by CP1-7 scope.
Keep SQL/package invariance and record the complete current frozen source.
No case oracle is changed. The first READINESS_SCOPE red is preserved.
"""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path.cwd()
SOURCE='0b7049d9203bac52b47a4c89f3e0d75646067a8f'
BASE='10a834712e515af86c6d8baa89bbe40cff9793e3'
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
assert git('rev-parse','HEAD')==SOURCE
assert git('merge-base',BASE,'HEAD')==BASE
assert not git('diff',BASE,'HEAD','--name-only','--','supabase')
assert not git('diff','HEAD','--name-only')
package=json.loads(Path('supabase/release/cp6-t3/MANIFEST.json').read_text())
assert len(package['files'])==30
hashes={}
for row in package['files']:
 d=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
 assert d==row['package_sha256'],row['key']
 hashes[row['key']]=d
changed=git('diff',BASE,'HEAD','--name-only').splitlines()
result=dict(label='SOL_CP1_7_READINESS_SOURCE',head=SOURCE,tree=git('rev-parse','HEAD^{tree}'),accepted_cp6_base=BASE,
 cp7_changes_included=True,sql_bytes_unchanged=True,package_files=30,package_hashes=hashes,
 changed_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).is_file() else 'DELETED' for p in changed},
 superseded_guard='READINESS_SCOPE: prior CP6-only allowed diff predates owner CP1-7 charter',
 initial_run=38560104256,new_qualification=True,oracle_change=False,production_go=False,independent_acceptance=False)
p=ROOT/'cp6-proof/t3/READINESS_SOURCE.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='changed_sha256'}))
