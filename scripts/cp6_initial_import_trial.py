#!/usr/bin/env python3
"""Proposed AP RPCs on the exact disposable AN runtime, fully rolled back.
This is a writer trial, never production or independent acceptance.
"""
from pathlib import Path
from datetime import timedelta
import hashlib,json,os,subprocess,traceback,uuid
import psycopg
import cp6_v2620an_runtime as runtime
import cp6_v2620al_import_review as inherited
from cp6_v2620ap_definitions import FUNCTIONS,PREDECESSOR,SCHEMA
from cp6_v2620n_rollback_guards import function_catalog

ROOT=Path('cp6-proof/initial-import');ROOT.mkdir(parents=True,exist_ok=True)
actors,base,production=inherited.actors,inherited.base,inherited.production
URL='postgresql://supabase_admin:postgres@127.0.0.1:54322/postgres'
report=dict(status='INCOMPLETE',head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cases={},production_go=False,independent_acceptance=False,migration_installed=False)
def save(): (ROOT/'NATIVE_TRIAL.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
def admin(cur):actors.admin(cur)
def ordinary(cur):
 admin(cur)
 cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=base.OPERATOR_AUTH,role='authenticated')),))
 cur.execute('set local session authorization authenticated')
 assert cur.execute('select current_user,session_user').fetchone()==('authenticated','authenticated')

def call(cur,action,payload,key=None):
 ordinary(cur)
 value=cur.execute('select public.erp_save_initial_import_action_v1(%s,%s::jsonb,%s)',(action,json.dumps(payload,default=str),key or uuid.uuid4())).fetchone()[0]
 admin(cur);return value

def read(cur,batch=None):
 ordinary(cur);value=cur.execute('select public.erp_get_initial_import_workspace_v1(%s)',(batch,)).fetchone()[0];admin(cur);return value

def invoke(cur,action,batch,**extra):
 return call(cur,action,dict(batch_id=batch,expected_revision=read(cur,batch)['batch']['revision'],**extra))
def upload(cur,batch,entity,rows):return invoke(cur,'SAVE_FILE',batch,entity=entity,filename=entity+'.csv',rows=[dict(source_row_no=n+2,payload=r) for n,r in enumerate(rows)])

def valid(cur,today):
 batch=call(cur,'CREATE',dict(batch_code='AP-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=1))))['batch_id']
 code='AP-'+uuid.uuid4().hex[:14]
 upload(cur,batch,'CUSTOMER',[dict(customer_code=code,customer_name='AP ordinary owner')])
 rows=[dict(balance_type='CUSTOMER_RECEIVABLE',customer_code=code,amount='14.25',control_key='AR')]
 upload(cur,batch,'OPENING_BALANCE_ITEM',rows)
 upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='14.25')])
 return batch,code,rows

def lifecycle(cur,today):
 before=production.ledger(cur);batch,code,rows=valid(cur,today)
 assert production.ledger(cur)==before
 assert invoke(cur,'VALIDATE',batch)['error_rows']==0
 old=read(cur,batch)['batch']['revision']
 rows[0]['amount']='17.25';upload(cur,batch,'OPENING_BALANCE_ITEM',rows)
 assert invoke(cur,'FINALIZE',batch)['status']=='DRAFT'
 assert production.ledger(cur)==before
 assert any('amount:' in e for r in read(cur,batch)['batch']['rows'] for e in r['errors'])
 inherited.refused(cur,lambda:call(cur,'FINALIZE',dict(batch_id=batch,expected_revision=old)))
 upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='17.25')])
 assert invoke(cur,'VALIDATE',batch)['error_rows']==0
 payload=dict(batch_id=batch,expected_revision=read(cur,batch)['batch']['revision']);key=uuid.uuid4()
 result=call(cur,'FINALIZE',payload,key);assert result['status']=='POSTED',result
 boundary=actors.boundary(cur);assert call(cur,'FINALIZE',payload,key)==result and actors.boundary(cur)==boundary
 rows=cur.execute("select s.original_amount from erp.opening_subledger_balances s join erp.opening_balance_items i on i.id=s.opening_item_id join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s",(batch,)).fetchall()
 assert rows==[(inherited.Decimal('17.25'),)],rows
 assert cur.execute('select count(*) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s',(batch,)).fetchone()[0]==1
 inherited.refused(cur,lambda:invoke(cur,'SAVE_FILE',batch,entity='CUSTOMER',rows=[]))
 return dict(status='PASS',draft_ledger_inert=True,latest_value='17.25',control_not_posted=True,replay_identical=True)

