"""Disposable-only native history/UI fixture; no business fact fabrication."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json,contextlib
import psycopg
import cp7_planning_history_cases as cases
import cp7_f03_e01_cases as e01
import hashlib

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':out=cases.fixture(cur,date.fromisoformat(p['today']))
  elif op=='cut_prepare':
   # Production emits diagnostic checkpoints. Keep the fixture protocol a
   # single JSON result; preserve those diagnostics on stderr for the receipt.
   with contextlib.redirect_stdout(sys.stderr):
    out=e01.production(cur,date.fromisoformat(p['today']),cutting_draft_only=True)
  elif op=='cut_state':
   f=p['fixture'];cases.b.api.admin(cur)
   qty,value=cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot)from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()
   posted=cur.execute('select material_issue_posted from erp.cutting_groups where id=%s',(f['group'],)).fetchone()[0]
   pcs=cur.execute('select sum(y.qty_pcs)from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id where r.cutting_group_id=%s',(f['group'],)).fetchone()[0]
   snapshot=cases.b.boundary.snapshot(cur)
   out=dict(raw_qty=str(qty),raw_value=str(value),posted=posted,cut_pcs=str(pcs),native_hash=hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest(),own_runs=cur.execute('select count(*)from cp7_cutting_yield.runs where actor=%s',(p['actor'],)).fetchone()[0])
  elif op=='post':out=cases.sales.fg.post_sale(cur,p['fixture']['draft'])
  elif op=='state':
   f=p['fixture'];out=cases.capture(cur,date.fromisoformat(p['today']));out={'history':out,'native_rows':cur.execute('select count(*)from cp7_planning.history_runs where actor=%s',(p['actor'],)).fetchone()[0]}
   cases.stock_assert(cur,out['history'],f,76 if p.get('posted')else 100,0 if p.get('posted')else 24,76)
  elif op=='deactivate':
   cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(p['actor'],));out={'status':'PASS'}
  elif op=='restore':
   cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(p['actor'],));out={'status':'PASS'}
  else:raise ValueError('UNKNOWN_P05_BROWSER_FIXTURE_ACTION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))

if __name__=='__main__':main()
