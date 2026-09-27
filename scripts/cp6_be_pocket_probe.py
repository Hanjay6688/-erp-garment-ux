"""Writer ALL-C04 continuation of historical pocket expense; native database only."""
from datetime import timedelta
import uuid
import cp6_bd_probe as b
api,one,q=b.api,b.one,b.q

def active_unit(cur,r):
    api.admin(cur);r['MATERIAL'][0]['unit_code']=one(cur,"select unit_code from erp.uom_definitions where dimension='LENGTH' and is_active and unit_code=upper(unit_code) order by unit_code limit 1")
    return r

def rows(cutover):
    r=b.bcp.po_rows(target='5',wip=('5','50.00'))
    r['MATERIAL']=[dict(material_sku='{C}K',material_name='BE kain kantong historis',material_type='FABRIC',unit_code='YARD')]
    r['OPENING_BALANCE_ITEM'].append(dict(balance_type='FINISHED_GOODS',product_sku='{C}P',location_code='{C}G',qty='3',unit_cost='10.00',quality_grade='GRADE_A',hpp_input_method='MANUAL',opening_source_key='FG',control_key='FG'))
    r['OPENING_CONTROL'].append(dict(control_key='FG',balance_type='FINISHED_GOODS',qty='3',amount='30.00'))
    day=str(cutover-timedelta(days=1))
    r['OPENING_POCKET_USAGE']=[dict(document_number='KELUAR-{C}',line_number='1',physical_date=day,material_sku='{C}K',qty='5',amount='11.25',allocation_status='UNALLOCATED',control_key='POCKET',control_qty='5',control_amount='11.25')]
    r['OPENING_POCKET_SEWING']=[dict(document_number='JAHIT-{C}',line_number=str(i),physical_date=day,contractor_code='{C}',qty=str(n),target_kind=k,control_key='SEWN',control_qty='10',**fields)
       for i,n,k,fields in [(1,5,'WIP',dict(target_source_key='WIP')),(2,3,'FINISHED_GOODS',dict(target_source_key='FG')),(3,2,'COGS',dict(product_sku='{C}P',sold_reference='JUAL-LAMA-{C}'))]]
    return r

def call(cur,action,payload,key=None):
    b.bcp.session(cur);result=one(cur,'select public.erp_save_pocket_fabric_action_v1(%s,%s::jsonb,%s)',action,b.json.dumps(payload,default=str),key or str(uuid.uuid4()));api.admin(cur);return result

def preview(cur,start,end):
    b.bcp.session(cur);result=one(cur,'select public.erp_preview_pocket_fabric_period_v1(%s,%s)',start,end);api.admin(cur);return result

def amounts(cur):return {k:b.gl(cur,k) for k in ['WIP','FG_INVENTORY','COGS','OTHER_EXPENSE','OPENING_EQUITY']}
def difference(a,z):return {k:z[k]-v for k,v in a.items()}

