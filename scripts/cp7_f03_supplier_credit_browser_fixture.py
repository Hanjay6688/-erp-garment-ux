"""Loopback-only Native setup/read; no accounting writes from observation."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_f03_supplier_credit_cases as cases

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
  elif op=='revoke':
   role=cases.credit.one(cur,'select role_id from erp.app_users where auth_user_id=%s',p['actor'])
   rows=cur.execute("select role_id::text,permission_key,granted_by::text,granted_at from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.view'",(role,)).fetchall()
   assert rows,'Expected the real current owner finance permission before revocation'
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.view'",(role,));out=dict(rows=rows)
  elif op=='restore':
   cur.executemany('insert into erp.app_role_permissions(role_id,permission_key,granted_by,granted_at)values(%s,%s,%s,%s)',p['rows']);out=dict(status='RESTORED')
  else:raise ValueError('Unknown supplier-credit fixture operation')
  cases.credit.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
