"""Native cutover quantities, cost attribution, partial continuation and inverses."""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp6_initial_import_receipt_trial as receipts
from cp6_pocket_period_trial import reported_effects


def fixture(a,cur,today,stage='SEWING',fully_consumed=False):
    f=receipts.fixture(a,cur,today,qty='12',cost='10');b=f['batch'];code=f['code']
    for entity,rows in {
        'MODEL':[dict(model_code=code,model_name='Cutover model')],
        'SIZE':[dict(size_code=code)],
        'BRAND':[dict(brand_code=code,brand_name='Cutover brand')],
        'PRODUCT':[dict(sku=code,product_name='Cutover product',model_code=code,brand_code=code,color_name='Blue',size_code=code)],
        'CONTRACTOR':[dict(contractor_code=code,contractor_name='Cutover holder',contractor_type='MANDOR')],
        'LAUNDRY_VENDOR':[dict(vendor_code=code,vendor_name='Cutover laundry')],
        'LOCATION':[dict(location_code=code,location_name='Raw warehouse',location_type='RAW_MATERIAL_WAREHOUSE'),dict(location_code=code+'F',location_name='FG warehouse',location_type='FG_WAREHOUSE')],
        'OPEN_PO':[dict(po_number=code,model_code=code,contractor_code=code,target_qty_pcs='10',status=stage,current_stage=stage)],
    }.items():a.upload(cur,b,entity,rows)
    stock=dict(f['stock'],qty='4')
    base=dict(po_number=code,size_code=code,contractor_code=code,vendor_code=code,accessory_cost_included='true')
    wip=dict(base,balance_type='WIP',stage=stage,qty='8',unit_cost='5',amount='40.00',opening_source_key='WIP',control_key='WIP')
    bs=dict(base,balance_type='BS',stage='QC',product_sku=code,qty='2',unit_cost='10',amount='20.00',opening_source_key='BS',control_key='BS')
    fg=dict(balance_type='FINISHED_GOODS',product_sku=code,location_code=code+'F',qty='4',unit_cost='5',opening_source_key='FG',control_key='FG')
    rows=[wip,bs,fg] if fully_consumed else [stock,wip,bs,fg]
    a.upload(cur,b,'OPENING_BALANCE_ITEM',rows)
    r=dict(f['receipt'],qty='8' if fully_consumed else '12')
    if fully_consumed:r.pop('opening_source_key')
    a.upload(cur,b,'UNINVOICED_RECEIPT',[r])
    origins=[dict(supplier_code=code,receipt_number=r['receipt_number'],receipt_line_number='001',target_source_key=k,qty=q) for k,q in [('WIP','4'),('BS','2'),('FG','2')]]
    a.upload(cur,b,'OPENING_COST_ORIGIN',origins)
    controls=[dict(control_key=k,balance_type=t,qty=q,amount=v) for k,t,q,v in [('WIP','WIP','8','40.00'),('BS','BS','2','20.00'),('FG','FINISHED_GOODS','4','20.00'),('GRNI','GRNI_MATERIAL',r['qty'],'80.00' if fully_consumed else '120.00')]]
    if not fully_consumed:controls.append(dict(control_key='STOCK',balance_type='MATERIAL',qty='4',amount='40.00'))
    a.upload(cur,b,'OPENING_CONTROL',controls)
    return dict(f,receipt=r,rows=rows,origins=origins,controls=controls)


