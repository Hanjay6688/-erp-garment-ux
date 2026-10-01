"""Accepted Native settlement/inverse controls; never direct history inserts."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json,hashlib
import psycopg
import cp7_obligation_history_cases as history
ep=history.previous
def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='repeat26':
   today=date.fromisoformat(p['today']);original=history.parent.read(cur,p['run_id'],p['actor'])
   for i in range(25):
    paid=ep.ar.sales.payment(cur,dict(sale=p['sale'],tag=p['tag']+'-history-'+str(i)),today,'300')
    closed=ep.row(ep.evaluate(cur,original,subject=p['actor']),p['sale']);assert closed['episode']['state']=='RESOLVED'
    ep.ar.sales.native(cur,'select erp.reverse_sales_payment(%s,%s)',(paid,'P16 actual saved-history Native inverse'))
    opened=ep.row(ep.evaluate(cur,original,subject=p['actor']),p['sale']);assert opened['episode']['number']==str(i+2)
   out=dict(episode=opened['episode'])
  elif op=='state':
   business=history.b.boundary.snapshot(cur)
   out=dict(analysis_count=cur.execute('select count(*)from cp7_analysis_native.runs where actor=%s',(p['actor'],)).fetchone()[0],business_sha256=hashlib.sha256(json.dumps(business,sort_keys=True,default=str).encode()).hexdigest(),monitoring=history.signature(cur))
  else:raise ValueError('UNKNOWN_NATIVE_HISTORY_BROWSER_CONTROL')
  history.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl;conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
