"""E06: actual prior-year physical facts, March invoice, present knowledge.

The accepted E01 source uses newly dated masters and ordinary writers. Its
only variant is an ESTIMATED material receipt (GRNI1000, not supplier AP).
No clock, ledger, stock, posted status, archive or cost result is fabricated.
Known-at is the real execution time, never pretended to be March.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal as D
import time
import uuid
import psycopg
import cp7_f03_e01_cases as e01
import cp7_invoice_cases as invoice
import cp7_finance_cases as finance
import cp7_period_cases as period
import cp7_recost_cases as recost

b, auth = finance.b, finance.auth


def fixture(cur, today):
    # All March dates are in the past, including executions before April.
    year = today.year if today >= date(today.year, 4, 1) else today.year-1
    receipt_day, cutoff, invoice_day = date(year-1, 12, 30), date(year-1, 12, 31), date(year, 3, 31)
    f = e01.production(cur, receipt_day+timedelta(days=3), receipt_final=False)
    f.update(cutoff=cutoff, invoice_day=invoice_day)
    f['item'] = str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s', (f['purchase'],)).fetchone()[0])
    f['receipt'] = dict(purchase_id=f['purchase'])
    f['sale_at'] = e01.prod.at(cutoff, 18).isoformat()
    e01.drafts.create(cur, f, e01.drafts.payload(f, '20', '25'))
    payload, version = e01.cmd.review(cur, f)
    e01.cmd.command(cur, 'POST', payload, version)
    assert e01.physical(cur, f) == 40
    assert values(cur, f) == dict(hpp=D(900), fg=D(600), cogs=D(300)), values(cur, f)
    review = period.read(cur, cutoff)
    assert review['preflight']['status'] == 'READY', ('E06_SOURCE_NOT_READY', review)
    return f, review


def values(cur, f):
    return {k:D(str(v)) for k,v in recost.values(cur, f).items()}


def facts(cur, f):
    """Physical facts may never be redated/repeated by valuation correction."""
    zone=cur.execute('show timezone').fetchone()[0]
    cur.execute("set local timezone='UTC'")
    material = cur.execute("select coalesce(jsonb_agg(jsonb_build_array(id,material_id,location_id,qty_signed,physical_at,source_type,source_id,reversal_of_id) order by id),'[]') from erp.material_stock_movements where material_id=%s", (f['material'],)).fetchone()[0]
    fg = cur.execute("select coalesce(jsonb_agg(jsonb_build_array(m.id,m.lot_id,m.location_id,m.qty_signed,m.physical_at,m.source_type,m.source_id,m.reversal_of_id) order by m.id),'[]') from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s", (f['po'],)).fetchone()[0]
    work = cur.execute("select coalesce(jsonb_agg(to_jsonb(e) order by e.id),'[]') from erp.work_completion_events e where e.po_id=%s", (f['po'],)).fetchone()[0]
    cur.execute("select set_config('TimeZone',%s,true)",(zone,))
    return dict(material=material, fg=fg, work=work)


def filings(cur):
    zone=cur.execute('show timezone').fetchone()[0]
    try:
        cur.execute("set local timezone='UTC'")
        return period.filings(cur)
    finally:
        cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def payload(f, price):
    return dict(purchase_id=f['purchase'], supplier_invoice_number='E06-'+uuid.uuid4().hex,
                invoice_date=str(f['invoice_day']), received_at=e01.prod.at(f['invoice_day'], 15).isoformat(),
                due_date=str(f['invoice_day']+timedelta(days=30)), reason='E06 December receipt, actual March supplier invoice',
                lines=[dict(purchase_item_id=f['item'], qty_invoiced='100', final_unit_price=str(price))])


def post(cur, f, price, key=None, p=None, version=None):
    version = version or invoice.read(cur, f['purchase'])['purchase_version']
    return invoice.command(cur, 'FINALIZE', p or payload(f, price), version, key)


def confidence(cur, f):
    report = finance.read(cur, f['cutoff'])
    preflight = period.read(cur, f['cutoff'])['preflight']
    queued = cur.execute("select status from erp.cost_recalc_queue where entity_type='PO' and entity_id=%s and status in('PENDING','RUNNING','FAILED')", (f['po'],)).fetchall()
    own = finance.aw.codes(preflight, [f['po']])
    assert bool(queued) == ('RECOST_PENDING' in own), ('E06_PENDING_TRUTH', queued, own)
    assert report['snapshot']['data_confidence']['status'] == preflight['status']
    return dict(queue=[r[0] for r in queued], status=preflight['status'], own_blockers=own)


def journey(cur, today, price, zone):
    f, review = fixture(cur, today)
    closed = period.command(cur, 'CLOSE', period.intent(review))
    ident = closed['filing_id']
    old = finance.read(cur, f['cutoff'], filing_id=ident)
    all_filings = filings(cur)
    physical = facts(cur, f)
    ledger = e01.cmd.accounts(cur)
    raw_before = cur.execute('select cached_stock_qty,moving_average_cost from erp.materials where id=%s', (f['material'],)).fetchone()
    previous_events = [str(r[0]) for r in cur.execute('select id from erp.po_hpp_gl_events where po_id=%s',(f['po'],)).fetchall()]
    known_before = cur.execute('select clock_timestamp()').fetchone()[0]
    cur.execute('select set_config(\'TimeZone\',%s,true)', (zone,))
    key, p = uuid.uuid4(), payload(f, price)
    version = invoice.read(cur, f['purchase'])['purchase_version']
    result = post(cur, f, price, key, p, version)
    boundary = b.boundary.snapshot(cur)
    assert post(cur, f, price, key, p, version) == result and b.boundary.snapshot(cur) == boundary
    after_invoice = confidence(cur, f)
    processed = recost.command(cur)
    current = finance.read(cur, f['cutoff'], filing_id=ident)
    assert current['filing'] == old['filing'] and filings(cur) == all_filings
    assert current['snapshot']['financial_position'] == old['snapshot']['financial_position']
    assert current['snapshot']['performance'] == old['snapshot']['performance']
    assert current['snapshot']['data_confidence']['status'] == 'READY'
    assert current['snapshot']['data_confidence']['changed_since_filing'], current['snapshot']['data_confidence']
    change = D(price)-10
    expected = dict(hpp=D(900)+60*change, fg=D(600)+40*change, cogs=D(300)+20*change)
    assert values(cur, f) == expected, ('E06_COST_WORKSHEET', values(cur, f), expected)
    assert facts(cur, f) == physical and e01.physical(cur, f) == 40
    assert cur.execute('select cached_stock_qty,moving_average_cost from erp.materials where id=%s', (f['material'],)).fetchone() == (40,D(price))
    assert invoice.amounts(cur, f) == (100*D(price), 0, 40, D(price))
    expected_gl = {'MATERIAL_INVENTORY':40*change, 'FG_INVENTORY':40*change, 'COGS':20*change, 'AP_SUPPLIER':-100*D(price), 'GRNI_MATERIAL':D(1000)}
    expected_gl = {e01.cmd.mapping(cur,k):v for k,v in expected_gl.items() if v}
    assert e01.cmd.delta(ledger, e01.cmd.accounts(cur)) == expected_gl, ('E06_GL', e01.cmd.delta(ledger,e01.cmd.accounts(cur)), expected_gl)
    dates = cur.execute('select invoice_date,received_at,created_at,posted_at from erp.material_supplier_invoices where id=%s', (result['invoice_id'],)).fetchone()
    assert dates[0] == f['invoice_day'] and dates[1] == e01.prod.at(f['invoice_day'],15)
    # created_at may use the transaction start; posted_at is always bounded
    # by the actual transaction, never backdated to the supplier's paper.
    tx_start = cur.execute('select transaction_timestamp()').fetchone()[0]
    known_after = cur.execute('select clock_timestamp()').fetchone()[0]
    assert tx_start <= dates[2] <= known_after and tx_start <= dates[3] <= known_after
    assert dates[2].date() > f['invoice_day'] and dates[3].date() > f['invoice_day']
    events = cur.execute('select effective_date,fg_delta,cogs_delta from erp.po_hpp_gl_events where po_id=%s and id<>all(%s::uuid[])', (f['po'],previous_events)).fetchall()
    if change:
        assert events and all(r[0] == today for r in events), ('E06_OPEN_DAY_HPP', events, today)
        assert sum(r[1] for r in events)==40*change and sum(r[2] for r in events)==20*change
    invoice.reverse(cur, f, result['invoice_id'])
    recost.command(cur)
    assert values(cur, f) == dict(hpp=D(900), fg=D(600), cogs=D(300))
    assert invoice.amounts(cur, f) == (0,1000,*raw_before)
    assert e01.cmd.accounts(cur) == ledger and facts(cur,f) == physical
    assert finance.read(cur, f['cutoff'], filing_id=ident)['filing'] == old['filing']
    return dict(status='PASS', fixture='E01_60_GOOD_ESTIMATED_RECEIPT_20_SOLD', receipt=str(f['day']), production=str(f['production_day']), invoice=str(f['invoice_day']), known_at_actual=[str(known_before),str(known_after)], invoice_dates=list(map(str,dates)), caller_zone=zone, expected_costs=expected, after_invoice=after_invoice, processed=processed, closed_day_GL_and_filing_immutable=True, exact_replay_and_inverse=True, physical_source_facts_unchanged=True, no_invented_March_knowledge=True, actual_browser_case=False)


def pending(cur, today):
    f, review = fixture(cur,today)
    closed = period.command(cur,'CLOSE',period.intent(review))
    original = finance.read(cur,f['cutoff'],filing_id=closed['filing_id'])['filing']
    # A real backdated receipt queues the existing PO without synthetic queue
    # inserts. This complements the invoice's legitimate synchronous recost.
    period.late(cur,dict(material=f['material'],purchase_day=f['day']))
    state = confidence(cur,f)
    assert state['queue'] and state['status'] != 'READY', state
    period.command(cur,'REOPEN',period.intent(period.read(cur,f['cutoff']),'REOPEN',review['control']['closed_through']))
    before=b.boundary.snapshot(cur)
    auth.refused(cur,lambda:period.command(cur,'CLOSE',period.intent(period.read(cur,f['cutoff']))),'CLOSE_BLOCKED')
    assert b.boundary.snapshot(cur)==before
    physical=facts(cur,f)
    recost.command(cur)
    assert not confidence(cur,f)['queue'] and confidence(cur,f)['status']=='READY'
    assert facts(cur,f)==physical and finance.read(cur,f['cutoff'],filing_id=closed['filing_id'])['filing']==original
    period.command(cur,'CLOSE',period.intent(period.read(cur,f['cutoff'])))
    assert len(filings(cur))==2
    return dict(status='PASS', actual_backdated_receipt_queues_year_end_PO=True, pending_blocks_close=True, native_recost_then_fresh_close=True, two_distinct_filings_original_unchanged=True, no_repeated_physical_facts=True)


def cases(cur,today):
    return [('F03_E06_YEAR_END_INCREASE_UTC',lambda:journey(cur,today,'11','UTC')),
            ('F03_E06_YEAR_END_ZERO_DELTA_LA',lambda:journey(cur,today,'10','America/Los_Angeles')),
            ('F03_E06_YEAR_END_PENDING_CLOSE',lambda:pending(cur,today))]


def races(tools,today):
    def invoice_close():
        with tools.connect() as conn,conn.cursor() as cur:
            f,state=fixture(cur,today);before=filings(cur);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select singleton_id from erp.accounting_period_control where singleton_id=1 for update')
            def close():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:
                        r=period.command(cur,'CLOSE',period.intent(state));conn.commit();return r
                    except psycopg.Error as exc:
                        conn.rollback();return str(exc).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(close);waiting=False;deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    with tools.connect() as conn,conn.cursor() as cur:
                        waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and query like 'select public.erp_cp7_save_period_control_v1%')").fetchone()[0]
                    if waiting:break
                    time.sleep(.05)
                try:
                    assert waiting,'E06 close did not wait on real period row lock'
                    result=post(h,f,'11')
                    holder.commit()
                finally:
                    holder.rollback()
                outcome=future.result(30)
        assert isinstance(outcome,str) and 'CP7_PERIOD_REVIEW_CHANGED' in outcome, ('E06_STALE_CLOSE',outcome)
        with tools.connect() as conn,conn.cursor() as cur:
            assert filings(cur)==before
            recost.command(cur)
            fresh=period.read(cur,f['cutoff'])
            assert fresh['preflight']['status']=='READY'
            period.command(cur,'CLOSE',period.intent(fresh));assert len(filings(cur))==len(before)+1;conn.commit()
        return dict(status='PASS', real_period_lock_wait=True, March_invoice_commits_while_old_review_waits=True, stale_close_refused_without_archive=True, fresh_review_one_filing=True, invoice=result)
    return [('F03_E06_INVOICE_DURING_CLOSE_WAIT',invoice_close)]
