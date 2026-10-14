"""Sol 0 -> exactly +1 target anomaly -> 0 detector controls.
All zero-argument ERP table-returning check functions are retained at each point.
Privileged poisoning is confined to a disposable savepoint, with trigger checks
bypassed only during the artificial mutation. This is detector sensitivity proof,
not an assertion that the normal application can bypass append-only protection.
"""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import contract_probe as c
probe,b,cmd=c.probe,c.b,c.cmd
original=c.original;results=[]
IDS=['SOL_FG_CACHE_DETECTOR_0_1_0','SOL_POSTED_JOURNAL_DETECTOR_0_1_0']
def outputs(cur):
 b.api.admin(cur)
 names=[r[0]for r in cur.execute("select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and p.prokind='f' and p.pronargs=0 and p.proname~'^run_[a-z0-9_]+checks$' and p.proargnames @> array['check_name','severity','issue_count','details']::text[] order by p.proname").fetchall()]
 assert len(names)==len(set(names)) and 'run_integrity_checks'in names
 return {name:[dict(check_name=r[0],severity=r[1],issue_count=int(r[2]),details=r[3])for r in cur.execute('select check_name,severity,issue_count,details from erp.'+name+'() order by check_name,severity,details').fetchall()]for name in names}
def target(o,key):
 return next(r['issue_count']for r in o['run_integrity_checks']if r['check_name']==key)
def factory(cur,today):
 def exercise(kind):
  f=c.stock(cur,today)
  if kind=='JOURNAL':c.drafts.create(cur,f,c.drafts.payload(f,'3','17.25'));c.post(cur,f)
  before=outputs(cur);name='FG_CACHE_MISMATCH'if kind=='CACHE'else'UNBALANCED_POSTED_JOURNALS'
  assert target(before,name)==0,(name,before)
  cur.execute('savepoint sol_detector_poison');cur.execute('set local session_replication_role=replica')
  if kind=='CACHE':
   n=cur.execute('update erp.fg_inventory_balances set cached_qty_pcs=cached_qty_pcs+1 where product_id=%s and location_id=%s',(f['product'],f['location'])).rowcount
   dimensions=dict(product=f['product'],location=f['location'],legitimate_quantity='10',poisoned_quantity='11')
  else:
   ident=cur.execute("select l.id::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='SALE' and j.source_id=%s order by l.id limit 1",(f['sale'],)).fetchone()[0]
   n=cur.execute('update erp.journal_lines set debit=debit+1.00 where id=%s',(ident,)).rowcount
   dimensions=dict(sale=f['sale'],one_journal_line=ident,debit_increase='1.00')
  assert n==1,n
  cur.execute('set local session_replication_role=origin')
  during=outputs(cur);assert target(during,name)==1,(name,during)
  cur.execute('rollback to savepoint sol_detector_poison');cur.execute('release savepoint sol_detector_poison')
  after=outputs(cur);assert after==before and target(after,name)==0
  return dict(status='PASS',evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='SOL_ONE_ROW_ONE_TARGET_VIOLATION',
    target_detector='erp.run_integrity_checks:'+name,expected_target=[0,1,0],observed_target=[target(x,name)for x in [before,during,after]],
    dimensions=dimensions,all_detector_outputs=dict(before=before,during=during,after=after),
    detector_functions=len(before),privileged_injection_role='supabase_admin fixture; no access-control acceptance credit',
    temporary_weakened_fixture='session_replication_role=replica during mutation only, restored and savepoint rolled back',
    normal_business_setup='Native found-at-opname stock; public sales draft/post as authenticated OWNER',
    scope='Every zero-argument ERP detector with check_name/severity/issue_count/details; parameterized detectors excluded explicitly',production_go=False)
 return [(IDS[0],lambda:exercise('CACHE')),(IDS[1],lambda:exercise('JOURNAL'))]
def wrapped(name,factory0,verify):
 normal=original(name,factory0,verify)
 if name=='CP7_K3_CLEANUP':
  own=original('SOL_CP1_7_DETECTOR_CONTROLS',factory,verify);results.append(own)
  own.update(candidate_sha=c.IDS and '0b7049d9203bac52b47a4c89f3e0d75646067a8f',expected_ids=IDS,expected_count=2,probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
  (probe.OUT.parent/'SOL_DETECTOR_CASES.json').write_text(json.dumps(own,indent=2,default=str)+'\n')
  print(json.dumps({'sol_detector_result':own},default=str),flush=True)
 return normal
probe.native.strict_group=wrapped
def runtime(browser_mode=False):
 normal=probe.run(k3_cleanup=True)
 assert len(results)==1
 if results[0].get('counts')!={'PASS':2}or set(results[0].get('cases',{}))!=set(IDS)or not results[0].get('complete_boundary_restored'):normal=dict(normal,status='INCOMPLETE',sol_detector_failure=True)
 return normal
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
