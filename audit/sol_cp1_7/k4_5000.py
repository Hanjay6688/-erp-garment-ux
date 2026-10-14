"""Independent coverage: 5,000 Native targets completed by real pg_cron alone.

Predeclared oracle: exactly 5,000 distinct planned targets, every unit once,
every public result page intact, identical request/run on reopening. No manual
step/tick and no whole-build implementation used as an expected-value oracle.
Not a timing SLA, forecast-quality proof, hosted install, or physical browser.
"""
import hashlib,json,sys,time,types,uuid
from pathlib import Path
from urllib.parse import urlparse,urlunparse
import psycopg

CANDIDATE=Path(__file__).resolve().parents[3]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'))
import cp7_f05_analysis_probe as probe
import cp7_k4_runner_cases as k4
import cp7_p19_scale_cases as scale
ID='SOL_K4_5000_REAL_CRON_NO_PAGE'
OUT=CANDIDATE/'cp6-proof/t3/SOL_K4_5000.json'
DETAIL=CANDIDATE/'cp6-proof/t3/SOL_K4_5000_DETAIL.json'
observed=[]

def races(tools,today):
 def operation():
  started=time.monotonic(); key=uuid.uuid4()
  detail=dict(case_id=ID,candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',
    expected_targets=5000,evidence_origin='INDEPENDENT_NATIVE_RERUN',
    oracle_origin='SOL_LITERAL_COVERAGE_AND_BUSINESS_BOUNDARY',
    fixture_origin='REUSED_NATIVE_SCALE_WRITERS_SYNTHETIC_NOT_FACTORY_DEFAULT',
    page_step_calls_after_request=0,auditor_tick_calls=0,driver_deadline_seconds=1800,
    source_probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    production_go=False)
  def save():
   DETAIL.parent.mkdir(parents=True,exist_ok=True)
   DETAIL.write_text(json.dumps(detail,indent=2,default=str)+'\n')
  save()
  with tools.connect() as conn,conn.cursor() as cur:
   detail['seed']=scale.ensure(cur,today,5000,wip_done=False,commit=conn.commit)
   expected=set(scale.current_targets(cur));assert len(expected)==5000
   before=k4.b.boundary.snapshot(cur)
   b=k4.b; b.api.admin(cur)
   role=cur.execute('select r.role_code from erp.app_users a join erp.app_roles r on r.id=a.role_id where a.auth_user_id=%s',
     (k4.auth.base.OPERATOR_AUTH,)).fetchone()[0]
   assert role in ('OWNER','ADMIN'),role
   q=scale.history.query(today,3)
   capture=time.monotonic()
   first=k4.staged.checked(k4.staged.request(cur,today,key,q=q),key,'RUNNING')
   detail.update(actor_role=role,query=q,initial=first,capture_ms=round((time.monotonic()-capture)*1000,3))
   assert first['targets_total']==5000,first
   defs=[d for d in k4.schedule.definitions(cur)if d['name']==k4.RUNNER['name']]
   assert defs==[k4.RUNNER],defs
   conn.commit();save()
  u=urlparse(tools.admin);database=u.path.lstrip('/')
  cron_url=urlunparse(u._replace(path='/postgres'))
  history=[]
  with psycopg.connect(cron_url,autocommit=True)as cron,cron.cursor()as cc:
   version=cc.execute("select extversion from pg_extension where extname='pg_cron'").fetchone()
   assert version and tuple(int(x)for x in version[0].split('.')[:2])>=(1,5),version
   detail.update(pg_cron=version[0],test_schedule_override='5 seconds',native_tick_statement_timeout='8s')
   since=cc.execute('select now()').fetchone()[0]
   ids=k4.schedule.install(cc,database,'postgres',defs,{k4.RUNNER['name']:'5 seconds'})
   try:
    deadline=time.monotonic()+1800;last=None;done=None
    while time.monotonic()<deadline:
     with tools.connect()as conn,conn.cursor()as cur:
      done=k4.staged.checked(k4.staged.status(cur,key),key);conn.commit()
     point={k:done[k]for k in ('state','units_done','unit_count','unit_attempts','stage','run_id')}
     if point!=last:
      point['elapsed_s']=round(time.monotonic()-started,3);history.append(point);last={k:done[k]for k in point if k!='elapsed_s'}
      detail['progress']=history;save()
      print(json.dumps(dict(sol_k4_5000_progress=point)),flush=True)
     if done['state']!='RUNNING':break
     time.sleep(2)
    runs=k4.schedule.runs(cc,ids[k4.RUNNER['name']],since)
   finally:
    removed=k4.schedule.uninstall(cc,database)
    quiet=time.monotonic()+60
    while time.monotonic()<quiet:
     cc.execute('select pg_stat_clear_snapshot()')
     if not cc.execute("select count(*)from pg_stat_activity where datname=%s and application_name='pg_cron'",(database,)).fetchone()[0]:break
     time.sleep(.5)
    assert not cc.execute("select count(*)from pg_stat_activity where datname=%s and application_name='pg_cron'",(database,)).fetchone()[0]
    cc.execute('delete from cron.job_run_details where jobid=any(%s)',(list(ids.values()),))
   detail.update(final=done,cron_runs=runs,removed_after_test=removed);save()
   assert removed==[k4.schedule.job_name(k4.RUNNER['name'],database)]and k4.schedule.installed(cc,database)==[]
   assert done and done['state']=='DONE',('SOL_K4_5000_NOT_DONE',done)
   finished=[r for r in runs if r['status']in ('succeeded','failed')]
   assert finished and all(r['status']=='succeeded'for r in finished),runs
  with tools.connect()as conn,conn.cursor()as cur:
   n=k4.units_once(cur,key)
   original,ps,shape=k4.staged.fetch(cur,done['run_id'])
   recs=original['analysis']['recommendations']
   rec_keys=[r['target']['key']for r in recs]
   labels=[r['target_key']for r in original['product_labels']]
   assert len(rec_keys)==len(set(rec_keys))==5000 and set(rec_keys)==expected
   assert len(labels)==len(set(labels))==5000 and set(labels)==expected
   assert ps['targets_total']==done['targets_total']==5000
   count=k4.staged.counts(cur,key)
   assert count[:3]==(0,0,1),count
   reopened=k4.staged.checked(k4.staged.request(cur,today,key,q=q),key,'DONE')
   assert reopened['run_id']==done['run_id'] and reopened['request_id']==done['request_id']
   assert k4.units_once(cur,key)==n and k4.staged.counts(cur,key)==count
   assert k4.b.boundary.snapshot(cur)==before,'SOL_K4_5000_ANALYSIS_CHANGED_BUSINESS'
   conn.commit()
  detail.update(status='PASS',units=n,pages=shape,identity_hash=ps['identity_hash'],
    recommendations=5000,distinct_recommendations=5000,labels=5000,distinct_labels=5000,
    expected_target_sha256=scale.digest('\n'.join(sorted(expected))),
    observed_target_sha256=scale.digest('\n'.join(sorted(rec_keys))),
    reopened_same_job_and_run=True,every_unit_once=True,all_pages_hash_and_range_verified=True,
    complete_business_boundary_unchanged=True,total_ms=round((time.monotonic()-started)*1000,3))
  save();return detail
 return [(ID,operation)]

original_races=probe.modes.run_races
def wrapped(module,verify,phase):
 normal=original_races(module,verify,phase)
 if phase=='cp7_k4_runner':
  # Exactly one run of the independent case: no automatic retry or green-chasing.
  result=probe.modes._run_races_once(types.SimpleNamespace(races=races),verify,'sol_k4_5000')
  result.update(candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',expected_ids=[ID],expected_count=1,
    source_probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
  observed.append(result);OUT.write_text(json.dumps(result,indent=2,default=str)+'\n')
  print(json.dumps(dict(sol_k4_5000_result=result),default=str),flush=True)
 return normal
probe.modes.run_races=wrapped
def runtime(browser_mode=False):
 normal=probe.run(k4_runner=True)
 assert len(observed)==1,'SOL_K4_5000_CASE_NOT_EXECUTED'
 if observed[0].get('counts')!={'PASS':1}or set(observed[0].get('races',{}))!={ID}or observed[0].get('database_remaining')!=0:
  normal=dict(normal,status='INCOMPLETE',sol_k4_5000_failure=True)
 return normal
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
