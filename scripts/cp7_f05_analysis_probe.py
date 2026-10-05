"""Native product-bound global matching/netting and dated scenario composition."""
import hashlib,json,traceback
import psycopg
import cp7_analysis_bundle as bundle
import cp7_schedule_bundle as schedule
import cp7_f03_bundle as f03
import cp7_note_correction_verify as note_correction
import cp7_sales_payment_correction_bundle as payment_correction_ownership
import cp7_sales_return_correction_bundle as return_correction_ownership
import cp7_sales_chain_bundle as sales_chain_ownership
import cp7_planning_bundle as planning
import cp7_baseline_bundle as baseline
import cp7_supply_bundle as supply
import cp7_analysis_cases as history_cases
import cp7_p12_nota_probe as payroll
import cp7_p13_finance_probe as finance
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp7_catalog_state import canonical_public_state,exact_public_catalog
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_F05_NATIVE_ANALYSIS.json'
def public_state(cur):
 # The accepted harness aggregates functions ORDER BY 1, a constant inside
 # jsonb_agg. PostgreSQL may return unchanged pg_proc members in another physical
 # order after ACL updates. Sort every original [signature,definition_hash]
 # pair without deleting a field/member or changing the frozen case runner.
 state=native.public_state(cur)
 return canonical_public_state(state)

def verify(cur):
 bundle.verify(cur)
 payroll.verify(cur,True,True,True,True,True);finance.verify(cur);f03.journal.verify(cur);f03.misc.verify(cur);f03.installment.verify(cur)
 note_correction.verify(cur);f03.transaction_source.verify(cur);f03.misc_correction.verify(cur)
 payment_correction_ownership.verify(cur)
 return_correction_ownership.verify(cur)
 sales_chain_ownership.verify(cur)
 f03.cutting_correction.verify(cur)
 return dict(stage='EXPLICIT_F03_COMBINED_DEVELOPMENT_STACK',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),full_family_acceptance=False)

