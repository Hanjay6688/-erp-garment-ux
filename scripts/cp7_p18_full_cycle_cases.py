"""P18 full lifecycle: stock -> WIP -> HPP -> GL -> payables -> cash, reconciled at every boundary.

Continues the frozen E01 worksheet (framework-v2/04_BUKTI_DAN_ORACLE.md) after sale/payment/return and closes
every payable it created: supplier AP1000, laundry vendor AP120 and Mandor payroll180. No new oracle number is
invented: every amount comes from the E01 worksheet and the payables it already produced.

Writers used:
- E01 production, sale, payment and return: exactly the existing qualified E01 path.
- Laundry vendor payment: the application writer erp_save_laundry_bd_action_v1 PAY_VENDOR_DOCUMENT (owner).
- Mandor payroll payment: the application writer erp_cp7_save_payroll_v1 PAY (owner).
- Material supplier payment: the application writer erp_cp7_create_supplier_payment_v1 (owner), which posts
  through the unchanged Native erp.post_supplier_payment. Before it existed, the first qualified run (8beab7fe)
  used Native posting on a DRAFT row and recorded the missing application entry as a P18 gap; that result stays.

At every boundary the global GL change since the start equals the fixture subledgers: material stock value,
WIP, FG lots, supplier AP, laundry vendor AP, contractor payable, customer AR and cash. Only this fixture writes
after the start snapshot, so a global change that is not explained by a subledger fails the case.
"""
from datetime import timedelta
from decimal import Decimal as D
import uuid

import cp7_f03_e01_cases as e01
import cp7_receipt_correction_cases as receipt_fix
import cp7_supplier_payment_create_cases as pay_create

b, prod, cmd, finance, settlement, laundry = e01.b, e01.prod, e01.cmd, e01.finance, e01.settlement, e01.laundry
refused = settlement.auth.refused
KEYS = ('MATERIAL_INVENTORY', 'WIP', 'FG_INVENTORY', 'AP_SUPPLIER', 'AP_VENDOR', 'CONTRACTOR_PAYABLE', 'AR_CUSTOMER', 'SALES_REVENUE', 'COGS')
POSITION = ('cash', 'customer_ar', 'material_inventory', 'wip_inventory', 'fg_inventory', 'supplier_final_ap', 'grni_estimated_liability',
            'liabilities', 'assets', 'recorded_equity', 'current_earnings', 'balance_difference')


def one(cur, sql, args=()):
    return cur.execute(sql, args).fetchone()[0]


def accounts(cur):
    return {k: one(cur, 'select erp.account_id(%s)::text', (k,)) for k in KEYS}


def ledger(cur):
    return {str(k): D(v) for k, v in cur.execute("select l.account_id,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') group by l.account_id").fetchall()}


def change(before, after):
    return {k: after.get(k, D(0))-before.get(k, D(0)) for k in set(before) | set(after) if after.get(k, D(0)) != before.get(k, D(0))}


def subledgers(cur, f):
    """Fixture subledgers read from their own documents, never from the GL."""
    s = dict(material=D(one(cur, 'select coalesce(sum(qty_signed*unit_cost_snapshot),0) from erp.material_stock_movements where material_id=%s', (f['material'],))))
    s['fg'] = D(one(cur, 'select coalesce(sum(m.qty_signed*h.hpp_per_pcs),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id join erp.v_current_hpp h on h.lot_id=l.id where l.po_id=%s', (f['po'],)))
    s['fg_pcs'] = e01.physical(cur, f)
    s['wip'] = laundry.wip(cur, f['po'])
    s['supplier_ap'] = D(one(cur, "select erp.material_purchase_final_ap_total(%s)-coalesce((select sum(amount) from erp.supplier_payments where purchase_id=%s and status='POSTED'),0)", (f['purchase'], f['purchase'])))
    s['vendor_ap'] = D(one(cur, "select h.total_amount-coalesce((select sum(p.amount) from erp.vendor_payments p where p.vendor_invoice_id=h.id and p.status='POSTED'),0) from erp.vendor_invoices h where h.id=%s", (f['laundry_invoice'],)))
    payroll = settlement.doc(cur, f['payroll'])
    s['payroll_status'] = payroll['status']
    s['contractor_payable'] = D(0) if payroll['status'] == 'PAID' else D(payroll['net_payable'])
    s['ar'] = D(e01.source.read(cur, f)['detail']['financial']['open_balance']) if f.get('sale') else D(0)
    return s


