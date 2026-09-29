"""Native fixture controls for read-only P11 browser proof. No R10 write claim."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_sales_cases as cases
import cp7_sales_command_cases as commands
import cp7_sales_draft_cases as drafts
import cp7_sales_payment_cases as payments

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('127.0.0.1','localhost') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op=sys.argv[1];p=json.loads(sys.argv[2])
 with psycopg.connect(target) as conn,conn.cursor() as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='create':
   out=cases.fixture(cur,date.fromisoformat(p['today']))
   if p.get('ops'):
    role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,));cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.invoice.view')",(role,))
  elif op=='create_payment_source':
   out=cases.fixture(cur,date.fromisoformat(p['today']),qty=3,price='10.01',discount='0.02');out['bank']=str(cases.bc.bank_account(cur,'P11CASH'+__import__('uuid').uuid4().hex[:8]));out['bank_code']=cur.execute('select cash_account_code from erp.cash_accounts where id=%s',(out['bank'],)).fetchone()[0];out['cash_coa']=payments.bank_account(cur,out);out['ar_coa']=commands.mapping(cur,'AR_CUSTOMER')
  elif op=='read_payment':
   out=dict(document=cases.read(cur,p)['detail'],cash=payments.cash(cur,p),available=commands.available(cur,p),accounts={key:str(value) for key,value in commands.accounts(cur).items()})
  elif op=='create_draft_source':
   out=drafts.fixture(cur,date.fromisoformat(p['today']),30);out['second']=drafts.fixture(cur,date.fromisoformat(p['today']),30)
  elif op=='read_draft':
   found=cur.execute('select id::text from erp.sales_headers where sale_number=%s',(p['tag'],)).fetchone();d=cases.read(cur,dict(p,sale=found[0]))['detail'] if found else None
   out=dict(document=d,available=[commands.available(cur,p),commands.available(cur,p['second'])],gl=[[str(x) for x in row] for row in cases.gl(cur)])
  elif op=='progress':
   cases.fg.post_sale(cur,p['draft']);cases.payment(cur,p,date.fromisoformat(p['today']),'30');cases.returned(cur,p);out={'ok':True}
  elif op=='read':
   out=dict(document=cases.read(cur,p)['detail'],movements=cur.execute('select count(*),sum(qty_signed) from erp.fg_stock_movements where lot_id=%s',(p['lot'],)).fetchone(),gl=[[str(x) for x in row] for row in cases.gl(cur)],available=commands.available(cur,p),accounts={key:str(value) for key,value in commands.accounts(cur).items()})
  else:raise ValueError('Unknown fixture operation')
  cases.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
