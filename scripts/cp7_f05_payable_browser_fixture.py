"""Actual accepted supplier receipt/invoice/payment controls, disposable only."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json,hashlib
import psycopg
import cp7_payable_condition_cases as cases
def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f=cases.invoice.fixture(cur,date.fromisoformat(p['today']),qty='20',price='25');out=f
  elif op=='finalize_pay200':
   f=p['receipt'];f['day']=date.fromisoformat(f['day']);cases.finalize(cur,f,date.fromisoformat(p['today']));cases.payment(cur,f,date.fromisoformat(p['today']),'200');out=dict(status='PASS')
  elif op=='settle':out=dict(payment=cases.payment(cur,p['receipt'],date.fromisoformat(p['today']),'300'))
  elif op=='inverse':cases.inverse(cur,p['payment']);out=dict(status='PASS')
  elif op=='state':
   business=cases.b.boundary.snapshot(cur);out=dict(analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0],business_sha256=hashlib.sha256(json.dumps(business,sort_keys=True,default=str).encode()).hexdigest())
  else:raise ValueError('UNKNOWN_NATIVE_MATERIAL_AP_BROWSER_CONTROL')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