def roundtrip(cur,today,installed,snapshot=None):
    cut=today-timedelta(days=10);r=rows(cut)
    if not installed:
        batch=api.call(cur,'CREATE',dict(batch_code='BE-PRE-'+uuid.uuid4().hex[:12],cutover_date=str(cut)))['batch_id']
        return b.no_route(cur,lambda:api.upload(cur,batch,'OPENING_POCKET_USAGE',r['OPENING_POCKET_USAGE']))
    api.admin(cur);r['MATERIAL'][0]['unit_code']=one(cur,"select unit_code from erp.uom_definitions where dimension='LENGTH' and is_active and unit_code=upper(unit_code) order by unit_code limit 1")
    f=b.bbp.production_post(cur,today,r);start=cut-timedelta(days=1)
    origin=q(cur,'select id::text from erp.be_pocket_usage_v1 where batch_id=%s',f['batch'])[0][0]
    fake_before=(one(cur,'select count(*) from erp.material_stock_movements'),one(cur,'select count(*) from erp.sewing_terminal_events'))
    truth=b.all_truth(cur);g0=amounts(cur);p=preview(cur,start,cut);key=str(uuid.uuid4())
    payload=dict(period_start=str(start),period_end=str(cut),expected_revision=p['revision'],reason='BE C04 actual historical period')
    post=call(cur,'POST_PERIOD',payload,key);again=call(cur,'POST_PERIOD',payload,key)
    first=difference(g0,amounts(cur));pool=post['id'];truth1=b.all_truth(cur)
    if snapshot:
        b.bcp.session(cur);snapshot('pocket',one(cur,"select public.erp_get_pocket_fabric_workspace_v1('')"));api.admin(cur)
    corr=call(cur,'CORRECT_OPENING_USAGE',dict(usage_id=origin,amount='15.00',expected_amount='11.25',economic_date=str(cut+timedelta(days=1)),reason='BE source sheet correction'),str(uuid.uuid4()))
    second=difference(g0,amounts(cur));truth2=b.all_truth(cur)
    # Deliberate corruption only inside a rolled-back disposable savepoint:
    # the adapted lineage detector must still catch one unsourced cost unit.
    api.admin(cur);cur.execute('savepoint be_pocket_detector_negative')
    try:
        cur.execute("update erp.hpp_versions set total_cost=total_cost+1 where is_current and lot_id in(select lot_id from erp.fg_stock_movements where source_type='OPENING_BALANCE_ITEM' and source_id in(select opening_item_id from erp.initial_import_opening_stock_sources where batch_id=%s) and movement_type='OPENING')",(f['batch'],))
        detected=b.all_truth(cur)['V2620E_OPENING_HPP_LINEAGE_MISMATCH']>truth2['V2620E_OPENING_HPP_LINEAGE_MISMATCH']
    finally:
        cur.execute('rollback to savepoint be_pocket_detector_negative');cur.execute('release savepoint be_pocket_detector_negative')
    revision=one(cur,'select erp.pocket_period_state_v1(%s)',pool)['revision']
    call(cur,'CANCEL_PERIOD',dict(id=pool,expected_revision=revision,reason='BE inverse allocation only'))
    inverse=difference(g0,amounts(cur));unchanged=fake_before==(one(cur,'select count(*) from erp.material_stock_movements'),one(cur,'select count(*) from erp.sewing_terminal_events'))
    return b.verdict(dict(quantity=p['quantity']=='10',amount=p['amount']=='11.25',no_fake_events=unchanged,replay=post==again,
      first=first['WIP']==b.D('5.62') and first['FG_INVENTORY']==b.D('3.38') and first['COGS']==b.D('2.25') and first['OTHER_EXPENSE']==b.D('-11.25'),
      correction=second['WIP']==b.D('7.50') and second['FG_INVENTORY']==b.D('4.50') and second['COGS']==b.D('3.00') and second['OTHER_EXPENSE']==b.D('-11.25'),
      inverse=inverse['WIP']==inverse['FG_INVENTORY']==inverse['COGS']==0 and inverse['OTHER_EXPENSE']==b.D('3.75'),
      truth=b.truth_quiet(truth,truth1) and b.truth_quiet(truth,truth2),detector_negative=detected),first=first,corrected=second,inverse=inverse,preview=p,correction=corr,detectors=[truth,truth1,truth2])

