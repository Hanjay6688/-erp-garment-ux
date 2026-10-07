"""Native product-bound global matching/netting and dated scenario composition."""
import hashlib,json,traceback
import psycopg
import cp7_plan_bundle as bundle
import cp7_schedule_bundle as schedule
import cp7_f03_bundle as f03
import cp7_planning_bundle as planning
import cp7_baseline_bundle as baseline
import cp7_supply_bundle as supply
import cp7_plan_native_cases as history_cases
import cp7_p12_nota_probe as payroll
import cp7_p13_finance_probe as finance
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp7_catalog_state import canonical_public_state,exact_public_catalog
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_F04_NATIVE_PLANS.json'
def public_state(cur):
 # The accepted harness aggregates functions ORDER BY 1, a constant inside
 # jsonb_agg. PostgreSQL may return unchanged pg_proc members in another physical
 # order after ACL updates. Sort every original [signature,definition_hash]
 # pair without deleting a field/member or changing the frozen case runner.
 state=native.public_state(cur)
 return canonical_public_state(state)

def verify(cur):
 bundle.predecessor.verify(cur)
 payroll.verify(cur,True,True,True,True,True);finance.verify(cur);f03.journal.verify(cur);f03.misc.verify(cur);f03.installment.verify(cur)
 return dict(stage='EXPLICIT_F03_COMBINED_DEVELOPMENT_STACK',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),full_family_acceptance=False)

