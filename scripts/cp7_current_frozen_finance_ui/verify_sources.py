"""Verify byte-exact B input and retain every qualified A backend source."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def check():
 manifest=json.loads((HERE/'B_SOURCE.json').read_bytes())
 expected=set()
 for item in manifest['files']:
  p=HERE/item['vendored_path'];expected.add(p)
  raw=p.read_bytes()
  assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],item['path']
 assert expected=={p for p in (HERE/'vendor').rglob('*') if p.is_file()},'Unpinned or missing vendored source'
 # All pre-existing tracked source remains at the public followup base tree.
 # Only this new opt-in directory may differ, including after it is committed.
 changes=subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',manifest['A_backend_tree']]).decode().splitlines()
 assert all(p.startswith('scripts/cp7_current_frozen_finance_ui/') for p in changes),changes
 return {'status':'PASS','B_source_head':manifest['B_source_head'],'exact_B_files':len(expected),'qualified_A_backend_unchanged':True,'production_go':False}

if __name__=='__main__':print(json.dumps(check()))
