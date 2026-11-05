from pathlib import Path
import json,hashlib,argparse
p=argparse.ArgumentParser(description='Read-only B UI source compatibility; never authorizes backend or applies patches')
p.add_argument('--root',required=True)
a=p.parse_args();root=Path(a.root);m=json.loads((Path(__file__).parent/'SOURCE.json').read_text())
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
result={};unknown=False
for name,files in [('retained_B',m['retained_B_files']),('proposed_copy',m['copy_files'])]:
 states={}
 for path,refs in files.items():
  f=root/path;v=pin(f.read_bytes()) if f.is_file() else None
  states[path]='BEFORE' if v==refs['before'] else 'AFTER' if v==refs['after'] else 'REVIEW_REQUIRED'
 unknown|=any(s=='REVIEW_REQUIRED' for s in states.values())
 result[name]={'files':states,'action':'ALREADY_APPLIED_SKIP' if all(s=='AFTER' for s in states.values()) else 'BYTE_COMPATIBLE_REVIEW_BACKEND_FIRST' if all(s=='BEFORE' for s in states.values()) else 'SELECTIVE_REVIEW_REQUIRED'}
print(json.dumps({'packages':result,'backend_admission':'NOT_DETERMINED_REQUIRES_A','applies_changes':False},indent=2))
raise SystemExit(1 if unknown else 0)
