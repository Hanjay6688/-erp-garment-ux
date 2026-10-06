"""Only the existing isolated Native browser database; no production target."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_fabric_recipe_cases as cases
def main():
 url=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(url)
 assert parsed.hostname in('localhost','127.0.0.1')and parsed.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(url)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f=cases.setup(cur,date.fromisoformat(p['today']),p['actor']);cases.b.api.admin(cur)
   material=next(m for m in f['workspace']['materials']if m['id']==f['payload']['config']['material_id'])
   now,too_old=cur.execute("select (clock_timestamp()-interval'1 minute')at time zone'Asia/Jakarta',(clock_timestamp()-interval'2 years')at time zone'Asia/Jakarta'").fetchone()
   # The exact value a datetime-local input holds: Chromium normalizes a zero
   # second away (07:41:00 -> 07:41), and Playwright then refuses the fill.
   local=lambda t:t.isoformat(timespec='seconds').removesuffix(':00')if t.second==0 else t.isoformat(timespec='seconds')
   out=dict(root=f['plan']['root'],target=f['target'],material=material,from_wib=local(now),rejected_from_wib=local(too_old),expected_gross='170',selected_rate='2')
  elif op=='state':
   cases.b.api.admin(cur);out=dict(business=cases.b.boundary.snapshot(cur),recipes=cur.execute('select count(*)from cp7_fabric_native.recipes where actor=%s',(p['actor'],)).fetchone()[0],commands=cur.execute('select count(*)from cp7_fabric_native.commands where actor=%s',(p['actor'],)).fetchone()[0],analyses=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0])
  elif op in('deactivate','restore'):
   cases.b.api.admin(cur);cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_FABRIC_BROWSER_ACTION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