def finalize(a,cur,f):
    counts=lambda:tuple(cur.execute('select count(*) from erp.'+t).fetchone()[0] for t in ['work_completion_events','cutting_groups','sewing_terminal_events','material_stock_movements'])
    before=a.production.ledger(cur);prior=counts()
    assert a.invoke(cur,'VALIDATE',f['batch'])['error_rows']==0,a.read(cur,f['batch'])
    assert a.production.ledger(cur)==before and counts()==prior
    payload=dict(batch_id=f['batch'],expected_revision=a.read(cur,f['batch'])['batch']['revision']);key=uuid.uuid4()
    result=a.call(cur,'FINALIZE',payload,key);assert result['status']=='POSTED',a.read(cur,f['batch'])
    state=a.actors.boundary(cur);assert a.call(cur,'FINALIZE',payload,key)==result and a.actors.boundary(cur)==state
    assert counts()[:3]==prior[:3],'Opening fabricated historical production/payroll'
    batch=a.read(cur,f['batch'])['batch'];sources={r['balance_type']:r for r in batch['production_sources']}
    assert sources['WIP']['qty_pcs']==8 and sources['BS']['qty_pcs']==2
    assert cur.execute("select sum(qty_pcs) from erp.wip_stage_events where source_type='INITIAL_IMPORT_WIP_OPENING' and source_id=%s",(sources['WIP']['opening_item_id'],)).fetchone()[0]==8
    return batch['uninvoiced_receipts'][0],sources


def output(a,cur,f,today,qty='4'):
    s=next(x for x in a.read(cur,f['batch'])['batch']['production_sources'] if x['balance_type']=='WIP')
    payload=dict(batch_id=f['batch'],opening_item_id=s['opening_item_id'],expected_remaining=str(s['remaining_qty_pcs']),operation='COMPLETE',
      qty_pcs=qty,product_sku=f['code'],location_code=f['code']+'F',date=str(today-timedelta(days=3)),reason='Verified good cutover WIP')
    key=uuid.uuid4();r=a.call(cur,'WIP_OUTPUT',payload,key);state=a.actors.boundary(cur)
    assert a.call(cur,'WIP_OUTPUT',payload,key)==r and a.actors.boundary(cur)==state
    return r


def reverse_output(a,cur,f,o):
    s=next(x for x in a.read(cur,f['batch'])['batch']['production_sources'] if x['balance_type']=='WIP')
    return a.call(cur,'WIP_OUTPUT',dict(batch_id=f['batch'],opening_item_id=s['opening_item_id'],expected_remaining=str(s['remaining_qty_pcs']),operation='REVERSE',output_id=o['output_id'],reason='Restore checked opening position'))


def bs_action(a,cur,action,payload,version):
    a.ordinary(cur)
    r=cur.execute('select public.erp_save_bs_resolution_action_v1(%s,%s::jsonb,%s,%s)',(action,json.dumps(payload,default=str),uuid.uuid4(),version)).fetchone()[0]
    a.admin(cur);return r['result']


def effects(a,cur):
    names=['MATERIAL_INVENTORY','WIP','FG_INVENTORY','OTHER_EXPENSE','COGS']
    return {k:cur.execute('select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=erp.account_id(%s) and j.status in(\'POSTED\',\'REVERSED\')',(k,)).fetchone()[0] for k in names}


def truth(cur):
    names=['V2620C_PO_HPP_TARGET_STATE_MISMATCH','V2620C_HPP_COMPONENT_SUM_MISMATCH','V2620C_PO_HPP_BOOK_MISMATCH',
      'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH','V2620AF_OPENING_SOURCE_LINEAGE_MISMATCH']
    rows=cur.execute('select check_name,issue_count from erp.run_v268_financial_report_checks() where check_name=any(%s)',(names,)).fetchall()
    assert len(rows)==len(names) and all(v==0 for _,v in rows),rows


