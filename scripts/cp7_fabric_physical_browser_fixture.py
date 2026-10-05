"""Only the existing isolated Native browser database; no production target."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_fabric_physical_cases as cases
def main():
 url=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(url)
 assert parsed.hostname in('localhost','127.0.0.1')and parsed.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(url)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  # Every operation receives the same WIB day from the journey; refuse a missing one explicitly.
  if 'today' not in p:raise ValueError('FABRIC_BROWSER_FIXTURE_TODAY_REQUIRED')
  today=date.fromisoformat(p['today'])
  if op=='prepare':
   # Bound opening WIP (no ambiguous same-model WIP), explicit synthetic rate2,
   # one posted ten-unit roll and one opening OPEN_PURCHASE_ORDER remaining50
   # due two WIB days later (before the 10-day fixture deadline):
   # gap93 x2 = 186, installed0, allocated10, external186-10-50=126.
   f=cases.bound(cur,today,subject=p['actor']);cases.b.api.admin(cur);line=cases.commitment(cur,today,f,'50',today+cases.timedelta(days=2))
   cases.b.api.admin(cur)
   out=dict(root=f['root'],target=f['target'],material=f['payload']['config']['material_id'],roll=cases.roll(f),location=cases.location(f),commitment_line=str(line),
    expected=dict(gross='186',installed='0',unused='10',external='126'),after_receipt=dict(unused='30',external='106'))
  elif op=='receive':
   f=dict(payload=dict(config=dict(material_id=p['material'])),plan=dict(payload=dict(cutting=dict(source_location_id=p['location'],rolls=[dict(roll_id=p['roll'])]))))
   out=dict(receipt=cases.receive(cur,today,f,'20'))
  elif op=='state':
   cases.b.api.admin(cur);out=dict(business=cases.b.boundary.snapshot(cur),analyses=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0])
  elif op=='restore':
   cases.b.api.admin(cur);cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(p['actor'],));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_FABRIC_PHYSICAL_BROWSER_ACTION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
