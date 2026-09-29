"""Native fixture controls for read-only P11 browser proof. No R10 write claim."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_sales_cases as cases
import cp7_sales_command_cases as commands

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