def lifecycle(a,cur,today,stage='SEWING',closed=False,fully_consumed=False):
    cur.execute("set local timezone='Pacific/Kiritimati'" if closed else "set local timezone='UTC'")
    baseline=effects(a,cur);reports=reported_effects(a,cur,today)
    f=fixture(a,cur,today,stage,fully_consumed);r,s=finalize(a,cur,f);receipts.truth(cur)
    initial=effects(a,cur)
    assert {k:initial[k]-baseline[k] for k in initial}==dict(MATERIAL_INVENTORY=D(0 if fully_consumed else 40),WIP=D(60),FG_INVENTORY=D(20),OTHER_EXPENSE=D(0),COGS=D(0))
    original=cur.execute('select to_jsonb(i) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s order by i.id',(f['batch'],)).fetchall()
    o=output(a,cur,f,today);truth(cur)
    after=effects(a,cur);assert after['WIP']==initial['WIP']-20 and after['FG_INVENTORY']==initial['FG_INVENTORY']+20,after
    bs=s['BS']['bs_case_id'];version=cur.execute('select row_version from erp.bs_cases where id=%s',(bs,)).fetchone()[0]
    disposed=bs_action(a,cur,'DISPOSE_BS',dict(bs_case_id=bs,resolution_type='SCRAP',qty_pcs=1,physical_at=a.production.at(today-timedelta(days=3),14),change_reason='Cutover BS scrap'),version)
    truth(cur)
    after=effects(a,cur);assert after['WIP']==initial['WIP']-30 and after['OTHER_EXPENSE']==initial['OTHER_EXPENSE']+10,after
    if closed:receipts.rpc(a,cur,'close_accounting_through',today-timedelta(days=1),'Cutover recost date closed')
    journal_ids={x[0] for x in cur.execute('select id from erp.journal_entries').fetchall()}
    invoice=receipts.post_invoice(a,cur,receipts.invoice(a,cur,today,r,r['qty'],'12'))
    receipts.truth(cur);truth(cur)
    after=effects(a,cur)
    expected=dict(MATERIAL_INVENTORY=D(0 if fully_consumed else 48),WIP=D(36),FG_INVENTORY=D(48),OTHER_EXPENSE=D(12),COGS=D(0))
    assert {k:after[k]-baseline[k] for k in after}==expected,(after,baseline,expected)
    report=reported_effects(a,cur,today);assert {k:report[k]-reports[k] for k in report}==expected,(report,reports)
    fresh=[x for x in cur.execute('select id,source_type,economic_date,transaction_date from erp.journal_entries').fetchall() if x[0] not in journal_ids]
    assert fresh and all(e==today-timedelta(days=2) and t==(today if closed else e) for _,_,e,t in fresh),fresh
    assert cur.execute('select to_jsonb(i) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s order by i.id',(f['batch'],)).fetchall()==original
    receipts.rpc(a,cur,'reverse_material_supplier_invoice_v2',invoice['supplier_invoice_id'],'Restore estimated origin costs',uuid.uuid4(),invoice['row_version']);receipts.truth(cur)
    version=cur.execute('select row_version from erp.bs_cases where id=%s',(bs,)).fetchone()[0]
    bs_action(a,cur,'REVERSE_DISPOSITION',dict(resolution_id=disposed['bs_resolution_id'],change_reason='Restore original BS'),version)
    reverse_output(a,cur,f,o)
    assert effects(a,cur)==initial;truth(cur)
    final_wip=next(x for x in a.read(cur,f['batch'])['batch']['production_sources'] if x['balance_type']=='WIP')
    assert final_wip['remaining_qty_pcs']==8 and len(final_wip['outputs'])==1 and final_wip['outputs'][0]['reversed']
    return dict(status='PASS',stage=stage,closed=closed,fully_consumed=fully_consumed,exact_cutover_quantities=True,no_historic_payroll_or_cutting=True,
                origin_invoice_report_and_ledger_reconciled=True,partial_wip_output_and_bs_scrap=True,append_only_value_inverses=True,original_snapshots_unchanged=True)


