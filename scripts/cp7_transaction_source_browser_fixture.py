"""Disposable source-navigation setup; all economic changes use Native commands."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_misc_cases as misc
import cp7_installment_cases as installment

def main():
 target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
 assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
 op,p=sys.argv[1],json.load(sys.stdin)
 with psycopg.connect(target)as conn,conn.cursor()as cur:
  had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
  if not had:cur.execute('grant usage on schema erp to authenticated')
  if op=='prepare':
   f=misc.fixture(cur,date.fromisoformat(p['today']));saved=misc.command(cur,'SAVE',misc.save_payload(f));posted=misc.command(cur,'POST',misc.intent(saved));ident=posted['transaction_id'];doc=misc.native_document(cur,ident)
   out=dict(fixture=f,transaction_id=ident,document=doc,journal_id=doc['journals'][0]['id'])
  elif op=='state':
   f=p['fixture'];ident=p['transaction_id'];doc=misc.native_document(cur,ident)
   assert misc.stock_cost(cur)==f['stock_cost'],'SOURCE_NAVIGATION_STOCK_HPP_CHANGED'
   out=dict(document=doc,cash_delta=str((misc.cash_balance(cur,f['cash']['id'])-misc.D(f['cash_before'])).quantize(misc.D('.01'))),stock_HPP_unchanged=True)
  elif op=='prepare-payroll':
   f=installment.fixture(cur,date.fromisoformat(p['today']));payments=[installment.act(cur,f,amount='10.00')['payment_id']for _ in range(26)]
   page=installment.read(cur,f['payroll'],payment_offset=25);assert [x['id']for x in page['payments']['rows']]==[payments[-1]]
   if p.get('mobile'):
    role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
    f['admin_pay_original']=cur.execute("select exists(select 1 from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.pay')",(role,)).fetchone()[0]
    cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.payroll.pay')on conflict do nothing",(role,))
   out=dict(fixture=f,payment=page['payments']['rows'][0])
  elif op=='state-payroll':
   f=p['fixture'];page=installment.read(cur,f['payroll'],payment_offset=25)
   assert installment.physical.stock_cost(cur)==f['physical'],'SOURCE_PAYROLL_STOCK_HPP_CHANGED'
   assert installment.legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')==(2,installment.D(1000),installment.D(1000))
   assert installment.D(page['document']['approved_net'])==installment.D(1000)
   paid=installment.D(page['document']['paid_amount']);assert installment.delta(cur,f)=={installment.legacy.acct(cur,'CONTRACTOR_PAYABLE'):paid,f['cash']['account_id']:-paid}
   out=dict(document=page['document'],payments=page['payments'],stock_HPP_unchanged=True,approved_cost1000_once=True,GL_cash_matches_active_native_payments=True,
    requests=cur.execute("select count(*)from cp7_installment.requests where payload->>'payroll_id'=%s",(f['payroll'],)).fetchone()[0])
  elif op=='restore-payroll-admin':
   role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
   if p['original']:cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.payroll.pay')on conflict do nothing",(role,))
   else:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.pay'",(role,))
   out=dict(status='PASS',original_ADMIN_pay_permission_restored=True)
  else:raise ValueError('Unknown source navigation fixture operation')
  misc.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
