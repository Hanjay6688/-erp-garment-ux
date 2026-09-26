"""Writer ALL-C04 continuation of historical pocket expense; native database only."""
from datetime import timedelta
import uuid
import cp6_bd_probe as b
api,one,q=b.api,b.one,b.q

def rows(cutover):
    r=b.bcp.po_rows(target='5',wip=('5','50.00'))
    r['MATERIAL']=[dict(material_sku='{C}K',material_name='BE kain kantong historis',material_type='FABRIC',unit_code='YARD')]
    r['OPENING_BALANCE_ITEM'].append(dict(balance_type='FINISHED_GOODS',product_sku='{C}P',location_code='{C}G',qty='3',unit_cost='10.00',quality_grade='GRADE_A',hpp_input_method='MANUAL',opening_source_key='FG',control_key='FG'))
    r['OPENING_CONTROL'].append(dict(control_key='FG',balance_type='FINISHED_GOODS',qty='3',amount='30.00'))
    day=str(cutover-timedelta(days=1))
    r['OPENING_POCKET_USAGE']=[dict(document_number='KELUAR-{C}',line_number='1',physical_date=day,material_sku='{C}K',qty='5',amount='11.25',allocation_status='UNALLOCATED',control_key='POCKET',control_qty='5',control_amount='11.25')]
    r['OPENING_POCKET_SEWING']=[dict(document_number='JAHIT-{C}',line_number=str(i),physical_date=day,contractor_code='{C}',qty=str(n),target_kind=k,**fields)
       for i,n,k,fields in [(1,5,'WIP',dict(target_source_key='WIP')),(2,3,'FINISHED_GOODS',dict(target_source_key='FG')),(3,2,'COGS',dict(product_sku='{C}P',sold_reference='JUAL-LAMA-{C}'))]]
    return r

def call(cur,action,payload,key=None):
    b.bcp.session(cur);result=one(cur,'select public.erp_save_pocket_fabric_action_v1(%s,%s::jsonb,%s)',action,b.json.dumps(payload,default=str),key or str(uuid.uuid4()));api.admin(cur);return result

def preview(cur,start,end):
    b.bcp.session(cur);result=one(cur,'select public.erp_preview_pocket_fabric_period_v1(%s,%s)',start,end);api.admin(cur);return result

def amounts(cur):return {k:b.gl(cur,k) for k in ['WIP','FG_INVENTORY','COGS','OTHER_EXPENSE','OPENING_EQUITY']}
def difference(a,z):return {k:z[k]-v for k,v in a.items()}

def roundtrip(cur,today,installed):
    cut=today-timedelta(days=10);r=rows(cut)
    if not installed:
        batch=api.call(cur,'CREATE',dict(batch_code='BE-PRE-'+uuid.uuid4().hex[:12],cutover_date=str(cut)))['batch_id']
        return b.no_route(cur,lambda:api.upload(cur,batch,'OPENING_POCKET_USAGE',r['OPENING_POCKET_USAGE']))
    api.admin(cur);r['MATERIAL'][0]['unit_code']=one(cur,"select unit_code from erp.materials where material_type='FABRIC' order by id limit 1")
    f=b.bbp.production_post(cur,today,r);start=cut-timedelta(days=1)
    origin=q(cur,'select id::text from erp.be_pocket_usage_v1 where batch_id=%s',f['batch'])[0][0]
    fake_before=(one(cur,'select count(*) from erp.material_stock_movements'),one(cur,'select count(*) from erp.sewing_terminal_events'))
    truth=b.all_truth(cur);g0=amounts(cur);p=preview(cur,start,cut);key=str(uuid.uuid4())
    payload=dict(period_start=str(start),period_end=str(cut),expected_revision=p['revision'],reason='BE C04 actual historical period')
    post=call(cur,'POST_PERIOD',payload,key);again=call(cur,'POST_PERIOD',payload,key)
    first=difference(g0,amounts(cur));pool=post['id'];truth1=b.all_truth(cur)
    corr=call(cur,'CORRECT_OPENING_USAGE',dict(usage_id=origin,amount='15.00',expected_amount='11.25',economic_date=str(cut+timedelta(days=1)),reason='BE source sheet correction'),str(uuid.uuid4()))
    second=difference(g0,amounts(cur));truth2=b.all_truth(cur)
    revision=one(cur,'select erp.pocket_period_state_v1(%s)',pool)['revision']
    call(cur,'CANCEL_PERIOD',dict(id=pool,expected_revision=revision,reason='BE inverse allocation only'))
    inverse=difference(g0,amounts(cur));unchanged=fake_before==(one(cur,'select count(*) from erp.material_stock_movements'),one(cur,'select count(*) from erp.sewing_terminal_events'))
    return b.verdict(dict(quantity=p['quantity']=='10',amount=p['amount']=='11.25',no_fake_events=unchanged,replay=post==again,
      first=first['WIP']==b.D('5.62') and first['FG_INVENTORY']==b.D('3.38') and first['COGS']==b.D('2.25') and first['OTHER_EXPENSE']==b.D('-11.25'),
      correction=second['WIP']==b.D('7.50') and second['FG_INVENTORY']==b.D('4.50') and second['COGS']==b.D('3.00') and second['OTHER_EXPENSE']==b.D('-11.25'),
      inverse=inverse['WIP']==inverse['FG_INVENTORY']==inverse['COGS']==0 and inverse['OTHER_EXPENSE']==b.D('3.75'),
      truth=b.truth_quiet(truth,truth1) and b.truth_quiet(truth,truth2)),first=first,corrected=second,inverse=inverse,preview=p,correction=corr)

