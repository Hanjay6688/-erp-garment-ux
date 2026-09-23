"""Capture proposed AU in one rolled-back transaction; never a release gate."""
from datetime import date
from pathlib import Path
import json,os,subprocess,sys,traceback
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
import cp6_au_definitions as proposal
import cp6_au_probe as review
import cp6_at_trial as writer
import cp6_at_runtime as runtime
import cp6_ao_ap_installed as api
import cp6_successor_regression as boundary
from cp6_ao_ap_inventory import sha,function_pins
OUT=ROOT/'cp6-proof/au-capture';OUT.mkdir(parents=True,exist_ok=True)
report=dict(status='INCOMPLETE',migration_installed=False,production_go=False,independent_acceptance=False,
 head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
 definitions_sha256=sha(Path(proposal.__file__).read_bytes()),schema_sha256=sha(proposal.SCHEMA),cases={})
primary=None
try:
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==review.FROZEN
 with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:primary=boundary.snapshot(cur)
 writer.install_as();runtime.change('install',boundary.PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
 with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
  runtime.verified(cur);baseline=boundary.snapshot(cur)
  before=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0]
  report['before']=dict(objects=before,functions=function_pins(cur))
  for identity,old in proposal.OLD.items():
   assert cur.execute('select pg_get_functiondef(to_regprocedure(%s))',(identity,)).fetchone()[0]==old,identity
  cur.execute('set local role postgres');cur.execute(proposal.SCHEMA,prepare=False)
  for new in proposal.FUNCTIONS.values():cur.execute(new,prepare=False)
  if getattr(proposal,'TRIGGERS',''):cur.execute(proposal.TRIGGERS,prepare=False)
  report['after']=dict(objects=cur.execute(runtime.build.INVENTORY_SQL).fetchone()[0],functions=function_pins(cur))
  report['canonical_definitions']={i:cur.execute('select pg_get_functiondef(to_regprocedure(%s))',(i,)).fetchone()[0] for i in proposal.FUNCTIONS}
  assert report['canonical_definitions']==proposal.FUNCTIONS
  api.admin(cur)
  if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:cur.execute('grant usage on schema erp to authenticated')
  api.seed(cur);boundary.historical.prior.set_open_period(cur,date(2026,8,31))
  today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
  for variant in ('DISPLAY_NAME','UNUSED_IDENTITY','USED_SUCCESSOR','CANCEL_FUTURE'):
   cur.execute('savepoint case_run')
   try:row=review.master_case(cur,today,variant)
   except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint case_run');api.admin(cur);cur.execute('release savepoint case_run')
   report['cases'][variant]=row;print(json.dumps(dict(case=variant,**row),default=str),flush=True)
  conn.rollback();runtime.verified(cur)
  report['complete_boundary_restored']=boundary.snapshot(cur)==baseline
  assert report['complete_boundary_restored']
  report['status']='CAPTURE_PASS'
except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
finally:
 subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
 with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
  report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
  report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
 if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
 (OUT/'CATALOG.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('before','after','canonical_definitions')},default=str))
assert report['status']=='CAPTURE_PASS',report.get('error')
