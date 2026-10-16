"""CP17 installer + only three UAT-build/Native-transport cases; product source untouched."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'auditor/scripts'))
import cp7_cp17_fix_probe as probe
IDS=['SOL_R2_UAT_REAL_AUTH_HIDDEN_MENUS_PHONE','SOL_R2_UAT_CUSTOMER_LIFECYCLE_DESKTOP','SOL_R2_UAT_AUTO_PO_NATIVE_PHONE']
seen={};original_browser=probe.modes.run_browser;original_subprocess=probe.modes.subprocess.run
def redirected_host(args,*pos,**kw):
 if isinstance(args,list) and args[:2]==['node','scripts/cp6_auditor_browser_host.mjs']:
  args=[args[0],str(HERE/'uat_browser_host.mjs'),*args[2:]]
 return original_subprocess(args,*pos,**kw)
def browser(script,verify,phase):
 probe.modes.subprocess.run=redirected_host
 try:r=original_browser(HERE/'uat_cases.mjs',verify,'sol_r2_uat_native')
 finally:probe.modes.subprocess.run=original_subprocess
 seen.update(r);return r
skip=lambda *args,**kwargs:dict(status='NOT_RUN_THIS_ADDITIONAL_GROUP',cases={},counts={})
probe.native.strict_group=skip;probe.modes.run_races=skip;probe.modes.run_http=skip;probe.modes.run_browser=browser
probe.OUT=probe.OUT.parent/'SOL_R2_UAT_INSTALLATION.json'
def runtime(browser_mode=False):
 probe.run();installation=json.loads(probe.OUT.read_text())
 report=dict(label='SOL_R2_UAT_NATIVE',candidate_sha='2e9d6a468c110684c278d585418eb404250d1150',expected_ids=IDS,
  evidence_origin='INDEPENDENT_NATIVE_RERUN',frontend_mode='UAT_AUTH_SIMULATION',hosted_tested=False,
  transport='Expected-host browser requests rewritten to disposable Native before network; no business response mocks',
  production_go=False,cases=seen.get('cases',{}),counts=seen.get('counts',{}),native_browser=seen,
  cp6_restored=installation.get('cp6_restored'),advisor_gate=installation.get('advisor_gate'),provider_145_cases_reexecuted=False)
 report['status']='PASS' if set(report['cases'])==set(IDS) and report['counts']=={'PASS':3} and report['cp6_restored'] and report['advisor_gate'] and seen.get('database_remaining')==0 and seen.get('auth_counts',{}).get('restored') else 'INCOMPLETE'
 (probe.OUT.parent/'SOL_R2_UAT_RESULT.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
 print(json.dumps({k:report[k]for k in('label','status','counts','cp6_restored','advisor_gate')}),flush=True)
 return dict(status=report['status'],production_go=False)
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
