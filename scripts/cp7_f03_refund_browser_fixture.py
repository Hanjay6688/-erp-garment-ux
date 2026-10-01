"""Disposable-only source setup; browser observations never mutate money."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_f03_refund_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser'
 op=sys.argv[1];p=json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':out=cases.prepare(cur,date.fromisoformat(p['today']))
  elif op=='read':out=cases.observe(cur,p)
  elif op in('deactivate','restore'):
   cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('Unknown refund fixture operation')
  cases.bb.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
