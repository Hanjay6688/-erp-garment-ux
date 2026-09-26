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
