"""Native production setup and read-back for the actual receipt-correction UI journey."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_receipt_correction_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1') and url.path=='/cp6_auditor_browser','DISPOSABLE_RECEIPT_BROWSER_ONLY'
 op,p=sys.argv[1],json.loads(sys.argv[2])
 with psycopg.connect(target) as conn,conn.cursor() as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f=cases.e01.production(cur,date.fromisoformat(p['today']))
   f['purchase_number']=cur.execute('select purchase_number from erp.material_purchase_headers where id=%s',(f['purchase'],)).fetchone()[0]
   f['facts']=cases.facts(cur,f['purchase']);f['hpp']=[str(x) for x in cases.hpp(cur,f)]
   f['material_name'],f['roll_number']=cur.execute('select m.material_name,r.roll_number from erp.material_rolls r join erp.materials m on m.id=r.material_id where r.id=%s',(f['roll'],)).fetchone()
   out={k:f[k] for k in ('purchase','purchase_number','tag','roll','roll_number','material','material_name','raw_location','po','group','facts','hpp')}
  elif op=='read':
   w=cases.ws(cur,p['purchase'])
   out=dict(workspace=w,raw=[str(x) for x in cases.raw(cur,p['material'])],hpp=[str(x) for x in cases.hpp(cur,dict(po=p['po']))],
     facts=cases.facts(cur,p['purchase']),card=cases.full_card(cur,p['material'],p['roll'],p['raw_location']),
     requests=cur.execute("select count(*) from cp7_receipt_fix.requests where payload->>'purchase_id'=%s",(p['purchase'],)).fetchone()[0],
     material_name=cur.execute('select material_name from erp.materials where id=%s',(p['material'],)).fetchone()[0],
     name_requests=cur.execute("select count(*) from cp7_receipt_fix.name_requests where payload->>'material_id'=%s",(p['material'],)).fetchone()[0])
  else:raise ValueError('UNKNOWN_RECEIPT_BROWSER_FIXTURE_OPERATION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
  conn.commit()
 print(json.dumps(out,default=str))

if __name__=='__main__':main()
