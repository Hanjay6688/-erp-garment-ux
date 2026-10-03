"""Predeclared source navigation controls on actual Native writers.

No stock or journal outcome is seeded. Read-only resolver checks are counted
separately from the two retained combined-stack write/revoke schedules.
"""
import json,uuid
import cp7_material_cases as material
import cp7_material_count_cases as count
import cp7_fg_adjustment_cases as fg
import cp7_invoice_cases as invoice
import cp7_sales_payment_cases as payment
import cp7_sales_return_cases as returned
import cp7_note_correction_cases as note
import cp7_misc_cases as misc
import cp7_installment_cases as installment
import cp7_f03_e24_issue_cases as accessory
import cp6_bf_combined_probe as production
import cp7_f03_cases as combined
import cp7_transaction_source_bundle as bundle
b,auth=material.b,material.auth
REQUIRED=dict(native=24,races=2,http=5,browser=8)
EXPECTED=sum(REQUIRED.values())
RPC='erp_cp7_resolve_transaction_source_v1'

def accessory_fixture(cur,today):
 f=accessory.fixture(cur,today);f['before']=accessory.observe(cur,f)
 f['issue']=accessory.bc.note_call(cur,'POST',accessory.payload(f))
 f['issue_item']=str(cur.execute('select id from erp.contractor_material_issue_items where issue_id=%s',(f['issue']['id'],)).fetchone()[0])
 f['journals']=[dict(id=str(i),source_type=kind,number=number)for i,kind,number in cur.execute("select id,source_type,journal_number from erp.journal_entries where source_id=%s and source_type in('CONTRACTOR_ACCESSORY_STOCK_COST','CONTRACTOR_MATERIAL_RECEIVABLE')and status='POSTED'order by source_type,id",(f['issue']['id'],)).fetchall()]
 assert {j['source_type']for j in f['journals']}=={'CONTRACTOR_ACCESSORY_STOCK_COST','CONTRACTOR_MATERIAL_RECEIVABLE'}
 return f

def rework_fixture(cur,today,history=False):
 # The qualified ordinary rework worksheet is two new components at30,
 # two actual repaired FG pieces. No BS/stock/journal result is seeded.
 f=production.fixture(cur,today);wash=production.wash(cur,f,range(4),11)
 production.finish(cur,f,[wash],range(4),13,bs={3:2});chain=production.b.chain
 bs=production.one(cur,"select id::text from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",f['po'],f['roots'][3])
 chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=production.prod.COMPONENT,completed_before_bs_qty=0)],change_reason='Source rework components were not earned before BS'),chain.version(cur,'bs_cases',bs))
 component=production.one(cur,'select id::text from erp.bs_case_components where bs_case_id=%s and work_component_id=%s',bs,production.prod.COMPONENT)
 bom=production.one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)::text',bs,f['when'](15))
 number='CP7-SRC-RW-'+uuid.uuid4().hex[:10]
 made=chain.bs_action(cur,'SAVE_REWORK',dict(rework_number=number,bs_case_id=bs,destination_type='CONTRACTOR',contractor_id=production.prod.CONTRACTOR,vendor_id=None,qty_sent=2,physical_sent_at=f['when'](15).isoformat(),status='IN_PROGRESS',return_fg_location_id=production.base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],change_reason='Actual source repair of two pieces',components=[dict(bs_case_component_id=component,qty_performed=2)]))
 rid=made['result']['rework_order_id']
 chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=2,qty_bs=0,completed_at=f['when'](16).isoformat(),return_fg_location_id=production.base.LOCATION,change_reason='Two repaired source pieces physically returned'),chain.version(cur,'rework_orders',rid))
 b.api.admin(cur)
 order=cur.execute('select to_jsonb(r)from erp.rework_orders r where id=%s',(rid,)).fetchone()[0]
 journal=cur.execute("select id,journal_number,transaction_date from erp.journal_entries where source_type='REWORK_COMPLETION'and source_id=%s and status='POSTED'",(rid,)).fetchone();assert journal
 labor=cur.execute('select sum(amount_payable)from erp.rework_component_lines where rework_order_id=%s',(rid,)).fetchone()[0];assert labor==60
 movement=cur.execute("select id,qty_signed,physical_at from erp.fg_stock_movements where source_type='REWORK_ORDER'and source_id=%s and movement_type='REWORK_IN'",(rid,)).fetchone();assert movement and movement[1]==2
 if history:
  for i in range(51):
   chain.bs_action(cur,'CREATE_MANUAL_BS',dict(untracked_type='LEGACY',legacy_reference=number+'-BOOK-'+str(i),qty_pcs=1,physical_at=f['when'](12).isoformat(),change_reason='Actual older manual BS cases for page boundary'))
 return dict(bs=bs,rework=rid,number=number,order=order,lot=order['good_fg_lot_id'],journal=dict(id=str(journal[0]),number=journal[1],date=str(journal[2])),movement=dict(id=str(movement[0]),qty=str(movement[1]),physical_at=movement[2].isoformat()),labor='60.00',history=history)

