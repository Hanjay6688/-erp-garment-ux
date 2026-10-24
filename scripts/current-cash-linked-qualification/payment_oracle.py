"""Exact retained payment-date oracle plus explicit Native payroll prerequisite."""
from cp6_x_independent_audit import *
from prerequisites import complete_known_work

def payment_date(cur, cash, kind, posting_zone, noon_control=False):
    """Sourced invoice fixture; the tested payment itself uses actual OWNER SQL."""
    admin(cur)
    actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
    zone(cur, 'Asia/Jakarta')
    if kind == 'SALES_PAYMENT':
        parent = sales_fixture.opening_sale(cur, 'X-PAY')['sale']
        table, parent_key, function = 'sales_payments', 'sale_id', 'post_sales_payment'
        physical = '2026-09-04T12:00:00+07:00' if noon_control else '2026-09-04T00:30:00+07:00'
        days, sign = ('2026-09-03', '2026-09-04'), Decimal(1)
    else:
        fixture = base.setup_tiny_fg(cur, '9', 4)
        parent = laundry_fixture.finalize_laundry_invoice(cur, fixture['receipt_line'], Decimal('.01'))
        table, parent_key, function = 'vendor_payments', 'vendor_invoice_id', 'post_vendor_payment'
        physical = '2026-09-05T00:30:00+07:00'
        days, sign = ('2026-09-04', '2026-09-05'), Decimal(-1)
    complete_known_work(cur,cash)
    owner(cur)
    before = scrap.reports(cur, days)
    if any(r['data_confidence']['status'] != 'READY' for r in before.values()):
        raise AssertionError('INDEPENDENT_PAYMENT_FIXTURE_NOT_READY')
    ident = uuid.uuid4()
    # Table, column and function identifiers come exclusively from the two
    # literal cases above, never external input.
    cur.execute('insert into erp.' + table + '(id,' + parent_key + ',payment_number,payment_date,amount,cash_account_id,status) '
                "values(%s,%s,%s,%s,.03,%s,'DRAFT')",
                (ident, parent, 'X-AUD-PAY-' + str(ident), physical, cash))
    if scrap.reports(cur, days) != before:
        raise AssertionError('INDEPENDENT_PAYMENT_DRAFT_CHANGED_REPORT')
    zone(cur, posting_zone)
    cur.execute('select erp.' + function + '(%s)', (ident,))
    if one(cur, "select current_setting('TimeZone')") != posting_zone:
        raise AssertionError('INDEPENDENT_PAYMENT_LEAKED_TIMEZONE')
    zone(cur, 'Pacific/Kiritimati')
    after = scrap.reports(cur, days)
    admin(cur)
    if one(cur, 'select status from erp.' + table + ' where id=%s', (ident,)) != 'POSTED':
        raise AssertionError('INDEPENDENT_PAYMENT_NOT_POSTED')
    cur.execute("select j.id::text,j.status,j.economic_date::text,j.transaction_date::text,"
                '(select sum(l.debit)::text from erp.journal_lines l where l.journal_entry_id=j.id),'
                '(select sum(l.credit)::text from erp.journal_lines l where l.journal_entry_id=j.id) '
                'from erp.journal_entries j where j.source_type=%s and j.source_id=%s', (kind, ident))
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][1] != 'POSTED' or rows[0][4:] != ('0.03', '0.03'):
        raise AssertionError('INDEPENDENT_PAYMENT_JOURNAL_OR_CENTS:' + str(rows))
    instant = datetime.fromisoformat(physical)
    expected = instant.astimezone(ZoneInfo('Asia/Jakarta')).date().isoformat()
    effective_zone = 'UTC' if kind == 'SALES_PAYMENT' else posting_zone
    legacy_day = instant.astimezone(ZoneInfo(effective_zone)).date().isoformat()
    actual_day = rows[0][2]
    if actual_day not in {expected, legacy_day} or rows[0][3] != actual_day:
        raise AssertionError('INDEPENDENT_PAYMENT_DATE_NOT_QUALIFIED:' + str(rows))
    daily = {}
    for day in days:
        actual = Decimal(str(after[day]['financial_position']['cash'])) - Decimal(str(before[day]['financial_position']['cash']))
        observed = sign * Decimal('.03') if day >= actual_day else Decimal(0)
        expected_delta = sign * Decimal('.03') if day >= expected else Decimal(0)
        if actual != observed:
            raise AssertionError('INDEPENDENT_PAYMENT_REPORT_DISAGREEMENT:' + str((day, actual, observed)))
        daily[day] = dict(expected_cash_delta=str(expected_delta), actual_cash_delta=str(actual),
                          confidence=after[day]['data_confidence']['status'], before=before[day], after=after[day])
    facts = []
    if kind == 'SALES_PAYMENT':
        cur.execute('select to_jsonb(f) from erp.sales_payment_posting_facts f where payment_id=%s', (ident,))
        facts = [r[0] for r in cur.fetchall()]
        if len(facts) != 1 or Decimal(str(facts[0]['amount'])) != Decimal('.03'):
            raise AssertionError('INDEPENDENT_PAYMENT_FACT_CARDINALITY_OR_CENTS')
    return dict(status='NEW_X_BUG_REPRODUCED' if actual_day != expected else 'CONTROL_PASS',
                severity='P2' if actual_day != expected else None,
                classification='SILENT_PER_DATE_CASH_MISPOSTING' if actual_day != expected else 'LAWFUL_CONTROL',
                kind=kind, zone=posting_zone, effective_function_timezone=effective_zone,
                physical_at=physical, expected_date=expected, actual_date=actual_day,
                payment_id=str(ident), parent_id=str(parent), journals=rows, payment_facts=facts,
                amount='0.03', daily_evidence=daily, draft_inert=True, total_cents_conserved=True,
                identity=dict(current_user='authenticated', session_user='authenticated', app_role='OWNER'),
                fixture_preparation='Existing posted opening-FG/sale or laundry receipt/invoice workflow under disposable admin',
                caller_timezone_preserved=True, http_ui_reachability_proven=False)
