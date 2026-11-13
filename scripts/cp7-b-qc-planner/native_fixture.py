"""Prepare and read only the two B cases on the retained disposable browser host."""

from contextlib import redirect_stdout
from datetime import date, timedelta
from hashlib import sha1
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
from uuid import uuid4

import psycopg

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
EXPECTED_QC_BLOB = '5a1831fd851b04f5fcff59e6ed2d39795d1345e3'


def qc_module():
    root = Path(os.environ.get('CP7_B_QC_RETAINED_ROOT', SCRIPTS.parent))
    sources = root / 'docs/cp7/review/shutdown-20261111/sku-43166466578-combined'
    probe = sources / 'qc-p19/qc_cost_source_probe.py'
    if not probe.is_file():
        raise RuntimeError('BLOCKED: checkout bukti QC 7b337376 dan arahkan CP7_B_QC_RETAINED_ROOT ke checkout itu')
    body = probe.read_bytes()
    if sha1(f'blob {len(body)}\0'.encode() + body).hexdigest() != EXPECTED_QC_BLOB:
        raise RuntimeError('BLOCKED: sumber fixture QC tidak cocok dengan blob bukti 7b337376')
    sys.path[:0] = [str(probe.parent), str(sources)]
    import qc_cost_source_probe
    return qc_cost_source_probe


def label(cur, product):
    sku, size, code, root, commercial = cur.execute("""
        select p.sku, p.size_id, s.size_code, coalesce(p.identity_root_id,p.id),
               erp.bf_commercial_sku_at_v1(p.id,statement_timestamp())
        from erp.products p join erp.sizes s on s.id=p.size_id where p.id=%s
    """, (product,)).fetchone()
    return dict(product=product, sku=sku, commercialSku=commercial, size=size, sizeCode=code, root=root, targetKey=f'{root}:{size}')


def set_active_policy(cur, products):
    import cp6_bf_probe as commercial
    import cp7_identity_cases as policy
    at = cur.execute("select clock_timestamp()-interval '1 second'").fetchone()[0]
    groups = [commercial.group(cur, [p], at, settings=dict(price=None, bom=None, work_rates=[], laundry_rates=[])) for p in products]
    commercial.save(cur, groups, at)
    ids = [g['id'] for g in groups]
    view = policy.get(cur, ids)
    policy.apply(cur, [policy.proposal(policy.row(view, sku), 'ACTIVE') for sku in ids])


def prepare_qc(cur, today):
    qc = qc_module()
    retained = qc.retained
    estimated, build = qc.adapted_fixture()
    retained.admin(cur)
    if cur.execute('select 1 from erp.products where id=%s', (retained.base.BASE_PRODUCT,)).fetchone() is None:
        retained.base.load_fixture_foundation(cur)
    fixture = estimated(cur, today)
    retained.admin(cur)
    version = cur.execute('select row_version from erp.material_purchase_headers where id=%s', (fixture['purchase'],)).fetchone()[0]
    retained.rpc(cur, qc.FINAL, dict(
        purchase_id=fixture['purchase'], supplier_invoice_number='B-QC-' + str(uuid4()),
        invoice_date=fixture['purchase_day'], received_at=retained.at(fixture['purchase_day'], 23, 45),
        reason='Fixture biaya resmi sebelum pengeluaran bahan untuk QC',
        lines=[dict(purchase_item_id=fixture['item'], qty_invoiced=8, final_unit_price=29)],
    ), uuid4(), int(version))
    build(cur, fixture)
    retained.admin(cur)
    set_active_policy(cur, [fixture['product']])
    retained.admin(cur)
    po, version = cur.execute("""
        select o.po_number,g.row_version from erp.cutting_groups g
        join erp.production_orders o on o.id=g.po_id where g.id=%s
    """, (fixture['group'],)).fetchone()
    location = retained.base.LOCATION
    location_name = cur.execute('select location_name from erp.locations where id=%s', (location,)).fetchone()[0]
    at = retained.at(fixture['day'], 13)
    return {
        **label(cur, fixture['product']), 'po': fixture['po'], 'poNumber': po, 'group': fixture['group'], 'version': version,
        'location': location, 'locationName': location_name, 'qcLocal': at.strftime('%Y-%m-%dT%H:%M'),
        'qcAt': at.isoformat(), 'receiptLine': fixture['receipt_line'], 'receiptSize': fixture['receipt_size'],
        'day': fixture['day'], 'query': dict(from_date=fixture['day'], through_date=today-timedelta(days=1), group_mode='AS_SOLD'),
    }


def qc_books(cur, f, today):
    import cp7_r3_qc_note_cases as qc_native
    state = qc_native.qc_state(cur, f)
    lot_numbers = dict(cur.execute('select id::text,lot_number from erp.fg_lots where po_id=%s', (f['po'],)).fetchall())
    (cogs,) = cur.execute("""
        select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
        join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in ('POSTED','REVERSED') and j.transaction_date<=%s and l.po_id=%s and l.account_id=erp.account_id('COGS')
    """, (today, f['po'])).fetchone()
    hpp = cur.execute("""
        select f.initial_qty_pcs,h.hpp_per_pcs,h.total_cost from erp.fg_lots f
        join erp.hpp_versions h on h.lot_id=f.id and h.is_current
        where f.po_id=%s and f.product_id=%s and f.lot_origin='PRODUCTION' order by f.id
    """, (f['po'], f['product'])).fetchall()
    return dict(
        ledger=dict(WIP=state['wip_balance'], FG_INVENTORY=state['fg_balance'], COGS=qc_native.money(cogs)),
        progress=[state['received_good'], state['qc_accounted'], state['ready']], current_hpp=hpp,
        native=state, lot_numbers=lot_numbers,
    )