def rework_workspace(cur,f,offset=None,subject=None):
 d=read(cur,'REWORK_ORDER',f['rework'],subject)['document'];assert d['id']==f['bs']and d['focus']['id']==f['rework']
 auth.actor(cur,subject)
 r=cur.execute("select public.erp_get_bs_resolution_workspace_v1('ALL','BS',null,null,50,%s)",(d['focus']['page_offset']if offset is None else offset,)).fetchone()[0]
 b.api.admin(cur);return r

def rework_state(cur,f):
 b.api.admin(cur)
 order=cur.execute('select to_jsonb(r)from erp.rework_orders r where id=%s',(f['rework'],)).fetchone()[0]
 return dict(order=order,lot_qty=str(cur.execute('select coalesce(sum(qty_signed),0)from erp.fg_stock_movements where lot_id=%s',(f['lot'],)).fetchone()[0]),
  original_movement=cur.execute('select to_jsonb(m)from erp.fg_stock_movements m where id=%s',(f['movement']['id'],)).fetchone()[0],
  inverses=[dict(id=str(i),number=n,original_id=str(original))for i,n,original in cur.execute('select id,journal_number,reversal_of_id from erp.journal_entries where reversal_of_id=%s',(f['journal']['id'],)).fetchall()],business=b.boundary.snapshot(cur))

def read(cur,kind,ident,subject=None):
 auth.actor(cur,subject)
 out=cur.execute('select public.erp_cp7_resolve_transaction_source_v1(%s)',(json.dumps(dict(source_type=kind,source_id=str(ident))),)).fetchone()[0]
 b.api.admin(cur);return out

def exact(cur,kind,ident,domain,parent,focus=None,subject=None):
 before=b.boundary.snapshot(cur);r=read(cur,kind,ident,subject)
 assert r['contract_version']=='cp7.transaction-source.v1'and r['source']==dict(source_type=kind,source_id=str(ident))and r['status']=='AVAILABLE'and r['business_DML']is False
 assert set(r)=={'contract_version','actor_scope_id','source','status','document','read_at','business_DML'}
 d=r['document'];assert set(d)=={'domain','route','id','number','status','revision','focus'}
 assert d['domain']==domain and d['id']==str(parent)and d['number']
 if focus:assert d['focus']['kind']==focus[0]and d['focus']['id']==str(focus[1])
 else:assert d['focus']is None
 assert b.boundary.snapshot(cur)==before,'SOURCE_NAVIGATION_BUSINESS_DML'
 return d