def receipt_correction(cur,today,installed):
    cut=today-timedelta(days=10);r=rows(cut)
    if not installed:
        batch=api.call(cur,'CREATE',dict(batch_code='BE-RECPRE-'+uuid.uuid4().hex[:12],cutover_date=str(cut)))['batch_id']
        return b.no_route(cur,lambda:api.upload(cur,batch,'OPENING_POCKET_USAGE',r['OPENING_POCKET_USAGE']))
    api.admin(cur);r['MATERIAL'][0]['unit_code']=one(cur,"select unit_code from erp.materials where material_type='FABRIC' order by id limit 1")
    r['SUPPLIER']=[dict(supplier_code='{C}',supplier_name='BE pocket supplier',supplier_type='MATERIAL')]
    r['LOCATION'].append(dict(location_code='{C}R',location_name='BE raw warehouse',location_type='RAW_MATERIAL_WAREHOUSE'))
    r['OPENING_BALANCE_ITEM'].append(dict(balance_type='MATERIAL',material_sku='{C}K',location_code='{C}R',qty='15',unit_cost='2.25',opening_source_key='STOCK',control_key='STOCK'))
    r['OPENING_CONTROL'] += [dict(control_key='STOCK',balance_type='MATERIAL',qty='15',amount='33.75'),dict(control_key='GRNI',balance_type='GRNI_MATERIAL',qty='20',amount='45.00')]
    r['UNINVOICED_RECEIPT']=[dict(receipt_number='RCV-{C}',receipt_line_number='1',receipt_date=str(cut-timedelta(days=3)),supplier_code='{C}',material_sku='{C}K',location_code='{C}R',qty='20',unit_cost='2.25',opening_source_key='STOCK',control_key='GRNI')]
    r['OPENING_POCKET_USAGE'][0].update(supplier_code='{C}',receipt_number='RCV-{C}',receipt_line_number='1')
    f=b.bbp.production_post(cur,today,r);start=cut-timedelta(days=1);p=preview(cur,start,cut)
    pool=call(cur,'POST_PERIOD',dict(period_start=str(start),period_end=str(cut),expected_revision=p['revision'],reason='BE receipt-backed historical pool'))['id']
    row=q(cur,'select s.id::text,l.purchase_item_id::text,p.material_id::text from erp.initial_import_receipt_headers h join erp.initial_import_receipt_lines l on l.purchase_id=h.purchase_id join erp.suppliers s on s.id=h.supplier_id join erp.material_purchase_items p on p.id=l.purchase_item_id where h.batch_id=%s',f['batch'])[0]
    old=amounts(cur);material=one(cur,'select cached_stock_qty from erp.materials where id=%s',row[2]);stock_moves=one(cur,'select count(*) from erp.material_stock_movements where material_id=%s',row[2]);truth=b.all_truth(cur)
    trial=b.bbp.receipt_trial;doc=trial.post_invoice(api,cur,trial.invoice(api,cur,today,dict(supplier_id=row[0],purchase_item_id=row[1]),'20','3.00',date=cut+timedelta(days=1)))
    api.admin(cur);delta=difference(old,amounts(cur));newtruth=b.all_truth(cur)
    pool_value=one(cur,'select erp.pocket_period_total_v1(%s)',pool)
    trial.rpc(api,cur,'reverse_material_supplier_invoice_v2',doc['supplier_invoice_id'],'BE C04 invoice inverse',uuid.uuid4(),doc['row_version']);api.admin(cur)
    restored=difference(old,amounts(cur))
    return b.verdict(dict(receipt_quantity=material==15,stock_not_drawn_twice=one(cur,'select cached_stock_qty from erp.materials where id=%s',row[2])==15 and stock_moves==one(cur,'select count(*) from erp.material_stock_movements where material_id=%s',row[2]),
     recost=pool_value==15 and delta['WIP']==b.D('1.88') and delta['FG_INVENTORY']==b.D('1.12') and delta['COGS']==b.D('0.75') and delta['OTHER_EXPENSE']==0,
     inverse=all(x==0 for x in restored.values()),truth=b.truth_quiet(truth,newtruth)),delta=delta,restored=restored,pool_value=pool_value)
