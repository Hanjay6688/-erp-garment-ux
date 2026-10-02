"""Native production setup and read-back for the actual owning-note UI journey."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_note_correction_cases as cases

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_NOTE_BROWSER_ONLY'
 op,p=sys.argv[1],json.loads(sys.argv[2])
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f=cases.e01.production(cur,date.fromisoformat(p['today']));f['today']=p['today'];f['before_note_accounts']={k:str(v)for k,v in cases.cmd.accounts(cur).items()};cases.posted(cur,f,'20','25');f['root_sale']=f['sale'];f['original_facts']=cases.unchanged_facts(cur,f['sale']);cases.returned.payments.pay(cur,f,'200');f['allocations']=cases.returned.read(cur,f)['page']['rows'];payload,v=cases.returned.payload(cur,f,qty='5',refund='125',destination=f['location']);cases.cmd.command(cur,'RETURN',payload,v);f['brand_name']=cur.execute('select b.brand_name from erp.brands b join erp.products p on p.brand_id=b.id where p.id=%s',(f['product'],)).fetchone()[0];out=f
  elif op=='read':
   h=cases.history(cur,p['root_sale']);f=dict(p,sale=h['current_sale_id']);out=dict(history=h,document=cases.source.read(cur,f)['detail'],available=cases.e01.physical(cur,f),accounts={k:str(v)for k,v in cases.cmd.accounts(cur).items()},book=cases.complete_book(cur,f),original_facts=cases.unchanged_facts(cur,p['root_sale']),fg_value=str(cur.execute('select sum(m.qty_signed*h.hpp_per_pcs)from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id join erp.v_current_hpp h on h.lot_id=l.id where l.po_id=%s',(p['po'],)).fetchone()[0]))
  else:raise ValueError('UNKNOWN_NOTE_BROWSER_FIXTURE_OPERATION')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
  conn.commit()
 print(json.dumps(out,default=str))

if __name__=='__main__':main()
