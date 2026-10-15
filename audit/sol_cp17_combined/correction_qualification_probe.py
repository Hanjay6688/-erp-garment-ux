"""Separate tool qualification and new HTTP cases; no repeat of the other six
already-passing own cases or of the candidate's already-passing 61 CP17 cases.
Installation/definition/owner/ACL/restoration checks are the CP17 provider's
unchanged ones. The candidate checkout is never edited.
"""
from pathlib import Path
import hashlib,json,sys,traceback
HERE=Path(__file__).resolve().parent;CANDIDATE=HERE.parents[2]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'));sys.path.insert(0,str(HERE))
import psycopg
import cp7_cp17_fix_probe as source
import independent_cases as sol
import correction_http as http_cases
p09,bundle,native,modes,package=source.p09,source.bundle,source.native,source.modes,source.package
OUT=CANDIDATE/'cp6-proof/t3/SOL_CORRECTION_QUALIFIED.json'
ID='SOL_R1_CUSTOMER_PAYMENT_CORRECTION_FINAL_POSITIVE'
def factory(cur,today):return [(k,v)for k,v in sol.factory(cur,today)if k==ID]

def run(browser_mode=False):
 report=dict(label='SOL_CORRECTION_TOOL_QUALIFICATION',status='INCOMPLETE',candidate_sha='dfab13bf62398a69a02bf6221c06d29075e5e40b',
  original_run=38785656146,original_job=116596863442,original_case_status='INCOMPLETE',original_error='CP7_SALES_REVIEW_CHANGED',
  expected_ids=dict(native=[ID],http=http_cases.IDS),oracle_changed=False,candidate_files_changed=False,production_go=False)
 installed=False
 try:
  with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
   p09.wip.policy.bf.verified(cur);before=source.restore_state.capture(cur,package.boundary.snapshot,native.public_state,p09.functions);conn.rollback()
   originals,installation=p09.install(cur);report.update(installation);pre=p09.functions(cur)
   internal=cur.execute("select pg_get_functiondef('erp.require_internal()'::regprocedure)").fetchone()[0]
   originals['erp.require_owner_admin()']=cur.execute("select pg_get_functiondef('erp.require_owner_admin()'::regprocedure)").fetchone()[0]
   bundle.note_report.capture(cur,originals);cur.execute(bundle.extension(),prepare=False);after=p09.functions(cur)
   path=cur.execute('show search_path').fetchone()[0];cur.execute("select set_config('search_path','',true)");grants={}
   for principal,signatures in bundle.GRANTS.items():
    for signature in signatures:
     key=str(cur.execute('select %s::regprocedure::text',(signature,)).fetchone()[0]);grants.setdefault(key,set()).add((principal,'EXECUTE',False))
   cur.execute("select set_config('search_path',%s,true)",(path,))
   expected=bundle.note_report.expected_definitions(internal,originals,bundle.patched_internal,bundle.settlement.patched_owner)
   for sig,old in pre.items():
    new=after[sig];want=hashlib.md5(expected[sig].encode()).hexdigest()if sig in expected else old['definition']
    assert new['definition']==want and new['owner']==old['owner'],('F03_UNDECLARED_PREDECESSOR_CHANGE',sig)
    assert {tuple(x)for x in new['acl']or[]}=={tuple(x)for x in old['acl']or[]}|grants.get(sig,set()),('F03_UNDECLARED_ACL_DELTA',sig)
   for sig,definition in expected.items():assert cur.execute('select pg_get_functiondef(%s::regprocedure)',(sig,)).fetchone()[0]==definition,('F03_EXACT_ADMISSION_DELTA',sig)
   assert cur.execute("select pg_get_functiondef('cp7_payroll.rebuild_nonwork(uuid)'::regprocedure)").fetchone()[0]==bundle.settlement.derive_nonwork(bundle.settlement.accepted('populate_payroll_draft'))
   p09.INSTALLED_FUNCTIONS=after;conn.commit();installed=True;source.verify(cur);conn.rollback()
  report['native']=native.strict_group('SOL_CORRECTION_QUALIFIED',factory,source.verify)
  report['http']=modes.run_http(http_cases,source.verify,'sol_correction_contract')
 except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
 finally:
  if installed:
   try:
    with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
     for definition in originals.values():cur.execute(definition,prepare=False)
     for role in bundle.ROLES:cur.execute('drop owned by '+role+' cascade;drop role '+role,prepare=False)
     conn.commit();report['cp6_restored']=source.restore_state.prove(cur,before,package.boundary.snapshot,native.public_state,p09.functions,report)
     conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
   except Exception as exc:report.update(restore_error=str(exc),cp6_restored=False)
  report['case_sets_complete']=all(set(report.get(k,{}).get('cases',{}))==set(v)for k,v in report['expected_ids'].items())
  report['status']='PASS'if report['case_sets_complete']and report.get('cp6_restored')and not report.get('error')and all(report[k].get('counts')=={'PASS':len(ids)}for k,ids in report['expected_ids'].items())else'INCOMPLETE'
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
  print(json.dumps(dict(label=report['label'],status=report['status'],counts={k:report.get(k,{}).get('counts')for k in('native','http')},cp6_restored=report.get('cp6_restored'),error=report.get('error')),default=str),flush=True)
 return dict(status=report['status'],production_go=False)
package._writer_runtime=run
if __name__=='__main__':package.run('install')