def physical_stock(cur,today,roll=False):
 batch=call(cur,'CREATE',dict(batch_code='AP-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=1))))['batch_id']
 code='AP-'+uuid.uuid4().hex[:14]
 location=cur.execute("insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,'AP physical warehouse','RAW_MATERIAL_WAREHOUSE',true) returning location_code",(code,)).fetchone()[0]
 unit=cur.execute("select unit_code from erp.uom_definitions where dimension='LENGTH' and is_active and unit_code=upper(unit_code) order by unit_code limit 1").fetchone()[0] if roll else 'PCS'
 upload(cur,batch,'MATERIAL',[dict(material_sku=code,material_name='AP opening physical stock',material_type='FABRIC' if roll else 'OTHER',unit_code=unit)])
 if roll:
  upload(cur,batch,'MATERIAL_ROLL',[dict(material_sku=code,roll_number=code,opening_qty='7',unit_cost='2.25',location_code=location,control_key='STOCK')])
 else:
  upload(cur,batch,'OPENING_BALANCE_ITEM',[dict(balance_type='MATERIAL',material_sku=code,qty='7',unit_cost='2.25',location_code=location,control_key='STOCK')])
 upload(cur,batch,'OPENING_CONTROL',[dict(control_key='STOCK',balance_type='MATERIAL',qty='7',amount='15.75')])
 result=invoke(cur,'FINALIZE',batch)
 assert result['status']=='POSTED',read(cur,batch)
 values=cur.execute('select sum(s.qty_signed),sum(s.qty_signed*s.unit_cost_snapshot),count(*) from erp.material_stock_movements s join erp.materials m on m.id=s.material_id where m.material_sku=%s',(code,)).fetchone()
 assert values==(7,inherited.Decimal('15.75'),1),values
 return dict(status='PASS',qty='7',value='15.75',stock_movements=1,roll=roll)

def revision_zone(cur,today):
 batch,_,_=valid(cur,today)
 cur.execute("set local timezone='UTC'");a=read(cur,batch)['batch']['revision']
 cur.execute("set local timezone='Pacific/Kiritimati'");b=read(cur,batch)['batch']['revision']
 assert a==b,(a,b)
 return dict(status='PASS',same_revision_across_sessions=True)

def numeric_refusal(cur,today):
 batch,_,_=valid(cur,today)
 return dict(status='PASS',refusal=inherited.refused(cur,lambda:upload(cur,batch,'OPENING_BALANCE_ITEM',[dict(balance_type='CASH_BANK',amount='1.001',control_key='CASH')])) )

def control_refusal(cur,today,kind):
 batch,_,rows=valid(cur,today)
 if kind=='MISSING':upload(cur,batch,'OPENING_CONTROL',[])
 else:upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='14.25')]*2)
 before=production.ledger(cur);value=invoke(cur,'FINALIZE',batch)
 assert value['status']=='DRAFT' and value['error_rows']>0 and production.ledger(cur)==before,value
 return dict(status='PASS',errors=value['error_rows'],ledger_unchanged=True)

def authorization(cur,today):
 batch,_,_=valid(cur,today)
 admin(cur)
 # Preserve the real last-owner invariant while testing revocation of the
 # actor who created this draft; never disable the guard for a negative test.
 backup=uuid.uuid4()
 cur.execute("insert into auth.users(id,aud,role,email) values(%s,'authenticated','authenticated',%s)",(backup,'ap-backup-'+backup.hex+'@example.test'))
 cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) select gen_random_uuid(),%s,'AP backup owner','OWNER',id,true from erp.app_roles where role_code='OWNER'",(backup,))
 cur.execute("update erp.app_users set is_active=false where auth_user_id=%s",(base.OPERATOR_AUTH,))
 refused=inherited.refused(cur,lambda:read(cur,batch))
 return dict(status='PASS',revoked_owner_refused=refused)