def dimension(cur, key, column, ident):
    return D(one(cur, "select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id(%s) and l."+column+'=%s', (key, ident)))


def boundary(cur, f, name, expected_cash):
    """GL change since start == subledgers, for every control account the cycle touches."""
    a, gl = f['accounts'], change(f['gl0'], ledger(cur))
    s = subledgers(cur, f)
    g = {k: gl.get(a[k], D(0)) for k in KEYS}
    cash = gl.get(f['cash_coa'], D(0))
    pairs = dict(material=(g['MATERIAL_INVENTORY'], s['material']), wip=(g['WIP'], s['wip']), fg=(g['FG_INVENTORY'], s['fg']),
                 supplier_ap=(-g['AP_SUPPLIER'], s['supplier_ap']), vendor_ap=(-g['AP_VENDOR'], s['vendor_ap']),
                 contractor_payable=(-g['CONTRACTOR_PAYABLE'], s['contractor_payable']), ar=(g['AR_CUSTOMER'], s['ar']), cash=(cash, D(expected_cash)))
    off = {k: (str(x), str(y)) for k, (x, y) in pairs.items() if x != y}
    assert not off, ('P18_GL_SUBLEDGER_MISMATCH', name, off)
    # The same control accounts by their own dimension: only this vendor/contractor/customer moved.
    assert -dimension(cur, 'AP_VENDOR', 'vendor_id', f['vendor']) == s['vendor_ap'], ('P18_VENDOR_DIMENSION', name)
    assert -dimension(cur, 'CONTRACTOR_PAYABLE', 'contractor_id', f['contractor']) == s['contractor_payable'], ('P18_CONTRACTOR_DIMENSION', name)
    if f.get('customer'):
        assert dimension(cur, 'AR_CUSTOMER', 'customer_id', f['customer']) == s['ar'], ('P18_CUSTOMER_DIMENSION', name)
    explained = set(a.values()) | {f['cash_coa']}
    extra = {k: str(v) for k, v in gl.items() if k not in explained}
    assert not extra, ('P18_UNEXPLAINED_GL_CHANGE', name, extra)
    assert sum(gl.values(), D(0)) == 0, ('P18_TRIAL_BALANCE', name, sum(gl.values(), D(0)))
    point = dict(boundary=name, gl={k: str(v) for k, v in g.items() if v}, cash=str(cash), subledgers={k: str(v) for k, v in s.items()})
    f['boundaries'].append(point)
    e01.step('P18_'+name, **point)
    return s


def balanced_since(cur, known):
    """Every journal entry this cycle created is balanced; listed by source type."""
    rows = cur.execute("select j.source_type,count(distinct j.id),coalesce(sum(l.debit),0),coalesce(sum(l.credit),0) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where not(j.id::text=any(%s)) group by j.source_type order by 1", (known,)).fetchall()
    unbalanced = cur.execute('select j.id::text from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where not(j.id::text=any(%s)) group by j.id having sum(l.debit)<>sum(l.credit)', (known,)).fetchall()
    assert rows and not unbalanced, ('P18_UNBALANCED_JOURNAL', unbalanced)
    return [dict(source_type=t, entries=n, debit=str(d), credit=str(c)) for t, n, d, c in rows]


def position(cur, today):
    return finance.read(cur, today)['snapshot']['financial_position']


def moved(a, z):
    return {k: D(z[k])-D(a[k]) for k in POSITION if D(z[k]) != D(a[k])}


def supplier_payment(cur, f, amount, at, key=None):
    """The application entry: current review token, owner authority, Native posting."""
    w = pay_create.read(cur, dict(receipt=dict(purchase_id=f['purchase'])))
    p = dict(purchase_id=f['purchase'], review_token=w['review_token'], amount=amount, cash_account_id=f['bank'], payment_date=at.isoformat(), note='P18 pelunasan hutang bahan')
    return pay_create.command(cur, p, key), p