def rework(a,cur,today):
    f=fixture(a,cur,today);r,s=finalize(a,cur,f);before=effects(a,cur)
    product,location,vendor=cur.execute('select p.id,l.id,v.id from erp.products p join erp.locations l on l.location_code=%s join erp.laundry_vendors v on v.vendor_code=%s where p.sku=%s',(f['code']+'F',f['code'],f['code'])).fetchone()
    cur.execute('insert into erp.accessory_bom_versions(product_id,effective_from,notes) values(%s,%s,%s)',(product,a.production.at(today-timedelta(days=6),10),'Explicit empty rework BOM fixture'))
    order=bs_action(a,cur,'SAVE_REWORK',dict(rework_number='ORIGIN-'+uuid.uuid4().hex,bs_case_id=s['BS']['bs_case_id'],destination_type='LAUNDRY',vendor_id=vendor,
      qty_sent=2,physical_sent_at=a.production.at(today-timedelta(days=5),10),return_fg_location_id=location,accessory_bom_item_ids=[],change_reason='Recover initial BS using native rework'),None)
    complete=bs_action(a,cur,'COMPLETE_REWORK',dict(rework_order_id=order['rework_order_id'],qty_good=1,qty_bs=1,completed_at=a.production.at(today-timedelta(days=3),10),return_fg_location_id=location,change_reason='One good, one BS remains'),order['row_version'])
    after=effects(a,cur);assert after['WIP']==before['WIP']-10 and after['FG_INVENTORY']==before['FG_INVENTORY']+10,(before,after)
    truth(cur)
    invoice=receipts.post_invoice(a,cur,receipts.invoice(a,cur,today,r,6,'14'));receipts.truth(cur);truth(cur)
    lot=cur.execute('select good_fg_lot_id from erp.rework_orders where id=%s',(order['rework_order_id'],)).fetchone()[0]
    assert cur.execute('select total_cost from erp.hpp_versions where lot_id=%s and is_current',(lot,)).fetchone()[0]==12
    receipts.rpc(a,cur,'reverse_material_supplier_invoice_v2',invoice['supplier_invoice_id'],'Restore material estimate',uuid.uuid4(),invoice['row_version'])
    bs_action(a,cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=order['rework_order_id'],change_reason='Restore initial BS'),complete['row_version'])
    assert effects(a,cur)==before;truth(cur)
    return dict(status='PASS',native_rework_good=1,remaining_bs=1,partial_invoice_recost=True,all_accounts_restored=True)


def latest_draft(a,cur,today):
    f=fixture(a,cur,today);assert a.invoke(cur,'VALIDATE',f['batch'])['error_rows']==0
    f['rows'][1].update(amount='44.00',unit_cost='5.5');f['controls'][0]['amount']='44.00'
    a.upload(cur,f['batch'],'OPENING_BALANCE_ITEM',f['rows']);a.upload(cur,f['batch'],'OPENING_CONTROL',f['controls'])
    _,s=finalize(a,cur,f);assert s['WIP']['original_amount']=='44.00'
    return dict(status='PASS',latest_physical_source_value='44.00',prior_validation_not_reused=True)


