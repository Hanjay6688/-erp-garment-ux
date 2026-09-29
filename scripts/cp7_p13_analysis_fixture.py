"""Loopback disposable source preparation only; browser is a real report reader."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_finance_analysis_cases as cases
def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op=sys.argv[1];p=json.loads(sys.argv[2])
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f=cases.cash_fixture(cur,date.fromisoformat(p['today']));r=cases.read(cur,f['query']);assert cases.D(r['comparison']['revenue_growth_pct'])==20 and cases.D(r['comparison']['gross_margin_change_pp'])==-3 and cases.D(r['cash']['net_change'])==100
   out=dict(query=f['query'],expected=r,transfer=str(f['transfer']))
  elif op=='read':
   out=dict(report=cases.read(cur,p['query']),boundary=cases.b.boundary.snapshot(cur))
  else:raise ValueError('Unknown fixture operation')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
