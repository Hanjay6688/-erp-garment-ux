"""Fable (independent auditor) driver on the candidate's FULL CP7 composition, commit d0b9e9c2.

Installs exactly what the writer's K2/K3/K4/K6 suites install (F03 + planning + baseline + supply + schedule + analysis
with the staged path + reminders v2), through the candidate's own installer on the disposable aligned clone, then runs
the Fable scenario module named by FABLE_SCENARIO (own cases, own oracles) through the frozen strict runners:
savepoint group (cp6_auditor_runner.strict_group), races and HTTP (cp6_auditor_modes), optional browser module.
The install/restore skeleton mirrors scripts/cp7_f05_analysis_probe.run at d0b9e9c2 so the installed body is the
writer's product, not an auditor copy. Evidence only: production_go=False, independent_acceptance is written by the
auditor's report, never by this script."""
import hashlib,importlib,json,os,subprocess,traceback
from pathlib import Path
import psycopg
import cp7_f05_analysis_probe as f05
import cp7_analysis_bundle as bundle
import cp7_schedule_bundle as schedule
import cp7_f03_bundle as f03
import cp7_planning_bundle as planning
import cp7_baseline_bundle as baseline
import cp7_supply_bundle as supply
import cp7_reminder_v2_bundle as top
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp7_catalog_state import exact_public_catalog
from cp6_t3_aligned_install import advisors,advisor_delta

SCENARIO=os.environ['FABLE_SCENARIO']
GROUPS=[g.strip() for g in os.environ.get('FABLE_GROUPS','native,races,http').split(',') if g.strip()]
BROWSER=os.environ.get('FABLE_BROWSER','').strip()
HERE=Path(__file__).resolve().parent
scenario=importlib.import_module(SCENARIO)
OUT=bundle.ROOT/'cp6-proof/t3'/('FABLE_'+SCENARIO.upper()+'.json')
def checker(cur):f05.verify(cur);top.verify(cur)
def counts(group):return (group or {}).get('counts') or {}
def complete(group):
 return bool(group) and group.get('status') in ('PASS','RUN_COMPLETE') and set(counts(group))=={'PASS'} and counts(group)['PASS']>0 \
  and not group.get('missing') and not group.get('cleanup_failures') and not group.get('auth_cleanup_failures') and group.get('database_remaining',0)==0 and not group.get('error')
