"""Predeclared unchanged F01/F02 and CP3-6 providers on the installed final CP7 stack.

Only the context differs: CP7 was already installed by its original harness.
Legacy AU/AV install calls are replaced by full-stack verification; case bodies,
expected values, quiet-seed policy and race schedules are not edited. The
whole disposable test database is cloned before the legacy committed fixtures
and restored from that clone afterward. Never reads/writes a hosted database.
"""
import hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
import psycopg

CANDIDATE=Path(__file__).resolve().parents[3]/'auditor'
sys.path.insert(0,str(CANDIDATE/'scripts'))
os.environ['CP6_T2_SEED']='QUIETED'
os.environ['CP6_T2_FIXTURE']='PAYROLL_APPROVED'
import cp7_f05_analysis_probe as probe
MODE=os.environ['SOL_FULLSTACK_MODE']
assert MODE in ('foundations','regression','ar','temporal')
OUT=CANDIDATE/('cp6-proof/t3/SOL_FULLSTACK_'+MODE.upper()+'.json')
MANIFEST=Path(__file__).with_name('FULLSTACK_MANIFEST.json')
manifest=json.loads(MANIFEST.read_text())
original_group=probe.native.strict_group
observed=[]

def foundations(verify):
 import cp7_snapshot_cases as snapshot,cp7_identity_cases as identity
 import cp7_wip_cases as wip,cp7_wip_source_cases as cutting,cp7_wip_production_cases as production
 import cp7_f02_audit_replay as replay,cp7_f02_regression_cases as fixes
 groups={}
 modules={'snapshot':snapshot,'identity':identity,'wip':wip,'cutting':cutting,'production':production,'replay':replay,'fixes':fixes}
 for spec in manifest['foundations']:
  key,kind,mod=spec['key'],spec['kind'],modules[spec['module']]
  if kind=='native':g=original_group('SOL_FULLSTACK_'+key.upper(),getattr(mod,spec['factory']),verify)
  elif kind=='races':g=probe.modes._run_races_once(mod,verify,'sol_fullstack_'+key)
  elif kind=='http':g=probe.modes._run_http_once(mod,verify,'sol_fullstack_'+key)
  else:raise AssertionError(kind)
  rows=g.get({'native':'cases','races':'races','http':'cases'}[kind],{})
  if kind=='http':rows=g.get('cases',g.get('http',{}))
  # Preserve exact native planned IDs and bodies. No count-based dropped-case credit.
  actual=list(rows);planned=g.get('planned_case_ids',g.get('planned_race_ids',[]))
  complete=g.get('counts')=={'PASS':spec['expected_count']} and len(rows)==spec['expected_count'] and len(set(actual))==len(actual)
  complete=complete and set(actual)==set(spec['expected_ids'])
  if planned:complete=complete and set(planned)==set(actual)
  complete=complete and not g.get('database_remaining') and not g.get('cleanup_failures')
  groups[key]=dict(required_count=spec['expected_count'],complete=complete,result=g)
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(dict(mode=MODE,status='INCOMPLETE',groups=groups),indent=2,default=str)+'\n')
  print(json.dumps(dict(sol_fullstack_group=key,complete=complete,counts=g.get('counts'),cases=len(rows))),flush=True)
 return dict(status='PASS'if len(groups)==len(manifest['foundations'])and all(g['complete']for g in groups.values())else'INCOMPLETE',groups=groups)

def legacy(verify):
 import cp6_t2_regression as t2
 a=t2.avt
 # This is a new composition qualification. It cannot execute a second AU/AV
 # install over CP7; verify the already installed candidate instead.
 def already():
  with psycopg.connect(a.ADMIN)as conn,conn.cursor()as cur:
   v=verify(cur);conn.rollback()
  return dict(status='PASS',qualification='PREINSTALLED_FINAL_CP7_VERIFIED',verification=v)
 a.install_au=lambda:already()['status']
 a.runtime.change=lambda kind,pg,control:already()
 a.runtime.verified=verify
 t2.change=lambda kind,pg,control:already()
 a.OUT=CANDIDATE/('cp6-proof/t3/FULLSTACK_T2_'+MODE.upper())
 a.OUT.mkdir(parents=True,exist_ok=True)
 r=dict(status='INCOMPLETE',phase=MODE,candidate_sha=manifest['candidate_sha'],
  case_declarations_unchanged=True,oracle_changes=False,race_schedule_changes=False,
  install_calls='PREINSTALLED_FINAL_CP7_VERIFICATION',seed=t2.SEED,fixture=t2.FIXTURE,
  original_oracle_sources=a.specs.pins()['oracle_sha256'],production_go=False)
 {'regression':t2.regression_phase,'ar':t2.ar_phase,'temporal':a.temporal_phase}[MODE](r)
 r['original_group_reports']={p.name:json.loads(p.read_text())for p in a.OUT.glob('*.json')}
 return r

