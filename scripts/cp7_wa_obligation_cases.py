"""D17-14 OW-01. Native obligation writers -> WA collector -> fake transport.

Use the accepted opening/payroll/accessory/laundry fixtures. No substituted due
dates, computed payable amounts, or business-table changes by this suite. The
seven domains are exercised before/after actual payment, allocation and reversal.
"""
import json
from decimal import Decimal as D

import cp7_other_obligation_cases as other
import cp7_wa_forward_cases as wa

KINDS = ['OPENING_AR', 'OPENING_AP', 'PAYROLL_AP', 'ACCESSORY_AP', 'LAUNDRY_AP',
         'LAUNDRY_RECEIPT', 'LAUNDRY_OPENING_UNINVOICED']
IDS = ['WAF_OTHER_OPENING_AR_AP', 'WAF_OTHER_PAYROLL_PAYMENT_INVERSE',
       'WAF_OTHER_ACCESSORY_ALLOCATION_NOT_SETTLEMENT', 'WAF_OTHER_LAUNDRY_PAYMENT_INVERSE',
       'WAF_OTHER_LAUNDRY_OPENING_UNKNOWN', 'WAF_OTHER_NARROWER_PERMISSIONS',
       'WAF_OTHER_ALL_DOMAINS_SUMMARY_PRIVATE']


def source(cur, owner):
    wa.auth.actor(cur, owner)
    # Same current identity as the tick. Private reader is not exposed to authenticated.
    wa.b.api.admin(cur)
    result = wa.one(cur, 'select cp7_reminder_native.other_obligation_source()')
    wa.b.api.admin(cur)
    return result


def collect(cur):
    result = wa.tick(cur, 'collect_tick')
    assert result['outcome'] == 'COLLECTED', result
    assert all(k in result['kinds'] and 'error' not in result['kinds'][k] for k in KINDS), result
    return result


def row(cur, kind, identity):
    key = other.key(kind, identity)
    return dict(wa.alerts(cur, kind)[key], subject_key=key)


def assert_amount(cur, kind, identity, amount, state='DATA_REVIEW'):
    r = row(cur, kind, identity)
    d = r['detail']
    assert d['domain'] == kind and d['source_id'] == str(identity) and d['state'] == state, d
    if amount is None:
        assert d['remaining_state'] == 'UNKNOWN' and d['remaining'] is None, d
    else:
        assert d['remaining_state'] == 'KNOWN' and D(d['remaining']) == D(amount), d
    return r


def sent(cur):
    before = wa.last_request(cur)
    result = wa.tick(cur, 'send_tick')
    assert result['outcome'] == 'SENT', result
    message = wa.dispatch(cur, result['dispatch_id'])
    requests = wa.queued(cur, before)
    assert len(requests) == 1 and requests[0]['base'] == wa.FAKE and requests[0]['phone'] == wa.PHONE
    assert requests[0]['text'] == message['body'] and 0 < len(message['body']) <= 1000
    # Never return the decoded request or the key in case output.
    return message


