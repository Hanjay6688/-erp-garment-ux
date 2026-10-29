"""Disposable Native fixtures. No posted movement/HPP/journal is inserted here.

Masters and DRAFT opening documents are synthetic setup. Their authoritative
facts are posted by the existing Native opening/production/sales writers.
This does not claim that those prerequisites were created in a browser.
"""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp6_be_probe as be
import cp6_bf_probe as bf

b,one=bf.b,bf.one
BASE=b.chain.base
LEDGERS=('fg_stock_movements','hpp_versions','hpp_version_components','journal_entries','journal_lines','sale_stock_allocations')

def owner(cur):b.chain.production.owner(cur)
def admin(cur):b.api.admin(cur)

def public(cur,name,*args):
    owner(cur)
    result=cur.execute('select public.'+name+'('+','.join(['%s']*len(args))+')',args).fetchone()[0]
    admin(cur);return result

def public_as(cur,subject,name,*args):
    b.bcp.session(cur,subject)
    result=cur.execute('select public.'+name+'('+','.join(['%s']*len(args))+')',args).fetchone()[0]
    admin(cur);return result

def workspace(cur,filters=None):
    return public(cur,'erp_get_product_conversion_workspace_v1',json.dumps(filters or{},default=str))

def preview(cur,payload):return workspace(cur,dict(preview=payload))['preview']

def review(cur,payload):
    evidence=preview(cur,payload)
    return dict(payload,expected_version=evidence['source_revision']),evidence

def action(cur,kind,payload,key=None):
    return public(cur,'erp_save_product_conversion_action_v1',kind,json.dumps(payload,default=str),str(key or uuid.uuid4()))

def pair(cur,source,target,key=None,revision=None):
    admin(cur)
    revision=revision or one(cur,'select cp7_sku_conversion.pair_revision_v1()')
    p=dict(source_group_id=source,target_group_id=target,expected_version=revision,reason='Owner29 Native pair fixture')
    return public(cur,'erp_save_sku_action_v1','SAVE_PAIR',json.dumps(p),str(key or uuid.uuid4())),p

def native_ledgers(cur):
    admin(cur);zone=one(cur,'show timezone')
    try:
        cur.execute("set local timezone='UTC'")
        return {table:one(cur,'select md5(coalesce(jsonb_agg(to_jsonb(t)order by id),\'[]\'::jsonb)::text)from erp.'+table+' t')for table in LEDGERS}
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))

def stocks(cur,product,location):
    admin(cur)
    return one(cur,'select cp7_sku_conversion.stock_v1(%s,%s)',product,location)

def books(cur):return {key:b.gl(cur,key)for key in('FG_INVENTORY','COGS','WIP','OTHER_INCOME','OTHER_EXPENSE')}

def product_books(cur,product):
    admin(cur)
    target=cur.execute('select *from erp.compute_non_po_product_hpp_targets_v2620f(%s)',(product,)).fetchone()
    book=cur.execute('select *from erp.compute_non_po_product_hpp_book_v2620f(%s)',(product,)).fetchone()
    assert target==book,(product,target,book)
    return [str(value)for value in target]

