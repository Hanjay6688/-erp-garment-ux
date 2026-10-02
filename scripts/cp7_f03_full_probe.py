"""Full retained P09-P13 controls, each installed on the same explicit F03 stack.

Counts describe source-bound executions, not unique oracles or family acceptance.
Every HTTP/browser group uses real Auth and its own disposable committed copy.
"""
import hashlib,importlib,json,os,subprocess,traceback
import psycopg
import cp7_restore_state as restore_state
import cp7_f03_bundle as bundle
import cp7_p09_procurement_probe as p09
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
from cp7_f03_probe import verify
from cp6_t3_aligned_install import advisors,advisor_delta
MANIFEST=bundle.ROOT/'scripts/cp7_f03_full_manifest.json'
BUCKET=os.environ['CP7_F03_BUCKET']
manifest=json.loads(MANIFEST.read_text())
assert manifest['schema']=='cp7-f03-full-native-manifest-v1'
assert BUCKET in manifest['buckets'],'UNKNOWN_F03_QUALIFICATION_BUCKET'
spec=manifest['buckets'][BUCKET]
OUT=bundle.ROOT/'cp6-proof/t3'/('CP7_F03_FULL_'+BUCKET.upper()+'.json')

def group_complete(group):
 return (group.get('status')in('PASS','RUN_COMPLETE') and set(group.get('counts',{}))=={'PASS'}
  and group['counts']['PASS']>0 and not group.get('missing') and not group.get('cleanup_failures')
  and not group.get('auth_cleanup_failures') and group.get('database_remaining',0)==0
  and group.get('console_errors',0)==0 and group.get('auth_counts',{}).get('restored',True))

def run():
 report=dict(label='CP7_F03_FULL_'+BUCKET.upper(),bucket=BUCKET,status='INCOMPLETE',
  production_go=False,independent_acceptance=False,full_family_acceptance=False,unique_oracle_total_claim=False,
  source_sha256=hashlib.sha256(bundle.bundle().encode()).hexdigest(),
  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=bundle.ROOT,text=True).strip(),
  source_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=bundle.ROOT,text=True).strip(),
  manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
  provider_sha256={g['key']:hashlib.sha256((bundle.ROOT/(g['module']if g['kind']=='browser'else'scripts/'+g['module']+'.py')).read_bytes()).hexdigest()for g in spec['groups']},
  retained_probe_sha256={p:hashlib.sha256((bundle.ROOT/'scripts'/p).read_bytes()).hexdigest()for p in sorted({g['retained_probe']for g in spec['groups']})},
  scope=manifest['qualification_scope'],expected_case_count=spec['expected_case_executions'],
  expected_smoke_count=spec['expected_smoke_executions'],expected_group_executions={g['key']:g['expected_executions']for g in spec['groups']},predeclared_groups=spec['groups'],
  private_role_count=len(bundle.ROLES),groups={});installed=False
 assert report['private_role_count']==31,'FULL_F03_ROLE_STACK_CHANGED_REQUIRES_EXPLICIT_REVIEW'
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
  for g in spec['groups']:
   key=g['key'];phase='cp7_f03_full_'+BUCKET+'_'+key
   try:
    if g['kind']=='browser':result=modes.run_browser(bundle.ROOT/g['module'],verify,phase)
    else:
     module=importlib.import_module(g['module'])
     if g['kind']=='native':result=native.strict_group(phase.upper(),getattr(module,g['entry']),verify)
     elif g['kind']=='races':result=modes.run_races(module,verify,phase)
     elif g['kind']=='http':result=modes.run_http(module,verify,phase)
     else:raise AssertionError(('UNKNOWN_PREDECLARED_GROUP_KIND',g))
    report['groups'][key]=result
   except Exception as exc:
    report['groups'][key]=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
 except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
 finally:
  if installed:
   try:
    with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
     for definition in originals.values():cur.execute(definition,prepare=False)
     for role in bundle.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
     conn.commit();report['cp6_restored']=restore_state.prove(cur,restore_before,package.boundary.snapshot,native.public_state,p09.functions,report)
     conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
    report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report.get('advisors_with_cp7',{}));d=report['advisor_delta']
    report['advisor_gate']=d['status']=='NO_NEW_FINDINGS' or(d['status']=='REVIEW_REQUIRED' and all(f.get('name')=='rls_enabled_no_policy' and f.get('level')=='INFO' and(f.get('metadata')or{}).get('schema')in('cp7_recost','cp7_period','cp7_sales','cp7_payroll','cp7_attendance','cp7_fg','cp7_private','cp7_identity','cp7_wip','cp7_procurement','cp7_material','cp7_supplier_return','cp7_invoice')for f in d.get('added',[])))
   except Exception as exc:report.update(restore_error=str(exc),restore_traceback=traceback.format_exc(),cp6_restored=False)
  report['observed_group_count']=len(report['groups'])
  report['predeclared_group_count']=len(spec['groups'])
  report['groups_complete']=set(report['groups'])=={g['key']for g in spec['groups']}and all(group_complete(report['groups'].get(g['key'],{}))and sum(report['groups'].get(g['key'],{}).get('counts',{}).values())==g['expected_executions']for g in spec['groups'])
  report['observed_case_count']=sum(sum(report['groups'].get(g['key'],{}).get('counts',{}).values())for g in spec['groups']if not g['smoke'])
  report['observed_smoke_count']=sum(sum(report['groups'].get(g['key'],{}).get('counts',{}).values())for g in spec['groups']if g['smoke'])
  complete_count=report['observed_case_count']==report['expected_case_count']and report['observed_smoke_count']==report['expected_smoke_count']
  report['status']='PASS'if complete_count and report['groups_complete']and report.get('cp6_restored')and report.get('advisor_gate')and not report.get('error')and not report.get('restore_error')else'INCOMPLETE'
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
  print(json.dumps({k:report.get(k)for k in('label','status','source_commit','source_tree','source_sha256','manifest_sha256','observed_case_count','expected_case_count','observed_smoke_count','observed_group_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
 return dict(status=report['status'],production_go=False,independent_acceptance=False,full_family_acceptance=False)
if __name__=='__main__':
 package._writer_runtime=lambda browser_mode=False:run();package.run('install')
