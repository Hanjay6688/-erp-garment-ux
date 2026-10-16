"""Install the pinned CP17 composition and run only Sol's additional declared group.

Uses the provider's unchanged installer and restore checks. CP17's 145 cases are
not repeated here and its original declaration is not changed or claimed PASS.
"""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'auditor/scripts'));sys.path.insert(0,str(HERE))
import cp7_cp17_fix_probe as probe
import new_cases as sol

original_strict=probe.native.strict_group
seen={}
def strict(name,factory,verify):
 result=original_strict('SOL_R2_NEW_BOUNDARIES',sol.factory,verify)
 assert set(result.get('cases',{}))==set(sol.IDS),'SOL_NEW_CASESET'
 seen.update(result)
 return result
probe.native.strict_group=strict
skipped=lambda *args,**kwargs:dict(status='NOT_RUN_THIS_ADDITIONAL_GROUP',cases={},counts={})
probe.modes.run_races=skipped;probe.modes.run_http=skipped;probe.modes.run_browser=skipped
probe.OUT=probe.OUT.parent/'SOL_R2_NEW_INSTALLATION.json'
def runtime(browser_mode=False):
 probe.run()
 installation=json.loads(probe.OUT.read_text())
 report=dict(label='SOL_R2_NEW_BOUNDARIES',candidate_sha='2e9d6a468c110684c278d585418eb404250d1150',
  production_go=False,evidence_origin='INDEPENDENT_NATIVE_RERUN',cases=seen.get('cases',{}),
  counts=seen.get('counts',{}),cp6_restored=installation.get('cp6_restored'),advisor_gate=installation.get('advisor_gate'),
  status='PASS' if seen.get('counts')=={'PASS':len(sol.IDS)} and installation.get('cp6_restored') and installation.get('advisor_gate') else 'INCOMPLETE',
  provider_145_cases_reexecuted=False,installation_report='SOL_R2_NEW_INSTALLATION.json')
 (probe.OUT.parent/'SOL_R2_NEW_RESULT.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
 print(json.dumps({k:v for k,v in report.items()if k!='cases'}),flush=True)
 return dict(status=report['status'],production_go=False)
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