def custom_group_products(cur,labels=('34','35','36')):
    admin(cur);model,brand=str(uuid.uuid4()),str(uuid.uuid4());tag=uuid.uuid4().hex[:10]
    cur.execute("insert into erp.product_models(id,model_code,model_name,is_active)values(%s,%s,'SKU29 different model',true)",(model,'S29M-'+tag))
    cur.execute("insert into erp.brands(id,brand_code,brand_name,is_active)values(%s,%s,'SKU29 different brand',true)",(brand,'S29B-'+tag))
    rows=[]
    for i,label in enumerate(labels):
        size,product=str(uuid.uuid4()),str(uuid.uuid4())
        cur.execute('insert into erp.sizes(id,size_code,sort_order,is_active)values(%s,%s,%s,true)',(size,'S29-'+tag+'-'+label,200+i))
        cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order)values(%s,%s,%s)',(model,size,200+i))
        cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)
          select %s,%s,%s,%s,'S29-BLUE',%s,%s,%s,effective_from,true,true from erp.products where id=%s""",
          (product,'S29-'+tag+'-'+label,model,brand,size,'SKU29 target '+label,product,BASE.BASE_PRODUCT))
        cur.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes)values(%s,'S29-EMPTY','2026-01-01',true,'Explicit empty fixture BOM')",(product,))
        rows.append((product,size))
    return rows

def masters(cur):
    admin(cur);now=one(cur,'select clock_timestamp()');effective=now-timedelta(minutes=4)
    rows=bf.products(cur,('31','32','33'),'S29-'+uuid.uuid4().hex[:8]);target_rows=custom_group_products(cur)
    groups=[bf.group(cur,[p for p,_ in rows],effective),bf.group(cur,[p for p,_ in target_rows],effective)]
    for _ in range(2):groups.append(bf.group(cur,[p for p,_ in bf.products(cur,('27',))],effective))
    bf.save(cur,groups,effective)
    return dict(now=now,at=(now-timedelta(seconds=60)).isoformat(),reserve_at=(now-timedelta(seconds=90)).isoformat(),
      back_at=(now-timedelta(seconds=30)).isoformat(),source=rows[0][0],target=target_rows[0][0],other=target_rows[1][0],
      source_roots=[p for p,_ in rows],target_roots=[p for p,_ in target_rows],groups=groups,location=BASE.LOCATION)

def opening(cur,product,qty,unit,day):
    admin(cur);ident=str(uuid.uuid4())
    cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by)values(%s,%s,%s,'DRAFT',%s)",
      (ident,'S29-'+ident,day,BASE.OPERATOR_APP))
    cur.execute("insert into erp.opening_balance_items(opening_id,balance_type,product_id,location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method)values(%s,'FINISHED_GOODS',%s,%s,%s,%s,'GRADE_A','MANUAL')",
      (ident,product,BASE.LOCATION,qty,str(unit)))
    b.internal(cur,'post_opening_balance',ident);admin(cur)
    # The opening posting has one item, so its new lot is identified by the
    # document's item provenance rather than a latest-created guess.
    lots=cur.execute("select distinct m.lot_id::text from erp.fg_stock_movements m join erp.opening_balance_items i on i.id=m.source_id where m.source_type='OPENING_BALANCE_ITEM'and i.opening_id=%s and i.product_id=%s",(ident,product)).fetchall()
    assert len(lots)==1,('SKU29_OPENING_NATIVE_PROVENANCE',ident,lots)
    return lots[0][0]

def reserve(cur,f,product,qty,at=None):
    admin(cur);customer=BASE.create_customer(cur,'S29-'+uuid.uuid4().hex[:8])
    p=dict(sale_number='S29-SALE-'+uuid.uuid4().hex[:12],customer_id=customer,source_location_id=f['location'],
      sale_date=at or f['reserve_at'],reason='SKU29 Native reservation',items=[dict(product_id=product,qty_pcs=qty,unit_price_snapshot='185000',discount_amount=0)])
    result=b.internal(cur,'save_sale_draft_v2',json.dumps(p),str(uuid.uuid4()),None);admin(cur)
    return result['sale_id']

def cancel_reservation(cur,sale):
    admin(cur);version=one(cur,'select row_version from erp.sales_headers where id=%s',sale)
    b.internal(cur,'cancel_sale_draft_v2',sale,'SKU29 release actual reservation',str(uuid.uuid4()),version);admin(cur)

def payload(f,qty=4,target=None,source=None,at=None):
    return dict(source_product_id=source or f['source'],target_product_id=target or f['target'],location_id=f['location'],
      qty_pcs=qty,physical_at=at or f['at'],reason='Owner29 mixed garments manual SKU correction')

def nonpo(cur,today,reservation=True):
    f=masters(cur)
    f['lots']=[opening(cur,f['source'],3,'10.01',today-timedelta(days=3)),opening(cur,f['source'],7,'20.02',today-timedelta(days=2))]
    f['target_lot']=opening(cur,f['target'],4,'30.03',today-timedelta(days=4))
    if reservation:f['reserved_sale']=reserve(cur,f,f['source'],1)
    f['payload']=payload(f)
    return f

def allocations(cur,result):
    admin(cur)
    return [dict(zip(('conversion_id','source_lot_id','destination_lot_id','qty_pcs','unit_hpp','destination_value'),row))for row in cur.execute(
      """select a.conversion_id::text,a.source_lot_id::text,a.destination_lot_id::text,a.qty_pcs,a.original_hpp_per_pcs::text,h.total_cost::text
      from cp7_sku_conversion.members_v1 m join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id
      join erp.hpp_versions h on h.lot_id=a.destination_lot_id and h.is_current where m.group_id=%s order by m.line_no""",(result['conversion_id'],)).fetchall()]
