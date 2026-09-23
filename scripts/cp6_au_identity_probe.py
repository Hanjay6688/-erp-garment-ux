"""Additional frozen-AT probes: direct identity-key and metadata authority."""
from datetime import date,timedelta
from pathlib import Path
import json,os,subprocess,sys,traceback,uuid
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
import cp6_at_runtime as runtime
import cp6_at_trial as writer
import cp6_au_probe as peer
import cp6_au_cases as fixtures
import cp6_as_probe as dates
import cp6_at_probe as attempt
import cp6_ao_ap_installed as api
import cp6_successor_regression as boundary
OUT=ROOT/'cp6-proof/au-identity-review';OUT.mkdir(parents=True,exist_ok=True)

def probe(cur,today,variant):
 f,s,p=fixtures.fixture(cur,today)
 code=f['code']+'PROBE';brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
 old,new=attempt.series(cur,code,p[2],brand,p[4],dates.invoice.at(today-timedelta(days=6),0),dates.invoice.at(today-timedelta(days=3),0))
 before=boundary.snapshot(cur);new_id=uuid.uuid4()
 def operation():
  api.ordinary(cur)
  if variant=='DIRECT_SUCCESSOR_ID':return cur.execute('update erp.products set id=%s where id=%s returning id',(new_id,new)).fetchone()[0]
  cur.execute("select set_config('app.product_identity_controlled','on',true)")
  return cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from,effective_to)
    values(%s,'Forged metadata',%s,%s,%s,'Yellow',true,%s,%s) returning id''',
    (code+'FORGE',p[2],brand,p[4],dates.invoice.at(today-timedelta(days=2),0),dates.invoice.at(today+timedelta(days=2),0))).fetchone()[0]
 result,error=attempt.attempt(cur,operation)
 return dict(status='COUNTEREXAMPLE' if not error else 'PASS',variant=variant,ordinary_authenticated=True,
     expected='Direct identity/period writes without controlled RPC are rejected atomically',result=result,refusal=error,
     all_boundary_unchanged=boundary.snapshot(cur)==before)

report=dict(status='INCOMPLETE',frozen_source=peer.FROZEN,cases={},production_go=False,independent_acceptance=False)
primary=None
try:
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==peer.FROZEN
 report['auditor_head']=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:primary=boundary.snapshot(cur)
 writer.install_as();runtime.change('install',boundary.PG,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
 with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
  runtime.verified(cur);before=boundary.snapshot(cur)
  if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:cur.execute('grant usage on schema erp to authenticated')
  api.seed(cur);boundary.historical.prior.set_open_period(cur,date(2026,8,31))
  today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
  for variant in ('DIRECT_SUCCESSOR_ID','FORGED_METADATA'):
   cur.execute('savepoint identity_probe')
   try:row=probe(cur,today,variant)
   except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint identity_probe');api.admin(cur);cur.execute('release savepoint identity_probe')
   report['cases'][variant]=row;print(json.dumps(row,default=str),flush=True)
  conn.rollback();runtime.verified(cur);assert boundary.snapshot(cur)==before
  report['full_boundary_restored']=True
  assert all(r['status']!='INCOMPLETE' for r in report['cases'].values())
  report['status']='REVIEW_COMPLETE'
except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
finally:
 subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
 with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
  report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
  report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
 if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
 (OUT/'RESULT.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print(json.dumps(report,default=str));assert report['status']=='REVIEW_COMPLETE'
