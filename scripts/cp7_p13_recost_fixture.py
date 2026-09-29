"""Disposable late-price source preparation; only the browser processes recost."""
from datetime import date
from urllib.parse import urlparse
from unittest.mock import patch
import json,os,sys,uuid
import psycopg
import cp7_recost_cases as cases
def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op=sys.argv[1];p=json.loads(sys.argv[2])
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   # The browser cases share a disposable database. Give each actual production
   # lot its own zero-rate mandor master so its lawful payroll does not overlap
   # the preceding case's approved period. No payroll/queue constraint is changed.
   cases.b.api.admin(cur);contractor=uuid.uuid4()
   cur.execute("insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required) values(%s,%s,'P13 recost isolated mandor','MANDOR',false)",(contractor,'P13RC-'+contractor.hex[:12]))
   with patch.object(cases.aw.chain.production,'CONTRACTOR',str(contractor)):
    f=cases.fixture(cur,date.fromisoformat(p['today']))
   out=dict(po=str(f['f']['po']),contractor=str(contractor),day=str(f['day']),filing=f['filing'],original=f['original']['filing'],position=f['original']['snapshot']['financial_position'])
  elif op=='read':
   out=dict(queue=cases.read(cur),values=cases.values(cur,dict(po=p['po'])),stock=cases.stock(cur),report=cases.finance.read(cur,date.fromisoformat(p['day']),filing_id=p['filing']),attempts=cur.execute('select coalesce(sum(attempt_count),0) from erp.cost_recalc_queue where entity_id=%s',(p['po'],)).fetchone()[0])
  else:raise ValueError('Unknown fixture action')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
