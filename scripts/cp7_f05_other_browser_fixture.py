"""Actual Native controls on the one disposable browser copy; no source mock."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json
import psycopg
import cp7_other_obligation_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   today=date.fromisoformat(p['today']);cases.setup(cur,today)
   payroll=cases.installments.fixture(cur,today,attendance=False,manual='9007199254740993.01')
   opening=cases.opening.fixture(cur,today)
   laundry=cases.laundry_fixture(cur,today,priced=False)
   out=dict(payroll=payroll,opening_id=opening['balances']['UPAH-OLD'],receipt_line=laundry['line'])
  elif op=='partial':out=cases.installments.act(cur,p['payroll'],amount='9007199254740993.00')
  elif op=='final':out=cases.installments.act(cur,p['payroll'],amount='0.01')
  elif op=='inverse':out=cases.installments.act(cur,p['payroll'],'REVERSE_PAYMENT',payment=p['payment_id'])
  elif op=='state':out=dict(analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0])
  elif op in('deactivate','restore'):
   cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
  else:raise ValueError('UNKNOWN_OTHER_OBLIGATION_FIXTURE_ACTION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