def receipt_correction(cur,today,installed):
    cut=today-timedelta(days=10);r=rows(cut)
    if not installed:
        batch=api.call(cur,'CREATE',dict(batch_code='BE-RECPRE-'+uuid.uuid4().hex[:12],cutover_date=str(cut)))['batch_id']
        return b.no_route(cur,lambda:api.upload(cur,batch,'OPENING_POCKET_USAGE',r['OPENING_POCKET_USAGE']))
    api.admin(cur);r['MATERIAL'][0]['unit_code']=one(cur,"select unit_code from erp.uom_definitions where dimension='LENGTH' and is_active and unit_code=upper(unit_code) order by unit_code limit 1")
    r['SUPPLIER']=[dict(supplier_code='{C}',supplier_name='BE pocket supplier',supplier_type='MATERIAL')]
    r['LOCATION'].append(dict(location_code='{C}R',location_name='BE raw warehouse',location_type='RAW_MATERIAL_WAREHOUSE'))
    r['MATERIAL_ROLL']=[dict(roll_number='ROLL-{C}',material_sku='{C}K',location_code='{C}R',opening_qty='15',unit_cost='2.25',supplier_code='{C}',opening_source_key='STOCK',control_key='STOCK')]
    r['OPENING_CONTROL'] += [dict(control_key='STOCK',balance_type='MATERIAL',qty='15',amount='33.75'),dict(control_key='GRNI',balance_type='GRNI_MATERIAL',qty='20',amount='45.00')]
    r['UNINVOICED_RECEIPT']=[dict(receipt_number='RCV-{C}',receipt_line_number='1',receipt_date=str(cut-timedelta(days=3)),supplier_code='{C}',material_sku='{C}K',location_code='{C}R',qty='20',unit_cost='2.25',opening_source_key='STOCK',control_key='GRNI')]
    r['OPENING_POCKET_USAGE'][0].update(supplier_code='{C}',receipt_number='RCV-{C}',receipt_line_number='1')
    f=b.bbp.production_post(cur,today,r);start=cut-timedelta(days=1);p=preview(cur,start,cut)
    pool=call(cur,'POST_PERIOD',dict(period_start=str(start),period_end=str(cut),expected_revision=p['revision'],reason='BE receipt-backed historical pool'))['id']
    row=q(cur,'select s.id::text,l.purchase_item_id::text,p.material_id::text from erp.initial_import_receipt_headers h join erp.initial_import_receipt_lines l on l.purchase_id=h.purchase_id join erp.suppliers s on s.id=h.supplier_id join erp.material_purchase_items p on p.id=l.purchase_item_id where h.batch_id=%s',f['batch'])[0]
    old=amounts(cur);material=one(cur,'select cached_stock_qty from erp.materials where id=%s',row[2]);stock_moves=one(cur,'select count(*) from erp.material_stock_movements where material_id=%s',row[2]);truth=b.all_truth(cur)
    def certainty():
        return one(cur,"select h.cost_state from erp.be_pocket_sewing_v1 s join erp.fg_stock_movements m on m.source_id=s.opening_item_id and m.source_type='OPENING_BALANCE_ITEM' and m.movement_type='OPENING' join erp.v_current_hpp h on h.lot_id=m.lot_id where s.batch_id=%s and s.target_kind='FINISHED_GOODS'",f['batch'])
    initial_certainty=certainty();trial=b.bbp.receipt_trial
    # An invoice at exactly the estimate must still resolve certainty; zero money
    # difference must not skip the refresh. Its inverse restores ESTIMATED.
    same=trial.post_invoice(api,cur,trial.invoice(api,cur,today,dict(supplier_id=row[0],purchase_item_id=row[1]),'20','2.25',date=cut+timedelta(days=1)))
    api.admin(cur);same_certainty=certainty();same_delta=difference(old,amounts(cur))
    trial.rpc(api,cur,'reverse_material_supplier_invoice_v2',same['supplier_invoice_id'],'BE same-price certainty inverse',uuid.uuid4(),same['row_version']);api.admin(cur)
    inverse_certainty=certainty()
    doc=trial.post_invoice(api,cur,trial.invoice(api,cur,today,dict(supplier_id=row[0],purchase_item_id=row[1]),'20','3.00',date=cut+timedelta(days=1)))
    api.admin(cur);delta=difference(old,amounts(cur));newtruth=b.all_truth(cur)
    pool_value=one(cur,'select erp.pocket_period_total_v1(%s)',pool)
    trial.rpc(api,cur,'reverse_material_supplier_invoice_v2',doc['supplier_invoice_id'],'BE C04 invoice inverse',uuid.uuid4(),doc['row_version']);api.admin(cur)
    restored=difference(old,amounts(cur))
    return b.verdict(dict(certainty=initial_certainty==inverse_certainty==certainty()=='ESTIMATED' and same_certainty=='ADJUSTED' and all(x==0 for x in same_delta.values()),receipt_quantity=material==15,stock_not_drawn_twice=one(cur,'select cached_stock_qty from erp.materials where id=%s',row[2])==15 and stock_moves==one(cur,'select count(*) from erp.material_stock_movements where material_id=%s',row[2]),
     recost=pool_value==15 and delta['WIP']==b.D('1.88') and delta['FG_INVENTORY']==b.D('1.12') and delta['COGS']==b.D('0.75') and delta['OTHER_EXPENSE']==0,
     inverse=all(x==0 for x in restored.values()),truth=b.truth_quiet(truth,newtruth)),delta=delta,restored=restored,pool_value=pool_value,certainty=[initial_certainty,same_certainty,inverse_certainty,certainty()])

