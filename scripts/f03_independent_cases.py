"""Auditor-owned F03 oracles; lawful retained source builders, new expectations.

No product mutation. Native writers make stock/journal facts. Administrative
setup is limited to disposable master/identity fixtures supplied by the repo.
Every caller must use the strict disposable auditor runtime.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D, ROUND_HALF_UP
import copy
import json
import re
import threading
import time
import uuid
import psycopg
import cp7_sales_cases as sales
import cp7_sales_command_cases as command
import cp7_sales_draft_cases as drafts
import cp7_sales_payment_cases as payments
import cp7_sales_return_cases as returns
import cp7_procurement_cases as procurement
import cp7_fg_adjustment_cases as adjustment
import cp7_installment_cases as installments
import cp7_finance_cases as finance
import cp7_f03_e01_cases as production
import cp6_auditor_modes as modes

b, auth = sales.b, sales.auth


def gl(cur):
    return {str(k): v for k, v in cur.execute(
        'select account_id,sum(debit-credit) from erp.journal_lines group by account_id having sum(debit-credit)<>0')}


def difference(before, after):
    return {k: after.get(k, D(0))-before.get(k, D(0)) for k in before.keys() | after.keys()
            if after.get(k, D(0)) != before.get(k, D(0))}


def expected(cur, **values):
    return {command.mapping(cur, k): D(str(v)) for k, v in values.items() if D(str(v))}


def refuse(cur, operation, pattern, sqlstate=None):
    """Never accepts a setup/undefined-column/transport error as business denial."""
    b.api.admin(cur)
    cur.execute('savepoint independent_refusal')
    error = None
    try:
        operation()
    except psycopg.Error as exc:
        error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
    finally:
        cur.execute('rollback to savepoint independent_refusal')
        b.api.admin(cur)
        cur.execute('release savepoint independent_refusal')
    assert error is not None, ('EXPECTED_BUSINESS_REFUSAL', pattern)
    assert error['sqlstate'] in ('P0001', '42501', '22023'), error
    assert re.search(pattern, error['message'], re.I), error
    if sqlstate:
        assert error['sqlstate'] == sqlstate, error
    return error


def custom(cur, permissions):
    subject, role = auth.custom_actor(cur)
    cur.execute('delete from erp.app_role_permissions where role_id=%s', (role,))
    for key in permissions:
        cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)', (role, key))
    return subject, role


PAY_PERMISSIONS = ('sales.invoice.view', 'finance.ar.view', 'sales.payment.view', 'sales.payment.create', 'sales.payment.post')


def seven(cur, today, posted=False):
    f = sales.fixture(cur, today, qty=7, price='37.13', discount='0.06')
    f['bank'] = str(sales.bc.bank_account(cur, 'I-F03-'+uuid.uuid4().hex[:10]))
    if posted:
        p, v = command.review(cur, f)
        command.command(cur, 'POST', p, v)
    return f


def cases(cur, today):
    def physical_to_money():
        # Reuse only the lawful upstream production builder. Sale quantities,
        # prices, cash/return sequence and downstream oracle are auditor-owned.
        f = production.production(cur, today)
        before, report0 = gl(cur), finance.read(cur, today)
        drafts.create(cur, f, drafts.payload(f, '17', '31.17', '0.23'))
        assert production.physical(cur, f) == 43 and gl(cur) == before
        p, v = command.review(cur, f)
        command.command(cur, 'POST', p, v)
        assert production.physical(cur, f) == 43
        assert difference(before, gl(cur)) == expected(cur, AR_CUSTOMER='529.66', SALES_REVENUE='-529.66', FG_INVENTORY=-255, COGS=255)
        cash = payments.pay(cur, f, '173.29')
        f['allocations'] = returns.read(cur, f)['page']['rows']
        p, v = returns.payload(cur, f, qty='3', refund='93.42')
        key = uuid.uuid4()
        returned = command.command(cur, 'RETURN', p, v, key)
        baseline = b.boundary.snapshot(cur)
        assert command.command(cur, 'RETURN', p, v, key) == returned
        assert b.boundary.snapshot(cur) == baseline
        assert production.physical(cur, f) == 46
        wanted = expected(cur, AR_CUSTOMER='262.95', SALES_REVENUE='-436.24', FG_INVENTORY=-210, COGS=210)
        wanted[f['cash_coa']] = D('173.29')
        assert difference(before, gl(cur)) == wanted
        report1 = finance.read(cur, today)
        worksheet = [('financial_position','cash','173.29'), ('financial_position','customer_ar','262.95'),
                     ('financial_position','fg_inventory','-210'), ('performance','sales_revenue_gl','436.24'),
                     ('performance','cogs_gl','210'), ('performance','gross_profit','226.24')]
        for section, name, amount in worksheet:
            assert D(report1['snapshot'][section][name])-D(report0['snapshot'][section][name]) == D(amount), (section, name)
        payments.inverse(cur, f, cash['payment_id'])
        returns.inverse(cur, f, returned['return_id'])
        returns.reverse_sale(cur, f)
        assert production.physical(cur, f) == 60 and gl(cur) == before
        return dict(status='PASS', setup='RETAINED_LAWFUL_60_PCS_PRODUCTION_BUILDER', independent_sale_qty=17,
                    net_sales='436.24', cash='173.29', ar='262.95', cogs='210', gross_profit='226.24',
                    remaining_fg=46, remaining_fg_value='690', replay_one_effect=True, inverse_stock=60, inverse_all_GL=True)

    def decimal_cash():
        f = seven(cur, today)
        before = gl(cur)
        assert command.available(cur, f) == 3
        p, v = command.review(cur, f)
        command.command(cur, 'POST', p, v)
        assert command.available(cur, f) == 3
        assert difference(before, gl(cur)) == expected(cur, AR_CUSTOMER='259.85', SALES_REVENUE='-259.85', FG_INVENTORY=-70, COGS=70)
        posted, report0 = gl(cur), finance.read(cur, today)
        a = payments.pay(cur, f, '123.45')
        assert sales.read(cur, f)['detail']['financial']['open_balance'] == '136.40'
        z = payments.pay(cur, f, '136.40')
        assert sales.read(cur, f)['detail']['status'] == 'PAID'
        want = expected(cur, AR_CUSTOMER='-259.85')
        want[payments.bank_account(cur, f)] = D('259.85')
        assert difference(posted, gl(cur)) == want
        assert finance.read(cur, today)['snapshot']['performance'] == report0['snapshot']['performance']
        payments.inverse(cur, f, a['payment_id'])
        assert sales.read(cur, f)['detail']['financial']['open_balance'] == '123.45'
        payments.inverse(cur, f, z['payment_id'])
        assert gl(cur) == posted and command.available(cur, f) == 3
        return dict(status='PASS', invoice='259.85', payments=['123.45','136.40'], post_does_not_rereserve=True, cash_not_revenue=True, inverse_all_GL=True)

    def returned_grades():
        f = seven(cur, today, True)
        f['destination'] = returns.location(cur, 'Independent grade destination')
        f['allocations'] = returns.read(cur, f)['page']['rows']
        before = gl(cur)
        one = returns.returned(cur, f, qty='2', refund='74.22', grade='GRADE_B')
        two = returns.returned(cur, f, qty='1', refund='37.11', grade='HOLD')
        assert returns.positions(cur, f) == {(f['location'],'GRADE_A'):3, (f['destination'],'GRADE_B'):2, (f['destination'],'HOLD'):1}
        assert sales.read(cur, f)['detail']['financial']['open_balance'] == '148.52'
        assert difference(before, gl(cur)) == expected(cur, AR_CUSTOMER='-111.33', SALES_REVENUE='111.33', FG_INVENTORY=30, COGS=-30)
        returns.inverse(cur, f, two['return_id']); returns.inverse(cur, f, one['return_id'])
        assert gl(cur) == before and returns.positions(cur, f) == {(f['location'],'GRADE_A'):3}
        return dict(status='PASS', grades={'A':3,'B':2,'HOLD':1}, ar='148.52', returned_cost='30', inverse_exact=True)

    def paid_policy():
        f = seven(cur, today, True); payments.pay(cur, f, '259.85')
        f['destination'] = returns.location(cur); f['allocations'] = returns.read(cur, f)['page']['rows']
        p, v = returns.payload(cur, f, qty='1', refund='37.11')
        before = b.boundary.snapshot(cur)
        error = refuse(cur, lambda:command.command(cur, 'RETURN', p, v), 'pembayaran customer melebihi')
        assert b.boundary.snapshot(cur) == before
        return dict(status='PASS', existing_paid_return_policy_preserved=True, no_automatic_refund_or_stock= True, refusal=error)

    def changed_payment():
        f = seven(cur, today, True); p, v = payments.payment_payload(cur, f, '123.45'); key = uuid.uuid4()
        first = command.command(cur, 'PAYMENT', p, v, key); before = b.boundary.snapshot(cur)
        error = refuse(cur, lambda:command.command(cur, 'PAYMENT', dict(p, amount='123.46'), v, key), 'CP7_SALES_REQUEST_CHANGED')
        assert b.boundary.snapshot(cur) == before and command.command(cur, 'PAYMENT', p, v, key) == first
        assert cur.execute('select count(*) from erp.sales_payments where sale_id=%s', (f['sale'],)).fetchone()[0] == 1
        return dict(status='PASS', same_key_changed_cent_refused=True, one_payment=True, refusal=error)

    def current_replay():
        f = seven(cur, today, True); actor, role = custom(cur, PAY_PERMISSIONS)
        p, v = payments.payment_payload(cur, f, '17.29'); key = uuid.uuid4()
        first = command.command(cur, 'PAYMENT', p, v, key, actor)
        assert command.command(cur, 'PAYMENT', p, v, key, actor) == first
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.payment.post'", (role,))
        before = b.boundary.snapshot(cur)
        error = refuse(cur, lambda:command.command(cur, 'PAYMENT', p, v, key, actor), 'CP7_SALES_WRITE_DENIED', '42501')
        assert b.boundary.snapshot(cur) == before
        return dict(status='PASS', active_positive_control=True, revoked_cached_request_refused=True, refusal=error)

    def pages():
        prefix = 'IF03-PAGE-'+uuid.uuid4().hex[:8]; ids = set()
        for i in range(13):
            f = sales.fixture(cur, today, qty=1, tag=f'{prefix}-{i:02d}'); ids.add(f['sale'])
        seen = []
        for offset in (0, 5, 10):
            page = sales.read(cur, q=prefix, offset=offset, limit=5)['page']
            assert page['total'] == '13' and len(page['rows']) == (3 if offset == 10 else 5)
            assert page['next_offset'] == (None if offset == 10 else offset+5)
            seen.extend(r['id'] for r in page['rows'])
        assert len(seen) == len(set(seen)) == 13 and set(seen) == ids
        return dict(status='PASS', source_documents=13, page_sizes=[5,5,3], all_ids_once=True)

    def procurement_decimal():
        f = procurement.fixture(cur, today, qty='1.234567', price='17.000001', final=True)
        d = procurement.command(cur, 'SAVE_DRAFT', f['payload']); procurement.post(cur, d)
        row = procurement.workspace(cur, dict(purchase_id=d['purchase_id']))['detail']['items'][0]
        product = D('1.234567')*D('17.000001')
        expected_value = product.quantize(D('.000001'), rounding=ROUND_HALF_UP)
        assert D(row['finance']['line_total']) == expected_value == D('20.987640')
        assert procurement.qty(cur, f) == (D('1.234567'), 1)
        ap, grni = cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)', (d['purchase_id'], d['purchase_id'])).fetchone()
        assert ap.quantize(D('.01'), rounding=ROUND_HALF_UP) == D('20.99') and grni == 0
        return dict(status='PASS', qty='1.234567', source_value='20.987640', ap_cents='20.99', stock_events=1)

    def procurement_large():
        f = procurement.fixture(cur, today, qty='3', price='22000000.01', final=True)
        d = procurement.command(cur, 'SAVE_DRAFT', f['payload']); key = uuid.uuid4()
        first = procurement.post(cur, d, key); baseline = b.boundary.snapshot(cur)
        assert procurement.post(cur, d, key) == first and b.boundary.snapshot(cur) == baseline
        ap, grni = cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)', (d['purchase_id'], d['purchase_id'])).fetchone()
        assert ap == D('66000000.03') and grni == 0 and procurement.qty(cur, f) == (3, 1)
        return dict(status='PASS', receipt='66000000.03', ap='66000000.03', one_stock_effect=True, no_int32_cent_overflow=True)

    def fg_adjust():
        f = sales.fg.fixture(cur, today); before = gl(cur)
        d, _ = adjustment.draft(cur, f, '-3'); z = adjustment.action(cur, 'POST', d)
        assert command.available(cur, f) == 7
        valuation = adjustment.read(cur, d['adjustment_id'])['detail']['items'][0]['valuation']
        assert D(valuation['unit_cost']) == 10 and D(valuation['value']) == -30
        adjustment.action(cur, 'REVERSE', z)
        assert command.available(cur, f) == 10 and gl(cur) == before
        return dict(status='PASS', correction=-3, value=-30, final_stock=10, inverse_all_GL=True)

    def thirds():
        f = installments.fixture(cur, today)
        before = gl(cur); cost = installments.legacy.journal(cur, f['payroll'], 'PAYROLL_ATTENDANCE_ACCRUAL')
        rows = [installments.act(cur, f, amount=x) for x in ('333.33','333.33','333.34')]
        d = installments.read(cur, f['payroll'])['document']
        assert (D(d['approved_net']), D(d['paid_amount']), D(d['remaining_amount']), d['native_status']) == (D(1000),D(1000),D(0),'PAID')
        assert cost == (2,D(1000),D(1000)) == installments.legacy.journal(cur, f['payroll'], 'PAYROLL_ATTENDANCE_ACCRUAL')
        want = {installments.legacy.acct(cur,'CONTRACTOR_PAYABLE'):D(1000),f['cash']['account_id']:D(-1000)}
        assert difference(before, gl(cur)) == want and installments.physical.stock_cost(cur) == f['physical']
        installments.act(cur, f, 'REVERSE_PAYMENT', payment=rows[0]['payment_id'])
        d = installments.read(cur, f['payroll'])['document']
        assert D(d['paid_amount']) == D('666.67') and D(d['remaining_amount']) == D('333.33')
        assert installments.legacy.journal(cur, f['payroll'], 'PAYROLL_ATTENDANCE_ACCRUAL') == cost
        return dict(status='PASS', approved='1000', installments=['333.33','333.33','333.34'], reverse_remaining='333.33', cost_recognized_once=True, stock_HPP_unchanged=True)

    def installment_stale():
        f = installments.fixture(cur, today); d = installments.read(cur, f['payroll'])['document']
        old = installments.intent(d, 'PAY', f, '600.01')
        installments.act(cur, f, amount='400.00'); before = b.boundary.snapshot(cur)
        error = refuse(cur, lambda:installments.command(cur, 'PAY', old, d['row_version']), 'REVIEW_CHANGED|SOURCE_CHANGED|STALE')
        assert b.boundary.snapshot(cur) == before
        d = installments.read(cur, f['payroll'])['document']
        fresh = installments.intent(d, 'PAY', f, '600.01')
        error2 = refuse(cur, lambda:installments.command(cur, 'PAY', fresh, d['row_version']), 'AMOUNT|REMAINING')
        assert b.boundary.snapshot(cur) == before
        return dict(status='PASS', stale_refusal=error, overpay_one_cent_refusal=error2, paid='400', remaining='600')

    def operational_redaction():
        f = seven(cur, today); actor, role = custom(cur, ('sales.invoice.view', 'warehouse.procurement.view'))
        assert sales.read(cur, f)['detail']['financial']['gross_total'] == '259.85'
        w = sales.read(cur, f, actor); body = json.dumps(w)
        assert w['financial_captured'] is False
        for key in ('"financial":','"unit_price":','"line_total":','259.85'):
            assert key not in body, key
        r = procurement.fixture(cur, today, price='12345.67'); d = procurement.command(cur, 'SAVE_DRAFT', r['payload'])
        w = procurement.workspace(cur, dict(purchase_id=d['purchase_id']), actor)
        for key in ('"finance":', 'unit_price', 'line_total', '12345.67'):
            assert key not in json.dumps(w), key
        p = installments.fixture(cur, today)
        refuse(cur, lambda:installments.read(cur, p['payroll'], actor), 'DENIED', '42501')
        return dict(status='PASS', invoice_receipt_money_redacted=True, payroll_finance_denied=True, positive_owner_control=True)

    def report_read_only():
        seven(cur, today, True)
        baseline = b.boundary.snapshot(cur)
        r = finance.read(cur, today)
        assert r['snapshot']['basis']['balance_sheet_as_of'] == str(today)
        assert b.boundary.snapshot(cur) == baseline
        for q in ({'as_known':'2020-01-01'}, {'as_of':'2026-02-30'}, {'offset':-1}, {'limit':'25'}):
            refuse(cur, lambda:finance.read(cur, today, **q), 'CP7_FINANCE_QUERY')
        assert b.boundary.snapshot(cur) == baseline
        return dict(status='PASS', report_does_not_write=True, invalid_dates_and_unsupported_history_refused=True)

    return [('IF03_N01_PRODUCTION_MONEY',physical_to_money), ('IF03_N02_DECIMAL_CASH',decimal_cash),
            ('IF03_N03_GRADE_RETURNS',returned_grades), ('IF03_N04_PAID_RETURN_POLICY',paid_policy),
            ('IF03_N05_CHANGED_REPLAY',changed_payment), ('IF03_N06_REVOKED_REPLAY',current_replay),
            ('IF03_N07_COMPLETE_PAGES',pages), ('IF03_N08_RECEIPT_PRECISION',procurement_decimal),
            ('IF03_N09_LARGE_RECEIPT',procurement_large), ('IF03_N10_FG_INVERSE',fg_adjust),
            ('IF03_N11_PAYROLL_THIRDS',thirds), ('IF03_N12_STALE_OVERPAY',installment_stale),
            ('IF03_N13_OPERATIONAL_REDACTION',operational_redaction), ('IF03_N14_READ_ONLY_REPORT',report_read_only)]


def races(tools, today):
    def cash(same):
        with tools.connect() as conn, conn.cursor() as cur:
            f = seven(cur, today, True); p, v = payments.payment_payload(cur, f, '200.01')
            before = gl(cur); bank = payments.bank_account(cur, f); ar = command.mapping(cur, 'AR_CUSTOMER'); conn.commit()
        gate = threading.Barrier(2); request = uuid.uuid4()
        def send(n):
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=10)
                try:
                    payload = p if same else dict(p, payment_number=p['payment_number']+'-'+str(n))
                    r = command.command(cur, 'PAYMENT', payload, v, request if same else uuid.uuid4()); conn.commit(); return dict(ok=r)
                except psycopg.Error as exc:
                    conn.rollback(); return dict(sqlstate=exc.sqlstate, error=exc.diag.message_primary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(send, n) for n in (1,2)]; results = [x.result(45) for x in futures]
        if same:
            assert results[0] == results[1] and 'ok' in results[0], results
        else:
            assert sum('ok' in x for x in results) == 1, results
            loser = next(x for x in results if 'ok' not in x)
            assert loser == dict(sqlstate='P0001', error='CP7_SALES_REVIEW_CHANGED'), loser
        with tools.connect() as conn, conn.cursor() as cur:
            assert difference(before, gl(cur)) == {bank:D('200.01'), ar:D('-200.01')}
            assert sales.read(cur, f)['detail']['financial']['open_balance'] == '59.84'
            assert command.available(cur, f) == 3
            assert cur.execute('select count(*) from erp.sales_payments where sale_id=%s', (f['sale'],)).fetchone()[0] == 1
        return dict(status='PASS', same_UUID=same, results=results, committed_payments=1, cash='200.01', AR='59.84', stock=3)

    def revoke_during_replay():
        request = uuid.uuid4()
        with tools.connect() as conn, conn.cursor() as cur:
            f = seven(cur, today, True); actor, role = custom(cur, PAY_PERMISSIONS)
            p, v = payments.payment_payload(cur, f, '17.29'); command.command(cur, 'PAYMENT', p, v, request, actor); conn.commit()
        marker = 'if03-replay-'+uuid.uuid4().hex
        with tools.connect() as holder, holder.cursor() as h:
            h.execute('select 1 from cp7_sales.requests where actor=%s and request_id=%s for update', (actor,request))
            assert h.fetchone() is not None
            def send():
                with tools.connect(application_name=marker) as conn, conn.cursor() as cur:
                    try:
                        command.command(cur,'PAYMENT',p,v,request,actor); conn.commit(); return dict(unexpected_success=True)
                    except psycopg.Error as exc:
                        conn.rollback(); return dict(sqlstate=exc.sqlstate, error=exc.diag.message_primary)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(send)
                try:
                    with tools.connect(autocommit=True) as inspect, inspect.cursor() as c:
                        deadline = time.monotonic()+10; waited = None
                        while time.monotonic() < deadline:
                            c.execute('select pg_stat_clear_snapshot()')
                            waited = c.execute("select pid from pg_stat_activity where datname=current_database() and application_name=%s and wait_event_type='Lock'", (marker,)).fetchone()
                            if waited: break
                            time.sleep(.025)
                        assert waited, 'OWN_WORKER_MUST_BE_OBSERVED_WAITING'
                        c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.payment.post'", (role,))
                        baseline = b.boundary.snapshot(c)
                finally:
                    holder.rollback()
                result = future.result(45)
        assert result == dict(sqlstate='42501', error='CP7_SALES_WRITE_DENIED'), result
        with tools.connect() as conn, conn.cursor() as cur:
            assert b.boundary.snapshot(cur) == baseline
            assert sales.read(cur,f)['detail']['financial']['open_balance'] == '242.56'
        return dict(status='PASS', observed_worker_pid=waited[0], exact_denial=result, state_after_revocation_unchanged=True)

    def payroll():
        with tools.connect() as conn, conn.cursor() as cur:
            f=installments.fixture(cur,today); d=installments.read(cur,f['payroll'])['document']
            p=installments.intent(d,'PAY',f,'700.01'); before=gl(cur); conn.commit()
        gate=threading.Barrier(2)
        def send():
            with tools.connect() as conn,conn.cursor() as cur:
                gate.wait(timeout=10)
                try:
                    r=installments.command(cur,'PAY',p,d['row_version']);conn.commit();return dict(ok=r)
                except psycopg.Error as exc:
                    conn.rollback();return dict(sqlstate=exc.sqlstate,error=exc.diag.message_primary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(send) for _ in range(2)]; results=[j.result(45) for j in jobs]
        assert sum('ok' in x for x in results)==1,results
        loser=next(x for x in results if 'ok' not in x)
        assert loser['sqlstate']=='P0001' and re.search('REVIEW_CHANGED|SOURCE_CHANGED|STALE',loser['error']),loser
        with tools.connect() as conn,conn.cursor() as cur:
            row=installments.read(cur,f['payroll'])['document']
            assert (D(row['paid_amount']),D(row['remaining_amount']))==(D('700.01'),D('299.99'))
            assert difference(before,gl(cur))=={installments.legacy.acct(cur,'CONTRACTOR_PAYABLE'):D('700.01'),f['cash']['account_id']:D('-700.01')}
            assert installments.physical.stock_cost(cur)==f['physical']
        return dict(status='PASS',results=results,paid='700.01',remaining='299.99',stock_HPP_unchanged=True)

    return [('IF03_R01_CASH_SAME_UUID',lambda:cash(True)),('IF03_R02_CASH_COMPETING',lambda:cash(False)),
            ('IF03_R03_REVOKE_WHILE_REPLAY_WAITING',revoke_during_replay),('IF03_R04_PAYROLL_COMPETING',payroll)]


def http_cases(http, today):
    def sale():
        owner=http.login('OWNER','independent-f03-sale')
        with http.connect() as conn,conn.cursor() as cur:
            f=seven(cur,today);p,v=command.review(cur,f);conn.commit()
        args=dict(p_action='POST',p_payload=p,p_request=str(uuid.uuid4()),p_expected=v)
        assert http.anon_rpc('erp_cp7_save_sale_v1',args)['status'] in (401,403)
        result=owner.rpc('erp_cp7_save_sale_v1',args)
        assert result['status']==200 and result['body']['status']=='POSTED',result
        assert owner.rpc('erp_cp7_save_sale_v1',args)==result
        with http.connect() as conn,conn.cursor() as cur:
            assert command.available(cur,f)==3
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
            before=b.boundary.snapshot(cur);conn.rollback()
        denied=owner.rpc('erp_cp7_save_sale_v1',args)
        assert denied['status']==403 and denied['body']['code']=='42501',denied
        with http.connect() as conn,conn.cursor() as cur:assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',actual_auth=True,post_and_replay=True,inactive_replay_http=403,stock=3,denied_state_unchanged=True)

    def private_rest():
        owner=http.login('OWNER','independent-f03-private')
        # Profile rejection proves the real private schema is unexposed. Calling
        # an invented public RPC with wrong parameters would not prove that.
        observed={}
        for schema in ('cp7_sales','cp7_payroll','cp7_installment','cp7_procurement','cp7_fg','cp7_finance'):
            r=modes._call(modes.REST_URL+'/rpc/access_now',{},
                 {'apikey':http._anon,'Authorization':'Bearer '+owner._token,'Content-Profile':schema})
            assert r['status']==406 and r['body']['code']=='PGRST106',(schema,r)
            observed[schema]=dict(status=r['status'],code=r['body']['code'])
        return dict(status='PASS',actual_private_schema_rest_rejections=observed)

    def payroll():
        owner=http.login('OWNER','independent-f03-payroll')
        with http.connect() as conn,conn.cursor() as cur:
            had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            if not had:cur.execute('grant usage on schema erp to authenticated')
            f=installments.fixture(cur,today);d=installments.read(cur,f['payroll'])['document']
            b.api.admin(cur)
            if not had:cur.execute('revoke usage on schema erp from authenticated')
            conn.commit()
        args=dict(p_action='PAY',p_payload=installments.intent(d,'PAY',f,'333.33'),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
        r=owner.rpc('erp_cp7_save_payroll_installment_v1',args)
        assert r['status']==200,r
        assert owner.rpc('erp_cp7_save_payroll_installment_v1',args)==r
        read=owner.rpc('erp_cp7_get_payroll_installments_v1',dict(p_query=dict(payroll_id=f['payroll'])))
        assert read['status']==200 and D(read['body']['document']['remaining_amount'])==D('666.67'),read
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        denied=owner.rpc('erp_cp7_save_payroll_installment_v1',args)
        assert denied['status']==403 and denied['body']['code']=='42501',denied
        return dict(status='PASS',same_request_one_installment=True,remaining='666.67',inactive_replay_http=403)

    return [('IF03_H01_SALE_AUTH',sale),('IF03_H02_PRIVATE_REST',private_rest),('IF03_H03_PAYROLL_AUTH',payroll)]
