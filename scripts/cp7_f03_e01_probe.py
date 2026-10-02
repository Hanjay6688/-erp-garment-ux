"""E01 exact worksheet on the explicitly qualified combined stack."""
import hashlib,json,traceback
import psycopg
import cp7_restore_state as restore_state
import cp7_f03_bundle as bundle
import cp7_f03_e01_cases as cases
import cp7_p12_nota_probe as payroll
import cp7_p13_finance_probe as finance
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_F03_E01.json'

def verify(cur):
 payroll.verify(cur,True,True,True,True,True);finance.verify(cur)
 return dict(stage='EXPLICIT_F03_COMBINED_DEVELOPMENT_STACK',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),full_family_acceptance=False)

def run():
 report=dict(label='CP7_F03_E01',status='INCOMPLETE',production_go=False,independent_acceptance=False,full_family_acceptance=False,scope='FROZEN_E01_NATIVE_PRODUCTION_PLUS_NATIVE_HTTP_BROWSER_SALES_CASH_RETURN_REPORT',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),expected_case_count=4);installed=False
 try:
  with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
   p09.wip.policy.bf.verified(cur);restore_before=restore_state.capture(cur,package.boundary.snapshot,native.public_state,p09.functions);before=restore_before['boundary'];public_before=restore_before['public'];conn.rollback();originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
   internal_before=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
   originals['erp.require_owner_admin()']=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
   bundle.note_report.capture(cur,originals)
   cur.execute(bundle.extension(),prepare=False);after=p09.functions(cur)
   path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)");grants={}
   for principal,signatures in bundle.GRANTS.items():
    for signature in signatures:
     key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add((principal,'EXECUTE',False))
   cur.execute("select set_config('search_path',%s,true)",(path,))
   expected_definitions=bundle.note_report.expected_definitions(internal_before,originals,bundle.patched_internal,bundle.settlement.patched_owner)
   for sig,old in pre.items():
    new=after[sig];expected=hashlib.md5(expected_definitions[sig].encode()).hexdigest() if sig in expected_definitions else old['definition']
    assert new['definition']==expected and new['owner']==old['owner'],('F03_UNDECLARED_PREDECESSOR_CHANGE',sig)
    assert {tuple(x)for x in new['acl']or[]}=={tuple(x)for x in old['acl']or[]}|grants.get(sig,set()),('F03_UNDECLARED_ACL_DELTA',sig)
   for signature,definition in expected_definitions.items():assert cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]==definition,('F03_EXACT_ADMISSION_DELTA',signature)
   assert cur.execute("select pg_get_functiondef('cp7_payroll.rebuild_nonwork(uuid)'::regprocedure)").fetchone()[0]==bundle.settlement.derive_nonwork(bundle.settlement.accepted('populate_payroll_draft'))
   p09.INSTALLED_FUNCTIONS=after;report['combined_declared_execute_grants']={k:sorted(v)for k,v in grants.items()};report['exact_guard_sha256']={k:hashlib.sha256(v.encode()).hexdigest()for k,v in expected_definitions.items()};report['all_other_predecessor_definitions_and_owners_unchanged']=True
   conn.commit();installed=True;verify(cur);conn.rollback()
  report['advisors_with_cp7']=advisors(package.boundary.PG)
  report['native']=native.strict_group('CP7_F03_E01',cases.cases,verify)
  report['http']=modes.run_http(cases,verify,'cp7_f03_e01')
  report['browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_f03_e01_browser.mjs',verify,'cp7_f03_e01_browser')
 except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
 finally:
  if installed:
   with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
    for definition in originals.values():cur.execute(definition,prepare=False)
    for role in bundle.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
    conn.commit();report['cp6_restored']=restore_state.prove(cur,restore_before,package.boundary.snapshot,native.public_state,p09.functions,report);conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
   report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));d=report['advisor_delta'];report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or(d['status']=='REVIEW_REQUIRED' and all(f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and(f.get('metadata')or{}).get('schema')in('cp7_recost','cp7_period','cp7_sales','cp7_payroll','cp7_attendance','cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice')for f in d.get('added',[])))
  groups=[report.get(k,{})for k in('native','http','browser')];report['observed_case_count']=sum(sum(g.get('counts',{}).values())for g in groups);report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and report['observed_case_count']==4 and all(g.get('status')in('PASS','RUN_COMPLETE') and set(g.get('counts',{}))=={'PASS'} and g.get('database_remaining',0)==0 for g in groups) else 'INCOMPLETE'
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({k:report.get(k)for k in('label','status','source_sha256','observed_case_count','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
 return dict(status=report['status'],production_go=False,independent_acceptance=False,full_family_acceptance=False)
if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run();package.run('install')