def historical_continuation(cur,today,installed):
    if not installed:return roundtrip(cur,today,False)
    cut=today-timedelta(days=10);f=b.bbp.production_post(cur,today,active_unit(cur,rows(cut)))
    # A wholly historical period can be allocated only from its opening date;
    # native transaction periods retain their original closed-period checks.
    b.boundary.historical.prior.set_open_period(cur,cut)
    p=preview(cur,cut-timedelta(days=1),cut-timedelta(days=1))
    made=call(cur,'POST_PERIOD',dict(period_start=p['period_start'],period_end=p['period_end'],expected_revision=p['revision'],reason='BE historical-only period at cutover'))
    post_date=one(cur,"select economic_date from erp.pocket_period_events where pool_id=%s and kind='POST'",made['id'])
    b.bbp.split(cur,f,cut+timedelta(days=2),2);b.bbp.complete(cur,f,cut+timedelta(days=3),3)
    source=b.bbp.source_of(cur,f);sp=source['bb']['splits'][0];api.admin(cur)
    lot=one(cur,"select id::text from erp.fg_lots where po_id=%s and lot_origin='PRODUCTION'",f['po'])
    before=b.lot_value(cur,lot)
    b.bbp.bs_act(cur,'DISPOSE_BS',dict(bs_case_id=sp['bs_case_id'],resolution_type='SCRAP',qty_pcs=2,physical_at=b.chain.production.at(cut+timedelta(days=3),15),change_reason='BE historical pocket BS cost'),b.bbp.bs_version(cur,sp['bs_case_id']))
    old_bs=b.bbp.ledger(cur,'OTHER_EXPENSE',f['po'])
    usage=one(cur,'select id::text from erp.be_pocket_usage_v1 where batch_id=%s',f['batch']);truth=b.all_truth(cur)
    call(cur,'CORRECT_OPENING_USAGE',dict(usage_id=usage,amount='15.00',expected_amount='11.25',economic_date=str(cut+timedelta(days=4)),reason='BE historical source after BS split and completion'))
    current=b.lot_value(cur,lot);new_bs=b.bbp.ledger(cur,'OTHER_EXPENSE',f['po'])
    source_value=one(cur,'select erp.initial_import_source_value_v1(%s)',source['opening_item_id'])
    return b.verdict(dict(cutover_date=post_date==cut and p['economic_date']==str(cut),source_value=source_value==b.D('57.50'),
      fg_current=current==b.D('34.50'),bs_current=new_bs==b.D('23.00'),fg_was_sourced=abs(before-b.D('33.372'))<=b.D('0.01'),
      bs_was_sourced=abs(old_bs-b.D('22.248'))<=b.D('0.01'),truth=b.truth_quiet(truth,b.all_truth(cur))),
      before=dict(fg=before,bs=old_bs),after=dict(fg=current,bs=new_bs,source=source_value),post_date=post_date)