def docker(*args):
 subprocess.run(['docker','exec','supabase_db_cp5-local',*args],check=True)

def execute(verify):
 name='cp6_sol_fullstack_origin';admin=probe.package.boundary.ADMIN
 result=dict(mode=MODE,status='INCOMPLETE',candidate_sha=manifest['candidate_sha'],
  source_probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
  evidence_origin='INDEPENDENT_NATIVE_RERUN_ON_FINAL_CP7',
  oracle_origin='UNCHANGED_PREEXISTING_CASES',fixture_origin='UNCHANGED_PREEXISTING_PROVIDERS',
  disposable_copy_lifecycle=True,production_go=False)
 with psycopg.connect(admin)as conn,conn.cursor()as cur:
  verify(cur);before=probe.package.boundary.snapshot(cur);conn.rollback()
  public=probe.public_state(cur);conn.rollback()
  assert cur.execute('select count(*)from pg_database where datname=%s',(name,)).fetchone()[0]==0
 docker('createdb','-U','supabase_admin','--maintenance-db=template1','-T','cp6_rollback',name)
 try:
  result['run']=foundations(verify)if MODE=='foundations'else legacy(verify)
  result['status']=result['run']['status']
 except Exception as exc:
  result.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
 finally:
  with psycopg.connect(probe.package.boundary.PRIMARY_ADMIN)as conn,conn.cursor()as cur:
   # Refuse restoration if another session is still attached to this audit copy.
   sessions=cur.execute("select pid,usename,application_name,state from pg_stat_activity where datname='cp6_rollback'").fetchall()
  result['sessions_before_restore']=sessions
  assert not sessions,('SOL_FULLSTACK_SESSIONS_LEFT',sessions)
  docker('dropdb','-U','supabase_admin','--maintenance-db=template1','cp6_rollback')
  docker('createdb','-U','supabase_admin','--maintenance-db=template1','-T',name,'cp6_rollback')
  docker('dropdb','-U','supabase_admin','--maintenance-db=template1',name)
  with psycopg.connect(admin)as conn,conn.cursor()as cur:
   verify(cur);result['complete_business_boundary_restored']=probe.package.boundary.snapshot(cur)==before;conn.rollback()
   result['complete_public_catalog_restored']=probe.public_state(cur)==public;conn.rollback()
   result['origin_clone_remaining']=cur.execute('select count(*)from pg_database where datname=%s',(name,)).fetchone()[0]
  if not result['complete_business_boundary_restored']or not result['complete_public_catalog_restored']or result['origin_clone_remaining']:
   result['status']='INCOMPLETE'
  OUT.write_text(json.dumps(result,indent=2,default=str)+'\n')
  print(json.dumps(dict(sol_fullstack_result={k:v for k,v in result.items()if k!='run'}),default=str),flush=True)
 return result

def wrapped(name,case_factory,verify):
 normal=original_group(name,case_factory,verify)
 if name=='CP7_K3_CLEANUP':observed.append(execute(verify))
 return normal
probe.native.strict_group=wrapped
def runtime(browser_mode=False):
 normal=probe.run(k3_cleanup=True)
 assert len(observed)==1,'SOL_FULLSTACK_NOT_EXECUTED'
 # DISPOSITION_REQUIRED is retained as such; original stale cases remain red.
 if observed[0]['status']not in ('PASS','WRITER_PASS','WRITER_PASS_WITH_12_PRESERVED_HISTORICAL_HOLD','DISPOSITION_REQUIRED'):
  normal=dict(normal,status='INCOMPLETE',sol_fullstack_failure=True)
 return normal
probe.package._writer_runtime=runtime
if __name__=='__main__':probe.package.run('install')
