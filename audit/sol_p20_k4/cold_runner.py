"""Unmodified candidate run_next + runner DDL; controlled access/step fixture.
Native PostgreSQL only, disposable socket, no external URL. Not an RLS/UI proof.
"""
import concurrent.futures as futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
import psycopg

SOURCE=Path('scripts/cp7-src/planning/analysis-stages.sql').read_text()
FN=re.search(r'create function cp7_analysis_stage.run_next\(\)returns jsonb.*?end \$\$;',SOURCE,re.S).group()
DDL=re.search(r'create table cp7_analysis_stage.runner\(.*?;',SOURCE,re.S).group()
report=dict(candidate='8cc1b0818fdba54f3ebeb64e132f7f3e20309e24',source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
            scope='UNMODIFIED_RUNNER_AND_DDL_CONTROLLED_STEP_ACCESS_KERNEL_ONLY',status='INCOMPLETE',cases=[],production_go=False)
root=Path('/usr/lib/postgresql');bins=sorted(root.glob('*/bin'),key=lambda p:int(p.parent.name),reverse=True)
if os.getuid()==0 or not bins:raise RuntimeError('native non-root PostgreSQL required')
bin=bins[0];tmp=tempfile.TemporaryDirectory(prefix='sol-k4-');base=Path(tmp.name);data=base/'data'
env={k:v for k,v in os.environ.items()if not k.startswith('PG')}
def cmd(name,*args):return subprocess.run([str(bin/name),*args],env=env,text=True,capture_output=True,check=True,timeout=30)
def connect():return psycopg.connect(host=str(base),user='sol',dbname='postgres',autocommit=True)
def check(id,ok,**witness):report['cases'].append(dict(id=id,status='PASS'if ok else'FAIL',**witness))
started=False
try:
 cmd('initdb','-D',str(data),'-U','sol','--auth-local=trust','--auth-host=reject','--no-locale','--encoding=UTF8')
 cmd('pg_ctl','-D',str(data),'-l',str(base/'pg.log'),'-o',f"-k {base} -c listen_addresses='' -c max_connections=10",'-w','start');started=True
 with connect()as c:
  report['runtime']=c.execute('select version()').fetchone()[0]
  c.execute('create schema cp7_analysis_stage;create schema cp7_schedule_native')
  c.execute('create table cp7_analysis_stage.jobs(id uuid primary key,actor uuid,updated_at timestamptz,state text,units_done int,unit_count int)')
  c.execute(DDL)
  c.execute('create table public.sol_outputs(job_id uuid primary key,actor text)')
  c.execute("create function cp7_schedule_native.access_now(boolean)returns jsonb language sql as $$select current_setting('request.jwt.claims')::jsonb$$")
  c.execute("""create function cp7_analysis_stage.step(p uuid,a jsonb)returns jsonb language plpgsql as $$begin
   if p='00000000-0000-0000-0000-000000000001'then perform pg_advisory_xact_lock(918271);end if;
   insert into public.sol_outputs values(p,a->>'sub');
   update cp7_analysis_stage.jobs set state='DONE',units_done=1 where id=p;
   return jsonb_build_object('state','DONE','units_done',1,'unit_count',1);end $$""")
  c.execute(FN)
  for setting in ['0','8001ms']:
   c.execute('set statement_timeout='+"'"+setting+"'")
   try:c.execute('select cp7_analysis_stage.run_next()');code=None
   except psycopg.Error as e:code=e.sqlstate
   check('LIMIT_'+setting,code=='55000'and c.execute('select count(*)from cp7_analysis_stage.runner').fetchone()[0]==0,sqlstate=code)
  c.execute("set statement_timeout='8s';begin isolation level repeatable read")
  try:c.execute('select cp7_analysis_stage.run_next()');code=None
  except psycopg.Error as e:code=e.sqlstate
  c.execute('rollback');check('FRESH_ACCESS_ISOLATION',code=='P0001',sqlstate=code)

 def tick(conn):
  conn.execute("set statement_timeout='8s'")
  with conn.transaction():return conn.execute('select cp7_analysis_stage.run_next()').fetchone()[0]
 # The first tick is deliberately held in its step, after inserting heartbeat.
 # The second must reach its own job without waiting for that heartbeat.
 for cold in [True,False]:
  with connect()as control,connect()as one,connect()as two:
   control.execute('truncate cp7_analysis_stage.jobs,public.sol_outputs')
   for i in [1,2]:control.execute("insert into cp7_analysis_stage.jobs values(%s,%s,now()+%s*interval'1 second','RUNNING',0,1)",(f'00000000-0000-0000-0000-{i:012d}',f'10000000-0000-0000-0000-{i:012d}',i))
   control.execute('select pg_advisory_lock(918271)')
   with futures.ThreadPoolExecutor(max_workers=2)as pool:
    first=pool.submit(tick,one)
    until=time.monotonic()+5
    while time.monotonic()<until:
     row=control.execute('select wait_event from pg_stat_activity where pid=%s',(one.info.backend_pid,)).fetchone()
     if row and row[0]=='advisory':break
     time.sleep(.02)
    else:raise AssertionError('first tick did not reach controlled unit')
    second=pool.submit(tick,two)
    until=time.monotonic()+1.5;wait=None
    while time.monotonic()<until and not second.done():
     row=control.execute('select wait_event from pg_stat_activity where pid=%s',(two.info.backend_pid,)).fetchone()
     if row:wait=row[0]
     time.sleep(.02)
    progressed=second.done()
    locks=control.execute("select locktype,mode,granted from pg_locks where pid=%s and not granted",(two.info.backend_pid,)).fetchall()
    control.execute('select pg_advisory_unlock(918271)')
    a=first.result(timeout=10);b=second.result(timeout=10)
   check('COLD_SECOND_TICK_NO_HEARTBEAT_WAIT'if cold else'WARM_SECOND_TICK_NO_HEARTBEAT_WAIT',progressed,second_wait_event=wait,ungranted_locks=locks,first=a,second=b)
   rows=control.execute('select count(*),count(distinct job_id)from public.sol_outputs').fetchone()
   check('COLD_RECOVERY_NO_DUPLICATE'if cold else'WARM_NO_DUPLICATE',rows==(2,2),outputs=list(rows))
 with connect()as c:
  c.execute('truncate cp7_analysis_stage.jobs,public.sol_outputs')
  c.execute("insert into cp7_analysis_stage.jobs values('00000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003',now(),'RUNNING',0,1)")
  c.execute("set statement_timeout='8s';begin")
  prior=['{"sub":"prior-admin","role":"service_role"}','stale-sub','stale-claim']
  keys=['request.jwt.claims','request.jwt.claim.sub','request.jwt.claim']
  for k,v in zip(keys,prior):c.execute('select set_config(%s,%s,true)',(k,v))
  result=c.execute('select cp7_analysis_stage.run_next()').fetchone()[0]
  restored=[c.execute('select current_setting(%s)',(k,)).fetchone()[0]for k in keys]
  actor=c.execute('select actor from public.sol_outputs').fetchone()[0]
  check('ACTOR_AND_ALL_PRIOR_CLAIMS_RESTORED',restored==prior and actor=='10000000-0000-0000-0000-000000000003',actor=actor,claims_restored=restored==prior,outcome=result['outcome'])
  c.execute('rollback')
 report['status']='FAIL'if any(x['status']=='FAIL'for x in report['cases'])else'PASS'
except BaseException as e:report['error']=repr(e);raise
finally:
 if started:cmd('pg_ctl','-D',str(data),'-m','immediate','-w','stop')
 tmp.cleanup();Path('test-results/sol-p20-k4').mkdir(parents=True,exist_ok=True)
 Path('test-results/sol-p20-k4/COLD_RUNNER.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report))
if report['status']!='PASS':raise SystemExit(1)
