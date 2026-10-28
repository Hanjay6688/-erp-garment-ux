"""Explicit source successor: A base plus exact qualified B driver and proofs."""
from pathlib import Path
from hashlib import sha256
import json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='3efecab381578cb12b06b9bedd97b31b7a20b26a';B='b2492bdb647f075d613842a4a779879d88ca0ddd';QUALIFIED='f5e4a0eb98f52c7615c3f4fb2459128bc76ed007'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def verify_files(overrides=None):
 cfg=json.loads((HERE/'CONFIG.json').read_bytes());assert cfg['base_head']==BASE and cfg['B_delivery']==B and cfg['B_qualification']==QUALIFIED
 def read(p):return(overrides or{}).get(p,(ROOT/p).read_bytes())
 for item in cfg['imports']:
  raw=read(item['path']);assert sha256(raw).hexdigest()==item['sha256'],item['path']
  assert raw==git('show',B+':'+item['path']),item['path']
 graph=json.loads(read('scripts/current-finance-combined-browser-qualification/BUILD_SOURCE_3194.json'))
 assert len(graph['files'])==79
 for row in graph['files']:
  raw=read(row['path']);assert len(raw)==row['bytes']and sha256(raw).hexdigest()==row['sha256'],row['path']
 return cfg

def check():
 cfg=verify_files();assert not git('status','--porcelain','--untracked-files=no').strip()
 allowed={r['path']for r in cfg['imports']}|set(cfg['status_paths'])
 assert all(p in allowed or p.startswith('scripts/current-integrated-B3194-source/')for p in git('diff','--name-only',BASE,'HEAD').decode().splitlines()),'UNDECLARED_A_INTEGRATION_CHANGE'
 assert not git('diff',QUALIFIED,'HEAD','--','src','supabase','scripts/cp7-src','package.json','package-lock.json','vite.config.ts').strip(),'PRODUCT_DIFFERS_FROM_ACTUAL_B_CANDIDATE'
 for p in ('src/nativeStagedJob.ts','src/nativeStagedJob.initial.test.ts'):
  assert(ROOT/p).read_bytes()==git('show',cfg['B_driver']+':'+p)
 # All other former A source/proof bytes remain unchanged by the allowlist;
 # old 4313-file manifests are preserved, not rewritten for the new driver.
 return dict(status='PASS_EXACT_A_B_DRIVER_BROWSER_SOURCE_SUCCESSOR',head=git('rev-parse','HEAD').decode().strip(),base=BASE,B_qualification=QUALIFIED,imported_exact_entries=len(cfg['imports']),compiled_graph_files=79,changed_product_files=['src/nativeStagedJob.ts'],historical_manifests_rewritten=False,new_DB_or_Auth_browser_cases=0,production_go=False,independent_acceptance=False)
if __name__=='__main__':print(json.dumps(check()))