def cycle(cur, today):
    # Clear foundation obligations first, so after the start snapshot only this fixture writes.
    b.api.admin(cur)
    e01.procurement.aa.prior.set_open_period(cur, today-timedelta(days=4))
    seed = e01.attendance.quiet_seed(cur, today-timedelta(days=3), today)
    assert not seed['refused'], ('P18_SEED_COMPLETION', seed)
    e01.native(cur, 'select erp.process_cost_recalc_queue(100)')
    b.api.admin(cur)
    known = [r[0] for r in cur.execute('select id::text from erp.journal_entries').fetchall()]
    gl0, p0 = ledger(cur), position(cur, today)
    f = e01.production(cur, today)
    assert not any(f['seed_completion'][k] for k in ('attendance', 'approved', 'work_payrolls')), ('P18_SEED_WROTE_AFTER_START', f['seed_completion'])
    f.update(gl0=gl0, accounts=accounts(cur), boundaries=[])
    assert f['cash_coa'] not in f['accounts'].values(), 'P18_CASH_COA_IS_A_CONTROL_ACCOUNT'
    assert gl0.get(f['cash_coa'], D(0)) == 0, 'P18_FRESH_BANK_HAS_HISTORY'

    s = boundary(cur, f, 'B1_PRODUCTION_HPP_FINAL', 0)
    assert (s['material'], s['wip'], s['fg'], s['fg_pcs']) == (400, 0, 900, 60), ('P18_B1_STOCK', s)
    assert (s['supplier_ap'], s['vendor_ap'], s['contractor_payable'], s['payroll_status']) == (1000, 120, 180, 'APPROVED'), ('P18_B1_PAYABLES', s)
    p1 = position(cur, today)
    assert moved(p0, p1) == dict(material_inventory=D(400), fg_inventory=D(900), supplier_final_ap=D(1000), liabilities=D(1300), assets=D(1300)), ('P18_B1_REPORT', moved(p0, p1))

    report_before = e01.ready_report(cur, today, f['sale_at'])
    e01.drafts.create(cur, f, e01.drafts.payload(f, '20', '25'))
    p, version = cmd.review(cur, f)
    cmd.command(cur, 'POST', p, version)
    s = boundary(cur, f, 'B2_SALE_POSTED', 0)
    assert (s['fg'], s['fg_pcs'], s['ar']) == (600, 40, 500), ('P18_B2', s)
    e01.payments.pay(cur, f, '200')
    s = boundary(cur, f, 'B3_CUSTOMER_CASH', 200)
    assert s['ar'] == 300, ('P18_B3', s)
    f['allocations'] = e01.returns.read(cur, f)['page']['rows']
    payload, version = e01.returns.payload(cur, f, qty='5', refund='125')
    cmd.command(cur, 'RETURN', payload, version)
    s = boundary(cur, f, 'B4_RETURN', 200)
    assert (s['fg'], s['fg_pcs'], s['ar']) == (675, 45, 175), ('P18_B4', s)
    report_after = e01.ready_report(cur, today, f['sale_at'])
    for section, name, expected in [('performance', 'sales_revenue_gl', 375), ('performance', 'cogs_gl', 225), ('performance', 'gross_profit', 150)]:
        assert finance.change(report_before, report_after, section, name) == expected, ('P18_PERFORMANCE', section, name)

    now = one(cur, 'select clock_timestamp()')
    first, _ = supplier_payment(cur, f, '400.00', now-timedelta(minutes=3))
    assert first['remaining_after'] == '600.00', ('P18_SUPPLIER_PAY', first)
    s = boundary(cur, f, 'B5_SUPPLIER_PARTIAL', -200)
    assert s['supplier_ap'] == 600 and one(cur, 'select payment_status from erp.material_purchase_headers where id=%s', (f['purchase'],)) == 'PARTIAL', ('P18_B5', s)
    paykey = uuid.uuid4()
    last, sent = supplier_payment(cur, f, '600.00', now-timedelta(minutes=2), paykey)
    s = boundary(cur, f, 'B6_SUPPLIER_PAID', -800)
    assert s['supplier_ap'] == 0 and one(cur, 'select payment_status from erp.material_purchase_headers where id=%s', (f['purchase'],)) == 'PAID', ('P18_B6', s)
    gl = ledger(cur)
    assert pay_create.command(cur, sent, paykey) == last and ledger(cur) == gl, 'P18_SUPPLIER_REPLAY_SECOND_EFFECT'
    replay = refused(cur, lambda: pay_create.command(cur, dict(sent, amount='0.01')), 'CP7_SUPPLIER_PAYMENT_STALE_REVIEW')
    over = refused(cur, lambda: supplier_payment(cur, f, '0.01', now-timedelta(minutes=1)), 'CP7_SUPPLIER_PAYMENT_NOTHING_PAYABLE')
    assert ledger(cur) == gl, 'P18_REFUSED_SUPPLIER_PAYMENT_CHANGED_GL'

    key = uuid.uuid4()
    vendor = dict(target_kind='VENDOR_INVOICE', target_id=f['laundry_invoice'], amount='120.00', date=str(today), cash_account_id=f['bank'], reason='P18 pelunasan tagihan laundry')
    paid = laundry.bd(cur, 'PAY_VENDOR_DOCUMENT', vendor, key=key)
    assert paid['remaining'] == '0.00', ('P18_VENDOR_PAY', paid)
    s = boundary(cur, f, 'B7_VENDOR_PAID', -920)
    assert s['vendor_ap'] == 0 and one(cur, 'select status from erp.vendor_invoices where id=%s', (f['laundry_invoice'],)) == 'PAID', ('P18_B7', s)
    gl = ledger(cur)
    again = laundry.bd(cur, 'PAY_VENDOR_DOCUMENT', vendor, key=key)
    assert again['replayed'] is True and {k: v for k, v in again.items() if k != 'replayed'} == paid and ledger(cur) == gl, ('P18_VENDOR_REPLAY_SECOND_EFFECT', again)
    vendor_over = refused(cur, lambda: laundry.bd(cur, 'PAY_VENDOR_DOCUMENT', dict(vendor, amount='0.01')), 'still unpaid')
    assert ledger(cur) == gl, 'P18_REFUSED_VENDOR_PAYMENT_CHANGED_GL'

    approved = settlement.doc(cur, f['payroll'])
    paykey = uuid.uuid4()
    pay = settlement.act(cur, 'PAY', approved, paykey, payment_date=str(today), cash_account_id=f['bank'])
    s = boundary(cur, f, 'B8_PAYROLL_PAID', -1100)
    assert s['contractor_payable'] == 0 and s['payroll_status'] == 'PAID', ('P18_B8', s)
    gl = ledger(cur)
    assert settlement.act(cur, 'PAY', approved, paykey, payment_date=str(today), cash_account_id=f['bank']) == pay and ledger(cur) == gl, 'P18_PAYROLL_REPLAY_SECOND_EFFECT'

    final = change(gl0, ledger(cur))
    a = f['accounts']
    wanted = {a['MATERIAL_INVENTORY']: D(400), a['FG_INVENTORY']: D(675), a['AR_CUSTOMER']: D(175), a['SALES_REVENUE']: D(-375), a['COGS']: D(225), f['cash_coa']: D(-1100)}
    assert final == wanted, ('P18_FINAL_LEDGER', {k: str(v) for k, v in final.items()})
    p9 = position(cur, today)
    assert moved(p0, p9) == dict(cash=D(-1100), customer_ar=D(175), material_inventory=D(400), fg_inventory=D(675), assets=D(150), current_earnings=D(150)), ('P18_FINAL_REPORT', moved(p0, p9))
    journals = balanced_since(cur, known)
    e01.step('P18_FINAL', raw=400, fg=675, wip=0, supplier_ap=0, vendor_ap=0, contractor_payable=0, ar=175, cash=-1100, revenue=375, cogs=225, gross_profit=150)
    return f, gl0, p0, known, dict(status='PASS', journey='P18_FULL_CYCLE', execution='E01_QUALIFIED_PATH_PLUS_PAYABLES_TO_CASH',
                boundaries=f['boundaries'], journals_by_source=journals, report_position_change={k: str(v) for k, v in moved(p0, p9).items()},
                refusals=dict(supplier_stale_review=replay, supplier_nothing_payable=over, vendor_overpay=vendor_over),
                writers=dict(supplier_payment='APP_erp_cp7_create_supplier_payment_v1', vendor_payment='APP_erp_save_laundry_bd_action_v1_PAY_VENDOR_DOCUMENT', payroll_payment='APP_erp_cp7_save_payroll_v1_PAY'),
                source_ids={k: f[k] for k in ('po', 'purchase', 'group', 'laundry_invoice', 'note', 'payroll', 'sale')},
                full_P18_acceptance=False, full_family_acceptance=False)