def cases(cur, today):
    def opening():
        f = other.opening.bb.financial_fixture(cur, today, documents=[
            ('CUSTOMER_RECEIVABLE', 'WAF-AR', '100.00', '30.00'),
            ('SUPPLIER_PAYABLE', 'WAF-AP', '100.00', '35.00')])
        cfg = wa.setup(cur, kinds=KINDS)
        before = wa.b.boundary.snapshot(cur)
        collect(cur)
        ar = assert_amount(cur, 'OPENING_AR', f['balances']['WAF-AR'], '70')
        ap = assert_amount(cur, 'OPENING_AP', f['balances']['WAF-AP'], '65')
        assert ar['detail']['due_date'] is None and ap['detail']['due_date'] is None
        assert ar['detail']['reason'] == ap['detail']['reason'] == 'MISSING_RECORDED_DUE_DATE'
        src = source(cur, cfg['owner'])
        for actual in (ar, ap):
            native = next(r for r in src['rows'] if r['key'] == actual['subject_key'])
            assert actual['detail']['remaining'] == native['financial_source']['remaining']['value']
            assert actual['detail']['source_hash'] == native['source_hash']
        collect(cur)
        assert wa.one(cur, 'select count(*) from cp7_alert_native.outbox where item_id=any(%s::uuid[])', ([ar['id'], ap['id']],)) == 2
        message = sent(cur)
        assert 'Piutang saldo awal' in message['body'] and 'Utang saldo awal' in message['body']
        assert f['code'] not in message['body'] and 'perlu diperiksa' in message['body']
        assert wa.b.boundary.snapshot(cur) == before
        return dict(status='PASS', opening_receivable='70.00', opening_payable='65.00', no_invented_due_date=True,
                    exact_native_source=True, one_episode_each=True, fake_message=True, business_unchanged=True)

    def payroll():
        f = other.installments.fixture(cur, today)
        # The fixture includes other open payrolls. Detailed mode must carry
        # this payroll's exact 400; summary correctly adds all open payrolls.
        wa.setup(cur, kinds=KINDS, detail='DETAILED', max_items=20)
        collect(cur)
        first = assert_amount(cur, 'PAYROLL_AP', f['payroll'], '1000')
        payment = other.installments.act(cur, f)
        collect(cur)
        partial = assert_amount(cur, 'PAYROLL_AP', f['payroll'], '400')
        assert first['id'] == partial['id'] and first['episode'] == partial['episode']
        message = sent(cur)
        assert 'Tagihan gaji' in message['body'] and 'Rp400' in message['body'], message['body']
        other.installments.act(cur, f, amount='400.00')
        collect(cur)
        assert other.key('PAYROLL_AP', f['payroll']) not in wa.alerts(cur, 'PAYROLL_AP')
        other.installments.act(cur, f, 'REVERSE_PAYMENT', payment=payment['payment_id'])
        collect(cur)
        reopened = assert_amount(cur, 'PAYROLL_AP', f['payroll'], '600')
        assert reopened['id'] != first['id'] and reopened['episode'] == first['episode'] + 1
        return dict(status='PASS', exact_native_balances=['1000', '400', '0', '600'], partial_keeps_episode=True,
                    settled_closes_inverse_new_episode=True, fake_message=True)

    def accessory():
        f = other.accessory_fixture(cur, today)
        wa.setup(cur, kinds=KINDS)
        collect(cur)
        original = assert_amount(cur, 'ACCESSORY_AP', f['credit']['event_id'], '12')
        other.allocate_accessory(cur, f)
        collect(cur)
        allocated = assert_amount(cur, 'ACCESSORY_AP', f['credit']['event_id'], None)
        assert allocated['id'] == original['id'] and allocated['detail']['reason'] == 'ALLOCATION_NOT_SETTLEMENT'
        message = sent(cur)
        assert 'Kredit retur aksesori mandor' in message['body'] and 'perlu diperiksa' in message['body']
        assert 'nilai terbuka' not in message['body'].split('Kredit retur aksesori mandor:')[1].split('\n')[0]
        other.pay_accessory(cur, f)
        collect(cur)
        assert other.key('ACCESSORY_AP', f['credit']['event_id']) not in wa.alerts(cur, 'ACCESSORY_AP')
        return dict(status='PASS', credit='12.00', allocated_not_paid_keeps_episode_and_unknown=True,
                    paid_closes=True, no_unknown_zero_or_double_total=True)

    def laundry():
        f = other.laundry_fixture(cur, today, invoice=True)
        wa.setup(cur, kinds=KINDS)
        collect(cur)
        a = assert_amount(cur, 'LAUNDRY_AP', f['invoice'], '17312.90', 'ACTIVE')
        r = assert_amount(cur, 'LAUNDRY_RECEIPT', f['line'], None)
        other.fund_main(cur, '17312.90')
        payment = other.bd.pay(cur, f['invoice'], '17312.90', f['day'])
        # Recheck at send time also closes pending rows; no second message for the settled documents.
        wa.tick(cur, 'send_tick')
        for kind, identity in [('LAUNDRY_AP', f['invoice']), ('LAUNDRY_RECEIPT', f['line'])]:
            assert other.key(kind, identity) not in wa.alerts(cur, kind)
        for item in (a, r):
            assert wa.outbox(cur, item['id'])[0]['state'] == 'RESOLVED_BEFORE_SEND'
        other.bd.internal(cur, 'reverse_vendor_payment', payment, 'D17-14 WA Native inverse')
        collect(cur)
        assert_amount(cur, 'LAUNDRY_AP', f['invoice'], '17312.90', 'ACTIVE')
        assert_amount(cur, 'LAUNDRY_RECEIPT', f['line'], None)
        wa.age_dispatches(cur, 2)
        message = sent(cur)
        assert 'Tagihan laundry' in message['body'] and 'Penerimaan laundry perlu diperiksa' in message['body']
        assert 'nilai terbuka' not in message['body'].split('Penerimaan laundry perlu diperiksa:')[1].split('\n')[0]
        return dict(status='PASS', final_payable='17312.90', receipt_not_double_payable=True,
                    send_recheck_sees_paid=True, inverse_reopens=True)

    def laundry_opening():
        f = other.laundry_opening_fixture(cur, today)
        wa.setup(cur, kinds=KINDS)
        collect(cur)
        for identity in f['ids'].values():
            assert_amount(cur, 'LAUNDRY_OPENING_UNINVOICED', identity, None)
        message = sent(cur)
        assert 'Laundry awal belum ditagih' in message['body'] and 'perlu diperiksa' in message['body']
        assert 'Rp70.000' not in message['body'] and 'Rp0' not in message['body']
        return dict(status='PASS', two_opening_receipts_unknown=True, estimate_not_final_payable=True, fake_message=True)

    def permissions():
        f = other.installments.fixture(cur, today)
        wa.setup(cur, kinds=KINDS)
        collect(cur)
        subject, role = other.actor(cur)
        full = wa.rpc(cur, 'erp_cp7_get_alerts_v1', ('{}',), subject)
        assert any(r['kind'] == 'PAYROLL_AP' and r['detail']['source_id'] == f['payroll'] for r in full['rows'])
        for permission, hidden in [
            ('finance.payroll.view', {'PAYROLL_AP'}),
            ('warehouse.accessory.view', {'ACCESSORY_AP'}),
            ('production.laundry.view', {'LAUNDRY_AP', 'LAUNDRY_RECEIPT', 'LAUNDRY_OPENING_UNINVOICED'}),
            ('finance.ar.view', {'OPENING_AR'}),
            ('finance.ap.view', set(KINDS) - {'OPENING_AR'}),
        ]:
            other.revoke(cur, role, permission)
            narrowed = wa.rpc(cur, 'erp_cp7_get_alerts_v1', ('{}',), subject)
            assert not any(r['kind'] in hidden for r in narrowed['rows'] + narrowed['kinds']), (permission, narrowed)
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)', (role, permission))
        return dict(status='PASS', current_domain_permissions_on_cached_rows_and_kind_counts=True, cases=5)

    def all_summary():
        cfg = wa.setup(cur, kinds=KINDS)
        defaults = wa.one(cur, 'select cp7_alert_native.defaults()')
        assert set(KINDS) <= set(defaults['kinds'])
        # SYNTHETIC_RENDER_INPUT: privacy/overflow oracle only, never a business-source or settlement proof.
        items = [dict(kind=k, subject_key=k, title='Rahasia pihak '+k, detail=dict(label='Rahasia pihak '+k,
                     remaining_state='UNKNOWN', remaining=None, economic_state='UNKNOWN', state='DATA_REVIEW')) for k in KINDS]
        body = wa.one(cur, "select cp7_alert_native.render('DIGEST',%s::jsonb,'{}','SUMMARY',10,statement_timestamp(),'{}')", (json.dumps(items),))
        assert 'Rahasia pihak' not in body and 'Rp0' not in body and len(body) <= 1000
        assert body.count('1 pengingat') == 7 and body.count('perlu diperiksa') >= 7
        assert body.endswith('Buka ERP > Reminder')
        # ACTIVE has no review suffix. It must not concatenate SQL NULL and
        # lose the whole message (first failure run 39406686784, laundry).
        active = [dict(x, detail=dict(x['detail'], domain=x['kind'], state='ACTIVE', remaining_state='KNOWN',
                      remaining='17312.90', economic_state='OPEN', due_date='2026-10-20')) for x in items]
        body_active = wa.one(cur, "select cp7_alert_native.render('INSTANT',%s::jsonb,'{}','SUMMARY',10,statement_timestamp(),'{}')", (json.dumps(active),))
        assert body_active is not None and body_active.count('Rp17.312,9') == 7 and body_active.endswith('Buka ERP > Reminder'), body_active
        settings = wa.rpc(cur, 'erp_cp7_get_wa_settings_v1', (), cfg['owner'])
        assert set(settings['settings']['kinds']) == set(KINDS)
        return dict(status='PASS', seven_default_domains_and_saved_settings=True, summary_private_and_all_counted=True,
                    synthetic_render_input=True, unknown_not_zero=True, active_without_review_suffix_not_null=True)

    return list(zip(IDS, [opening, payroll, accessory, laundry, laundry_opening, permissions, all_summary]))
