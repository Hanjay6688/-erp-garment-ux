"""Disposable E01 production sources and read-only browser result observations."""
from datetime import date
from urllib.parse import urlparse
import json
import os
import sys
import psycopg
import cp7_f03_e01_cases as cases


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    op, p = sys.argv[1], json.loads(sys.argv[2])
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had: cur.execute('grant usage on schema erp to authenticated')
        if op == 'prepare':
            out = cases.production(cur, date.fromisoformat(p['today']))
            out['today'] = p['today']
            out['destination_name'] = cur.execute('select location_name from erp.locations where id=%s', (out['location'],)).fetchone()[0]
        elif op == 'read':
            found = cur.execute('select id::text from erp.sales_headers where sale_number=%s', (p['tag'],)).fetchone()
            f = dict(p, sale=found[0]) if found else None
            out = dict(document=cases.source.read(cur, f)['detail'] if f else None,
                       returns=cases.returns.read(cur, f, 'RETURNS') if f else None,
                       cash=cases.payments.cash(cur, f) if f else None,
                       available=cases.physical(cur, p),
                       accounts={k:str(v) for k,v in cases.cmd.accounts(cur).items()},
                       report=cases.ready_report(cur, date.fromisoformat(p['today'])))
            out['fg_value'] = str(cur.execute('select sum(m.qty_signed*h.hpp_per_pcs) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id join erp.v_current_hpp h on h.lot_id=l.id where l.po_id=%s', (p['po'],)).fetchone()[0])
        else: raise ValueError('Unknown E01 fixture operation')
        cases.b.api.admin(cur)
        if not had: cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0] == had
        conn.commit()
    print(json.dumps(out, default=str))


if __name__ == '__main__': main()
