"""P11 bounded source/UI reader qualification; R10 connected writes remain open."""
from pathlib import Path
import hashlib,json,traceback
import psycopg
import cp7_sales_bundle as bundle
import cp7_sales_cases as cases
import cp7_sales_command_cases as commands
import cp7_sales_draft_cases as drafts
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp6_t3_aligned_install import advisors,advisor_delta
OUT=bundle.ROOT/'cp6-proof/t3/CP7_P11_SALES_READ.json'

def verify(cur):
 result=p09.verify(cur)
 got=cur.execute("select p.proname,pg_get_userbyid(p.proowner),p.prosecdef,p.provolatile::text,p.proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_sales'").fetchall()
 expected={n:('cp7_sales_read',False,'s') for n in ('access_now','header','workspace','review_token','form_options')}
 expected['validate_draft']=('cp7_sales_read',False,'i')
 expected.update(command_access=('cp7_sales_read',True,'s'),apply_command=('postgres',True,'v'),command=('cp7_sales_write',False,'v'))
 assert {x[0] for x in got}==set(expected)
 for name,owner,secdef,vol,config in got:assert (owner,secdef,vol)==expected[name] and config==['search_path=""'],name
 for sig,who,vol in [('public.erp_cp7_get_sales_v1(jsonb)','cp7_sales_read','s'),('public.erp_cp7_save_sale_v1(text,jsonb,uuid,text)','cp7_sales_write','v'),('public.erp_cp7_get_sales_form_v1(jsonb)','cp7_sales_read','s')]:
  assert cur.execute('select pg_get_userbyid(proowner),prosecdef,provolatile::text,proconfig from pg_proc where oid=%s::regprocedure',(sig,)).fetchone()==(who,True,vol,['search_path=""'])
 return dict(result,cp7_p11_bundle_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest())

def run():
 report=dict(label='CP7_P11_SALES_READ',status='INCOMPLETE',production_go=False,independent_acceptance=False,scope='INVOICE_READER_SOURCE_CREATE_EDIT_POST_CANCEL_BROWSER_R10_RETURN_PAYMENT_OPEN',source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),expected_case_count=33)
 installed=False
 try:
  with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
   p09.wip.policy.bf.verified(cur);before=package.boundary.snapshot(cur);public_before=native.public_state(cur);conn.rollback()
   originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
   cur.execute(bundle.extension(),prepare=False);after=p09.functions(cur)
   path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)")
   grants={str(cur.execute('select %s::regprocedure::text',(s,)).fetchone()[0]):{('cp7_sales_read','EXECUTE',False)} for s in bundle.GRANTS}
   uid=str(cur.execute("select 'auth.uid()'::regprocedure::text").fetchone()[0]);grants[uid].add(('cp7_sales_write','EXECUTE',False))
   cur.execute("select set_config('search_path',%s,true)",(path,))
   for sig,old in pre.items():
    new=after[sig];assert new['definition']==old['definition'] and new['owner']==old['owner'],('P11_PREDECESSOR_CHANGED',sig)
    assert {tuple(x) for x in new['acl'] or []}=={tuple(x) for x in old['acl'] or []}|grants.get(sig,set()),('P11_UNDECLARED_ACL_DELTA',sig)
   p09.INSTALLED_FUNCTIONS=after;report['sales_declared_execute_grants']={k:sorted(v) for k,v in grants.items()}
   conn.commit();installed=True;verify(cur);conn.rollback()
  report['advisors_with_cp7']=advisors(package.boundary.PG)
  report['native']=native.strict_group('CP7_P11_READ_NATIVE',cases.cases,verify)
  report['http']=modes.run_http(cases,verify,'cp7_p11_read')
  report['commands']=native.strict_group('CP7_P11_COMMAND_NATIVE',commands.cases,verify)
  report['command_races']=modes.run_races(commands,verify,'cp7_p11_commands')
  report['command_http']=modes.run_http(commands,verify,'cp7_p11_commands')
  report['drafts']=native.strict_group('CP7_P11_DRAFT_NATIVE',drafts.cases,verify)
  report['draft_races']=modes.run_races(drafts,verify,'cp7_p11_drafts')
  report['draft_http']=modes.run_http(drafts,verify,'cp7_p11_drafts')
  report['browser']=modes.run_browser(bundle.ROOT/'scripts/cp7_p11_sales_browser.mjs',verify,'cp7_p11_read')
 except Exception as e:report.update(error=str(e),traceback=traceback.format_exc())
 finally:
  if installed:
   with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
    for definition in originals.values():cur.execute(definition,prepare=False)
    for role in ('cp7_sales_write','cp7_sales_read','cp7_return_write','cp7_return_read','cp7_invoice_write','cp7_invoice_read','cp7_material_write','cp7_material_read','cp7_procure_write','cp7_procure_read','cp7_policy','cp7_capture'):
     cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
    conn.commit();report['cp6_restored']=package.boundary.snapshot(cur)==before and native.public_state(cur)==public_before;conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
   report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));d=report['advisor_delta']
   report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or (d['status']=='REVIEW_REQUIRED' and all(f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and (f.get('metadata') or {}).get('schema') in ('cp7_sales','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice') for f in d.get('added',[])))
  groups=[report.get(k,{}) for k in ('native','http','commands','command_races','command_http','drafts','draft_races','draft_http','browser')];report['observed_case_count']=sum(sum(g.get('counts',{}).values()) for g in groups)
  report['status']='PASS' if not report.get('error') and report.get('cp6_restored') and report.get('advisor_gate') and report['observed_case_count']==33 and all(g.get('status') in('PASS','RUN_COMPLETE') and set(g.get('counts',{}))=={'PASS'} and g.get('database_remaining',0)==0 for g in groups) else 'INCOMPLETE'
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({k:report.get(k) for k in ('label','status','source_sha256','observed_case_count','cp6_restored','advisor_gate','error','traceback')},default=str),flush=True)
 return dict(status=report['status'],production_go=False,independent_acceptance=False)

if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run()
 package.run('install')
