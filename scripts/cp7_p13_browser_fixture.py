"""Disposable native controls for P13 read-only UI proof; not browser writes."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_finance_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in ('localhost','127.0.0.1') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op=sys.argv[1];p=json.loads(sys.argv[2])
 with psycopg.connect(target) as conn,conn.cursor() as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   today=date.fromisoformat(p['today']);f,day,ident=cases.archive_fixture(cur,today);filed=cases.read(cur,day,filing_id=ident)['filing']
   cases.aw.chain.prior.post_purchase(cur,f['material'],cases.aw.chain.production.at(f['purchase_day'],22),unit_price=12);cases.b.api.admin(cur);cases.aw.chain.production.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');cases.b.api.admin(cur)
   corrected=cases.read(cur,day,filing_id=ident)
   assert corrected['filing']==filed and corrected['snapshot']['data_confidence']['status']=='READY' and corrected['snapshot']['data_confidence']['changed_since_filing']
   sale=cases.source.fixture(cur,today);before=cases.read(cur,today);cases.source.fg.post_sale(cur,sale['draft']);cases.source.returned(cur,sale);cases.source.payment(cur,sale,today,'30');current=cases.read(cur,today)
   assert cases.change(before,current,'financial_position','customer_ar')==30 and cases.change(before,current,'financial_position','cash')==30
   assert cases.change(before,current,'performance','sales_revenue_gl')==60 and cases.change(before,current,'performance','cogs_gl')==30
   out=dict(today=str(today),day=str(day),filing_id=ident,current=current,corrected=corrected)
  elif op=='read':
   r=cases.read(cur,date.fromisoformat(p['day']),filing_id=p['filing_id']);out=dict(report=r,accounts={k:str(v) for k,v in cases.cmd.accounts(cur).items()},stock_hash=cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(m) order by m.id)::text,'[]')) from erp.fg_stock_movements m").fetchone()[0])
  else:raise ValueError('Unknown fixture operation')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
