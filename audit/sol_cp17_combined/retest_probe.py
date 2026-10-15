"""Run the unmodified candidate CP17 suite plus separate Sol oracles.
Candidate product paths are not changed. Original provider budgets stay intact.
"""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parents[2]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'));sys.path.insert(0,str(HERE))
import cp7_cp17_fix_probe as probe
import independent_cases as sol
original=probe.native.strict_group
seen=[]
def wrapped(name,factory,verify):
 result=original(name,factory,verify)
 if name=='CP7_CP17_FIXES':
  extra=original('SOL_R1_INDEPENDENT',sol.factory,verify)
  extra.update(candidate_sha='dfab13bf62398a69a02bf6221c06d29075e5e40b',probe_sha256=hashlib.sha256((HERE/'independent_cases.py').read_bytes()).hexdigest(),expected_ids=sol.IDS,production_go=False)
  seen.append(extra)
  (probe.OUT.parent/'SOL_INDEPENDENT.json').write_text(json.dumps(extra,indent=2,default=str)+'\n')
  print(json.dumps({'SOL_INDEPENDENT_RESULT':extra},default=str),flush=True)
 return result
probe.native.strict_group=wrapped
def runtime(browser_mode=False):
 result=probe.run()
 assert len(seen)==1 and set(seen[0].get('cases',{}))==set(sol.IDS),'SOL_INDEPENDENT_CASESET'
 if seen[0].get('counts')!={'PASS':len(sol.IDS)} or not seen[0].get('complete_boundary_restored'):
  return dict(result,status='INCOMPLETE',sol_independent_nonpass=True)
 return result
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
