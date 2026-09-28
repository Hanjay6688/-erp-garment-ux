"""Independent CP6 final probe: can a backdated SKU move rewrite a posted lot's historical commercial identity?"""
from datetime import timedelta
import json

import cp6_bf_combined_probe as p


def backdated_move_after_posted_fg(cur, today):
    f=p.fixture(cur, today)
    wash=p.wash(cur,f,range(4),11)
    p.finish(cur,f,[wash],range(4),13)
    lot=p.lots(cur,f)[3]
    stamp=f['when'](13)
    before=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',f['roots'][3],stamp)
    assert before==f['z']['sku'], ('PRECONDITION_OLD_SKU',before)
    old_stock=p.stock(cur,lot)
    cur.execute('savepoint independent_backdate')
    try:
        p.move34(cur,f,12)
    except Exception as exc:
        cur.execute('rollback to savepoint independent_backdate')
        cur.execute('release savepoint independent_backdate')
        p.b.api.admin(cur)
        return dict(status='PASS' if 'financial commitment time' in str(exc) else 'INCOMPLETE',posted_lot=lot,original_sku=before,
            guard=str(exc).splitlines()[0][:500],stock_pcs=old_stock)
    cur.execute('release savepoint independent_backdate')
    after=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',f['roots'][3],stamp)
    same_lot=p.one(cur,'select id::text from erp.fg_lots where id=%s',lot)==lot
    same_stock=p.stock(cur,lot)==old_stock
    return dict(status='COUNTEREXAMPLE' if after!=before else 'INCOMPLETE',
        posted_lot=lot,produced_at=stamp.isoformat(),backdated_effective_at=f['when'](12).isoformat(),
        original_sku=before,after_sku=after,same_physical_lot=same_lot,same_stock_qty=same_stock,
        explanation='Existing posted FG maps to a different SKU at its original timestamp after a permitted backdated edit.')


def backdated_move_after_posted_sale(cur,today):
    f=p.fixture(cur,today)
    wash=p.wash(cur,f,range(4),11)
    p.finish(cur,f,[wash],range(4),13)
    lot=p.lots(cur,f)[3]
    sale=p.sale(cur,f,3,1,15)
    at=f['when'](13)
    before=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',f['roots'][3],at)
    assert before==f['z']['sku']
    cur.execute('savepoint independent_sale_backdate')
    try:
        p.move34(cur,f,12)
    except Exception as exc:
        cur.execute('rollback to savepoint independent_sale_backdate')
        cur.execute('release savepoint independent_sale_backdate')
        p.b.api.admin(cur)
        return dict(status='PASS' if 'financial commitment time' in str(exc) else 'INCOMPLETE',sale_id=sale,posted_lot=lot,guard=str(exc).splitlines()[0][:500])
    cur.execute('release savepoint independent_sale_backdate')
    after=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',f['roots'][3],at)
    sold=p.one(cur,'select count(*) from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s and a.lot_id=%s',sale,lot)
    return dict(status='COUNTEREXAMPLE' if after!=before and sold>0 else 'INCOMPLETE',
        sale_id=sale,posted_lot=lot,original_sku=before,after_sku=after,sale_allocation_count=sold,
        explanation='Sale remains allocated to the exact lot, but its historical SKU has changed.')



