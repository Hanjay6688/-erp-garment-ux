"""Disposable source-navigation setup; all economic changes use Native commands."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_misc_cases as misc
import cp7_installment_cases as installment
import cp7_transaction_source_cases as source
import cp7_supplier_payment_cases as supplier_payment
import cp7_qc_source_cases as qc_source
import cp7_laundry_source_cases as laundry_source
import cp7_cutting_source_cases as cutting_source

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
  elif op=='prepare-accessory':
   today=date.fromisoformat(p['today']);f=source.accessory_fixture(cur,today)
   for i in range(51):
    payload=source.accessory.payload(f);payload.update(number=f['issue_number']+'-NEW-'+str(i),physical_at=source.accessory.bc.local_at(today,11))
    source.accessory.bc.note_call(cur,'SAVE_DRAFT',payload)
   w=source.accessory.bc.note_read(cur,dict(id=f['issue']['id'],query=f['code']))
   assert len(w['history'])==50 and w['history_count']>=52 and f['issue']['id']not in[x['id']for x in w['history']]
   assert w['document']['id']==f['issue']['id']
   out=f
  elif op=='state-accessory':
   f=p['fixture'];observed=source.accessory.observe(cur,f)
   assert observed['document']['id']==f['issue']['id']
   inverses=[dict(id=str(i),number=number,original_id=str(original))for i,number,original in cur.execute('select id,journal_number,reversal_of_id from erp.journal_entries where reversal_of_id=any(%s::uuid[])order by id',([j['id']for j in f['journals']],)).fetchall()]
   out=dict(observation=observed,inverses=inverses,business=source.b.boundary.snapshot(cur))
  elif op=='prepare-rework':
   f=source.rework_fixture(cur,date.fromisoformat(p['today']),True)
   d=source.read(cur,'REWORK_ORDER',f['rework'])['document'];assert d['focus']['page_offset']>=50
   first=source.rework_workspace(cur,f,0);assert len(first['rows'])==50 and f['bs']not in[r['id']for r in first['rows']]
   f['first_offset']=d['focus']['page_offset'];out=f
  elif op=='state-rework':
   f=p['fixture'];out=source.rework_state(cur,f)
   out['source']=source.read(cur,'REWORK_ORDER',f['rework'])['document']
  elif op=='prepare-laundry-source':
   out=laundry_source.fixture(cur,date.fromisoformat(p['today']))
  elif op=='state-laundry-source':
   out=laundry_source.observe(cur,p['fixture'])
  elif op=='prepare-laundry-dependencies':
   f=laundry_source.fixture(cur,date.fromisoformat(p['today']))
   f['qc']=laundry_source.physical.qc(cur,f,1,0,14)['qc_inspection_id'];source.b.api.admin(cur)
   f['qc_number']=cur.execute('select inspection_number from erp.qc_inspections where id=%s',(f['qc'],)).fetchone()[0]
   f['item']=str(cur.execute('select id from erp.qc_inspection_items where inspection_id=%s',(f['qc'],)).fetchone()[0])
   f['lot']=str(cur.execute('select id from erp.fg_lots where qc_item_id=%s',(f['item'],)).fetchone()[0])
   f['movement']=str(cur.execute("select id from erp.fg_stock_movements where source_type='QC_ITEM'and source_id=%s and reversal_of_id is null",(f['item'],)).fetchone()[0]);out=f
  elif op=='state-laundry-dependencies':
   f=p['fixture'];out=dict(laundry=laundry_source.observe(cur,f),qc=qc_source.observe(cur,f))
  elif op=='prepare-qc-source':
   out=qc_source.fixture(cur,date.fromisoformat(p['today']))
  elif op=='prepare-cutting-source':
   out=cutting_source.browser_fixture(cur,date.fromisoformat(p['today']))
  elif op=='state-cutting-source':
   f=p['fixture'];out=dict(business=source.b.boundary.snapshot(cur),document=cutting_source.document(cur,f)[0])
   if f.get('unpicked'):out['unpicked_document']=cutting_source.document(cur,f['unpicked'])[0]
  elif op=='state-qc-source':
   out=qc_source.observe(cur,p['fixture'])
  elif op=='prepare-supplier-payment':
   out=supplier_payment.fixture(cur,date.fromisoformat(p['today']))
  elif op=='state-supplier-payment':
   out=supplier_payment.observe(cur,p['fixture'])
   # All Native economic/platform rows, not only the panel subtotal. Only the
   # read's capture timestamp is volatile; the browser keeps every other fact.
   out['business']=source.b.boundary.snapshot(cur)
  elif op=='prepare-production-read':
   f=source.production.fixture(cur,date.fromisoformat(p['today']))
   wash=source.production.wash(cur,f,range(4),11)
   misc.b.api.admin(cur)
   role=str(cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0])
   original={key:cur.execute('select exists(select 1 from erp.app_role_permissions where role_id=%s and permission_key=%s)',(role,key)).fetchone()[0]for key in('production.laundry.view','production.final_sku.view')}
   for key in original:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,key))
   group=cur.execute('select group_number from erp.cutting_groups where id=%s',(f['group'],)).fetchone()[0]
   delivery=cur.execute('select delivery_number from erp.laundry_deliveries where id=%s',(wash['sent']['delivery_id'],)).fetchone()[0]
   out=dict(group_id=f['group'],group_number=group,delivery_id=wash['sent']['delivery_id'],delivery_number=delivery,admin_role=role,original_permissions=original,actual_qty_by_size=f['qtys'],actual_total=sum(f['qtys']))
  elif op=='production-read':
   source.auth.actor(cur,p['actor'])
   out=cur.execute('select public.erp_get_laundry_qc_workspace_v1(%s,%s)',(p['scope'],p['query'])).fetchone()[0]
  elif op=='production-permission':
   assert p['permission']in('production.laundry.view','production.final_sku.view')and isinstance(p['allowed'],bool)
   assert str(cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0])==p['role']
   if p['allowed']:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(p['role'],p['permission']))
   else:cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(p['role'],p['permission']))
   out=dict(status='PASS',current_ADMIN_view=p['allowed'])
  elif op=='production-boundary':
   out=source.b.boundary.snapshot(cur)
  else:raise ValueError('Unknown source navigation fixture operation')
  misc.b.api.admin(cur)
  if not had:cur.execute('revoke usage on schema erp from authenticated')
  assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
  conn.commit()
 print(json.dumps(out,default=str))
if __name__=='__main__':main()
