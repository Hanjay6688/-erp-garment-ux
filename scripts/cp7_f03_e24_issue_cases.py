"""P09 receipt/transfer sources through the inherited accessory-note writers.

No payroll installment, paid-source supplier carry or customer-refund policy is
introduced. Fixture master data is administrative; all stock/value facts use
the admitted public/native domain commands.
"""
from datetime import timedelta
from decimal import Decimal as D
import uuid
import cp6_bc_probe as bc
import cp7_procurement_cases as procurement
import cp7_material_cases as material
import cp7_invoice_cases as invoice
import cp7_sales_command_cases as sales_command


def receipt(cur,today,qty='30',zones=False):
    f=bc.fixture(cur,today,purchase=False,zones=zones,days=8)
    p=dict(purchase_number=f['code']+'-P09',supplier_id=f['supplier'],location_id=f['main'],physical_at=bc.local_at(f['received'],9),
      change_reason='E24 source receipt through CP7',lines=[dict(material_id=f['material'],qty=qty,unit_price='2',price_state='ESTIMATED',price_source='MANUAL_ESTIMATE',rolls=[])])
    d=procurement.command(cur,'SAVE_DRAFT',p);d=procurement.post(cur,d)
    f.update(purchase=d['purchase_id'],item=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(d['purchase_id'],)).fetchone()[0]),receipt=d,
      day=f['received'],tag=f['code'],location=f['main'],roll=None,issue_number=f['code']+'-ISSUE',issue_at=bc.local_at(today-timedelta(days=1),10))
    return f


def fixture(cur,today):
    f=receipt(cur,today)
    transfer,_=material.draft(cur,f,'10',dest=f['other'],at=bc.local_at(today-timedelta(days=2),9))
    f['transfer']=material.post(cur,transfer)
    return f


def payload(f):
    return dict(id=None,expected_version=None,number=f['issue_number'],contractor_id=f['mandor'],location_id=f['other'],po_id=None,
      physical_at=f['issue_at'],reason='Seven counted accessories issued from the transferred source',notes='P09 to inherited accessory note',
      items=[dict(material_id=f['material'],qty='7',mode='MANUAL',manual_price='3.25')])


def observe(cur,f):
    row=cur.execute('select id::text from erp.contractor_material_issues where issue_number=%s',(f['issue_number'],)).fetchone()
    document=bc.note_read(cur,dict(id=row[0]))['document'] if row else None
    return dict(stock={loc:bc.stock(cur,f['material'],f[loc]) for loc in ('main','other')},document=document,
      accounts=sales_command.accounts(cur),source=invoice.amounts(cur,f),
      master_price_count=cur.execute('select count(*) from erp.contractor_accessory_price_versions where contractor_id=%s',(f['mandor'],)).fetchone()[0])


def assert_posted(cur,f,before):
    r=observe(cur,f);d=r['document']
    assert r['stock']==dict(main=D(20),other=D(3)) and r['source']==(0,60,23,2),r
    assert d['status']=='POSTED' and D(d['total'])==D('22.75') and len(d['items'])==1
    assert D(d['items'][0]['qty'])==7 and D(d['items'][0]['amount'])==D('22.75')
    assert r['master_price_count']==before['master_price_count']==0
    return r


def issue_inverse(cur,today):
    f=fixture(cur,today);before=observe(cur,f);p=payload(f)
    saved=bc.note_call(cur,'SAVE_DRAFT',p)
    drafted=observe(cur,f);assert drafted['accounts']==before['accounts'] and drafted['stock']==before['stock']
    p.update(id=saved['id'],expected_version=saved['row_version']);key=uuid.uuid4()
    posted=bc.note_call(cur,'POST',p,key);assert_posted(cur,f,before)
    state=procurement.b.boundary.snapshot(cur)
    assert bc.note_call(cur,'POST',p,key)==posted and procurement.b.boundary.snapshot(cur)==state
    reason=dict(id=posted['id'],expected_version=posted['row_version'],reason='Return the exact issue to its source warehouse')
    reverse=bc.note_call(cur,'REVERSE',reason);r=observe(cur,f)
    assert r['accounts']==before['accounts'] and r['stock']==before['stock'] and r['source']==before['source']
    material.reverse(cur,f['transfer'])
    assert bc.stock(cur,f['material'],f['main'])==30 and bc.stock(cur,f['material'],f['other'])==0
    return dict(status='PASS',source_CP7_receipt30_at2_transfer10=True,note7_at3_25_receivable='22.75',stock_after=[20,3],no_master_price_created=True,
      same_note_request_once=True,note_inverse_restores_every_account=True,transfer_inverse_restores30_to_original_warehouse=True)