def master_opening_family(cur,today):
 code='A'+uuid.uuid4().hex[:8]
 batch=call(cur,'CREATE',dict(batch_code='AP-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=1))))['batch_id']
 unit=cur.execute("select unit_code from erp.uom_definitions where dimension='LENGTH' and is_active and unit_code=upper(unit_code) order by unit_code limit 1").fetchone()[0]
 masters={
  'LAUNDRY_VENDOR':[dict(vendor_code=code,vendor_name='Imported laundry')],
  'LOCATION':[dict(location_code=code+'R',location_name='Imported raw warehouse',location_type='RAW_MATERIAL_WAREHOUSE'),dict(location_code=code+'F',location_name='Imported FG warehouse',location_type='FG_WAREHOUSE')],
  'CHART_ACCOUNT':[dict(account_code=code+'C',account_name='Cash child first',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT',parent_account_code=code+'P'),dict(account_code=code+'P',account_name='Parent after child',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT',is_postable='false')],
  'CASH_ACCOUNT':[dict(cash_account_code=code,cash_account_name='Imported bank',coa_account_code=code+'C',account_kind='BANK')],
  'BRAND':[dict(brand_code=code,brand_name='Imported brand')],
  'SIZE':[dict(size_code=code,sort_order='1')],
  'MODEL':[dict(model_code=code,model_name='Imported model')],
  'PRODUCT':[dict(sku=code,product_name='Imported FG',model_code=code,brand_code=code,color_name='Blue',size_code=code)],
  'CUSTOMER':[dict(customer_code=code,customer_name='Imported customer')],
  'SUPPLIER':[dict(supplier_code=code,supplier_name='Imported supplier',supplier_type='MATERIAL')],
  'CONTRACTOR':[dict(contractor_code=code,contractor_name='Imported contractor',contractor_type='MANDOR')],
  'ACCESSORY_CATEGORY':[dict(category_code=code,category_name='Imported buttons',base_uom_code='PCS')],
  'MATERIAL':[dict(material_sku=code+'A',material_name='Imported buttons',material_type='ACCESSORY',unit_code='PCS',accessory_category_code=code),dict(material_sku=code+'R',material_name='Imported fabric',material_type='FABRIC',unit_code=unit)],
 }
 tables=['laundry_vendors','locations','chart_accounts','cash_accounts','brands','sizes','product_models','products','customers','suppliers','contractors','accessory_categories','materials']
 counts=lambda:{t:cur.execute('select count(*) from erp.'+t).fetchone()[0] for t in tables}
 before_counts=counts();before_ledger=production.ledger(cur)
 # Upload children first as well as reversing account parent order.
 for entity,rows in reversed(list(masters.items())):upload(cur,batch,entity,rows)
 upload(cur,batch,'MATERIAL_ROLL',[dict(material_sku=code+'R',roll_number=code,opening_qty='7',unit_cost='2.25',location_code=code+'R',supplier_code=code,control_key='ROLL')])
 opening=[
  dict(balance_type='MATERIAL',material_sku=code+'A',location_code=code+'R',qty='5',unit_cost='2',control_key='ACCESSORY'),
  dict(balance_type='FINISHED_GOODS',product_sku=code,location_code=code+'F',qty='5',unit_cost='4',control_key='FG'),
  dict(balance_type='WIP',model_code=code,stage='SEWING',amount='6.25',control_key='WIP'),
  dict(balance_type='BS',product_sku=code,contractor_code=code,qty='2',control_key='BS'),
  dict(balance_type='CONTRACTOR_RECEIVABLE',contractor_code=code,amount='9.25',control_key='CAR'),
  dict(balance_type='CONTRACTOR_PAYABLE',contractor_code=code,amount='10.50',control_key='CAP'),
  dict(balance_type='CUSTOMER_RECEIVABLE',customer_code=code,amount='31.25',control_key='AR'),
  dict(balance_type='VENDOR_PAYABLE',vendor_code=code,amount='19.75',control_key='VAP'),
  dict(balance_type='SUPPLIER_PAYABLE',supplier_code=code,amount='41.75',control_key='SAP'),
  dict(balance_type='CASH_BANK',cash_account_code=code,amount='100.50',control_key='CASH'),
 ]
 controls=[dict(control_key='ROLL',balance_type='MATERIAL',qty='7',amount='15.75')]
 for r in opening:
  amount=r.get('amount',{'MATERIAL':'10','FINISHED_GOODS':'20','BS':'0'}.get(r['balance_type']))
  controls.append(dict(control_key=r['control_key'],balance_type=r['balance_type'],amount=amount,**({'qty':r['qty']} if 'qty' in r else {})))
 upload(cur,batch,'OPENING_BALANCE_ITEM',opening);upload(cur,batch,'OPENING_CONTROL',controls)
 upload(cur,batch,'OPEN_PO',[dict(po_number=code,model_code=code,contractor_code=code,target_qty_pcs='100',status='SEWING',current_stage='SEWING')])
 checked=invoke(cur,'VALIDATE',batch);assert checked['error_rows']==0,read(cur,batch)
 assert counts()==before_counts and production.ledger(cur)==before_ledger,'Preview created business records'
 posted=invoke(cur,'FINALIZE',batch);assert posted['status']=='POSTED',read(cur,batch)
 expected={t:(2 if t in('locations','chart_accounts','materials') else 1) for t in tables}
 assert {t:counts()[t]-before_counts[t] for t in tables}==expected
 assert cur.execute('select p.account_code from erp.chart_accounts a join erp.chart_accounts p on p.id=a.parent_account_id where a.account_code=%s',(code+'C',)).fetchone()==(code+'P',)
 assert cur.execute('select sum(l.debit-l.credit) from erp.journal_lines l join erp.chart_accounts a on a.id=l.account_id where a.account_code=%s',(code+'C',)).fetchone()==(inherited.Decimal('100.50'),)
 assert cur.execute('select count(*) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s',(batch,)).fetchone()==(11,)
 balances=cur.execute('select s.party_type,s.direction,s.original_amount from erp.opening_subledger_balances s join erp.opening_balance_items i on i.id=s.opening_item_id join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s order by 1,2',(batch,)).fetchall()
 assert balances==[('CONTRACTOR','PAYABLE',inherited.Decimal('10.50')),('CONTRACTOR','RECEIVABLE',inherited.Decimal('9.25')),('CUSTOMER','RECEIVABLE',inherited.Decimal('31.25')),('SUPPLIER','PAYABLE',inherited.Decimal('41.75')),('VENDOR','PAYABLE',inherited.Decimal('19.75'))],balances
 assert cur.execute('select cached_stock_qty from erp.materials where material_sku=%s',(code+'A',)).fetchone()==(5,)
 assert cur.execute('select sum(m.qty_signed) from erp.fg_stock_movements m join erp.products p on p.id=m.product_id where p.sku=%s',(code,)).fetchone()==(5,)
 assert cur.execute('select sum(b.qty_pcs) from erp.bs_cases b join erp.products p on p.id=b.product_id where p.sku=%s',(code,)).fetchone()==(2,)
 assert cur.execute('select target_qty_pcs from erp.production_orders where po_number=%s',(code,)).fetchone()==(100,)
 return dict(status='PASS',all_17_entities=True,preview_business_inert=True,opening_items=11,controls_not_posted=True,parent_order_independent=True,cash='100.50',party_balances=balances,physical_wip_claimed=False)

def master_refusal(cur,today,kind):
 code='A'+uuid.uuid4().hex[:8]
 batch=call(cur,'CREATE',dict(batch_code='AP-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=1))))['batch_id']
 chart=dict(account_code=code,account_name='Imported account',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')
 if kind in('CYCLE','MISSING_PARENT'):
  chart['parent_account_code']=code if kind=='CYCLE' else code+'MISSING';entity='CHART_ACCOUNT';rows=[chart];field='parent_account_code'
 elif kind=='ACCOUNT_SEMANTICS':
  existing=cur.execute('select a.account_code,a.account_name,a.report_group,a.normal_balance,a.is_postable,a.is_active,p.account_code,a.account_type from erp.chart_accounts a left join erp.chart_accounts p on p.id=a.parent_account_id order by a.account_code limit 1').fetchone()
  chart=dict(account_code=existing[0],account_name=existing[1],account_type='LIABILITY' if existing[7]=='ASSET' else 'ASSET',report_group=existing[2],normal_balance=existing[3],is_postable=str(existing[4]).lower(),is_active=str(existing[5]).lower(),parent_account_code=existing[6] or '')
  entity='CHART_ACCOUNT';rows=[chart];field='account_code'
 elif kind=='CASH_NON_ASSET':
  chart['account_type']='LIABILITY';upload(cur,batch,'CHART_ACCOUNT',[chart]);entity='CASH_ACCOUNT';rows=[dict(cash_account_code=code,cash_account_name='Bad bank',coa_account_code=code,account_kind='BANK')];field='coa_account_code'
 elif kind=='BAD_LOCATION':entity='LOCATION';rows=[dict(location_code=code,location_name='Bad location',location_type='UNKNOWN')];field='location_type'
 elif kind=='DUPLICATE_VENDOR':entity='LAUNDRY_VENDOR';rows=[dict(vendor_code=code,vendor_name='Duplicated laundry')]*2;field='Duplicate'
 else:raise AssertionError(kind)
 upload(cur,batch,entity,rows);before=production.ledger(cur)
 result=invoke(cur,'FINALIZE',batch);assert result['status']=='DRAFT' and result['error_rows']>0,read(cur,batch)
 assert production.ledger(cur)==before
 errors=[e for r in read(cur,batch)['batch']['rows'] for e in r['errors']]
 assert any(field in e for e in errors),errors
 return dict(status='PASS',refused_field=field,ledger_unchanged=True)

def financial_batch(cur,today,code=None,document=True,rows=None,balance_type='CUSTOMER_RECEIVABLE'):
 code=code or 'D'+uuid.uuid4().hex[:10]
 batch=call(cur,'CREATE',dict(batch_code='AP-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=1))))['batch_id']
 entity,code_field,name_field=({'CUSTOMER_RECEIVABLE':('CUSTOMER','customer_code','customer_name'),
  'SUPPLIER_PAYABLE':('SUPPLIER','supplier_code','supplier_name'),'VENDOR_PAYABLE':('LAUNDRY_VENDOR','vendor_code','vendor_name'),
  'CONTRACTOR_RECEIVABLE':('CONTRACTOR','contractor_code','contractor_name'),'CONTRACTOR_PAYABLE':('CONTRACTOR','contractor_code','contractor_name')})[balance_type]
 upload(cur,batch,entity,[{code_field:code,name_field:'Imported open invoice'}])
 row=dict(balance_type=balance_type,amount='67.25',control_key='AR',**{code_field:code})
 if document:row.update(document_number='INV-'+code,document_date=str(today-timedelta(days=45)),due_date=str(today-timedelta(days=15)),original_amount='100.00',settled_before_cutover='32.75')
 rows=rows or [row]
 upload(cur,batch,'OPENING_BALANCE_ITEM',rows)
 upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type=balance_type,amount=str(sum(inherited.Decimal(r['amount']) for r in rows)))])
 return batch,code,row

def partial_invoice_settlement(cur,today,balance_type):
 batch,code,row=financial_batch(cur,today,balance_type=balance_type)
 upload(cur,batch,'CHART_ACCOUNT',[dict(account_code=code,account_name='Payment bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')])
 upload(cur,batch,'CASH_ACCOUNT',[dict(cash_account_code=code,cash_account_name='Payment bank',coa_account_code=code,account_kind='BANK')])
 upload(cur,batch,'OPENING_BALANCE_ITEM',[row,dict(balance_type='CASH_BANK',cash_account_code=code,amount='100.00',control_key='CASH')])
 upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type=balance_type,amount='67.25'),dict(control_key='CASH',balance_type='CASH_BANK',amount='100.00')])
 payment_counts=lambda:tuple(cur.execute('select count(*) from erp.'+t).fetchone()[0] for t in ('sales_payments','supplier_payments','vendor_payments'))
 before_counts=payment_counts();before_ledger=production.ledger(cur)
 def truth():
  names=['V2620M_OPENING_SUBLEDGER_STATE','V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','V2620M_ORPHAN_PAYMENT_JOURNAL','V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE']
  checks=cur.execute('select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name=any(%s) order by check_name',(names,)).fetchall()
  assert {r[0] for r in checks}==set(names) and all(r[1]==0 for r in checks),checks
 truth()
 checked=invoke(cur,'VALIDATE',batch);assert checked['error_rows']==0,read(cur,batch)
 assert production.ledger(cur)==before_ledger
 assert cur.execute('select count(*) from erp.initial_import_financial_sources where batch_id=%s',(batch,)).fetchone()==(0,)
 assert invoke(cur,'FINALIZE',batch)['status']=='POSTED',read(cur,batch)
 truth()
 assert payment_counts()==before_counts,'Imported historic payment was incorrectly posted as new cash'
 source=cur.execute('select s.original_amount,s.settled_before_cutover,s.outstanding_amount,b.original_amount,b.settled_amount,b.id from erp.initial_import_financial_sources s join erp.opening_subledger_balances b on b.opening_item_id=s.opening_item_id where s.batch_id=%s',(batch,)).fetchone()
 assert source[:5]==(inherited.Decimal('100'),inherited.Decimal('32.75'),inherited.Decimal('67.25'),inherited.Decimal('67.25'),0),source
 cash=cur.execute('select id from erp.cash_accounts where cash_account_code=%s',(code,)).fetchone()[0]
 cash_balance=lambda:cur.execute('select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.chart_accounts a on a.id=l.account_id where a.account_code=%s',(code,)).fetchone()[0]
 assert cash_balance()==100,'Pre-cutover settlement must not change imported cash balance'
 settlement=cur.execute("insert into erp.opening_subledger_settlements(settlement_number,balance_id,amount,cash_account_id,physical_at,status,created_by) values(%s,%s,7.25,%s,%s,'DRAFT',erp.current_app_user_id()) returning id",('DOC-'+uuid.uuid4().hex,source[5],cash,production.at(today-timedelta(days=1),18))).fetchone()[0]
 cur.execute('select erp.post_opening_subledger_settlement(%s)',(settlement,))
 truth()
 assert cur.execute('select original_amount-settled_amount from erp.opening_subledger_balances where id=%s',(source[5],)).fetchone()==(inherited.Decimal('60.00'),)
 assert cash_balance()==(inherited.Decimal('107.25') if balance_type.endswith('RECEIVABLE') else inherited.Decimal('92.75'))
 cur.execute('select erp.reverse_opening_subledger_settlement(%s,%s)',(settlement,'Native document settlement reversal'))
 truth()
 assert cur.execute('select original_amount-settled_amount from erp.opening_subledger_balances where id=%s',(source[5],)).fetchone()==(inherited.Decimal('67.25'),)
 assert cash_balance()==100
 return dict(status='PASS',balance_type=balance_type,original='100.00',paid_before_cutover='32.75',posted_outstanding='67.25',no_historic_cash_posting=True,later_payment_remaining='60.00',reversal_restores='67.25',financial_truth_checks_zero=True)

def distinct_documents(cur,today):
 first,code,_=financial_batch(cur,today);assert invoke(cur,'FINALIZE',first)['status']=='POSTED',read(cur,first)
 second,_,row=financial_batch(cur,today,code);row['document_number']+='-SECOND';upload(cur,second,'OPENING_BALANCE_ITEM',[row])
 assert invoke(cur,'FINALIZE',second)['status']=='POSTED',read(cur,second)
 value=cur.execute('select count(*),sum(b.original_amount-b.settled_amount) from erp.opening_subledger_balances b join erp.customers c on c.id=b.customer_id where c.customer_code=%s',(code,)).fetchone()
 assert value==(2,inherited.Decimal('134.50')),value
 return dict(status='PASS',distinct_documents=2,same_party=True,total='134.50')

def document_refusal(cur,today,kind):
 batch,code,row=financial_batch(cur,today)
 if kind in('CROSS_BATCH_DUPLICATE','CROSS_BATCH_SUMMARY'):
  assert invoke(cur,'FINALIZE',batch)['status']=='POSTED',read(cur,batch)
  batch,_,row=financial_batch(cur,today,code,document=kind=='CROSS_BATCH_DUPLICATE')
  if kind=='CROSS_BATCH_DUPLICATE':
   row['document_number']=row['document_number'].lower();upload(cur,batch,'OPENING_BALANCE_ITEM',[row])
 elif kind=='SUMMARY_THEN_DOCUMENT':
  summary={k:v for k,v in row.items() if k not in('document_number','document_date','due_date','original_amount','settled_before_cutover')}
  upload(cur,batch,'OPENING_BALANCE_ITEM',[summary]);assert invoke(cur,'FINALIZE',batch)['status']=='POSTED',read(cur,batch)
  batch,_,row=financial_batch(cur,today,code)
 elif kind=='MIXED_SUMMARY':
  summary={k:v for k,v in row.items() if k not in('document_number','document_date','due_date','original_amount','settled_before_cutover')}
  upload(cur,batch,'OPENING_BALANCE_ITEM',[row,summary]);upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='134.50')])
 elif kind=='DUPLICATE_WITHIN':
  upload(cur,batch,'OPENING_BALANCE_ITEM',[row,row]);upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='134.50')])
 elif kind=='WRONG_REMAINDER':row['settled_before_cutover']='33.75';upload(cur,batch,'OPENING_BALANCE_ITEM',[row])
 elif kind=='FUTURE_DOCUMENT':row['document_date']=str(today);upload(cur,batch,'OPENING_BALANCE_ITEM',[row])
 else:raise AssertionError(kind)
 before=production.ledger(cur);count=cur.execute('select count(*) from erp.initial_import_financial_sources').fetchone()[0]
 result=invoke(cur,'FINALIZE',batch);assert result['status']=='DRAFT' and result['error_rows']>0,read(cur,batch)
 assert production.ledger(cur)==before and cur.execute('select count(*) from erp.initial_import_financial_sources').fetchone()[0]==count
 errors=[e for r in read(cur,batch)['batch']['rows'] if r['entity']=='OPENING_BALANCE_ITEM' for e in r['errors']]
 assert any(('amount:' if kind=='WRONG_REMAINDER' else 'document_date:' if kind=='FUTURE_DOCUMENT' else 'document_number:') in e for e in errors),errors
 return dict(status='PASS',refusal=kind,ledger_unchanged=True,source_registry_unchanged=True)