def backdated_move_after_posted_conversion(cur,today):
    f=p.fixture(cur,today)
    wash=p.wash(cur,f,range(4),11)
    p.finish(cur,f,[wash],range(4),13)
    source=p.lots(cur,f)[1]
    label='BFC-CONV-'+p.uuid.uuid4().hex[:8]
    target=p.b.sized_product(cur,f['size_ids'][1],label)
    sibling=p.b.sized_product(cur,f['size_ids'][2],label)
    a=p.bf.group(cur,[target],f['when'](14))
    z=p.bf.group(cur,[sibling],f['when'](14))
    p.bf.save(cur,[a,z],f['when'](14))
    sent=p.bf.be.be(cur,'POST',dict(source_lot_id=source,target_product_id=target,
        location_id=p.base.LOCATION,qty_pcs=1,physical_at=f['when'](15).isoformat(),
        reason='Independent conversion before commercial range move',
        expected_version=p.one(cur,'select erp.be_source_revision_v1(%s,%s)',source,p.base.LOCATION)))
    destination=sent['destination_lot_id']
    stamp=f['when'](15)
    before=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',target,stamp)
    assert before==a['sku'],('PRECONDITION_CONVERSION_SKU',before)
    assert p.one(cur,'select count(*) from erp.fg_lots where id=%s',destination)==1
    def document():
        p.prod.owner(cur)
        payload=p.one(cur,'select public.erp_get_product_conversion_workspace_v1(%s::jsonb)',json.dumps({}))
        p.b.api.admin(cur)
        return next(row for row in payload['documents'] if row['id']==sent['conversion_id'])
    before_document=document()['target_sku']
    before_hpp=p.report(cur,a['sku'],stamp+timedelta(seconds=1))['groups']
    before_stock=p.stock(cur,destination)
    at=f['when'](14,30)
    a2=p.bf.group(cur,[target],at,sku=a['sku'],gid=a['id'],revision=1)
    a2.update(members=[],legacy_basis=[])
    z2=p.bf.group(cur,[sibling,target],at,sku=z['sku'],gid=z['id'],revision=1)
    cur.execute('savepoint independent_conversion_backdate')
    try:
        p.bf.save(cur,[a2,z2],at)
    except Exception as exc:
        cur.execute('rollback to savepoint independent_conversion_backdate')
        cur.execute('release savepoint independent_conversion_backdate')
        p.b.api.admin(cur)
        return dict(status='PASS' if 'financial commitment time' in str(exc) or 'BF_TARIFF_HISTORY' in str(exc) else 'INCOMPLETE',conversion_id=sent['conversion_id'],destination_lot=destination,
            original_sku=before,guard=str(exc).splitlines()[0][:500])
    cur.execute('release savepoint independent_conversion_backdate')
    after=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',target,stamp)
    after_document=document()['target_sku']
    old_hpp=p.report(cur,a['sku'],stamp+timedelta(seconds=1))['groups']
    new_hpp=p.report(cur,z['sku'],stamp+timedelta(seconds=1))['groups']
    same_lot=p.one(cur,'select count(*) from erp.fg_lots where id=%s',destination)==1
    same_stock=p.stock(cur,destination)==before_stock
    return dict(status='COUNTEREXAMPLE' if after!=before and after_document!=before_document and same_lot and same_stock else 'INCOMPLETE',
        document_label_before=before_document,document_label_after=after_document,
        historical_hpp_before=[dict(sku=x['sku'],qty=x['qty'],value=x['value']) for x in before_hpp],
        historical_hpp_old_after=[dict(sku=x['sku'],qty=x['qty'],value=x['value']) for x in old_hpp],
        historical_hpp_new_after=[dict(sku=x['sku'],qty=x['qty'],value=x['value']) for x in new_hpp],
        same_physical_lot=same_lot,same_stock_qty=same_stock,
        conversion_id=sent['conversion_id'],destination_lot=destination,
        physical_at=stamp.isoformat(),backdated_effective_at=at.isoformat(),
        original_sku=before,after_sku=after,
        explanation='Already-posted conversion destination changes historical commercial SKU without changing the physical lot.')


def cases(cur,today):
    return [
        ('INDEPENDENT:BACKDATE_AFTER_POSTED_FG',lambda:backdated_move_after_posted_fg(cur,today)),
        ('INDEPENDENT:BACKDATE_AFTER_POSTED_SALE',lambda:backdated_move_after_posted_sale(cur,today)),
        ('INDEPENDENT:BACKDATE_AFTER_POSTED_CONVERSION',lambda:backdated_move_after_posted_conversion(cur,today)),
    ]