def material_movements(cur,f):
    return cur.execute("select md5(coalesce(jsonb_agg(jsonb_build_array(id,source_type,source_id,material_id,location_id,qty_signed,extract(epoch from physical_at)) order by id),'[]'::jsonb)::text) from erp.material_stock_movements where material_id=%s",(f['material'],)).fetchone()[0]


def service_return_invoice(cur,today):
    f=receipt(cur,today,'1000',True);baseline=bc.findings(cur);day=today-timedelta(days=6)
    bc.fill(cur,f,120,day)
    bc.use(cur,f,f['SERVICE_POST'],[(40,day+timedelta(days=1),9,'FACTORY_USE')])
    lot=bc.receive(cur,f,'SERVICE_LEFTOVER',[(30,None)],day+timedelta(days=2),from_location_id=f['SERVICE_POST'])['lot_ids'][0]
    bc.inspect(cur,lot,bc.local_at(day+timedelta(days=2),12),'E24 checker',usable=25,damaged=5,usable_to=f['main'],damaged_to=f['DAMAGED'])
    bc.svc(cur,'DISPOSE_STOCK',dict(location_id=f['DAMAGED'],physical_at=bc.local_at(day+timedelta(days=3),9),items=[dict(material_id=f['material'],qty='5')],reason='Five inspected unusable pieces disposed'))
    _,item=bc.note(cur,f,10,'3.00',day+timedelta(days=3))
    nlot=bc.receive(cur,f,'NOTE_RETURN',day=day+timedelta(days=4),note_item_id=item,qty='4')['lot_ids'][0]
    bc.inspect(cur,nlot,bc.local_at(day+timedelta(days=4),12),'E24 checker',usable=4)
    bc.policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
    bc.credit(cur,nlot,'USABLE',4,bc.local_at(day+timedelta(days=5),9),f['main'])
    assert invoice.amounts(cur,f)==(0,2000,949,2)
    movements=material_movements(cur,f)
    p=invoice.payload(f,'1000','2.10');p.update(invoice_date=str(today),received_at=bc.local_at(today,8),due_date=str(today+timedelta(days=30)))
    result=invoice.finalize(cur,f,p=p);bc.internal(cur,'process_cost_recalc_queue',100)
    assert invoice.amounts(cur,f)==(2100,0,949,D('2.10'))
    assert material_movements(cur,f)==movements,'LATE_INVOICE_CREATED_PHYSICAL_FACT'
    assert cur.execute('select erp.bc_note_item_collectible_v1(%s)',(item,)).fetchone()[0]==18
    assert cur.execute("select bool_and(unit_cost_snapshot=2.10) from erp.material_stock_movements where material_id=%s and source_type='BC_NOTE_RETURN_CREDIT'",(f['material'],)).fetchone()[0]
    assert abs(bc.gl(cur,'MATERIAL_INVENTORY')-bc.subledger_value(cur))<=D('.05')
    assert bc.new_findings(baseline,bc.findings(cur))=={}
    invoice.reverse(cur,f,result['invoice_id']);bc.internal(cur,'process_cost_recalc_queue',100)
    assert invoice.amounts(cur,f)==(0,2000,949,2) and material_movements(cur,f)==movements
    assert cur.execute('select erp.bc_note_item_collectible_v1(%s)',(item,)).fetchone()[0]==18
    return dict(status='PASS',CP7_receipt_and_late_invoice=True,service_fill120_use40_inspect25good5bad_dispose5=True,note10_return4_credit12=True,
      remaining_quantity=949,mandor_collectible=18,source_AP=2100,source_GRNI=0,remaining_material_value='1992.90',late_invoice_reprices_return_without_physical_duplication=True,
      invoice_inverse_AP0_GRNI2000_cost2=True,no_new_integrity_findings=True)


def cases(cur,today):
    return [('F03_E24_TRANSFER_NOTE_INVERSE',lambda:issue_inverse(cur,today)),('F03_E24_SERVICE_NOTE_RETURN_LATE_INVOICE',lambda:service_return_invoice(cur,today))]