def validation_controls(cur,today,installed):
    if not installed:return roundtrip(cur,today,False)
    from copy import deepcopy
    cut=today-timedelta(days=10);base=active_unit(cur,rows(cut));results={}
    def attempt(label,edit,code):
        r=deepcopy(base);edit(r)
        api.admin(cur);cur.execute('savepoint be_pocket_negative')
        try:
            out=b.bbp.production_post(cur,today,r,expect=True)
            results[label]=dict(ok=code in str(out['errors']),errors=out['errors'])
        finally:
            api.admin(cur);cur.execute('rollback to savepoint be_pocket_negative');cur.execute('release savepoint be_pocket_negative')
    attempt('missing_document',lambda r:r['OPENING_POCKET_USAGE'][0].update(document_number=''),'BE_POCKET_PROVENANCE')
    attempt('already_allocated_without_reference',lambda r:r['OPENING_POCKET_USAGE'][0].update(allocation_status='ALLOCATED'),'BE_POCKET_PRIOR_ALLOCATION')
    attempt('future_history',lambda r:r['OPENING_POCKET_USAGE'][0].update(physical_date=str(cut)),'BE_POCKET_DATE')
    attempt('incomplete_numerator',lambda r:r['OPENING_POCKET_USAGE'][0].update(control_amount='12.00'),'BE_POCKET_CONTROL')
    attempt('incomplete_denominator',lambda r:r['OPENING_POCKET_SEWING'].pop(),'BE_POCKET_DENOMINATOR_INCOMPLETE')
    attempt('fractional_pieces',lambda r:r['OPENING_POCKET_SEWING'][0].update(qty='4.5'),'BE_POCKET_SEWING_PCS')
    attempt('missing_target',lambda r:r['OPENING_POCKET_SEWING'][0].update(target_source_key='ABSENT'),'BE_POCKET_TARGET_SOURCE_REQUIRED')
    return b.verdict({k:v['ok'] for k,v in results.items()},refusals=results)

def allocated_and_duplicate(cur,today,installed):
    if not installed:return roundtrip(cur,today,False)
    cut=today-timedelta(days=10);r=active_unit(cur,rows(cut));identity='BE-PRIOR-'+uuid.uuid4().hex
    r['OPENING_POCKET_USAGE'][0].update(document_number=identity,allocation_status='ALLOCATED',prior_allocation_reference='APPROVED-HISTORICAL-SHEET')
    expense=b.gl(cur,'OTHER_EXPENSE');f=b.bbp.production_post(cur,today,r)
    history=q(cur,'select original_amount,journal_id from erp.be_pocket_usage_v1 where batch_id=%s',f['batch'])
    p=preview(cur,cut-timedelta(days=1),cut)
    before=(one(cur,'select count(*) from erp.material_stock_movements'),b.gl(cur,'OTHER_EXPENSE'))
    second=b.bbp.production_post(cur,today,r,expect=True)
    unchanged=before==(one(cur,'select count(*) from erp.material_stock_movements'),b.gl(cur,'OTHER_EXPENSE'))
    refused='BE_POCKET_DUPLICATE_SOURCE' in str(second['errors'])
    return b.verdict(dict(no_second_expense=b.gl(cur,'OTHER_EXPENSE')==expense,reference_only=len(history)==1 and history[0][1] is None,
      excluded=p['amount']=='0.00' and not p['can_post'],duplicate_refused=refused,unchanged=unchanged),preview=p,errors=second['errors'])

def return_sale(cur,sale,day):
    api.admin(cur);ident=str(uuid.uuid4())
    allocation,product,lot,location=q(cur,'select a.id,p.product_id,a.lot_id,a.location_id from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id join erp.fg_lots p on p.id=a.lot_id where i.sale_id=%s order by a.id limit 1',sale)[0]
    customer=one(cur,'select customer_id from erp.sales_headers where id=%s',sale)
    cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,status,notes,created_by) values(%s,%s,%s,%s,%s,'DRAFT','BE real customer return',%s)",(ident,'BE-RETURN-'+ident,sale,customer,b.chain.production.at(day,18),b.chain.base.OPERATOR_APP))
    cur.execute("insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,quality_grade,qty_pcs,unit_hpp_snapshot,refund_amount,notes) values(%s,%s,%s,%s,%s,'GRADE_A',1,0,1,'BE return lineage')",(ident,allocation,product,lot,location))
    b.internal(cur,'post_sales_return',ident)
    return ident