def run():
 report=dict(label='FABLE_'+SCENARIO.upper(),auditor='Fable',status='INCOMPLETE',production_go=False,independent_acceptance=False,
  scenario=SCENARIO,scenario_sha256=hashlib.sha256((HERE/(SCENARIO+'.py')).read_bytes()).hexdigest(),groups_requested=GROUPS,browser=BROWSER or None,
  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=bundle.ROOT,text=True).strip(),
  source_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=bundle.ROOT,text=True).strip(),
  composition_sha256=hashlib.sha256((f03.extension()+'\n'+planning.extension()+'\n'+baseline.extension()+'\n'+supply.extension()+'\n'+schedule.extension()+'\n'+bundle.predecessor.extension()+'\n'+bundle.extension()+'\n'+top.extension()).encode()).hexdigest(),
  installer='writer (scripts at d0b9e9c2), oracles Fable')
 if BROWSER:report['browser_sha256']=hashlib.sha256((HERE/BROWSER).read_bytes()).hexdigest()
 installed=False
 try:
  with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
   p09.wip.policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=f05.public_state(cur);accepted_functions_before=p09.functions(cur);conn.rollback()
   originals,installation=p09.install(cur);report['installation']=installation;pre=p09.functions(cur)
   internal_before=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
   originals['erp.require_owner_admin()']=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
   f03.note_report.capture(cur,originals)
   cur.execute(f03.extension()+'\n'+planning.extension()+'\n'+baseline.extension()+'\n'+supply.extension()+'\n'+schedule.extension()+'\n'+bundle.predecessor.extension()+'\n'+bundle.extension()+'\n'+top.extension(),prepare=False);after=p09.functions(cur)
   path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)");grants={}
   for principal,signatures in top.GRANTS.items():
    for signature in signatures:
     key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add((principal,'EXECUTE',False))
   cur.execute("select set_config('search_path',%s,true)",(path,))
   expected_definitions=f03.note_report.expected_definitions(internal_before,originals,f03.patched_internal,f03.settlement.patched_owner)
   for sig,old in pre.items():
    new=after[sig];expected_definition_hash=hashlib.md5(expected_definitions[sig].encode()).hexdigest() if sig in expected_definitions else old['definition']
    assert new['definition']==expected_definition_hash and new['owner']==old['owner'],('F03_UNDECLARED_PREDECESSOR_CHANGE',sig)
    assert {tuple(x)for x in new['acl']or[]}=={tuple(x)for x in old['acl']or[]}|grants.get(sig,set()),('F03_UNDECLARED_ACL_DELTA',sig)
   p09.INSTALLED_FUNCTIONS=after
   conn.commit();installed=True;checker(cur);conn.rollback()
  report['advisors_with_cp7']=advisors(package.boundary.PG)
  if 'native' in GROUPS and hasattr(scenario,'cases'):
   with exact_public_catalog(native,retain_raw=True) as catalog_audit:
    report['native']=native.strict_group(report['label']+'_NATIVE',scenario.cases,checker)
   report['native_public_catalog_comparison']=catalog_audit
  if 'races' in GROUPS and hasattr(scenario,'races'):report['races']=modes.run_races(scenario,checker,'fable_'+SCENARIO)
  if 'http' in GROUPS and hasattr(scenario,'http_cases'):report['http']=modes.run_http(scenario,checker,'fable_'+SCENARIO)
  if 'browser' in GROUPS and BROWSER:report['browser']=modes.run_browser(HERE/BROWSER,checker,'fable_'+SCENARIO+'_browser')
 except Exception as e:report.update(error=str(e)[:4000],traceback=traceback.format_exc()[-6000:])
 finally:
  if installed:
   try:
    with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
     for definition in originals.values():cur.execute(definition,prepare=False)
     for role in top.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
     conn.commit();restored_boundary=package.boundary.snapshot(cur);restored_public=f05.public_state(cur);restored_functions=p09.functions(cur)
     report['restore_components']=dict(erp_platform_auth_schema_acl=restored_boundary==before,public_catalog_and_rows=restored_public==public_before,erp_public_auth_function_definitions_owners_acls=restored_functions==accepted_functions_before)
     report['cp6_restored']=all(report['restore_components'].values());conn.rollback()
    report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}))
   except Exception as restoration_error:
    report.update(restore_error=str(restoration_error),restore_traceback=traceback.format_exc()[-4000:],cp6_restored=False)
    report.setdefault('error','CP7_RESTORATION_INCOMPLETE: '+str(restoration_error))
  groups={k:report[k] for k in ('native','races','http','browser') if k in report}
  report['counts']={k:counts(v) for k,v in groups.items()}
  def rows_of(v):return (v.get('races') if 'races' in v else v.get('cases')) or {}
  report['per_case']={k:{case:(row.get('status') if isinstance(row,dict) else repr(row)[:80]) for case,row in rows_of(v).items()} for k,v in groups.items() if isinstance(v,dict)}
  report['business_day_retried']={k:bool(v.get('business_day_retried')) for k,v in groups.items()}
  report['status']='PASS' if groups and all(complete(v) for v in groups.values()) and not report.get('error') and report.get('cp6_restored') else 'INCOMPLETE'
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
  print(json.dumps(dict(group='FABLE_SUMMARY',label=report['label'],status=report['status'],counts=report['counts'],per_case=report['per_case'],business_day_retried=report['business_day_retried'],cp6_restored=report.get('cp6_restored'),error=report.get('error')),default=str),flush=True)
 return dict(label=report['label'],status=report['status'],production_go=False,independent_acceptance=False)
if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run();package.run('install')