save()
try:
 with psycopg.connect(URL) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='120s';set local lock_timeout='8s'")
  assert len(runtime.verified_successor(cur))==692
  baseline=actors.boundary(cur);catalog=function_catalog(cur)
  # Persist schema diagnostics from genuine disposable Supabase, no user data.
  (ROOT/'TABLE_COLUMNS.json').write_text(json.dumps(cur.execute("select table_name,column_name,data_type,column_default,is_nullable from information_schema.columns where table_schema='erp' order by table_name,ordinal_position").fetchall(),indent=2,default=str)+'\n')
  for identity,definition,acl,owner in PREDECESSOR:
   found=cur.execute('select pg_get_functiondef(p.oid),p.proacl::text,pg_get_userbyid(p.proowner) from pg_proc p where p.oid=to_regprocedure(%s)',(identity,)).fetchone()
   assert found==(definition,acl,owner),identity
  cur.execute('set local role postgres')
  cur.execute(SCHEMA,prepare=False)
  for identity,definition in FUNCTIONS.items():
   cur.execute(definition,prepare=False)
   if identity not in {r[0] for r in PREDECESSOR}:
    cur.execute(f'revoke all on function {identity} from public,anon,authenticated,service_role')
    if identity.startswith('public.'):cur.execute(f'grant execute on function {identity} to authenticated,service_role')
  admin(cur)
  installed=function_catalog(cur)
  public=cur.execute("select 'public.'||p.oid::regprocedure::text,pg_get_functiondef(p.oid),p.proacl::text,pg_get_userbyid(p.proowner) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname in('erp_get_initial_import_workspace_v1','erp_save_initial_import_action_v1') order by 1").fetchall()
  (ROOT/'INSTALLED_FUNCTIONS.json').write_text(json.dumps(dict(functions=[r for r in installed if r[0] in FUNCTIONS]+public),indent=2)+'\n')
  # The inherited seed includes historical native calls: temporary USAGE is
  # fixture-only and rolled back. Neither public RPC requires this grant.
  cur.execute('grant usage on schema erp to authenticated')
  actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'));base.load_fixture_foundation(cur);admin(cur)
  cur.execute('revoke usage on schema erp from authenticated')
  today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
  cases=[('REVISION_TIMEZONE',lambda:revision_zone(cur,today)),('PHYSICAL_MATERIAL',lambda:physical_stock(cur,today)),('PHYSICAL_ROLL',lambda:physical_stock(cur,today,True)),('LATEST_DRAFT_TOTALS_REPLAY',lambda:lifecycle(cur,today)),('EXCESS_PRECISION',lambda:numeric_refusal(cur,today)),('MISSING_CONTROL',lambda:control_refusal(cur,today,'MISSING')),('DUPLICATE_CONTROL',lambda:control_refusal(cur,today,'DUPLICATE')),('REVOKED_OWNER',lambda:authorization(cur,today))]
  cases += [('MASTER_OPENING_FAMILY',lambda:master_opening_family(cur,today))]
  cases += [('MASTER_REFUSAL:'+k,lambda k=k:master_refusal(cur,today,k)) for k in ('CYCLE','MISSING_PARENT','ACCOUNT_SEMANTICS','CASH_NON_ASSET','BAD_LOCATION','DUPLICATE_VENDOR')]
  cases += [('PARTLY_PAID_DOCUMENT:'+t,lambda t=t:partial_invoice_settlement(cur,today,t)) for t in ('CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE')]
  cases += [('DISTINCT_DOCUMENTS_SAME_PARTY',lambda:distinct_documents(cur,today))]
  cases += [('DOCUMENT_REFUSAL:'+k,lambda k=k:document_refusal(cur,today,k)) for k in ('CROSS_BATCH_DUPLICATE','CROSS_BATCH_SUMMARY','SUMMARY_THEN_DOCUMENT','MIXED_SUMMARY','DUPLICATE_WITHIN','WRONG_REMAINDER','FUTURE_DOCUMENT')]
  for name,fn in cases:
   admin(cur);before=actors.boundary(cur);cur.execute('savepoint proposed_case')
   try:result=fn()
   except Exception as exc:result=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint proposed_case');admin(cur);cur.execute('release savepoint proposed_case')
   result['boundary_restored']=actors.boundary(cur)==before
   if not result['boundary_restored']:result['status']='INCOMPLETE'
   report['cases'][name]=result;save();print(json.dumps(dict(case=name,**result),default=str),flush=True)
  assert function_catalog(cur)==installed
  conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
  assert actors.boundary(cur)==baseline and function_catalog(cur)==catalog
  report['complete_boundary_restored']=True
  report['status']='WRITER_TRIAL_PASS' if all(r['status']=='PASS' for r in report['cases'].values()) else 'INCOMPLETE'
except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
save();print(json.dumps({k:v for k,v in report.items() if k!='cases'},default=str))
raise SystemExit(0 if report['status']=='WRITER_TRIAL_PASS' else 1)