def sold_origin(a,cur,today):
    f=fixture(a,cur,today);a.upload(cur,f['batch'],'CUSTOMER',[dict(customer_code=f['code'],customer_name='Opening cost buyer')])
    before=effects(a,cur);r,_=finalize(a,cur,f)
    product,location,customer=cur.execute('select p.id,l.id,c.id from erp.products p join erp.locations l on l.location_code=%s join erp.customers c on c.customer_code=%s where p.sku=%s',(f['code']+'F',f['code'],f['code'])).fetchone()
    sale=receipts.rpc(a,cur,'save_sale_draft_v2',json.dumps(dict(sale_number='ORIGIN-SALE-'+uuid.uuid4().hex,customer_id=customer,source_location_id=location,sale_date=str(a.production.at(today-timedelta(days=3),15)),reason='Sell sourced opening FG',items=[dict(product_id=product,qty_pcs=2,unit_price_snapshot='20',discount_amount=0)]),default=str),uuid.uuid4(),None)
    receipts.rpc(a,cur,'post_sale_v2',sale['sale_id'],uuid.uuid4(),sale['row_version'])
    invoiced=receipts.post_invoice(a,cur,receipts.invoice(a,cur,today,r,6,'14'));receipts.truth(cur);truth(cur)
    after=effects(a,cur)
    assert {k:after[k]-before[k] for k in after}==dict(MATERIAL_INVENTORY=D(48),WIP=D(72),FG_INVENTORY=D(12),COGS=D(12),OTHER_EXPENSE=D(0)),(before,after)
    receipts.rpc(a,cur,'reverse_material_supplier_invoice_v2',invoiced['supplier_invoice_id'],'Restore sold origin costs',uuid.uuid4(),invoiced['row_version']);truth(cur)
    after=effects(a,cur)
    assert {k:after[k]-before[k] for k in after}==dict(MATERIAL_INVENTORY=D(40),WIP=D(60),FG_INVENTORY=D(10),COGS=D(10),OTHER_EXPENSE=D(0))
    return dict(status='PASS',sold_opening_pcs=2,partial_invoice_qty=6,fg_and_cogs_follow_current_cost=True,inverse_restores_both=True)


def source_guards(a,cur,today,fully_consumed=False):
    f=fixture(a,cur,today,fully_consumed=fully_consumed);r,s=finalize(a,cur,f)
    msg=a.inherited.refused(cur,lambda:cur.execute("update erp.production_orders set status='FINISHED' where id=%s",(s['WIP']['po_id'],)))
    assert 'saldo awal' in msg['message'],msg
    mat,location=cur.execute('select i.material_id,h.location_id from erp.material_purchase_items i join erp.material_purchase_headers h on h.id=i.purchase_id where i.id=%s',(r['purchase_item_id'],)).fetchone()
    payload=dict(return_number='ORIGIN-RETURN-'+uuid.uuid4().hex,supplier_id=r['supplier_id'],location_id=location,physical_at=str(a.production.at(today-timedelta(days=1),12)),change_reason='Cannot return pre-cutover consumed fabric',items=[dict(material_id=mat,purchase_item_id=r['purchase_item_id'],qty='1' if fully_consumed else '5')])
    msg=a.inherited.refused(cur,lambda:receipts.rpc(a,cur,'save_material_supplier_return_draft_v2',json.dumps(payload,default=str),uuid.uuid4(),None))
    assert 'consumed before cutover' in msg['message'],msg
    return dict(status='PASS',fully_consumed=fully_consumed,po_close_with_wip_refused=True,return_cannot_use_consumed_quantity=True)