def run():
 candidate=bundle;case_provider=history_cases;checker=verify;extra='';expected=43;out=OUT;phase='cp7_f04_plan';browser_script='cp7_f04_plan_browser.mjs'
 report=dict(label='CP7_F04_NATIVE_PLANS',status='INCOMPLETE',production_go=False,independent_acceptance=False,full_family_acceptance=False,full_P08_acceptance=False,scope='NATIVE_DRAFT_INTENT_LINKED_EXACT_SIZE_PHYSICAL_ACTUAL_AND_GLOBAL_PHYSICAL_ROLL_PLAN_BUDGET_CURRENT_AUTH_MVCC_NO_RESERVATION',source_sha256=hashlib.sha256(candidate.bundle().encode()).hexdigest(),expected_case_count=expected);installed=False
 try:
  with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
   p09.wip.policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=public_state(cur);accepted_functions_before=p09.functions(cur);conn.rollback();originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
   internal_before=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
   originals['erp.require_owner_admin()']=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
   f03.note_report.capture(cur,originals)
   cur.execute(f03.extension()+'\n'+planning.extension()+'\n'+baseline.extension()+'\n'+supply.extension()+'\n'+schedule.extension()+'\n'+bundle.predecessor.predecessor.extension()+'\n'+bundle.predecessor.extension()+'\n'+extra,prepare=False);after=p09.functions(cur)
   path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)");grants={}
   for principal,signatures in candidate.GRANTS.items():
    for signature in signatures:
     key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add((principal,'EXECUTE',False))
   cur.execute("select set_config('search_path',%s,true)",(path,))
   expected_definitions=f03.note_report.expected_definitions(internal_before,originals,f03.patched_internal,f03.settlement.patched_owner)
   for sig,old in pre.items():
    new=after[sig];expected_definition_hash=hashlib.md5(expected_definitions[sig].encode()).hexdigest() if sig in expected_definitions else old['definition']
    assert new['definition']==expected_definition_hash and new['owner']==old['owner'],('F03_UNDECLARED_PREDECESSOR_CHANGE',sig)
    assert {tuple(x)for x in new['acl']or[]}=={tuple(x)for x in old['acl']or[]}|grants.get(sig,set()),('F03_UNDECLARED_ACL_DELTA',sig)
   for signature,definition in expected_definitions.items():assert cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]==definition,('F03_EXACT_ADMISSION_DELTA',signature)
   assert cur.execute("select pg_get_functiondef('cp7_payroll.rebuild_nonwork(uuid)'::regprocedure)").fetchone()[0]==f03.settlement.derive_nonwork(f03.settlement.accepted('populate_payroll_draft'))
   p09.INSTALLED_FUNCTIONS=after;report['combined_declared_execute_grants']={k:sorted(v)for k,v in grants.items()};report['exact_guard_sha256']={k:hashlib.sha256(v.encode()).hexdigest()for k,v in expected_definitions.items()};report['all_other_predecessor_definitions_and_owners_unchanged']=True
   conn.commit();installed=True;checker(cur);conn.rollback()
  report['advisors_with_cp7']=advisors(package.boundary.PG)
  with exact_public_catalog(native)as catalog_audit:
   report['native']=native.strict_group('CP7_F04_NATIVE_PLANS',case_provider.cases,checker)
  report['native_public_catalog_comparison']=catalog_audit
  report['races']=modes.run_races(case_provider,checker,phase)
  report['http']=modes.run_http(case_provider,checker,phase)
  # Keep port ownership evidence before opening the native browser host.
  import subprocess
  report['browser_port_state_before']=subprocess.run(['ss','-lntp','sport = :54328'],capture_output=True,text=True,check=False).stdout
  report['browser']=modes.run_browser(bundle.ROOT/'scripts'/browser_script,checker,phase+'_browser')
 except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
 finally:
  if installed:
   with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
    for definition in originals.values():cur.execute(definition,prepare=False)
    for role in candidate.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
    conn.commit();restored_boundary=package.boundary.snapshot(cur);restored_public=public_state(cur)
    restored_functions=p09.functions(cur)
    report['restore_components']=dict(erp_platform_auth_schema_acl=restored_boundary==before,public_catalog_and_rows=restored_public==public_before,erp_public_auth_function_definitions_owners_acls=restored_functions==accepted_functions_before)
    if restored_boundary!=before:report['restore_boundary_difference']=dict(before=before,after=restored_boundary)
    if restored_public!=public_before:report['restore_public_difference']=dict(before=public_before,after=restored_public)
    if restored_functions!=accepted_functions_before:report['restore_function_difference']=dict(before=accepted_functions_before,after=restored_functions)
    report['cp6_restored']=all(report['restore_components'].values());conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
   report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));d=report['advisor_delta'];report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or(d['status']=='REVIEW_REQUIRED' and all(f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and(f.get('metadata')or{}).get('schema')in('cp7_recost','cp7_period','cp7_sales','cp7_payroll','cp7_attendance','cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice','cp7_receipt_fix')for f in d.get('added',[])))
  report['required_case_counts']={'native':29,'races':8,'http':2,'browser':4}
  report['required_case_counts_pass']=all(report.get(k,{}).get('counts')=={'PASS':count}for k,count in report['required_case_counts'].items())
  declaration=json.loads((bundle.ROOT/'docs/cp7/f04/SHARED_MATERIAL_POOL.json').read_text());report['required_case_ids']=declaration['required_case_ids']
  report['required_case_ids_pass']=declaration['expected_case_count']==expected and declaration['required_case_counts']==report['required_case_counts'] and all(set(report.get(k,{}).get('races'if k=='races'else'cases',{}))==set(ids)for k,ids in report['required_case_ids'].items())
  groups=[report.get(k,{})for k in('native','races','http','browser')];report['observed_case_count']=sum(sum(g.get('counts',{}).values())for g in groups);report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and report['required_case_counts_pass'] and report['required_case_ids_pass'] and report['observed_case_count']==expected and all(g.get('status')in('PASS','RUN_COMPLETE') and set(g.get('counts',{}))=={'PASS'} and g.get('database_remaining',0)==0 for g in groups) else 'INCOMPLETE'
  out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({k:report.get(k)for k in('label','status','source_sha256','observed_case_count','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
 return dict(status=report['status'],production_go=False,independent_acceptance=False,full_family_acceptance=False)
if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run();package.run('install')
