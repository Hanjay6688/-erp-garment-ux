"""Bounded native report/archive reader; no finance/close writer acceptance."""
import hashlib,json,traceback
import psycopg
import cp7_finance_bundle as bundle
import cp7_finance_cases as cases
import cp7_period_bundle as periods
import cp7_p11_sales_probe as sales
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_P13_FINANCE_READ.json'

def verify(cur):
 result=sales.verify(cur)
 got=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_finance'").fetchall();assert {r[0]for r in got}=={'access_now','exact_numbers','workspace'}
 for name,owner,secdef,vol,config in got:assert (owner,secdef,vol,config)==('cp7_finance_read',False,'i' if name=='exact_numbers' else 's',['search_path=""']+(['TimeZone=UTC'] if name=='workspace' else [])),(name,owner,secdef,vol,config)
 assert cur.execute("select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid='public.erp_cp7_get_finance_report_v1(jsonb)'::regprocedure").fetchone()==('cp7_finance_read',True,'s',['search_path=""'])
 periods.verify(cur)
 return dict(result,cp7_p13_bundle_sha256=hashlib.sha256(periods.bundle().encode()).hexdigest())

def run(include_period=False):
 import cp7_period_cases
 out=OUT if not include_period else bundle.ROOT/'cp6-proof/t3/CP7_P13_PERIOD_CONTROL.json'
 expected=25 if include_period else 12
 report=dict(label='CP7_P13_FINANCE_READ',status='INCOMPLETE',production_go=False,independent_acceptance=False,scope='OWNER_ADMIN_NATIVE_DATED_FINANCIAL_SOURCE_PREFLIGHT_IMMUTABLE_FILINGS_READER_ONLY',source_sha256=hashlib.sha256(periods.bundle().encode()).hexdigest(),expected_case_count=expected);installed=False
 if include_period:report.update(label='CP7_P13_PERIOD_CONTROL',scope='NATIVE_REPORT_ARCHIVE_AND_REVIEWED_CLOSE_REOPEN_WITH_EXACT_REPLAY')
 try:
  with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
   p09.wip.policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=native.public_state(cur);conn.rollback();originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
   internal_before=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
   cur.execute(bundle.cp7_sales_bundle.extension()+'\n'+bundle.extension()+'\n'+periods.extension(),prepare=False);after=p09.functions(cur)
   path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)");grants={}
   for signatures,principal in [(bundle.cp7_sales_bundle.GRANTS,'cp7_sales_read'),(bundle.GRANTS,'cp7_finance_read'),(periods.READ_GRANTS,'cp7_period_read'),(periods.WRITE_GRANTS,'cp7_period_write'),(('auth.uid()',),'cp7_sales_write')]:
    for signature in signatures:
     key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add((principal,'EXECUTE',False))
   cur.execute("select set_config('search_path',%s,true)",(path,))
   for sig,old in pre.items():
    new=after[sig];expected=hashlib.md5(bundle.cp7_sales_bundle.patched_internal(internal_before).encode()).hexdigest() if sig=='erp.require_internal()' else old['definition'];assert new['definition']==expected and new['owner']==old['owner'],('P13_PREDECESSOR_CHANGED',sig)
    assert {tuple(x)for x in new['acl']or[]}=={tuple(x)for x in old['acl']or[]}|grants.get(sig,set()),('P13_UNDECLARED_ACL_DELTA',sig)
   p09.INSTALLED_FUNCTIONS=after;report['declared_execute_grants']={k:sorted(v)for k,v in grants.items()};report['P13_native_report_close_functions_unchanged']=True
   conn.commit();installed=True;verify(cur);conn.rollback()
  report['advisors_with_cp7']=advisors(package.boundary.PG)
  report['native']=native.strict_group('CP7_P13_REPORT_NATIVE',cases.cases,verify)
  report['races']=modes.run_races(cases,verify,'cp7_p13_report')
  report['http']=modes.run_http(cases,verify,'cp7_p13_report')
  report['browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p13_finance_browser.mjs',verify,'cp7_p13_report')
  if include_period:
   report['label']='CP7_P13_PERIOD_CONTROL';report['scope']='NATIVE_REPORT_ARCHIVE_AND_REVIEWED_CLOSE_REOPEN_WITH_EXACT_REPLAY'
   report['period_native']=native.strict_group('CP7_P13_PERIOD_NATIVE',cp7_period_cases.cases,verify)
   report['period_races']=modes.run_races(cp7_period_cases,verify,'cp7_p13_period')
   report['period_http']=modes.run_http(cp7_period_cases,verify,'cp7_p13_period')
   report['period_browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p13_period_browser.mjs',verify,'cp7_p13_period')
 except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
 finally:
  if installed:
   with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
    for definition in originals.values():cur.execute(definition,prepare=False)
    for role in ('cp7_period_write','cp7_period_read','cp7_finance_read','cp7_sales_write','cp7_sales_read','cp7_return_write','cp7_return_read','cp7_invoice_write','cp7_invoice_read','cp7_material_write','cp7_material_read','cp7_procure_write','cp7_procure_read','cp7_policy','cp7_capture'):cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
    conn.commit();report['cp6_restored']=package.boundary.snapshot(cur)==before and native.public_state(cur)==public_before;conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
   report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));d=report['advisor_delta'];report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or(d['status']=='REVIEW_REQUIRED' and all(f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and(f.get('metadata')or{}).get('schema')in('cp7_period','cp7_sales','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice')for f in d.get('added',[])))
  groups=[report.get(k,{})for k in(('native','races','http','browser','period_native','period_races','period_http','period_browser')if include_period else('native','races','http','browser'))];report['observed_case_count']=sum(sum(g.get('counts',{}).values())for g in groups);report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and report['observed_case_count']==expected and all(g.get('status')in('PASS','RUN_COMPLETE') and set(g.get('counts',{}))=={'PASS'} and g.get('database_remaining',0)==0 for g in groups) else 'INCOMPLETE'
  out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({k:report.get(k)for k in('label','status','source_sha256','observed_case_count','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
 return dict(status=report['status'],production_go=False,independent_acceptance=False)
if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run();package.run('install')
