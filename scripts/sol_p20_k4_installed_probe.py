"""Sol-only audit wrapper. Product source and writer's 16-case oracle untouched.
Independent cold/warm races use installed real step, real users and real locks.
"""
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import cp7_f05_analysis_probe as probe
import cp7_k4_runner_cases as k4

reports=[]
original=probe.modes.run_races

def independent(tools,today,cold):
 def test():
  keys=[uuid.uuid4(),uuid.uuid4()]
  with tools.connect()as c,c.cursor()as cur:
   k4.b.api.admin(cur)
   initial=cur.execute('select count(*)from cp7_analysis_stage.runner').fetchone()[0]
   assert initial==0,('audit requires actual empty runner immediately after installation',initial)
   if not cold:assert k4.tick(cur)['outcome']=='IDLE'
   for key in keys:k4.staged.checked(k4.staged.request(cur,today,key),key,'RUNNING')
   c.commit()
  holder=tools.connect();holder.execute('lock table cp7_analysis_stage.outputs in exclusive mode')
  one=tools.connect();two=tools.connect()
  def tick(c):
   with c.cursor()as cur:out=k4.tick(cur)
   c.commit();return out
  try:
   with ThreadPoolExecutor(max_workers=2)as pool:
    first=pool.submit(tick,one)
    with tools.connect(autocommit=True)as watch:
     deadline=time.monotonic()+5
     while time.monotonic()<deadline:
      waiting=watch.execute("select count(*)from pg_locks where pid=%s and relation='cp7_analysis_stage.outputs'::regclass and not granted",(one.info.backend_pid,)).fetchone()[0]
      if waiting:break
      time.sleep(.02)
     assert waiting,'first real step did not reach output INSERT'
     second=pool.submit(tick,two);deadline=time.monotonic()+1.5
     reached=False;wait=None
     while time.monotonic()<deadline:
      reached=watch.execute("select count(*)from pg_locks where pid=%s and relation='cp7_analysis_stage.outputs'::regclass and not granted",(two.info.backend_pid,)).fetchone()[0]>0
      row=watch.execute('select wait_event from pg_stat_activity where pid=%s',(two.info.backend_pid,)).fetchone()
      wait=row[0]if row else None
      if reached:break
      time.sleep(.02)
     witness=watch.execute('select locktype,mode,granted from pg_locks where pid=%s and not granted',(two.info.backend_pid,)).fetchall()
    holder.rollback();a=first.result(timeout=15);b=second.result(timeout=15)
  finally:holder.close();one.close();two.close()
  with tools.connect()as c,c.cursor()as cur:
   rows=[k4.staged.job_row(cur,key)for key in keys]
   advance=[r['units_done']for r in rows]
   outputs=cur.execute('select count(*),count(distinct(job_id,idx))from cp7_analysis_stage.outputs where job_id=any(%s::uuid[])',([str(r['id'])for r in rows],)).fetchone()
   assert advance==[1,1]and outputs==(2,2),(advance,outputs)
  return dict(status='PASS'if reached else'FAIL',initial_runner_rows=initial,second_reached_real_output_insert=reached,
              second_wait_event=wait,ungranted_locks=witness,first=a,second=b,units_done=advance,
              no_duplicate_outputs=outputs==(2,2),product_step_unmodified=True)
 return [('SOL_COLD_START'if cold else'SOL_WARM_START',test)]

def wrapped(module,verify,phase):
 normal=original(module,verify,phase)
 if module is k4:
  for cold in [True,False]:
   result=original(SimpleNamespace(races=lambda tools,today,cold=cold:independent(tools,today,cold)),verify,'sol_cold'if cold else'sol_warm')
   reports.append(result)
   path=probe.OUT.parent/('SOL_INSTALLED_COLD.json'if cold else'SOL_INSTALLED_WARM.json')
   path.write_text(json.dumps(result,indent=2,default=str)+'\n')
   print(json.dumps(dict(sol_independent_installed_race=result),default=str),flush=True)
 return normal

probe.modes.run_races=wrapped
def runtime(browser_mode=False):
 normal=probe.run(k4_runner=True)
 assert len(reports)==2,'independent installed probes did not execute'
 if any(r.get('counts')!={'PASS':1}or r.get('database_remaining')!=0 for r in reports):
  normal=dict(normal,status='INCOMPLETE',sol_independent_failure=True)
 return normal
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
