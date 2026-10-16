"""Pinned r2 CP17 provider plus unchanged Sol literal cases and real Auth HTTP witnesses."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parents[2]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'));sys.path.insert(0,str(HERE))
import cp7_cp17_fix_probe as probe
import independent_cases as sol
import correction_http as http_sol
strict=probe.native.strict_group
http=probe.modes.run_http
seen={}

def keep(name,result,ids):
 result.update(candidate_sha='2e9d6a468c110684c278d585418eb404250d1150',expected_ids=ids,
  prior_audit_seal='278a95cea5655c23f6bc94d1eb97959cdaaca5d6',oracle_amounts_and_expected_unchanged=True,production_go=False)
 assert set(result.get('cases',{}))==set(ids),(name,'SOL_CASESET')
 (probe.OUT.parent/(name+'.json')).write_text(json.dumps(result,indent=2,default=str)+'\n')
 seen[name]=result
 print(json.dumps(dict(group=name,counts=result.get('counts'),status=result.get('status'))),flush=True)

def wrapped(name,factory,verify):
 result=strict(name,factory,verify)
 if name=='CP7_CP17_FIXES':keep('SOL_R2_LITERAL',strict('SOL_R2_LITERAL',sol.factory,verify),sol.IDS)
 return result

def http_wrapped(provider,verify,label):
 result=http(provider,verify,label)
 if provider is probe.cases:keep('SOL_R2_CORRECTION_HTTP',http(http_sol,verify,'sol_r2_correction'),http_sol.IDS)
 return result

probe.native.strict_group=wrapped
probe.modes.run_http=http_wrapped
def runtime(browser_mode=False):
 result=probe.run()
 if set(seen)!= {'SOL_R2_LITERAL','SOL_R2_CORRECTION_HTTP'}:
  return dict(result,status='INCOMPLETE',sol_missing_groups=sorted({'SOL_R2_LITERAL','SOL_R2_CORRECTION_HTTP'}-set(seen)))
 bad={name:row.get('counts') for name,row in seen.items() if row.get('counts')!={'PASS':len(row['expected_ids'])}}
 if bad:return dict(result,status='INCOMPLETE',sol_nonpass=bad)
 return result
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
