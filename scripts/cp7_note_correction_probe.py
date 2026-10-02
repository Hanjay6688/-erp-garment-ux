"""Frozen CP6 -> full F03 -> owning historical-note qualification, disposable only."""
import hashlib,json,subprocess,traceback
import psycopg
import cp7_restore_state as restore_state
import cp7_f03_bundle as bundle
import cp7_note_correction_cases as cases
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp7_f03_probe import verify
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_NOTE_CORRECTION.json'
MANIFEST=bundle.ROOT/'scripts/cp7_note_correction_manifest.json'

def run(diagnostic_provider=None):
 report=dict(label='CP7_OWNING_HISTORICAL_NOTE_CORRECTION',status='INCOMPLETE',production_go=False,independent_acceptance=False,full_family_acceptance=False,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=bundle.ROOT,text=True).strip(),source_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=bundle.ROOT,text=True).strip(),source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),expected_case_count=cases.EXPECTED,required_case_counts=cases.REQUIRED,scope='OWNING_SALES_NOTE_CORRECTION_IMMUTABLE_SOURCE_ALL_HISTORICAL_PREFIXES_NATIVE_STOCK_AR_CASH_JOURNAL_HPP_AND_CURRENT_AUTHORITY');installed=False
 report['manifest_sha256']=hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
 report['predeclared_case_ids']=cases.MANIFEST['groups']
 report['provider_sha256']={p:hashlib.sha256((bundle.ROOT/'scripts'/p).read_bytes()).hexdigest()for p in('cp7_note_correction_cases.py','cp7_note_correction_verify.py','cp7_note_correction_browser.mjs','cp7_note_correction_browser_fixture.py')}
 if diagnostic_provider is not None:
  report.update(label='CP7_NOTE_COMMAND_DIAGNOSTIC',diagnostic_only=True,product_qualification=False,
   expected_case_count=1,required_case_counts={'native':1},predeclared_case_ids={'native':['NOTE_COMMAND_TIMING_AND_EXACT_ROLLBACK']},
   scope='ISOLATED_ACTUAL_NATIVE_COMMAND_TIMING_NO_PRODUCT_EXIT_CREDIT')
 try:
  with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
   p09.wip.policy.bf.verified(cur);restore_before=restore_state.capture(cur,package.boundary.snapshot,native.public_state,p09.functions);conn.rollback();originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
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
    new=after[signature];expected=hashlib.md5(expected_definitions[signature].encode()).hexdigest()if signature in expected_definitions else old['definition']
    assert new['definition']==expected and new['owner']==old['owner'],('NOTE_UNDECLARED_NATIVE_CHANGE',signature)
    assert{tuple(x)for x in new['acl']or[]}=={tuple(x)for x in old['acl']or[]}|grants.get(signature,set()),('NOTE_UNDECLARED_NATIVE_GRANT',signature)
   p09.INSTALLED_FUNCTIONS=after;report['all_other_predecessor_definitions_and_owners_unchanged']=True;report['combined_declared_execute_grants']={k:sorted(v)for k,v in grants.items()};report['native_note_ownership']=cases.ownership.verify(cur);conn.commit();installed=True;verify(cur);conn.rollback()
  report['advisors_with_cp7']=advisors(package.boundary.PG)
  # A rejected owning command must be diagnosed before constructing hundreds
  # of year-history notes. This repeats an existing mandatory economic oracle
  # in an isolated restored group; it grants zero required/unique case credit.
  if diagnostic_provider is None:
   report['composition_smoke']=native.strict_group('CP7_NOTE_COMPOSITION_ADMISSION_SMOKE',
    lambda cur,today:[(name,operation)for name,operation in cases.cases(cur,today)if name in('NOTE_FULL_NATIVE_FINANCIAL','NOTE_PREPAYMENT_REPLAY','NOTE_ECONOMIC_REPORT_RESTATEMENT')],verify)
   report['composition_smoke_required_case_credit']=0
   assert report['composition_smoke'].get('status')in('PASS','RUN_COMPLETE')and report['composition_smoke'].get('counts')=={'PASS':3},'NOTE_COMPOSITION_ADMISSION_SMOKE_FAILED'
   report['native']=native.strict_group('CP7_NOTE_CORRECTION',cases.cases,verify)
   report['races']=modes.run_races(cases,verify,'cp7_note_correction')
   report['http']=modes.run_http(cases,verify,'cp7_note_correction')
   report['browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_note_correction_browser.mjs',verify,'cp7_note_correction_browser')
  else:
   report['native']=native.strict_group('CP7_NOTE_COMMAND_DIAGNOSTIC',diagnostic_provider,verify)
 except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
 finally:
  if installed:
   try:
    with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
     for definition in originals.values():cur.execute(definition,prepare=False)
     for role in bundle.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
     conn.commit();report['cp6_restored']=restore_state.prove(cur,restore_before,package.boundary.snapshot,native.public_state,p09.functions,report);conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
    report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));delta=report['advisor_delta'];report['advisor_gate']=delta['status']=='NO_NEW_FINDINGS'or(delta['status']=='REVIEW_REQUIRED'and all(f.get('name')=='rls_enabled_no_policy'and f.get('level')=='INFO'and(f.get('metadata')or{}).get('schema')in('cp7_recost','cp7_period','cp7_sales','cp7_payroll','cp7_attendance','cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice','cp7_receipt_fix')for f in delta.get('added',[])))
   except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False)
  groups=[report.get(k,{})for k in report['required_case_counts']];report['observed_case_count']=sum(sum(g.get('counts',{}).values())for g in groups);report['required_case_counts_pass']=all(report.get(k,{}).get('counts')=={'PASS':n}for k,n in report['required_case_counts'].items());report['status']='PASS'if not report.get('error')and not report.get('restore_error')and report.get('cp6_restored')and report.get('advisor_gate')and report['required_case_counts_pass']and report['observed_case_count']==report['expected_case_count']and all(g.get('status')in('PASS','RUN_COMPLETE')and g.get('database_remaining',0)==0 and g.get('console_errors',0)==0 and not g.get('auth_cleanup_failures')for g in groups)else'INCOMPLETE'
  out=OUT if diagnostic_provider is None else OUT.with_name('CP7_NOTE_COMMAND_DIAGNOSTIC.json')
  out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({k:report.get(k)for k in('label','status','diagnostic_only','product_qualification','source_commit','source_tree','source_sha256','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
 return dict(status=report['status'],production_go=False,independent_acceptance=False,full_family_acceptance=False)

if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run();package.run('install')