def report_books(cur, p):
    (read,) = cur.execute("""
        select r.body from cp7_analysis_stage.report_reads r
        join cp7_analysis_stage.report_jobs j on j.id=r.job_id
        where j.actor=%s and j.request_id=%s and r.kind='ACTUALS'
    """, (p['actor'], p['request'])).fetchone()
    cutoff = read['read_at']
    raw, available = cur.execute("""
        select coalesce(sum(m.qty_signed) filter (where m.movement_type<>'SALE_RESERVE' and not exists(
            select 1 from erp.fg_stock_movements rev where rev.id=m.reversal_of_id and rev.movement_type='SALE_RESERVE')),0),
            coalesce(sum(m.qty_signed),0)
        from erp.fg_stock_movements m join erp.products p on p.id=m.product_id
        where coalesce(p.identity_root_id,p.id)=%s and m.quality_grade in ('GRADE_A','GRADE_B')
          and m.physical_at<=%s and m.system_created_at<=%s
    """, (p['root'], cutoff, cutoff)).fetchone()
    return dict(read=read, stock_book=dict(physical_fg_pcs=str(raw), available_fg_pcs=str(available)))


def planner_state(cur, actor):
    result = cur.execute("""
        select (select count(*) from cp7_initial_analysis.intents where actor=%s),
               (select count(*) from cp7_analysis_stage.jobs where actor=%s),
               (select to_jsonb(j) from (select j.request_id,j.state,j.units_done,j.unit_count,j.run_id,j.query,j.failure_code
                  from cp7_initial_analysis.intents i join cp7_analysis_stage.jobs j on j.id=i.job_id where i.actor=%s) j)
    """, (actor, actor, actor)).fetchone()
    return dict(zip(('intents', 'jobs', 'job'), result))


def finish_planner(conn, actor, request):
    ticks = []
    # Each tick uses the existing queue and commits one bounded server unit.
    # A small fixture can use this when the isolated copy has no live scheduler.
    for _ in range(80):
        with conn.transaction(), conn.cursor() as cur:
            state = planner_state(cur, actor)
            assert (state['intents'], state['jobs'], state['job']['request_id']) == (1, 1, request), state
            if state['job']['state'] != 'RUNNING':
                return dict(state=state, ticks=ticks)
            active = cur.execute("select count(*) from cp7_analysis_stage.jobs where state='RUNNING'").fetchone()[0]
            assert active == 1, 'BLOCKED: salinan B harus memiliki satu job Planner yang sedang berjalan'
            cur.execute("set local statement_timeout='8s'; set local role cp7_capture")
            ticks.append(cur.execute('select cp7_analysis_stage.run_next()').fetchone()[0])
    raise RuntimeError('B_PLANNER_LIMIT: satu fixture kecil belum selesai setelah 80 unit server')


def main():
    url = os.environ['AUDITOR_BROWSER_DB_URL']
    target = urlparse(url)
    if target.scheme not in ('postgres', 'postgresql') or target.hostname not in ('localhost', '127.0.0.1') or target.path != '/cp6_auditor_browser':
        raise RuntimeError('DISPOSABLE_BROWSER_COPY_ONLY')
    operation, p = sys.argv[1], json.load(sys.stdin)
    with psycopg.connect(url) as conn, redirect_stdout(sys.stderr):
        if operation == 'finish-planner':
            out = finish_planner(conn, p['actor'], p['request'])
        else:
            with conn.cursor() as cur:
                if operation == 'prepare-qc':
                    out = prepare_qc(cur, date.fromisoformat(p['today']))
                elif operation == 'qc-books':
                    out = qc_books(cur, p['fixture'], date.fromisoformat(p['today']))
                elif operation == 'report-books':
                    out = report_books(cur, p)
                elif operation == 'prepare-planner':
                    from cp7_planning_history_cases import fixture
                    today = date.fromisoformat(p['today'])
                    stocks = (6, 17)
                    rows = [fixture(cur, today, qty=1, stock=stock) for stock in stocks]
                    set_active_policy(cur, [f['product'] for f in rows])
                    out = [dict(label(cur, f['product']), stock=str(stock)) for f, stock in zip(rows, stocks)]
                elif operation == 'planner-state':
                    out = planner_state(cur, p['actor'])
                elif operation == 'reject-role':
                    (out,) = cur.execute("""
                        select role_code from erp.app_roles where is_active and role_code not in ('OWNER','ADMIN')
                        order by case role_code when 'GUDANG' then 0 when 'STAFF' then 1 else 2 end, role_code limit 1
                    """).fetchone()
                else:
                    raise ValueError('UNKNOWN_B_BROWSER_OPERATION')
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