def journey(cur, today):
    return cycle(cur, today)[4]


def late_price(cur, today):
    """E13 on the same cycle: the supplier price was 11, not 10, found after cutting, sale, return and full payment.

    Corrected through the owning receipt-correction command. The oracle follows from the E01 quantities only:
    remaining 40 m +40, 60 pcs HPP 15->16 so remaining FG 45 pcs +45 and net sold 15 pcs COGS +15, supplier AP +100.
    Paid supplier cash is replayed with its own dates, so cash stays -1100 until the difference is paid.
    """
    f, gl0, p0, known, _ = cycle(cur, today)
    checks_before = receipt_fix.checks(cur)
    old_purchase = f['purchase']
    paid_before = [r[0] for r in cur.execute("select id::text from erp.supplier_payments where purchase_id=%s and status='POSTED' order by payment_date", (old_purchase,)).fetchall()]
    assert len(paid_before) == 2, ('P18_E13_PAYMENTS_BEFORE', paid_before)
    w = receipt_fix.ws(cur, old_purchase)
    fixed = receipt_fix.fix(cur, receipt_fix.payload(w, reason='Harga bahan pada nota supplier 11, bukan 10; dicek dengan nota asli',
                                                     line=lambda n, item: item.update(unit_price='11')), w['purchase']['row_version'])
    f['purchase'] = fixed['purchase_id']
    s = boundary(cur, f, 'B9_LATE_PRICE_AFTER_FULL_CYCLE', -1100)
    assert (s['material'], s['wip'], s['fg'], s['fg_pcs'], s['supplier_ap'], s['vendor_ap'], s['contractor_payable'], s['ar']) == (440, 0, 720, 45, 100, 0, 0, 175), ('P18_B9', s)
    replays = cur.execute('''select o.id::text,o.status,n.status,n.amount=o.amount,n.payment_date=o.payment_date,n.purchase_id::text
        from cp7_receipt_fix.payment_replays r join erp.supplier_payments o on o.id=r.previous_payment_id
        join erp.supplier_payments n on n.id=r.replacement_payment_id where r.previous_payment_id::text=any(%s) order by o.payment_date''', (paid_before,)).fetchall()
    assert [r[1:] for r in replays] == [('REVERSED', 'POSTED', True, True, f['purchase'])] * 2, ('P18_E13_PAYMENT_REPLAY', replays)
    assert one(cur, 'select payment_status from erp.material_purchase_headers where id=%s', (f['purchase'],)) == 'PARTIAL'
    receipt_fix.same_checks(checks_before, receipt_fix.checks(cur))
    receipt_fix.reversal_dates(cur)
    difference, _ = supplier_payment(cur, f, '100.00', one(cur, 'select clock_timestamp()')-timedelta(minutes=1))
    assert difference['remaining_after'] == '0.00', ('P18_E13_DIFFERENCE', difference)
    s = boundary(cur, f, 'B10_SUPPLIER_DIFFERENCE_PAID', -1200)
    assert s['supplier_ap'] == 0 and one(cur, 'select payment_status from erp.material_purchase_headers where id=%s', (f['purchase'],)) == 'PAID', ('P18_B10', s)
    final = change(gl0, ledger(cur))
    a = f['accounts']
    wanted = {a['MATERIAL_INVENTORY']: D(440), a['FG_INVENTORY']: D(720), a['AR_CUSTOMER']: D(175), a['SALES_REVENUE']: D(-375), a['COGS']: D(240), f['cash_coa']: D(-1200)}
    assert final == wanted, ('P18_E13_FINAL_LEDGER', {k: str(v) for k, v in final.items()})
    p_end = position(cur, today)
    assert moved(p0, p_end) == dict(cash=D(-1200), customer_ar=D(175), material_inventory=D(440), fg_inventory=D(720), assets=D(135), current_earnings=D(135)), ('P18_E13_REPORT', moved(p0, p_end))
    journals = balanced_since(cur, known)
    e01.step('P18_E13_FINAL', raw=440, fg=720, wip=0, supplier_ap=0, ar=175, cash=-1200, revenue=375, cogs=240, gross_profit=135)
    return dict(status='PASS', journey='P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE', boundaries=f['boundaries'][-2:],
                corrected_purchase=f['purchase'], previous_purchase=old_purchase, payments_replayed_same_date_amount=len(replays),
                integrity_checks_unchanged=True, journals_by_source=journals, report_position_change={k: str(v) for k, v in moved(p0, p_end).items()},
                writers=dict(price_correction='APP_erp_cp7_correct_receipt_v1', difference_payment='APP_erp_cp7_create_supplier_payment_v1'),
                full_P18_acceptance=False, full_family_acceptance=False)


IDS = ['P18_FULL_CYCLE_STOCK_WIP_HPP_GL_PAYABLES_CASH', 'P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE']
EXPECTED = len(IDS)


def cases(cur, today):
    return list(zip(IDS, (lambda: journey(cur, today), lambda: late_price(cur, today))))
