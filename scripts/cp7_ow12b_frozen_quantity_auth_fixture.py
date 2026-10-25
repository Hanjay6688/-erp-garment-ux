"""Loopback fixture/readback only; the browser requests and completes its job."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_ow12b_frozen_choice_cases as choice


def main():
 url=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(url)
 assert u.hostname in('localhost','127.0.0.1')and u.path=='/cp6_auditor_browser'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(url)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   today=date.fromisoformat(p['today']);x=choice.plan.fixture(cur,today)
   imported=choice.reader.reader.volume.import_batch(cur,today,11,choice.reader.reader.volume.Phases())
   choice.reader.reader.historical.seed(cur,imported);target=imported[0]['target']
   choice.consumer.profile(cur,imported[0]['root'])
   out=dict(root=x['root'],target=target,query=choice.plan.staged.query(today),browser_job_created=False)
  elif op=='state':
   choice.plan.b.api.admin(cur)
   rows=cur.execute("select request_id::text,run_id::text,state,reference from cp7_analysis_stage.jobs where actor=%s order by captured_at,request_id",(p['actor'],)).fetchall()
   out=dict(jobs=[dict(zip(('request','run','state','reference'),r))for r in rows],physical=choice.plan.monetary_state(cur),choices=choice.choice.metadata(cur))
  elif op=='read':
   row=choice.plan.staged.job_row(cur,p['request'],p['actor']);assert row['state']=='DONE'
   original,pages,meta=choice.plan.staged.fetch(cur,row['run_id'],p['actor'])
   assert original['analysis']['scope']['actor_scope_id']==p['actor']and pages['request_id']==p['request']
   out=dict(page_set=pages,recommendations=original['analysis']['recommendations'],page_metadata=meta,reference=row['reference'])
  elif op=='stock':
   choice.plan.found_fg(cur,dict(root=p['root']),'1');out=dict(actual_Native_stock_writer=True)
  elif op in('deactivate','restore'):
   cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_FROZEN_QUANTITY_BROWSER_CONTROL')
  choice.plan.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))


if __name__=='__main__':main()
