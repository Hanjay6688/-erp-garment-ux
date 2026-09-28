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
        return dict(status='PASS',posted_lot=lot,original_sku=before,
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
        return dict(status='PASS',sale_id=sale,posted_lot=lot,guard=str(exc).splitlines()[0][:500])
    cur.execute('release savepoint independent_sale_backdate')
    after=p.one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',f['roots'][3],at)
    sold=p.one(cur,'select count(*) from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s and a.lot_id=%s',sale,lot)
    return dict(status='COUNTEREXAMPLE' if after!=before and sold>0 else 'INCOMPLETE',
        sale_id=sale,posted_lot=lot,original_sku=before,after_sku=after,sale_allocation_count=sold,
        explanation='Sale remains allocated to the exact lot, but its historical SKU has changed.')


def cases(cur,today):
    return [
        ('INDEPENDENT:BACKDATE_AFTER_POSTED_FG',lambda:backdated_move_after_posted_fg(cur,today)),
        ('INDEPENDENT:BACKDATE_AFTER_POSTED_SALE',lambda:backdated_move_after_posted_sale(cur,today)),
    ]