def stock_continuation(cur,today,installed):
    if not installed:return roundtrip(cur,today,False)
    import cp6_be_probe as be
    cut=today-timedelta(days=10);r=active_unit(cur,rows(cut))
    r['PRODUCT'].append(dict(r['PRODUCT'][0],sku='{C}T',color_name='BE target colour',product_name='BE cutover target'))
    f=b.bbp.production_post(cur,today,r)
    p=preview(cur,cut-timedelta(days=1),cut);unallocated=amounts(cur)
    pool=call(cur,'POST_PERIOD',dict(period_start=p['period_start'],period_end=p['period_end'],expected_revision=p['revision'],reason='BE C04 before stock lifecycle'))['id']
    lot,product,location=q(cur,"select m.lot_id::text,l.product_id::text,m.location_id::text from erp.be_pocket_sewing_v1 s join erp.fg_stock_movements m on m.source_type='OPENING_BALANCE_ITEM' and m.source_id=s.opening_item_id and m.movement_type='OPENING' join erp.fg_lots l on l.id=m.lot_id where s.batch_id=%s and s.target_kind='FINISHED_GOODS'",f['batch'])[0]
    target=one(cur,'select id::text from erp.products where sku=%s',f['code']+'T')
    customer=b.chain.base.create_customer(cur,'BE-C04-'+uuid.uuid4().hex[:8]);b.chain.production.owner(cur)
    made=one(cur,'select erp.save_sale_draft_v2(%s::jsonb,%s::uuid,null)',b.json.dumps(dict(sale_number='BE-C04-'+uuid.uuid4().hex[:10],customer_id=customer,
      source_location_id=location,sale_date=b.iso(b.chain.production.at(cut+timedelta(days=1),17)),reason='BE opening sale before correction',
      items=[dict(product_id=product,qty_pcs=1,unit_price_snapshot='20000',discount_amount=0)])),str(uuid.uuid4()))
    sale=made['sale_id'];version=one(cur,'select row_version from erp.sales_headers where id=%s',sale)
    b.chain.production.owner(cur);cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale,uuid.uuid4(),version));api.admin(cur)
    converted=be.be(cur,'POST',dict(source_lot_id=lot,target_product_id=target,location_id=location,qty_pcs=1,physical_at=b.iso(b.chain.production.at(cut+timedelta(days=2),15)),reason='BE opening FG converted',expected_version=one(cur,'select erp.be_source_revision_v1(%s,%s)',lot,location)))
    return_sale(cur,sale,cut+timedelta(days=3))
    snapshots=q(cur,'select id,total_hpp from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=%s)',sale)
    old=amounts(cur);truth=b.all_truth(cur);usage=one(cur,'select id::text from erp.be_pocket_usage_v1 where batch_id=%s',f['batch'])
    call(cur,'CORRECT_OPENING_USAGE',dict(usage_id=usage,amount='15.00',expected_amount='11.25',economic_date=str(cut+timedelta(days=4)),reason='BE C04 recost sold returned converted'))
    delta=difference(old,amounts(cur));dest=converted['destination_lot_id'];after=b.all_truth(cur)
    corrected=dict(child=b.lot_value(cur,dest),source=b.lot_value(cur,lot))
    call(cur,'CORRECT_OPENING_USAGE',dict(usage_id=usage,amount='11.25',expected_amount='15.00',economic_date=str(cut+timedelta(days=5)),reason='BE linked downward correction after return and conversion'))
    correction_inverse=amounts(cur)==old
    revision=one(cur,'select erp.pocket_period_state_v1(%s)',pool)['revision']
    call(cur,'CANCEL_PERIOD',dict(id=pool,expected_revision=revision,reason='BE inverse allocation after sold returned converted'))
    final_truth=b.all_truth(cur)
    return b.verdict(dict(qty=be.qty(cur,lot)==2 and be.qty(cur,dest)==1,child=corrected['child']==b.D('11.50'),source=corrected['source']==b.D('34.50'),
      ledger=abs(delta['FG_INVENTORY']-b.D('1.12'))<=b.D('.01') and abs(delta['COGS']-b.D('.75'))<=b.D('.01'),
      correction_inverse=correction_inverse,allocation_inverse=amounts(cur)==unallocated and b.lot_value(cur,dest)==10 and b.lot_value(cur,lot)==30,
      history=snapshots==q(cur,'select id,total_hpp from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=%s)',sale),truth=b.truth_quiet(truth,after) and b.truth_quiet(truth,final_truth)),delta=delta,corrected=corrected,detectors=[truth,after,final_truth])

