"""Frozen CP6 -> full F03 -> owning receipt correction qualification, disposable only."""
import hashlib,json,subprocess,traceback
import psycopg
import cp7_restore_state as restore_state
import cp7_f03_bundle as bundle
import cp7_receipt_correction_bundle as rf_bundle
import cp7_receipt_correction_cases as cases
import cp7_receipt_correction_verify as rf_verify
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp7_f03_probe import verify as f03_verify
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_RECEIPT_CORRECTION.json'
MANIFEST=bundle.ROOT/'scripts/cp7_receipt_correction_manifest.json'

def verify(cur):return dict(f03=f03_verify(cur),receipt_correction=rf_verify.verify(cur))

def run():
 report=dict(label='CP7_OWNING_RECEIPT_CORRECTION',status='INCOMPLETE',production_go=False,independent_acceptance=False,full_family_acceptance=False,
  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=bundle.ROOT,text=True).strip(),
  source_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=bundle.ROOT,text=True).strip(),
  f03_source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),source_sha256=rf_bundle.sha256(),
  expected_case_count=cases.EXPECTED,required_case_counts=cases.REQUIRED,
  scope='OWNING_POSTED_RECEIPT_CORRECTION_AFTER_USE_SOURCE_TIME_INVERSE_REPLACEMENT_SAME_ROLLS_MATERIAL_REATTRIBUTION_RECOST_HPP_GL_PAYMENT_REPLAY_EFFECTIVE_CARD_AND_CURRENT_AUTHORITY');installed=False
 report['manifest_sha256']=hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
 report['predeclared_case_ids']=cases.MANIFEST['groups']
 report['provider_sha256']={p:hashlib.sha256((bundle.ROOT/'scripts'/p).read_bytes()).hexdigest() for p in('cp7_receipt_correction_cases.py','cp7_receipt_correction_verify.py','cp7_receipt_correction_browser.mjs','cp7_receipt_correction_browser_fixture.py')}
 try:
  with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
   p09.wip.policy.bf.verified(cur);restore_before=restore_state.capture(cur,package.boundary.snapshot,native.public_state,p09.functions);conn.rollback()
   originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
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
   for signature,old in pre.items():
    new=after[signature];expected=hashlib.md5(expected_definitions[signature].encode()).hexdigest() if signature in expected_definitions else old['definition']
    assert new['definition']==expected and new['owner']==old['owner'],('RF_F03_UNDECLARED_CHANGE',signature)
    assert {tuple(x) for x in new['acl'] or []}=={tuple(x) for x in old['acl'] or []}|grants.get(signature,set()),('RF_F03_UNDECLARED_GRANT',signature)
   # The receipt correction itself: every existing function keeps its exact
   # definition and owner; only the declared composition grants are added.
   tables_before={t:cur.execute("select coalesce(relacl::text,'') from pg_class where oid=%s::regclass",(t,)).fetchone()[0] for t in rf_bundle.TABLE_GRANTS}
   cur.execute(rf_bundle.sql(),prepare=False);final=p09.functions(cur)
   for signature,old in after.items():
    new=final[signature];assert new['definition']==old['definition'] and new['owner']==old['owner'],('RF_UNDECLARED_CHANGE',signature)
    assert {tuple(x) for x in new['acl'] or []}=={tuple(x) for x in old['acl'] or []}|rf_bundle.GRANTS.get(signature,set()),('RF_UNDECLARED_GRANT',signature)
   for table,rights in rf_bundle.TABLE_GRANTS.items():
    for right in rights:assert cur.execute("select has_table_privilege('postgres',%s,%s)",(table,right)).fetchone()[0],('RF_DECLARED_TABLE_GRANT',table,right)
   report['table_acl_before']=tables_before
   p09.INSTALLED_FUNCTIONS=final;report['all_predecessor_definitions_owners_unchanged']=True
   report['receipt_correction_ownership']=rf_verify.verify(cur);conn.commit();installed=True;verify(cur);conn.rollback()
  report['advisors_with_cp7']=advisors(package.boundary.PG)
  report['native']=native.strict_group('CP7_RECEIPT_CORRECTION',cases.cases,verify)
  report['races']=modes.run_races(cases,verify,'cp7_receipt_correction')
  report['http']=modes.run_http(cases,verify,'cp7_receipt_correction')
  report['browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_receipt_correction_browser.mjs',verify,'cp7_receipt_correction_browser')
 except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
 finally:
  if installed:
   try:
    with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
     for definition in originals.values():cur.execute(definition,prepare=False)
     cur.execute('drop schema if exists cp7_receipt_fix cascade',prepare=False)
     for role in bundle.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
     conn.commit();report['cp6_restored']=restore_state.prove(cur,restore_before,package.boundary.snapshot,native.public_state,p09.functions,report);conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
    report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));delta=report['advisor_delta']
    report['advisor_gate']=delta['status']=='NO_NEW_FINDINGS' or (delta['status']=='REVIEW_REQUIRED' and all(f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and (f.get('metadata') or {}).get('schema') in ('cp7_recost','cp7_period','cp7_sales','cp7_payroll','cp7_attendance','cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice','cp7_receipt_fix') for f in delta.get('added',[])))
   except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False)
  groups=[report.get(k,{}) for k in cases.REQUIRED];report['observed_case_count']=sum(sum(g.get('counts',{}).values()) for g in groups)
  report['required_case_counts_pass']=all(report.get(k,{}).get('counts')=={'PASS':n} for k,n in cases.REQUIRED.items())
  report['status']='PASS' if not report.get('error') and not report.get('restore_error') and report.get('cp6_restored') and report.get('advisor_gate') and report['required_case_counts_pass'] and report['observed_case_count']==cases.EXPECTED and all(g.get('status') in ('PASS','RUN_COMPLETE') and g.get('database_remaining',0)==0 and g.get('console_errors',0)==0 and not g.get('auth_cleanup_failures') for g in groups) else 'INCOMPLETE'
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
  print(json.dumps({k:report.get(k) for k in ('label','status','source_commit','source_tree','source_sha256','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
 return dict(status=report['status'],production_go=False,independent_acceptance=False,full_family_acceptance=False)

if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run();package.run('install')
