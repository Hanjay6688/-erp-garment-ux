"""Disposable Native business setup; browser observations never change facts."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json,hashlib
import psycopg
import cp7_plan_native_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':out=cases.setup(cur,date.fromisoformat(p['today']),p['actor'])
  elif op=='state':out=dict(drafts=cur.execute('select count(*)from cp7_plan_native.drafts where actor=%s',(p['actor'],)).fetchone()[0],intents=cur.execute('select count(*)from cp7_plan_native.intents where actor=%s',(p['actor'],)).fetchone()[0],domain_drafts=cur.execute('select count(*)from erp.cutting_groups').fetchone()[0],ledger_hash=hashlib.sha256(json.dumps(cases.monetary_state(cur),sort_keys=True).encode()).hexdigest())
  elif op in('deactivate','restore'):cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_PLAN_BROWSER_CONTROL')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