def run(attention=False,p18_e01=False,rule_lifecycle=False,source_navigation=False,misc_correction=False,payment_correction=False,supplier_payment_correction=False,return_correction=False,sales_chain=False,cutting_correction=False,fabric_recipe=False):
 candidate=bundle;case_provider=history_cases;checker=verify;extra='';expected=152;out=OUT;phase='cp7_f05_analysis';browser_script='cp7_f05_analysis_browser.mjs'
 if attention:
  import cp7_obligation_report_bundle as candidate
  import cp7_obligation_report_cases as case_provider
  def checker(cur):verify(cur);candidate.verify(cur)
  extra=candidate.extension();expected=case_provider.EXPECTED;assert expected==284;out=OUT.with_name('CP7_F05_NATIVE_ATTENTION.json');phase='cp7_f05_attention';browser_script='cp7_f05_obligation_report_browser_all.mjs'
 if p18_e01:
  assert not attention
  import cp7_obligation_report_bundle as candidate
  import cp7_p18_e01_bridge_cases as case_provider
  def checker(cur):verify(cur);candidate.verify(cur)
  extra=candidate.extension();expected=case_provider.EXPECTED;assert expected==9;out=OUT.with_name('CP7_P18_E01_BRIDGE.json');phase='cp7_p18_e01_bridge';browser_script='cp7_p18_e01_bridge_browser.mjs'
 if rule_lifecycle:
  assert not attention and not p18_e01
  import cp7_obligation_report_bundle as candidate
  import cp7_rule_lifecycle_cases as case_provider
  def checker(cur):verify(cur);candidate.verify(cur)
  extra=candidate.extension();expected=case_provider.EXPECTED;assert expected==16;out=OUT.with_name('CP7_RULE_LIFECYCLE.json');phase='cp7_rule_lifecycle';browser_script='cp7_p18_e01_bridge_browser.mjs'
 if source_navigation:
  assert not attention and not p18_e01 and not rule_lifecycle
  import cp7_transaction_source_cases as case_provider
  expected=case_provider.EXPECTED;assert expected==78;out=OUT.with_name('CP7_TRANSACTION_SOURCE.json');phase='cp7_transaction_source';browser_script='cp7_transaction_source_browser.mjs'
 if misc_correction:
  assert not any((attention,p18_e01,rule_lifecycle,source_navigation))
  import cp7_misc_correction_cases as case_provider
  expected=case_provider.EXPECTED;assert expected==20;out=OUT.with_name('CP7_MISC_CORRECTION.json');phase='cp7_misc_correction';browser_script='cp7_misc_correction_browser.mjs'
 if payment_correction:
  assert not any((attention,p18_e01,rule_lifecycle,source_navigation,misc_correction))
  import cp7_payment_correction_cases as case_provider
  expected=case_provider.EXPECTED;assert expected==23;out=OUT.with_name('CP7_PAYMENT_CORRECTION.json');phase='cp7_payment_correction';browser_script='cp7_payment_correction_browser.mjs'
 if supplier_payment_correction:
  assert not any((attention,p18_e01,rule_lifecycle,source_navigation,misc_correction,payment_correction))
  import cp7_supplier_payment_correction_cases as case_provider
  expected=case_provider.EXPECTED;assert expected==23;out=OUT.with_name('CP7_SUPPLIER_PAYMENT_CORRECTION.json');phase='cp7_supplier_payment_correction';browser_script='cp7_supplier_payment_correction_browser.mjs'
 if return_correction:
  assert not any((attention,p18_e01,rule_lifecycle,source_navigation,misc_correction,payment_correction,supplier_payment_correction))
  import cp7_sales_return_correction_cases as case_provider
  expected=case_provider.EXPECTED;assert expected==25;out=OUT.with_name('CP7_RETURN_CORRECTION.json');phase='cp7_return_correction';browser_script='cp7_sales_return_correction_browser.mjs'
 if sales_chain:
  assert not any((attention,p18_e01,rule_lifecycle,source_navigation,misc_correction,payment_correction,supplier_payment_correction,return_correction))
  import cp7_sales_chain_cases as case_provider
  expected=case_provider.EXPECTED;assert expected==25;out=OUT.with_name('CP7_SALES_CHAIN.json');phase='cp7_sales_chain';browser_script='cp7_sales_chain_browser.mjs'
 if cutting_correction:
  assert not any((attention,p18_e01,rule_lifecycle,source_navigation,misc_correction,payment_correction,supplier_payment_correction,return_correction,sales_chain))
  import cp7_cutting_correction_cases as case_provider
  expected=case_provider.EXPECTED;assert expected==19;out=OUT.with_name('CP7_CUTTING_REOPEN.json');phase='cp7_cutting_reopen';browser_script='cp7_cutting_correction_browser.mjs'
 if fabric_recipe:
  assert not any((attention,p18_e01,rule_lifecycle,source_navigation,misc_correction,payment_correction,supplier_payment_correction,return_correction,sales_chain,cutting_correction))
  import cp7_fabric_recipe_cases as case_provider
  expected=case_provider.EXPECTED;assert expected==13;out=OUT.with_name('CP7_FABRIC_RECIPE.json');phase='cp7_fabric_recipe';browser_script='cp7_fabric_recipe_browser.mjs'
  declaration_path=bundle.ROOT/'docs/cp7/f04/NATIVE_FABRIC_RECIPE.json'
  declaration_bytes=declaration_path.read_bytes();declaration=json.loads(declaration_bytes)
  assert declaration['contract']=='cp7.fabric-recipe-declaration.v1' and declaration['expected_case_count']==expected and declaration['required_case_counts']==case_provider.REQUIRED and declaration['required_case_ids']==case_provider.IDS,'FABRIC_PREDECLARED_CASE_BUDGET_CHANGED'
 report=dict(label='CP7_MISC_CORRECTION'if misc_correction else'CP7_TRANSACTION_SOURCE'if source_navigation else'CP7_RULE_LIFECYCLE'if rule_lifecycle else'CP7_P18_E01_BRIDGE'if p18_e01 else'CP7_F05_NATIVE_ATTENTION'if attention else'CP7_F05_NATIVE_ANALYSIS',status='INCOMPLETE',production_go=False,independent_acceptance=False,full_family_acceptance=False,scope='ATOMIC_POSTED_MISC_NATIVE_INVERSE_REPLACEMENT_HISTORY_EXACT_UUID_CURRENT_AUTH_AND_BROWSER_CORRECTION'if misc_correction else'EXACT_NATIVE_SOURCE_PARENT_CHILD_PAGE_CURRENT_AUTH_OWNING_BROWSER_INVERSE_RETAINED_F03_REVOKE_SCHEDULES'if source_navigation else'NATIVE_INACTIVE_EPISODE_ARCHIVE_NOT_PAID_EXACT_SOURCE_REPLAY_CURRENT_AUTH_AND_RETAINED_E01_BRIDGE'if rule_lifecycle else'FOCUSED_E01_NATIVE_SOURCE_TO_ORIGINAL_REPORT_APPENDIX_RULE_EPISODES_NOT_FULL_P18'if p18_e01 else'IMMUTABLE_NATIVE_PUBLICATIONS_ATTENTION_ALL_NATIVE_OBLIGATION_DOMAINS_UNKNOWN_REVIEW_EPISODES_LOCAL_TEST_SINK'if attention else'FROZEN_ANALYSIS_V2_NATIVE_PUBLICATION_REVISION_PERIOD_COMPARISON_ACCEPTED_OWNER_FINANCE_REUSE_MATERIAL_APPLY_UNKNOWN',source_sha256=hashlib.sha256(candidate.bundle().encode()).hexdigest(),expected_case_count=expected);installed=False
 if attention:report['required_case_counts']=dict(native=179,races=40,http=29,browser=36)
 if payment_correction:
  report.update(label='CP7_PAYMENT_CORRECTION',scope='ORDINARY_CASH_PAYMENT_ATOMIC_NATIVE_INVERSE_REPLACEMENT_EXACT_HISTORY_OLD_DATES_CURRENT_AUTH_RECOVERY_BROWSER')
 if supplier_payment_correction:
  report.update(label='CP7_SUPPLIER_PAYMENT_CORRECTION',scope='ORDINARY_SUPPLIER_PAYMENT_ATOMIC_NATIVE_INVERSE_REPLACEMENT_THREE_SUPPORTED_FIELDS_HISTORY_OLD_DATE_CURRENT_AUTH_RECOVERY_BROWSER')
 if return_correction:
  report.update(label='CP7_RETURN_CORRECTION',scope='ORDINARY_CUSTOMER_RETURN_ATOMIC_NATIVE_INVERSE_POST_ORIGINAL_STOCK_HPP_CLOCK_364_LATER_PREFIXES_CURRENT_AUTH_AND_OWNING_BROWSER')
 if sales_chain:
  report.update(label='CP7_SALES_CHAIN',scope='ONE_REVIEWED_ALL_PAYMENT_RETURN_SALE_NATIVE_ATOMIC_INVERSE_IMMUTABLE_ORIGINALS_CURRENT_AUTH_SAME_UUID_RECOVERY')
 if cutting_correction:report.update(label='CP7_CUTTING_REOPEN',scope='ACTUAL_UNPICKED_POSTED_CUTTING_UNCHANGED_NATIVE_INVERSE_EXACT_CURRENT_AUTH_UUID_SOURCE_HISTORY_AND_FOLLOWING_DRAFT_EDIT')
 if rule_lifecycle or source_navigation or misc_correction or payment_correction or supplier_payment_correction or return_correction or sales_chain or cutting_correction:report['required_case_counts']=case_provider.REQUIRED
 if p18_e01:report['required_case_counts']=case_provider.REQUIRED;report['full_P18_acceptance']=False
 if fabric_recipe:report.update(label='CP7_FABRIC_RECIPE',scope='EXPLICIT_EFFECTIVE_DATED_EXACT_ROOT_SIZE_NATIVE_FABRIC_RECIPE_ASSUMPTIONS_SHARED_ANALYSIS_NO_INSTALLATION_ALLOCATION_OR_FEASIBILITY_CREDIT',required_case_counts=case_provider.REQUIRED,required_case_ids=case_provider.IDS,predeclared_case_contract=declaration,predeclared_case_sha256=hashlib.sha256(declaration_bytes).hexdigest(),full_P08_acceptance=False)
 try:
  with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
   p09.wip.policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=public_state(cur);accepted_functions_before=p09.functions(cur);conn.rollback();originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
   internal_before=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
   originals['erp.require_owner_admin()']=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
   f03.note_report.capture(cur,originals)
   cur.execute(f03.extension()+'\n'+planning.extension()+'\n'+baseline.extension()+'\n'+supply.extension()+'\n'+schedule.extension()+'\n'+bundle.predecessor.extension()+'\n'+bundle.extension()+'\n'+extra,prepare=False);after=p09.functions(cur)
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
   report['combined_declared_table_grants']=candidate.TABLE_GRANTS
   conn.commit();installed=True;checker(cur);conn.rollback()
  report['advisors_with_cp7']=advisors(package.boundary.PG)
  if attention:
   # Repeat three existing mandatory controls first to reject a bad private
   # admission/compiler change before the long aggregate. No extra case credit.
   early=('P14_NATIVE_ANALYSIS_FROZEN_NATIVE','P16_RULE_SOURCE_EXACT_CURRENT_SOURCE','P15_OBLIGATION_REPORT_NATIVE_EXACT_DATED_NATIVE')
   def admission(cur,today):
    selected=[(name,operation)for name,operation in case_provider.cases(cur,today)if name in early]
    assert len(selected)==3,('ATTENTION_ADMISSION_REQUIRED_CONTROLS',early,[name for name,_ in selected])
    return selected
   # The frozen reader's jsonb_agg ORDER BY 1 is a constant. The compiler
   # equivalence control rolls back CREATE OR REPLACE, which may reorder pg_proc
   # physically. Apply the same all-member/hash comparator as the full group;
   # retain the raw-order witness and keep every restoration/cleanup gate.
   with exact_public_catalog(native)as admission_catalog_audit:
    report['source_admission']=native.strict_group('CP7_ATTENTION_SOURCE_ADMISSION',admission,checker)
   report['source_admission_public_catalog_comparison']=admission_catalog_audit
   report['source_admission_required_case_credit']=0
   assert report['source_admission'].get('status')in('PASS','RUN_COMPLETE')and report['source_admission'].get('counts')=={'PASS':3},'ATTENTION_SOURCE_ADMISSION_FAILED'
  with exact_public_catalog(native,retain_raw=fabric_recipe)as catalog_audit:
   report['native']=native.strict_group('CP7_FABRIC_RECIPE'if fabric_recipe else'CP7_CUTTING_REOPEN'if cutting_correction else'CP7_SALES_CHAIN'if sales_chain else'CP7_RETURN_CORRECTION'if return_correction else'CP7_SUPPLIER_PAYMENT_CORRECTION'if supplier_payment_correction else'CP7_PAYMENT_CORRECTION'if payment_correction else'CP7_MISC_CORRECTION'if misc_correction else'CP7_TRANSACTION_SOURCE'if source_navigation else'CP7_RULE_LIFECYCLE'if rule_lifecycle else'CP7_P18_E01_BRIDGE'if p18_e01 else'CP7_F05_ATTENTION'if attention else'CP7_F05_ANALYSIS',case_provider.cases,checker)
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
  if fabric_recipe:
   report['required_case_ids_pass']=all(set(report.get(k,{}).get('races'if k=='races'else'cases',{}))==set(ids)for k,ids in case_provider.IDS.items())
  groups=[report.get(k,{})for k in('native','races','http','browser')];report['observed_case_count']=sum(sum(g.get('counts',{}).values())for g in groups);report['required_case_counts_pass']=not(attention or p18_e01 or rule_lifecycle or source_navigation or misc_correction or payment_correction or supplier_payment_correction or return_correction or sales_chain or cutting_correction or fabric_recipe)or all(report.get(k,{}).get('counts')=={'PASS':n}for k,n in report['required_case_counts'].items());report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and report['observed_case_count']==expected and report['required_case_counts_pass'] and(not fabric_recipe or report.get('required_case_ids_pass'))and all(g.get('status')in('PASS','RUN_COMPLETE') and set(g.get('counts',{}))=={'PASS'} and g.get('database_remaining',0)==0 for g in groups) else 'INCOMPLETE'
  out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({k:report.get(k)for k in('label','status','source_sha256','observed_case_count','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
 return dict(status=report['status'],production_go=False,independent_acceptance=False,full_family_acceptance=False)
if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run();package.run('install')
