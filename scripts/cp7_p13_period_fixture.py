"""Disposable source preparation and native read-back; browser owns period actions."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_period_cases as cases

def main():
 url=urlparse(os.environ['AUDITOR_BROWSER_DB_URL']);assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op=sys.argv[1];p=json.loads(sys.argv[2])
 with psycopg.connect(os.environ['AUDITOR_BROWSER_DB_URL'])as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f,day,state=cases.ready(cur,date.fromisoformat(p['today']));out=dict(day=str(day),previous_closed=state['control']['closed_through'],business=cases.business(cur))
  elif op=='read':out=dict(period=cases.read(cur,date.fromisoformat(p['day'])),filings=cases.filings(cur),business=cases.business(cur))
  else:raise ValueError('Unknown fixture action')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
