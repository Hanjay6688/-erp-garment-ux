"""Writer BD completion: seed/read only on the browser runtime's disposable copy.

The sale is fixture setup through the existing sale commands, not a browser-sale claim.
The browser under test fills the missing laundry price and reads the pending-HPP UI.
Expected deltas (D11 no. 11): 10 PCS, 2 sold, missing 1000/PCS -> lot +10000,
remaining FG +8000, COGS +2000; original sale snapshot stays unchanged.
"""
from datetime import date, timedelta
import json
import os
import sys
from urllib.parse import urlparse

import psycopg
import cp6_bd_probe as bdp


def read(cur, fx):
    bdp.chain.actors.admin(cur)
    sale = bdp.q(cur, "select a.qty_pcs::text,a.unit_hpp_snapshot::text from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s order by a.lot_id,a.sale_item_id", fx['sale'])
    return dict(lot_value=str(bdp.lot_value(cur, fx['lot'])),
                fg=str(bdp.gl(cur, 'FG_INVENTORY')), cogs=str(bdp.gl(cur, 'COGS')),
                blockers=bdp.blockers(cur, fx['day'], fx['delivery']), sale= sale,
                view=bdp.pending_cost(cur, fx['vendor']))


def create(cur, today):
    fx = bdp.fixture(cur, today - timedelta(days=1), 'GPT-DEC04-BROWSER')
    g = bdp.component(cur, fx, 'GPT_GAR', '5000.00')
    s = bdp.component(cur, fx, 'GPT_SPR', None, status='UNKNOWN')
    bdp.terms(cur, fx, 'COMPONENTS')
    sent = bdp.post_priced(cur, fx, dict(components=[dict(component_id=g, covered_qty=10), dict(component_id=s, covered_qty=10)]))
    rec = bdp.receive(cur, sent['delivery_id'], fx, 10, 13)
    product, lot = bdp.finish_goods(cur, fx, rec['receipt_id'], 10, 14)
    bdp.policy(cur, 'LAU_DEC04', dict(sale_with_unknown_laundry='ALLOW_PENDING'))
    sale = bdp.sell(cur, fx, product, 2, 15)
    charge = bdp.one(cur, "select c.id::text from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id where l.delivery_id=%s and c.rate_status='UNKNOWN'", sent['delivery_id'])
    result = dict(vendor=fx['vendor'], product=product, lot=lot, sale=sale,
                  delivery=sent['delivery_id'], charge=charge, day=str(fx['day']), label='BD GPT_SPR')
    result['before'] = read(cur, result)
    return result


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    parsed = urlparse(target)
    if parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.path != '/cp6_auditor_browser':
        raise RuntimeError('FIXTURE_DISPOSABLE_BROWSER_COPY_ONLY')
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        if sys.argv[1] == 'create':
            result = create(cur, date.fromisoformat(sys.argv[2]))
            conn.commit()
        elif sys.argv[1] == 'read':
            result = read(cur, json.loads(sys.argv[2]))
            conn.rollback()
        else:
            raise RuntimeError('UNKNOWN_FIXTURE_OPERATION')
    print(json.dumps(result, default=str))


if __name__ == '__main__':
    main()
