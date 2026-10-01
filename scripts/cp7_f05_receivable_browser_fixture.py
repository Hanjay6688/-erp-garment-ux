"""Actual invoice/payment Native controls in the disposable browser database."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json,hashlib
import psycopg
import cp7_receivable_condition_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   today=date.fromisoformat(p['today']);f=cases.sales.fixture(cur,today,qty=20,price='25',stock=30)
   cases.sales.fg.post_sale(cur,f['draft']);cases.sales.payment(cur,f,today,'200')
   out=dict(sale=f['sale'],tag=f['tag'],number=f['tag'])
  elif op=='settle':
   out=dict(payment=cases.sales.payment(cur,dict(sale=p['sale'],tag=p['tag']+'-final'),date.fromisoformat(p['today']),'300'))
  elif op=='inverse':
   cases.sales.native(cur,'select erp.reverse_sales_payment(%s,%s)',(p['payment'],'P16 actual browser Native payment inverse'));out=dict(status='PASS')
  elif op=='state':
   business=cases.b.boundary.snapshot(cur)
   out=dict(analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0],business_sha256=hashlib.sha256(json.dumps(business,sort_keys=True,default=str).encode()).hexdigest())
  else:raise ValueError('UNKNOWN_NATIVE_AR_BROWSER_CONTROL')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