def mixed_native_historical(cur,today,installed):
    """Two actual 10-piece sources, one imported and one native special contractor.

    Each supplies 11.25 of cost, shared across 20 pieces. Each 10-piece group has
    5 WIP, 3 FG and 2 sold: 5.62 + 3.38 + 2.25, with the residual left in WIP.
    The special contractor uses the same is_special policy as Afui; all native
    movements use the existing receipt/production/warehouse commands.
    """
    if not installed:return roundtrip(cur,today,False)
    import cp6_pocket_period_trial as native
    cut=today-timedelta(days=10)
    f=b.bbp.production_post(cur,today,active_unit(cur,rows(cut)))
    n=native.fixture(api,cur,today,special=True)
    api.admin(cur);start=cut-timedelta(days=1);end=n['end']
    b.boundary.historical.prior.set_open_period(cur,start)
    p=preview(cur,start,end);truth=b.all_truth(cur);old=amounts(cur)
    physical=q(cur,'select id,qty_signed from erp.material_stock_movements order by id')
    sewn=q(cur,'select id,qty_signed from erp.sewing_terminal_events order by id')
    made=call(cur,'POST_PERIOD',dict(period_start=str(start),period_end=str(end),expected_revision=p['revision'],reason='BE actual mixed cutover including special contractor'))
    pool=made['id'];delta=difference(old,amounts(cur))
    source_kinds=q(cur,'select adjustment_id is not null,historical_usage_id is not null,count(*) from erp.pocket_period_sources where pool_id=%s group by 1,2 order by 1,2',pool)
    destinations=q(cur,'select event_id is not null,sum(sewing_qty),sum(erp.pocket_period_amount_v1(pool_id,preceding_qty,sewing_qty)) from erp.pocket_period_destinations where pool_id=%s group by 1 order by 1',pool)
    special=one(cur,"select count(*) from erp.pocket_period_destinations d join erp.contractor_hpp_policy_versions c on c.contractor_id=d.contractor_id where d.pool_id=%s and d.event_id is not null and c.is_special and not c.attendance_required and c.effective_from<=%s and (c.effective_to is null or c.effective_to>=%s)",pool,end,end)
    after=b.all_truth(cur)
    revision=one(cur,'select erp.pocket_period_state_v1(%s)',pool)['revision']
    call(cur,'CANCEL_PERIOD',dict(id=pool,expected_revision=revision,reason='BE undo mixed allocation, preserve both sources'))
    final=b.all_truth(cur)
    return b.verdict(dict(combined=p['quantity']=='20' and p['amount']=='22.50' and p['per_piece']=='1.125000',
      sources=source_kinds==[(False,True,1),(True,False,1)],special_included=special==1,
      destinations=destinations==[(False,10,b.D('11.25')),(True,10,b.D('11.25'))],
      amounts=delta==dict(WIP=b.D('11.24'),FG_INVENTORY=b.D('6.76'),COGS=b.D('4.50'),OTHER_EXPENSE=b.D('-22.50'),OPENING_EQUITY=b.D('0.00')),
      inverse=amounts(cur)==old,no_fake_events=physical==q(cur,'select id,qty_signed from erp.material_stock_movements order by id') and sewn==q(cur,'select id,qty_signed from erp.sewing_terminal_events order by id'),
      truth=b.truth_quiet(truth,after) and b.truth_quiet(truth,final)),preview=p,delta=delta,destinations=destinations,sources=source_kinds,afui_policy_rows=special)

