"""Native fixture controls, private metadata counts and current Auth only."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json
import psycopg
import cp7_rule_source_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f,e,key=cases.due_fixture(cur,date.fromisoformat(p['today']));out=dict(condition_key=key,sale=f['sale'],number=f['tag'])
  elif op=='state':
   out=dict(claims=cur.execute('select id,status,body_sha256,occurrence_key,fence from cp7_reminder_native.local_claims where actor=%s order by created_at,id',(p['actor'],)).fetchall(),bindings=cur.execute('select count(*)from cp7_reminder_native.local_bindings where actor=%s',(p['actor'],)).fetchone()[0],resolutions=cur.execute('select count(*)from cp7_reminder_native.local_resolutions where actor=%s',(p['actor'],)).fetchone()[0],analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0],native_manual_count=cur.execute('select count(*)from erp.manual_reminders').fetchone()[0])
  elif op in('deactivate','restore'):
   cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_LOCAL_RULE_FIXTURE_ACTION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
