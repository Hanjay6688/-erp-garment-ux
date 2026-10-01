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
  if op=='prepare':out=cases.setup(cur,date.fromisoformat(p['today']),p['actor'],new_plan_po=p.get('actual_check',False))
  elif op=='state':out=dict(drafts=cur.execute('select count(*)from cp7_plan_native.drafts where actor=%s',(p['actor'],)).fetchone()[0],intents=cur.execute('select count(*)from cp7_plan_native.intents where actor=%s',(p['actor'],)).fetchone()[0],domain_drafts=cur.execute('select count(*)from erp.cutting_groups').fetchone()[0],ledger_hash=hashlib.sha256(json.dumps(cases.monetary_state(cur),sort_keys=True).encode()).hexdigest())
  elif op in('deactivate','restore'):cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  elif op=='actual_progress':
   from cp7_plan_actual_cases import post,complete_one
   row=cur.execute('select d.payload,d.target_key,i.cutting_group_id from cp7_plan_native.drafts d join cp7_plan_native.intents i on i.draft_id=d.id and i.actor=d.actor where d.id=%s and d.actor=%s',(p['draft_id'],p['actor'])).fetchone();assert row is not None,'OWNED_PLAN_NATIVE_INTENT_REQUIRED'
   assert cur.execute('select is_active from erp.laundry_vendors where id=%s',(p['vendor_id'],)).fetchone()[0]and cur.execute('select is_active from erp.wash_processes where id=%s',(p['process_id'],)).fetchone()[0]
   f=dict(payload=row[0],root=row[1].split(':')[0],options=dict(size_id=row[1].split(':')[1]),group=str(row[2]),fixture=dict(vendor=p['vendor_id'],process=p['process_id']))
   if p['stage']=='POST':out=post(cur,f)
   elif p['stage']=='QC_ONE':out=complete_one(cur,f)
   else:raise ValueError('UNKNOWN_ACTUAL_STAGE')
  else:raise ValueError('UNKNOWN_PLAN_BROWSER_CONTROL')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