def refusal(a,cur,today,kind):
    f=fixture(a,cur,today);b=f['batch']
    if kind in('OVER_OUTPUT','STALE_OUTPUT','WRONG_PRODUCT','OUTPUT_BEFORE_CUTOVER'):
        _,s=finalize(a,cur,f)
        p=dict(batch_id=b,opening_item_id=s['WIP']['opening_item_id'],expected_remaining='8',qty_pcs='4',product_sku=f['code'],location_code=f['code']+'F',date=str(today-timedelta(days=3)),reason='Refuse invalid output')
        if kind=='OVER_OUTPUT':p['qty_pcs']='9'
        elif kind=='STALE_OUTPUT':p['expected_remaining']='7'
        elif kind=='WRONG_PRODUCT':p['product_sku']='missing'
        else:p['date']=str(today-timedelta(days=9))
        before=a.actors.boundary(cur);msg=a.inherited.refused(cur,lambda:a.call(cur,'WIP_OUTPUT',p));assert a.actors.boundary(cur)==before
        return dict(status='PASS',refusal=msg,complete_boundary_unchanged=True)
    rows=f['rows'];origins=f['origins']
    if kind=='MISSING_CUSTODY':rows[1].pop('contractor_code')
    elif kind=='MISSING_PO':rows[1]['po_number']='missing'
    elif kind=='FRACTIONAL_PCS':rows[1]['qty']='7.5'
    elif kind=='MISSING_COST':rows[2].pop('amount');rows[2].pop('unit_cost')
    elif kind=='BS_SIZE_MISMATCH':
        a.upload(cur,b,'SIZE',[dict(size_code=f['code']),dict(size_code=f['code']+'X')]);rows[2]['size_code']=f['code']+'X'
    elif kind=='BS_MISSING_HOLDER':rows[2].pop('contractor_code');rows[2].pop('vendor_code')
    elif kind=='PO_TARGET_TOO_SMALL':a.upload(cur,b,'OPEN_PO',[dict(po_number=f['code'],model_code=f['code'],contractor_code=f['code'],target_qty_pcs='9',status='SEWING',current_stage='SEWING')])
    elif kind=='ORIGIN_OVER_VALUE':origins[0]['qty']='5'
    elif kind=='ORIGIN_MISSING_TARGET':origins[0]['target_source_key']='missing'
    elif kind=='ORIGIN_DUPLICATE':origins.append(origins[0])
    elif kind=='ORIGIN_MISSING_RECEIPT':origins[0]['receipt_line_number']='002'
    elif kind=='MISSING_ORIGIN':origins.pop()
    elif kind in('BS_CONTROL_VALUE','WIP_CONTROL_QUANTITY'):
        if kind=='BS_CONTROL_VALUE':f['controls'][1]['amount']='0.00'
        else:f['controls'][0].pop('qty')
        a.upload(cur,b,'OPENING_CONTROL',f['controls'])
    else:raise AssertionError(kind)
    a.upload(cur,b,'OPENING_BALANCE_ITEM',rows);a.upload(cur,b,'OPENING_COST_ORIGIN',origins)
    before=effects(a,cur);count=cur.execute('select count(*) from erp.initial_import_production_sources').fetchone()
    result=a.invoke(cur,'FINALIZE',b);assert result['status']=='DRAFT' and result['error_rows']>0,a.read(cur,b)
    assert effects(a,cur)==before and cur.execute('select count(*) from erp.initial_import_production_sources').fetchone()==count
    return dict(status='PASS',invalid_source_refused=kind,no_business_writes=True)


def cases(a,cur,today):
    return [('PRODUCTION_ORIGIN:'+stage+':'+str(closed)+':'+str(full),lambda stage=stage,closed=closed,full=full:lifecycle(a,cur,today,stage,closed,full))
      for stage,closed,full in [('SEWING',False,False),('LAUNDRY',True,False),('LAUNDRY',False,True)]] + [
      ('PRODUCTION_ORIGIN_REFUSAL:'+k,lambda k=k:refusal(a,cur,today,k)) for k in ['MISSING_CUSTODY','MISSING_PO','FRACTIONAL_PCS','MISSING_COST','BS_SIZE_MISMATCH','BS_MISSING_HOLDER','PO_TARGET_TOO_SMALL','ORIGIN_OVER_VALUE','ORIGIN_MISSING_TARGET','ORIGIN_DUPLICATE','ORIGIN_MISSING_RECEIPT','MISSING_ORIGIN','BS_CONTROL_VALUE','WIP_CONTROL_QUANTITY','OVER_OUTPUT','STALE_OUTPUT','WRONG_PRODUCT','OUTPUT_BEFORE_CUTOVER']] + [
      ('PRODUCTION_ORIGIN_REWORK',lambda:rework(a,cur,today)),('PRODUCTION_ORIGIN_LATEST_DRAFT',lambda:latest_draft(a,cur,today)),
      ('PRODUCTION_ORIGIN_SOLD',lambda:sold_origin(a,cur,today)),('PRODUCTION_ORIGIN_GUARDS',lambda:source_guards(a,cur,today)),
      ('PRODUCTION_ORIGIN_GUARDS_FULLY_CONSUMED',lambda:source_guards(a,cur,today,True))]
