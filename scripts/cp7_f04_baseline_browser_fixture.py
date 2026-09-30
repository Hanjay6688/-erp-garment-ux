"""Native disposable P06 UI fixture and observation; no fabricated business facts."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json
import psycopg
import cp7_planning_baseline_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':out=cases.history.fixture(cur,date.fromisoformat(p['today']))
  elif op=='state':
   f=p['fixture'];out=dict(profile_count=cur.execute('select count(*)from cp7_profile.profiles where root_id=%s',(f['product'],)).fetchone()[0],baseline_count=cur.execute('select count(*)from cp7_baseline_native.runs where actor=%s',(p['actor'],)).fetchone()[0],business=cases.b.boundary.snapshot(cur))
  elif op=='update_profile':
   f=p['fixture'];profile=cases.get(cur,[f['product']])['rows'][0];payload=cases.payload(cur,f,profile['revision']);payload['config']['daily_pcs']='20';out=cases.save(cur,payload)
  elif op in('deactivate','restore'):
   cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_P06_BROWSER_FIXTURE_ACTION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
