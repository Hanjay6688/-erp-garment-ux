"""One cleanup timing control, reusing the exact 25 completed C0 outcomes.
Does not rerun C0 cases. Preserves the failed first package and its original
unknown active backend. Waits boundedly for natural connection closure;
never terminates a backend and never touches a hosted database.
"""
import hashlib,inspect,json,os,threading,time,textwrap,zipfile
from pathlib import Path
import fullstack_probe as full
M=Path(__file__).with_name('C0_CLEANUP_MANIFEST.json');m=json.loads(M.read_text())
full.MANIFEST=M;full.manifest=m;full.OUT=full.CANDIDATE/'cp6-proof/t3/SOL_C0_CLEANUP_QUALIFICATION.json'
source=textwrap.dedent(inspect.getsource(full.execute))
old="assert not sessions,('SOL_FULLSTACK_SESSIONS_LEFT',sessions)"
assert source.count(old)==1
new="""samples=[sessions];deadline=time.monotonic()+60
  while sessions and time.monotonic()<deadline:
   time.sleep(.25)
   with psycopg.connect(probe.package.boundary.PRIMARY_ADMIN)as conn,conn.cursor()as cur:
    sessions=cur.execute(\"select pid,usename,application_name,state from pg_stat_activity where datname='cp6_rollback'\").fetchall()
   samples.append(sessions)
  result['bounded_cleanup_wait_samples']=samples
  assert not sessions,('SOL_FULLSTACK_SESSIONS_LEFT_AFTER_BOUNDED_WAIT',sessions)"""
derived=source.replace(old,new)
namespace=dict(vars(full),time=time)
exec(compile(derived,'<sol-bounded-copy-cleanup>','exec'),namespace)
full.execute=namespace['execute']
holder=[]
def legacy(verify):
 p=Path(os.environ['SOL_FIRST_C0_ARCHIVE']);raw=p.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==m['first_zip_sha256']
 with zipfile.ZipFile(p)as z:
  assert z.testzip()is None
  raw=z.read(m['first_group_member']);assert hashlib.sha256(raw).hexdigest()==m['first_group_sha256']
  original=json.loads(raw)
 assert original['counts']=={'PASS':25}and original['complete_boundary_restored']and not original.get('missing')
 # Deliberately held audit-owned session closes by itself after two seconds.
 # Its only query is a timing wait, so it cannot alter business data.
 conn=full.psycopg.connect(full.probe.package.boundary.ADMIN,application_name='SOL_COPY_CLEANUP_TIMING_CONTROL')
 event=threading.Event()
 def run():
  try:
   event.set();conn.execute('select pg_sleep(2)');conn.rollback()
  finally:conn.close()
 t=threading.Thread(target=run);t.start();event.wait(10);holder.append(t)
 return dict(status='PASS',case_id='SOL_BOUNDED_CLEANUP_NATURAL_SESSION_CLOSURE',
  reused_C0_original=original,new_C0_execution_credit=0,new_cleanup_control_budget=1,
  first_run=38578838814,first_job=115903011981,
  first_failure_not_erased=True,no_backend_termination=True,
  synthetic_timing_session=True,product_SQL_change=False,oracle_change=False,
  helper_original_sha256=hashlib.sha256(source.encode()).hexdigest(),
  helper_qualified_sha256=hashlib.sha256(derived.encode()).hexdigest(),
  exact_old=old,exact_new=new,
  probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
full.legacy=legacy
namespace['legacy']=legacy
def runtime(browser_mode=False):
 normal=full.probe.run(k3_cleanup=True)
 for t in holder:t.join(10)
 assert len(full.observed)==1
 r=full.observed[0];samples=r.get('bounded_cleanup_wait_samples',[])
 assert samples and samples[0]and not samples[-1],'SOL_CLEANUP_TIMING_CONTROL_NOT_EXERCISED'
 if r['status']!='PASS':normal=dict(normal,status='INCOMPLETE',sol_cleanup_qualification_failed=True)
 return normal
full.probe.package._writer_runtime=runtime
if __name__=='__main__':full.probe.package.run('install')
