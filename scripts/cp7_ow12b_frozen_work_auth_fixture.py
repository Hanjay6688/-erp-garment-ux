"""Loopback-only fixture/readback; all tested requests use real public HTTP."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_ow12b_frozen_work_cases as work

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(target)
 assert u.hostname in('localhost','127.0.0.1')and u.path=='/cp6_auditor_browser'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   today=date.fromisoformat(p['today']);x=work.plan.fixture(cur,today);work.plan.b.api.admin(cur)
   config=cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0]
   out=dict(root=x['root'],query=work.plan.staged.query(today),config=config)
  elif op=='state':
   work.plan.b.api.admin(cur)
   out=dict(plans=cur.execute('select count(*)from cp7_schedule_native.plans where actor=%s',(p['actor'],)).fetchone()[0],commands=cur.execute('select count(*)from cp7_schedule_native.commands where actor=%s',(p['actor'],)).fetchone()[0],physical=work.plan.monetary_state(cur))
   r=cur.execute("select request_id::text,run_id::text,state,reference->>'bounded_request_contract',reference->>'bounded_reference_contract',reference->>'bounded_input_coverage' from cp7_analysis_stage.jobs where actor=%s and reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v2' order by captured_at desc limit 1",(p['actor'],)).fetchone()
   out['job']=None if r is None else dict(zip(('request','run','state','request_contract','reference_contract','coverage'),r))
  elif op=='stock':
   work.plan.found_fg(cur,dict(root=p['root']),'1');out=dict(actual_Native_stock_writer=True)
  elif op in('deactivate','restore'):
   cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_FROZEN_WORK_BROWSER_CONTROL')
  work.plan.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