def cases(cur,today):
 def receipts():
  f=material.fixture(cur,today);parent=f['receipt']['purchase_id'];item=cur.execute('select purchase_item_id from erp.material_rolls where id=%s',(f['roll'],)).fetchone()[0]
  for kind,ident in [('MATERIAL_PURCHASE',parent),('MATERIAL_PURCHASE_ITEM',item),('MATERIAL_PURCHASE_ROLL',f['roll'])]:exact(cur,kind,ident,'RECEIPT',parent)
  return dict(status='PASS',actual_receipt_item_roll_same_owning_header_read_only=True)
 def invoices():
  f=invoice.fixture(cur,today);r=invoice.finalize(cur,f);ident=r['invoice_id'];line=cur.execute('select id from erp.material_supplier_invoice_lines where invoice_id=%s',(ident,)).fetchone()[0]
  for kind,i in [('MATERIAL_SUPPLIER_INVOICE',ident),('MATERIAL_SUPPLIER_INVOICE_LINE',line)]:
   d=exact(cur,kind,i,'RECEIPT',f['receipt']['purchase_id'],('PURCHASE_INVOICE',ident));assert d['focus']['page_offset']==0
  return dict(status='PASS',actual_invoice_line_FK_not_assumed_header_purchase_id=True)
 def transfers():
  f=material.fixture(cur,today);draft,_=material.draft(cur,f);post=material.post(cur,draft);ident=post['transfer_id'];item=cur.execute('select id from erp.material_transfer_items where transfer_id=%s',(ident,)).fetchone()[0]
  for kind,i in [('MATERIAL_TRANSFER',ident),('MATERIAL_TRANSFER_ITEM',item)]:exact(cur,kind,i,'MATERIAL_TRANSFER',ident)
  material.reverse(cur,post);assert exact(cur,'MATERIAL_TRANSFER',ident,'MATERIAL_TRANSFER',ident)['status']=='REVERSED'
  return dict(status='PASS',actual_transfer_parent_and_inverse_history_exact=True)
 def counts():
  f=material.fixture(cur,today);draft,_=count.draft(cur,f);post=count.action(cur,'POST',draft);ident=post['adjustment_id'];item=cur.execute('select id from erp.material_adjustment_items where adjustment_id=%s',(ident,)).fetchone()[0]
  exact(cur,'MATERIAL_ADJUSTMENT_ITEM',item,'MATERIAL_COUNT',ident);count.action(cur,'REVERSE',post);exact(cur,'MATERIAL_ADJUSTMENT',ident,'MATERIAL_COUNT',ident)
  return dict(status='PASS',actual_material_count_owner_not_ledger_inverse=True)
 def finished():
  f=fg.fg.fixture(cur,today);draft,_=fg.draft(cur,f);post=fg.action(cur,'POST',draft);ident=post['adjustment_id'];item=cur.execute('select id from erp.fg_adjustment_items where adjustment_id=%s',(ident,)).fetchone()[0]
  exact(cur,'FG_ADJUSTMENT_ITEM',item,'FG_ADJUSTMENT',ident);fg.action(cur,'REVERSE',post);exact(cur,'FG_ADJUSTMENT',ident,'FG_ADJUSTMENT',ident)
  return dict(status='PASS',actual_finished_adjustment_item_parent_and_inverse=True)
 def sales():
  f=note.stock(cur,today,120);note.posted(cur,f,'36');old=f['sale'];item=cur.execute('select id from erp.sales_items where sale_id=%s',(old,)).fetchone()[0]
  exact(cur,'SALE_ITEM',item,'SALE',old);p,v=note.edit(cur,f,'24');replacement=note.correct(cur,p,v)
  assert exact(cur,'SALE_ITEM',item,'SALE',old)['status']=='REVERSED'
  exact(cur,'SALE',replacement['sale_id'],'SALE',replacement['sale_id'])
  return dict(status='PASS',owning_atomic_note_correction_preserves_original_navigation_and_replacement=True)
 def payments():
  f=payment.fixture(cur,today);old=payment.pay(cur,f,'1')
  for _ in range(25):payment.pay(cur,f,'1')
  d=exact(cur,'SALES_PAYMENT',old['payment_id'],'SALE',f['sale'],('SALES_PAYMENT',old['payment_id']));assert d['focus']['page_offset']==25
  page=payment.cash(cur,f,payment_offset=25,payment_limit=25);assert any(x['id']==old['payment_id']for x in page['payments']['rows'])
  return dict(status='PASS',actual26_payments_old_exact_source_on_second_owning_page=True)
 def returns():
  f=returned.fixture(cur,today);r=returned.returned(cur,f);ident=r['return_id'];item=cur.execute('select id from erp.sales_return_items where return_id=%s',(ident,)).fetchone()[0]
  for kind,i in [('SALES_RETURN',ident),('SALES_RETURN_ITEM',item)]:exact(cur,kind,i,'SALE',f['sale'],('SALES_RETURN',ident))
  returned.inverse(cur,f,ident);exact(cur,'SALES_RETURN',ident,'SALE',f['sale'],('SALES_RETURN',ident))
  return dict(status='PASS',actual_return_child_and_retained_inverse_source=True)
 def journals():
  f=misc.fixture(cur,today);saved=misc.command(cur,'SAVE',misc.save_payload(f));posted=misc.command(cur,'POST',misc.intent(saved));ident=posted['transaction_id'];original=cur.execute("select id from erp.journal_entries where source_type='MISC_FINANCE'and source_id=%s",(ident,)).fetchone()[0]
  exact(cur,'MISC_FINANCE',ident,'MISC_FINANCE',ident);misc.command(cur,'REVERSE',misc.intent(posted));inverse=cur.execute('select source_type,source_id from erp.journal_entries where reversal_of_id=%s',(original,)).fetchone();assert inverse
  exact(cur,inverse[0],inverse[1],'MISC_FINANCE',ident)
  return dict(status='PASS',actual_inverse_journal_link_follows_immutable_parent_not_guessed_UUID=True)
 def payroll_headers():
  f=installment.fixture(cur,today);pid=f['payroll'];before=installment.read(cur,pid)['document']
  original=cur.execute("select id from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL'and source_id=%s and status='POSTED'",(pid,)).fetchone()[0]
  d=exact(cur,'PAYROLL_ATTENDANCE_ACCRUAL',pid,'PAYROLL',pid);assert d['route']=='finance-payroll'and d['revision']==before['row_version']
  installment.legacy.act(cur,'PAY',installment.legacy.doc(cur,pid),payment_date=f['payment_date'],cash_account_id=f['cash']['id'])
  d=exact(cur,'PAYROLL_PAYMENT',pid,'PAYROLL',pid);assert d['status']=='PAID'
  installment.legacy.act(cur,'REVERSE',installment.legacy.doc(cur,pid))
  inverse=cur.execute('select source_type,source_id from erp.journal_entries where reversal_of_id=%s',(original,)).fetchone();assert inverse
  d=exact(cur,inverse[0],inverse[1],'PAYROLL',pid);assert d['status']=='REVERSED'
  assert installment.physical.stock_cost(cur)==f['physical']
  return dict(status='PASS',actual_accrual_legacy_payment_and_immutable_inverse_same_payroll=True,Native_owning_reader_version_no_money_or_write=True)
 def payroll_payments():
  f=installment.fixture(cur,today);payments=[installment.act(cur,f,amount='10.00')['payment_id']for _ in range(26)];target=payments[-1]
  d=exact(cur,'PAYROLL_INSTALLMENT',target,'PAYROLL',f['payroll'],('PAYROLL_INSTALLMENT',target));assert d['route']=='finance-payroll'and d['focus']['page_offset']==25
  page=installment.read(cur,f['payroll'],payment_offset=25);assert [p['id']for p in page['payments']['rows']]==[target]
  assert(page['document']['paid_amount'],page['document']['remaining_amount'])==('260.00','740.00')
  installment.act(cur,f,'REVERSE_PAYMENT',payment=target)
  d=exact(cur,'PAYROLL_INSTALLMENT',target,'PAYROLL',f['payroll'],('PAYROLL_INSTALLMENT',target));assert d['focus']['page_offset']==25
  inverse=cur.execute('select j.source_type,j.source_id from cp7_installment.payments p join erp.journal_entries j on j.id=p.reversal_journal_id where p.id=%s',(target,)).fetchone()
  exact(cur,inverse[0],inverse[1],'PAYROLL',f['payroll'],('PAYROLL_INSTALLMENT',target))
  page=installment.read(cur,f['payroll'],payment_offset=25);assert(page['document']['paid_amount'],page['document']['remaining_amount'],page['payments']['rows'][0]['status'])==('250.00','750.00','REVERSED')
  assert installment.physical.stock_cost(cur)==f['physical']
  return dict(status='PASS',actual26_installments_exact_second_page_matches_existing_Native_order=True,inverse_keeps_original_child_date_page_and_link=True,approved_cost_and_stock_HPP_unchanged=True)
 def payroll_authority():
  f=installment.fixture(cur,today);payment=installment.act(cur,f,amount='10.00')['payment_id'];subject,role=auth.custom_actor(cur)
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.payroll.pay')",(role,))
  auth.refused(cur,lambda:read(cur,'PAYROLL_INSTALLMENT',payment,subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.payroll.view')",(role,))
  exact(cur,'PAYROLL_INSTALLMENT',payment,'PAYROLL',f['payroll'],('PAYROLL_INSTALLMENT',payment),subject=subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.view'",(role,))
  auth.refused(cur,lambda:read(cur,'PAYROLL_INSTALLMENT',payment,subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  assert not cur.execute("select has_table_privilege(%s,'cp7_installment.payments','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')or has_function_privilege(%s,'cp7_installment.command(text,jsonb,uuid,text)','EXECUTE')",(bundle.ROLE,bundle.ROLE)).fetchone()[0]
  return dict(status='PASS',current_custom_role_view_required_before_private_child_resolution=True,pay_permission_does_not_imply_view=True,no_payment_writer_or_DML_grant=True)
 def payroll_unavailable():
  missing=str(uuid.uuid4());before=b.boundary.snapshot(cur)
  for kind in('PAYROLL_INSTALLMENT','PAYROLL_ATTENDANCE_ACCRUAL','PAYROLL_PAYMENT'):auth.refused(cur,lambda:read(cur,kind,missing),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  unsupported=read(cur,'PAYROLL_INVENTED_SOURCE',missing);assert unsupported['status']=='UNSUPPORTED_SOURCE'and unsupported['document']is None
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',missing_payroll_or_child_refused_and_unregistered_payroll_kind_not_guessed=True,no_placeholder_payment_or_business_DML=True)
 def accessory_documents():
  f=accessory_fixture(cur,today);ident=f['issue']['id'];posted=accessory.assert_posted(cur,f,f['before'])
  d=exact(cur,'CONTRACTOR_MATERIAL_ISSUE_ITEM',f['issue_item'],'ACCESSORY_ISSUE',ident);assert d['route']=='contractor-issue'and d['revision']==f['issue']['row_version']
  for j in f['journals']:exact(cur,j['source_type'],ident,'ACCESSORY_ISSUE',ident)
  accessory.bc.note_call(cur,'REVERSE',dict(id=ident,expected_version=f['issue']['row_version'],reason='Inverse exact source accessory note'))
  restored=accessory.observe(cur,f);assert restored['stock']==f['before']['stock']and restored['accounts']==f['before']['accounts']and restored['source']==f['before']['source']
  for j in f['journals']:
   inverse=cur.execute('select source_type,source_id from erp.journal_entries where reversal_of_id=%s',(j['id'],)).fetchone();assert inverse
   assert exact(cur,inverse[0],inverse[1],'ACCESSORY_ISSUE',ident)['status']=='REVERSED'
  assert exact(cur,'CONTRACTOR_MATERIAL_ISSUE_ITEM',f['issue_item'],'ACCESSORY_ISSUE',ident)['status']=='REVERSED'
  return dict(status='PASS',actual_stock_item_and_cost_receivable_journals_same_Native_note=True,owning_Native_inverse_restores_stock_every_account_and_retains_original_child=True)
 def accessory_history():
  f=accessory_fixture(cur,today);ident=f['issue']['id']
  for i in range(51):
   p=accessory.payload(f);p.update(number=f['issue_number']+'-NEW-'+str(i),physical_at=accessory.bc.local_at(today,11))
   accessory.bc.note_call(cur,'SAVE_DRAFT',p)
  before=b.boundary.snapshot(cur);w=accessory.bc.note_read(cur,dict(id=ident,query=f['code']))
  assert len(w['history'])==50 and w['history_count']>=52 and ident not in[x['id']for x in w['history']]
  assert w['document']['id']==ident and w['document']['status']=='POSTED'and w['document']['row_version']==f['issue']['row_version']
  exact(cur,'CONTRACTOR_MATERIAL_ISSUE_ITEM',f['issue_item'],'ACCESSORY_ISSUE',ident)
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual52_Native_notes_original_outside_history50_opens_by_exact_id=True,no_client_scan_placeholder_or_write=True)
 def accessory_authority():
  f=accessory_fixture(cur,today);subject,role=auth.custom_actor(cur)
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.contractor_accessory.reverse')",(role,))
  auth.refused(cur,lambda:read(cur,'CONTRACTOR_MATERIAL_ISSUE_ITEM',f['issue_item'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.contractor_accessory.view')",(role,))
  exact(cur,'CONTRACTOR_MATERIAL_ISSUE_ITEM',f['issue_item'],'ACCESSORY_ISSUE',f['issue']['id'],subject=subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.contractor_accessory.view'",(role,))
  for kind,ident in [('CONTRACTOR_MATERIAL_ISSUE_ITEM',f['issue_item']),('CONTRACTOR_MATERIAL_RECEIVABLE',f['issue']['id'])]:auth.refused(cur,lambda:read(cur,kind,ident,subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  assert not cur.execute("select has_function_privilege(%s,'erp.save_accessory_issue_action_v1(text,jsonb,uuid)','EXECUTE')",(bundle.ROLE,)).fetchone()[0]
  bundle.verify(cur)
  return dict(status='PASS',current_custom_role_view_before_child_resolution_and_after_revoke=True,reverse_permission_does_not_imply_view=True,no_ERP_DML_or_Native_writer_EXEC=True)
 def accessory_unsupported():
  f=accessory_fixture(cur,today);fabric=material.receipt.fixture(cur,today)
  # The old receipt clone uses legacy lowercase yd. Configure this fresh,
  # unused master with an actual registered LENGTH unit before any receipt;
  # the Native issue trigger/FK is preserved, never bypassed with a new alias.
  unit=cur.execute("select unit_code from erp.uom_definitions where dimension='LENGTH'and is_active order by unit_code limit 1").fetchone();assert unit
  cur.execute('update erp.materials set unit_code=%s where id=%s',(unit[0],fabric['material']))
  receipt=material.receipt.command(cur,'SAVE_DRAFT',fabric['payload']);fabric['receipt']=material.receipt.post(cur,receipt)
  fabric['roll']=str(cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s',(receipt['purchase_id'],)).fetchone()[0])
  # Administrative master price only; the valid fabric document below is
  # saved by its Native writer, never inserted as a business outcome.
  cur.execute('insert into erp.contractor_material_price_versions(material_id,contractor_id,selling_price,effective_from,notes)values(%s,%s,%s,%s,%s)',(fabric['material'],f['mandor'],'3.25',fabric['payload']['physical_at'],'Source classification fixture configured fabric price'))
  p=dict(issue_number=f['issue_number']+'-FABRIC',contractor_id=f['mandor'],location_id=fabric['location'],physical_at=f['issue_at'],change_reason='Native fabric note is not a counted accessory editor',items=[dict(material_id=fabric['material'],roll_id=fabric['roll'],qty='1')])
  from psycopg.types.json import Jsonb
  draft=accessory.bc.internal(cur,'save_contractor_material_issue_draft_v2',Jsonb(p),uuid.uuid4(),None)
  ident=draft['contractor_material_issue_id'];item=cur.execute('select id from erp.contractor_material_issue_items where issue_id=%s',(ident,)).fetchone()[0];before=b.boundary.snapshot(cur)
  for kind,i in [('CONTRACTOR_MATERIAL_RECEIVABLE',ident),('CONTRACTOR_MATERIAL_ISSUE_ITEM',item)]:
   r=read(cur,kind,i);assert r['status']=='UNSUPPORTED_SOURCE'and r['document']is None and r['business_DML']is False
  missing=uuid.uuid4()
  for kind in('CONTRACTOR_MATERIAL_RECEIVABLE','CONTRACTOR_MATERIAL_ISSUE_ITEM'):auth.refused(cur,lambda:read(cur,kind,missing),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_Native_fabric_issue_not_redirected_into_PCS_accessory_editor=True,missing_header_or_child_refused_no_guessed_document=True)
 def rework_documents():
  f=rework_fixture(cur,today);before=rework_state(cur,f);assert before['lot_qty']=='2'
  for kind in('REWORK_ORDER','REWORK_COMPLETION'):
   d=exact(cur,kind,f['rework'],'BS_REWORK',f['bs'],('REWORK_ORDER',f['rework']));assert d['route']=='bs-rework'
  w=rework_workspace(cur,f);row=next(r for r in w['rows']if r['id']==f['bs']);assert row['kind']=='BS'and any(r['id']==f['rework']for r in row['rework_orders'])
  assert rework_state(cur,f)==before
  production.b.chain.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=f['rework'],change_reason='Inverse exact source of repaired goods'),production.b.chain.version(cur,'rework_orders',f['rework']))
  after=rework_state(cur,f);assert after['order']['id']==before['order']['id']and after['order']['bs_case_id']==before['order']['bs_case_id']and after['order']['physical_sent_at']==before['order']['physical_sent_at']
  assert after['order']['status']=='CANCELLED'and after['lot_qty']=='0'and after['original_movement']==before['original_movement']and len(after['inverses'])==1
  assert cur.execute('select count(*)from erp.bs_resolutions where source_rework_order_id=%s',(f['rework'],)).fetchone()[0]==0
  exact(cur,'JOURNAL_REVERSAL',f['journal']['id'],'BS_REWORK',f['bs'],('REWORK_ORDER',f['rework']))
  return dict(status='PASS',actual_rework_stock_and_labor_journal_same_bs_parent=True,owning_inverse_retains_order_and_original_movement_after_resolution_deleted=True,Native_two_PCS_labor60_to_zero_stock_no_second_write_from_source=True)
 def rework_history():
  f=rework_fixture(cur,today,True);d=exact(cur,'REWORK_ORDER',f['rework'],'BS_REWORK',f['bs'],('REWORK_ORDER',f['rework']));old_offset=d['focus']['page_offset'];assert old_offset>=50 and old_offset%50==0
  first=rework_workspace(cur,f,0);assert len(first['rows'])==50 and f['bs']not in[r['id']for r in first['rows']]
  w=rework_workspace(cur,f);assert w['offset']==old_offset and any(r['id']==f['bs']and any(o['id']==f['rework']for o in r['rework_orders'])for r in w['rows'])
  production.b.chain.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=f['rework'],change_reason='Closed case becomes open in Native case ordering'),production.b.chain.version(cur,'rework_orders',f['rework']))
  new=exact(cur,'REWORK_COMPLETION',f['rework'],'BS_REWORK',f['bs'],('REWORK_ORDER',f['rework']));assert new['focus']['page_offset']!=old_offset
  w=rework_workspace(cur,f);row=next(r for r in w['rows']if r['id']==f['bs']);assert row['status']=='OPEN'and row['available_qty']==2 and row['resolved_qty']==0 and any(o['id']==f['rework']and o['status']=='CANCELLED'for o in row['rework_orders'])
  return dict(status='PASS',actual51_older_manual_BS_cases_original_outside50=True,unchanged_Native_ALL_BS_order_exact_child=True,reversal_repositions_same_case_from_closed_to_open_without_scan=True,old_offset=old_offset,new_offset=new['focus']['page_offset'])
 def rework_authority():
  f=rework_fixture(cur,today);subject,role=auth.custom_actor(cur)
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'production.bs_rework.reverse')",(role,))
  auth.refused(cur,lambda:read(cur,'REWORK_ORDER',f['rework'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'production.bs_rework.view')",(role,))
  exact(cur,'REWORK_COMPLETION',f['rework'],'BS_REWORK',f['bs'],('REWORK_ORDER',f['rework']),subject=subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.bs_rework.view'",(role,))
  for kind in('REWORK_ORDER','REWORK_COMPLETION'):auth.refused(cur,lambda:read(cur,kind,f['rework'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  assert not cur.execute("select has_function_privilege(%s,'public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)','EXECUTE')or has_table_privilege(%s,'erp.bs_cases','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')or has_table_privilege(%s,'erp.rework_orders','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')",(bundle.ROLE,bundle.ROLE,bundle.ROLE)).fetchone()[0]
  return dict(status='PASS',current_native_custom_role_view_before_bs_fk_resolution=True,reverse_permission_never_implies_view=True,source_role_no_Native_bs_writer_EXEC_or_business_DML=True)
 def rework_unavailable():
  missing=str(uuid.uuid4());before=b.boundary.snapshot(cur)
  for kind in('REWORK_ORDER','REWORK_COMPLETION'):auth.refused(cur,lambda:read(cur,kind,missing),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  r=read(cur,'BS_INVENTED_SOURCE',missing);assert r['status']=='UNSUPPORTED_SOURCE'and r['document']is None
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',missing_actual_order_and_unknown_bs_kind_never_guessed=True,no_placeholder_case_or_native_writer=True)
 def authority():
  f=material.fixture(cur,today);subject,role=auth.custom_actor(cur)
  auth.refused(cur,lambda:read(cur,'MATERIAL_PURCHASE_ROLL',f['roll'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,'warehouse.procurement.view'))
  exact(cur,'MATERIAL_PURCHASE_ROLL',f['roll'],'RECEIPT',f['receipt']['purchase_id'],subject=subject)
  cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,'warehouse.procurement.view'))
  auth.refused(cur,lambda:read(cur,'MATERIAL_PURCHASE_ROLL',f['roll'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  return dict(status='PASS',Native_current_permission_before_child_resolution_and_after_revoke=True)
 def malformed():
  before=b.boundary.snapshot(cur);missing=str(uuid.uuid4())
  for value in [None,{},dict(source_type='SALE',source_id=missing,amount='1'),dict(source_type='sale',source_id=missing),dict(source_type='SALE',source_id='broken')]:
   def attempt():
    auth.actor(cur);cur.execute('select public.erp_cp7_resolve_transaction_source_v1(%s)',(json.dumps(value),))
   auth.refused(cur,attempt,'CP7_TRANSACTION_SOURCE_FIELDS');b.api.admin(cur)
  auth.refused(cur,lambda:read(cur,'SALE_ITEM',missing),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  unknown=read(cur,'UNREGISTERED_SOURCE',missing);assert unknown['document']is None and unknown['status']=='UNSUPPORTED_SOURCE'and unknown['business_DML']is False
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',closed_fields_missing_source_explicit_unsupported_never_guessed=True)
 def least_privilege():
  bundle.verify(cur)
  for who in('anon','service_role'):assert not cur.execute('select has_function_privilege(%s,\'public.erp_cp7_resolve_transaction_source_v1(jsonb)\',\'EXECUTE\')',(who,)).fetchone()[0]
  assert cur.execute('select has_function_privilege(\'authenticated\',\'public.erp_cp7_resolve_transaction_source_v1(jsonb)\',\'EXECUTE\')').fetchone()[0]
  return dict(status='PASS',public_current_auth_only_private_resolver_and_ERP_DML_denied=True)
 functions=[receipts,invoices,transfers,counts,finished,sales,payments,returns,journals,authority,malformed,least_privilege,payroll_headers,payroll_payments,payroll_authority,payroll_unavailable,accessory_documents,accessory_history,accessory_authority,accessory_unsupported,rework_documents,rework_history,rework_authority,rework_unavailable]
 assert len(functions)==REQUIRED['native']
 return [('CP7_SOURCE_'+f.__name__.upper(),f)for f in functions]

def races(tools,today):return [('CP7_SOURCE_RETAINED_'+name,fn)for name,fn in combined.races(tools,today)]

def http_cases(http,today):
 def exact_http():
  owner=http.login('OWNER','cp7-source-owner')
  with http.connect()as conn,conn.cursor()as cur:f=material.fixture(cur,today);conn.commit()
  args=dict(p_source=dict(source_type='MATERIAL_PURCHASE_ROLL',source_id=f['roll']))
  assert http.anon_rpc(RPC,args)['status']in(401,403)
  r=owner.rpc(RPC,args);assert r['status']==200,r
  assert r['body']['actor_scope_id']==owner.auth_user_id and r['body']['document']['id']==f['receipt']['purchase_id']and r['body']['business_DML']is False
  with http.connect()as conn,conn.cursor()as cur:before=b.boundary.snapshot(cur);conn.rollback()
  assert owner.rpc(RPC,args)['body']['document']==r['body']['document']
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before;conn.rollback()
  return dict(status='PASS',real_Auth_HTTP_exact_child_parent_anonymous_denied_no_business_write=True)
 def current_http():
  admin=http.login('ADMIN','cp7-source-current-admin')
  with http.connect()as conn,conn.cursor()as cur:
   f=material.fixture(cur,today);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,)).fetchone()[0];cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,'warehouse.procurement.view'));conn.commit()
  args=dict(p_source=dict(source_type='MATERIAL_PURCHASE_ROLL',source_id=f['roll']))
  assert admin.rpc(RPC,args)['status']==200
  with http.connect()as conn,conn.cursor()as cur:cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,'warehouse.procurement.view'));conn.commit()
  assert admin.rpc(RPC,args)['status']==403
  return dict(status='PASS',real_Auth_CURRENT_native_role_permission_revocation_not_token_metadata=True)
 def payroll_http():
  admin=http.login('ADMIN','cp7-source-payroll-current-admin')
  with http.connect()as conn,conn.cursor()as cur:
   f=installment.fixture(cur,today);payment=installment.act(cur,f,amount='10.00')['payment_id']
   role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,)).fetchone()[0]
   cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.payroll.view')on conflict do nothing",(role,))
   conn.commit();before=b.boundary.snapshot(cur);conn.rollback()
  args=dict(p_source=dict(source_type='PAYROLL_INSTALLMENT',source_id=payment))
  assert http.anon_rpc(RPC,args)['status']in(401,403)
  r=admin.rpc(RPC,args);assert r['status']==200,r
  assert r['body']['actor_scope_id']==admin.auth_user_id and r['body']['document']['id']==f['payroll']and r['body']['document']['focus']==dict(kind='PAYROLL_INSTALLMENT',id=payment,page_offset=0)and r['body']['business_DML']is False
  with http.connect()as conn,conn.cursor()as cur:
   assert b.boundary.snapshot(cur)==before
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.view'",(role,));conn.commit();revoked=b.boundary.snapshot(cur);conn.rollback()
  assert admin.rpc(RPC,args)['status']==403
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==revoked;conn.rollback()
  return dict(status='PASS',real_Auth_HTTP_exact_private_installment_to_Native_payroll=True,current_database_view_revoke_denied_despite_same_Auth_token=True,no_business_write=True)
 def accessory_http():
  admin=http.login('ADMIN','cp7-source-accessory-current-admin')
  with http.connect()as conn,conn.cursor()as cur:
   f=accessory_fixture(cur,today);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,)).fetchone()[0]
   cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.contractor_accessory.view')on conflict do nothing",(role,));conn.commit();before=b.boundary.snapshot(cur);conn.rollback()
  args=dict(p_source=dict(source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM',source_id=f['issue_item']))
  assert http.anon_rpc(RPC,args)['status']in(401,403)
  r=admin.rpc(RPC,args);assert r['status']==200,r
  assert r['body']['actor_scope_id']==admin.auth_user_id and r['body']['document']['id']==f['issue']['id']and r['body']['document']['route']=='contractor-issue'and r['body']['business_DML']is False
  with http.connect()as conn,conn.cursor()as cur:
   assert b.boundary.snapshot(cur)==before
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.contractor_accessory.view'",(role,));conn.commit();revoked=b.boundary.snapshot(cur);conn.rollback()
  assert admin.rpc(RPC,args)['status']==403
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==revoked;conn.rollback()
  return dict(status='PASS',real_Auth_HTTP_exact_Native_stock_child_to_note=True,current_database_view_revoke_denied_with_unchanged_Auth_token=True,no_business_write=True)
 def rework_http():
  admin=http.login('ADMIN','cp7-source-bs-current-admin')
  with http.connect()as conn,conn.cursor()as cur:
   f=rework_fixture(cur,today);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,)).fetchone()[0]
   cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'production.bs_rework.view')on conflict do nothing",(role,));conn.commit();before=b.boundary.snapshot(cur);conn.rollback()
  args=dict(p_source=dict(source_type='REWORK_ORDER',source_id=f['rework']))
  assert http.anon_rpc(RPC,args)['status']in(401,403)
  r=admin.rpc(RPC,args);assert r['status']==200,r
  assert r['body']['actor_scope_id']==admin.auth_user_id and r['body']['document']['id']==f['bs']and r['body']['document']['focus']['id']==f['rework']and r['body']['document']['route']=='bs-rework'and r['body']['business_DML']is False
  with http.connect()as conn,conn.cursor()as cur:
   assert b.boundary.snapshot(cur)==before
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.bs_rework.view'",(role,));conn.commit();revoked=b.boundary.snapshot(cur);conn.rollback()
  assert admin.rpc(RPC,args)['status']==403
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==revoked;conn.rollback()
  return dict(status='PASS',real_Auth_HTTP_exact_Native_rework_child_to_bs=True,current_database_view_revoke_same_token_denied=True,no_business_write=True)
 return [('CP7_SOURCE_HTTP_EXACT',exact_http),('CP7_SOURCE_HTTP_CURRENT_REVOKE',current_http),('CP7_SOURCE_HTTP_PAYROLL_CURRENT_VIEW',payroll_http),('CP7_SOURCE_HTTP_ACCESSORY_CURRENT_VIEW',accessory_http),('CP7_SOURCE_HTTP_BS_CURRENT_VIEW',rework_http)]