def closed_correction(cur,today,installed):
    """Closed economic dates retain their date and recognize the correction today.
    A report through yesterday must retain every old account balance.
    """
    if not installed:return roundtrip(cur,today,False)
    cut=today-timedelta(days=10);f=b.bbp.production_post(cur,today,active_unit(cur,rows(cut)))
    p=preview(cur,cut-timedelta(days=1),cut)
    pool=call(cur,'POST_PERIOD',dict(period_start=p['period_start'],period_end=p['period_end'],expected_revision=p['revision'],reason='BE period before close'))['id']
    usage=one(cur,'select id::text from erp.be_pocket_usage_v1 where batch_id=%s',f['batch'])
    frozen=q(cur,'select id,to_jsonb(j) from erp.journal_entries j order by id')
    def asof():
        return q(cur,"select l.account_id,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and j.transaction_date<=%s group by l.account_id order by l.account_id",today-timedelta(days=1))
    old=amounts(cur);old_asof=asof();truth=b.all_truth(cur)
    b.boundary.historical.prior.set_open_period(cur,today)
    request=str(uuid.uuid4());payload=dict(usage_id=usage,amount='15.00',expected_amount='11.25',economic_date=str(cut+timedelta(days=1)),reason='BE late correction to closed historical source')
    first=call(cur,'CORRECT_OPENING_USAGE',payload,request);again=call(cur,'CORRECT_OPENING_USAGE',payload,request)
    dates=q(cur,"select j.economic_date,j.transaction_date from erp.journal_entries j where j.id in(select journal_id from erp.be_pocket_source_events_v1 where id=%s union select journal_entry_id from erp.pocket_period_events where pool_id=%s and kind='RECOST') order by j.id",request,pool)
    stale=b.refused(cur,lambda:call(cur,'CORRECT_OPENING_USAGE',payload),'STALE_VERSION')
    invalid=b.refused(cur,lambda:call(cur,'CORRECT_OPENING_USAGE',dict(payload,amount='16.00',expected_amount='15.00',economic_date=str(cut-timedelta(days=1)))),'BE_POCKET_CORRECTION_DATE_REASON')
    after=amounts(cur);newtruth=b.all_truth(cur)
    historic_unchanged=frozen==q(cur,'select id,to_jsonb(j) from erp.journal_entries j where id=any(%s::uuid[]) order by id',[str(x[0]) for x in frozen])
    call(cur,'CORRECT_OPENING_USAGE',dict(payload,amount='11.25',expected_amount='15.00',economic_date=str(cut+timedelta(days=2)),reason='BE reverse late correction with a sourced event'))
    return b.verdict(dict(replay=first==again,closed_posting=len(dates)==2 and all(x==(cut+timedelta(days=1),today) for x in dates),
      asof=old_asof==asof(),history=historic_unchanged,stale=stale['ok'],before_cutover=invalid['ok'],
      delta=difference(old,after)==dict(WIP=b.D('1.88'),FG_INVENTORY=b.D('1.12'),COGS=b.D('.75'),OTHER_EXPENSE=b.D(0),OPENING_EQUITY=b.D('-3.75')),
      inverse=amounts(cur)==old,truth=b.truth_quiet(truth,newtruth) and b.truth_quiet(truth,b.all_truth(cur))),dates=dates,delta=difference(old,after),refusals=[stale,invalid])
