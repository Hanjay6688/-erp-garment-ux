"""Thirteen missing system-kind receipts, on thirteen fresh committed copies.

Expected cases are declared in EXPECTED.json before this module was written.
Each case uses the accepted Native fixtures, the real pg_net queue/worker and
the existing fake CallMeBot. Nothing inserts a provider answer or renders a
synthetic source. Native execution is pending; importing registers cases only.

The importing WA module passes itself to races(), avoiding a circular import.
The modes runner MUST recreate cp6_auditor_race before EACH registered case.
"""
from datetime import timedelta
from decimal import Decimal as D
from urllib.parse import urlparse

import cp7_other_obligation_cases as other


KINDS = (
    'FG_AT_REORDER_POINT', 'ACCESSORY_AT_REORDER_POINT', 'AR_DUE', 'AP_DUE',
    'PRODUCTION_GAP', 'FABRIC_NEED', 'OPENING_AR', 'OPENING_AP', 'PAYROLL_AP',
    'ACCESSORY_AP', 'LAUNDRY_AP', 'LAUNDRY_RECEIPT', 'LAUNDRY_OPENING_UNINVOICED',
)
RACE_IDS = tuple('WAF_RACE_ALL_KIND_' + kind + '_FAKE_PROVIDER' for kind in KINDS)
OTHER = frozenset(KINDS[6:])
ANALYSIS = frozenset(('PRODUCTION_GAP', 'FABRIC_NEED'))
HEADINGS = {
    'FG_AT_REORDER_POINT': 'Stok barang jadi menipis',
    'ACCESSORY_AT_REORDER_POINT': 'Stok aksesori menipis',
    'AR_DUE': 'Piutang pelanggan jatuh tempo', 'AP_DUE': 'Tagihan supplier jatuh tempo',
    'PRODUCTION_GAP': 'Kekurangan produksi', 'FABRIC_NEED': 'Kain perlu dibeli',
    'OPENING_AR': 'Piutang saldo awal', 'OPENING_AP': 'Utang saldo awal',
    'PAYROLL_AP': 'Tagihan gaji', 'ACCESSORY_AP': 'Kredit retur aksesori mandor',
    'LAUNDRY_AP': 'Tagihan laundry', 'LAUNDRY_RECEIPT': 'Penerimaan laundry perlu diperiksa',
    'LAUNDRY_OPENING_UNINVOICED': 'Laundry awal belum ditagih',
}


def _disposable(cur, tools, wa):
    wa.b.api.admin(cur)
    actual = wa.one(cur, 'select current_database()')
    assert actual == urlparse(tools.admin).path.lstrip('/') == 'cp6_auditor_race', (
        'WA_ALL_KINDS_REQUIRES_DISPOSABLE_RACE_COPY', actual)
    assert wa.one(cur, "select current_setting('pg_net.database_name',true)") != actual, (
        'WA_ALL_KINDS_WORKER_MUST_NOT_TARGET_COPY_BEFORE_SEND_COMMIT')


def _semantic(row):
    # These two read clocks are deliberately not a business/source revision.
    # data_as_of, actual document dates and every actual amount remain compared.
    return {**row, 'detail': {k: v for k, v in row['detail'].items()
                             if k not in ('as_of', 'checked_at')}}


def _policy(cur, wa, x, unit):
    wa.b.api.admin(cur)
    revision = wa.one(cur, "select coalesce(max(revision),0) from cp7_reminder_native.rule_policies "
                           "where rule_id=%s and scope_kind='GLOBAL' and scope_key='*'", (x['kind'],))
    wa.remv2.policy(cur, x['run'], x['kind'], unit, revision=str(revision), subject=x['owner'])


def _fixture(cur, today, wa, kind, owner):
    """Stop before any old case's later payment, receipt, inverse or local claim."""
    x = dict(kind=kind, owner=owner)
    if kind == 'FG_AT_REORDER_POINT':
        f = wa.formula.item(cur, today, 140)
        wa.formula.sell_days(cur, f, today, wa.formula.PATTERN)
        wa.formula.profile(cur, f, lead_days=7)
        point = wa.formula.oracle(140, wa.formula.PATTERN, today, lead=7)['point']
        free = 140 - sum(wa.formula.PATTERN)
        assert free <= point, ('WA_ALL_KINDS_FG_FIXTURE_NOT_LOW', free, point)
        wa.b.api.admin(cur)
        name, size = cur.execute('select p.product_name,s.size_code from erp.products p '
                                'join erp.sizes s on s.id=p.size_id where p.id=%s', (f['product'],)).fetchone()
        x.update(subjects=[f['target']], free=free, point=point,
                 body_fragments=[name + ' ' + size, ': sisa %s pcs, sedang diproduksi 0 pcs, titik pesan ulang %s pcs' % (free, point)])
    elif kind == 'ACCESSORY_AT_REORDER_POINT':
        admin = wa.master.role_actor(cur, 'ADMIN')
        f = wa.formula.accessory(cur, today, 280)
        wa.formula.accessory_days(cur, f, today, wa.formula.SPARSE)
        wa.formula.save_material(cur, admin, f['material'], lead=20,
                                estimate=dict(moq='5000', usage_month_qty='300', buffer_days='5'),
                                reason='Explicit all-kind fake-delivery minimum fixture')
        assert wa.formula.estimate_oracle(300, 20, 5) == 250
        x.update(subjects=[f['material']], body_fragments=[f['name']])
    elif kind in ('AR_DUE', 'AP_DUE'):
        f = wa.ar_overdue(cur, today) if kind == 'AR_DUE' else wa.ap_overdue(cur, today)
        x.update(subjects=[f['key']], due=str(today - timedelta(days=1)),
                 amount='300' if kind == 'AR_DUE' else '500', body_fragments=[f['party']])
    elif kind == 'PRODUCTION_GAP':
        r, c = wa.remv2.plan_target(cur, today, subject=owner)
        x.update(run=r, condition=c, subjects=[c['key']], amount=str(r['gap']))
        _policy(cur, wa, x, 'PCS')
        x['body_fragments'] = [c['label'] + ': kurang ' + wa.wa_num(r['gap']) + ' pcs']
    elif kind == 'FABRIC_NEED':
        f = wa.remv2.physical.bound(cur, today, subject=owner)
        _, _, done, _ = wa.remv2.staged.staged_done(cur, today, subject=owner)
        r = dict(run=done['run_id'], identity=wa.remv2.identity(cur, done['run_id']))
        wa.remv2.ready_set(cur, r['run'], owner)
        found = [c for c in wa.remv2.conditions(cur, r['run'], kind, subject=owner)
                 if c['target_key'] == f['target']]
        assert len(found) == 1, ('WA_ALL_KINDS_FABRIC_CONDITION_MISSING', len(found))
        c = found[0]
        assert c['state'] == 'ACTIVE' and c['value']['state'] == 'ASSUMED' and D(c['value']['value']) == 176, c
        x.update(run=r, condition=c, subjects=[c['key']], amount='176')
        _policy(cur, wa, x, c['value']['unit'])
        x['body_fragments'] = [': 176 ' + c['value']['unit']]
    elif kind in ('OPENING_AR', 'OPENING_AP'):
        name, domain, amount = ('WAF-AR', 'CUSTOMER_RECEIVABLE', '70') if kind == 'OPENING_AR' else ('WAF-AP', 'SUPPLIER_PAYABLE', '65')
        f = other.opening.bb.financial_fixture(cur, today, documents=[
            (domain, name, '100.00', '30.00' if kind == 'OPENING_AR' else '35.00')])
        x.update(subjects=[other.key(kind, f['balances'][name])], amount=amount,
                 reason='MISSING_RECORDED_DUE_DATE', source_state='DATA_REVIEW', body_fragments=['Rp' + amount, 'perlu diperiksa'])
    elif kind == 'PAYROLL_AP':
        f = other.installments.fixture(cur, today)
        other.installments.act(cur, f)  # The actual 600 payment PRECEDES the freeze/collect/send.
        x.update(subjects=[other.key(kind, f['payroll'])], amount='400',
                 source_state='DATA_REVIEW', body_fragments=['Rp400', 'perlu diperiksa'])
    elif kind == 'ACCESSORY_AP':
        f = other.accessory_fixture(cur, today)
        other.allocate_accessory(cur, f)  # Allocation is explicitly not payment.
        x.update(subjects=[other.key(kind, f['credit']['event_id'])], amount=None,
                 reason='ALLOCATION_NOT_SETTLEMENT', source_state='DATA_REVIEW',
                 body_fragments=['nilai belum diketahui', 'perlu diperiksa'])
    elif kind in ('LAUNDRY_AP', 'LAUNDRY_RECEIPT'):
        f = other.laundry_fixture(cur, today, invoice=kind == 'LAUNDRY_AP')
        x.update(subjects=[other.key(kind, f['invoice'] if kind == 'LAUNDRY_AP' else f['line'])],
                 amount='17312.90' if kind == 'LAUNDRY_AP' else None,
                 source_state='ACTIVE' if kind == 'LAUNDRY_AP' else 'DATA_REVIEW',
                 body_fragments=['Rp17.312,9'] if kind == 'LAUNDRY_AP' else ['nilai belum diketahui', 'perlu diperiksa'])
        if kind == 'LAUNDRY_AP':
            x['due'] = str(f['day'])
        else:
            x['reason'] = 'VALUE_PENDING'
    elif kind == 'LAUNDRY_OPENING_UNINVOICED':
        f = other.laundry_opening_fixture(cur, today)
        assert set(f['ids']) == {'GOOD', 'FAILED_ATTEMPT'}, f['ids']
        x.update(subjects=sorted(other.key(kind, i) for i in f['ids'].values()), amount=None,
                 source_state='DATA_REVIEW', body_fragments=['nilai belum diketahui', 'perlu diperiksa'])
    else:
        raise AssertionError(('WA_ALL_KINDS_UNREGISTERED_FIXTURE', kind))
    if kind in ANALYSIS:
        document, pages, _ = wa.remv2.staged.fetch(cur, x['run']['run'], owner)
        expected = wa.remv2.expected_rows(document)[x['condition']['key']]
        assert expected['value'] == x['condition']['value'], 'WA_ALL_KINDS_CONDITION_NOT_ORIGINAL_SOURCE'
        assert pages['identity_hash'] == x['run']['identity'], 'WA_ALL_KINDS_ORIGINAL_IDENTITY'
        x.update(original=document, original_identity=pages['identity_hash'])
    return x


def _native_source(cur, wa, x):
    """Read real source functions; never substitute an alert as the source oracle."""
    wa.auth.actor(cur, x['owner'])
    wa.b.api.admin(cur)  # Same JWT identity; private readers stay private.
    kind = x['kind']
    if kind in OTHER:
        raw = wa.one(cur, 'select cp7_reminder_native.other_obligation_source()')
        rows = [r for r in raw['rows'] if r['domain'] == kind and r['state'] in ('ACTIVE', 'DATA_REVIEW')]
        assert set(x['subjects']) <= {r['key'] for r in rows}, ('WA_ALL_KINDS_NATIVE_SOURCE_MISSING', kind)
        return {r['key']: dict({k: r[k] for k in ('domain', 'source_id', 'label', 'state', 'reason',
                                                  'economic_state', 'source_hash', 'financial_source')},
                              as_of=raw['as_of']) for r in rows}
    if kind in ANALYSIS:
        v = wa.remv2.recheck(cur, x['run']['run'], x['subjects'][0], x['owner'])
        assert v['verdict'] == 'STILL_OPEN', v
        assert v['condition_key'] == x['subjects'][0] and v['target_key'] == x['condition']['target_key'], v
        number = 'need_now_pcs' if kind == 'PRODUCTION_GAP' else 'snapshot_value'
        assert D(v['numbers'][number]) == D(x['amount']), v
        if kind == 'FABRIC_NEED':
            assert v['reason'] == 'FABRIC_NEED_UNCHANGED_SINCE_SNAPSHOT', v
            assert v['numbers']['snapshot_unit'] == x['condition']['value']['unit'], v
        # Dynamic checked_at is not a source revision. All monetary/quantity,
        # material, policy and recorded-source fields in numbers stay frozen.
        return {x['subjects'][0]: {k: v[k] for k in ('rule_id', 'condition_key', 'target_key',
                                                   'label', 'data_as_of', 'verdict', 'reason', 'numbers')}}
    sql = {
        'FG_AT_REORDER_POINT': 'select cp7_stock_formula.fg_source()',
        'ACCESSORY_AT_REORDER_POINT': "select cp7_stock_formula.material_source('ACCESSORY')",
        'AR_DUE': 'select cp7_alert_native.ar_source()',
        'AP_DUE': 'select cp7_alert_native.ap_source()',
    }[kind]
    raw = wa.one(cur, sql)
    rows = [r for r in raw['rows'] if r['subject_key'] in x['subjects']]
    assert len(rows) == len(x['subjects']), ('WA_ALL_KINDS_NATIVE_SOURCE_MISSING', kind)
    return {r['subject_key']: _semantic(r) for r in rows}


def _other_detail(src):
    """Exact actual-source projection, shared by required and comparison rows."""
    amount = src['financial_source']['remaining']
    return dict({k: src[k] for k in ('domain', 'source_id', 'label', 'state', 'reason',
                                     'economic_state', 'source_hash', 'as_of')},
                remaining_state=amount['state'], remaining=amount.get('value'),
                due_date=src['financial_source']['recorded_due_date'])


def _assert_alerts(cur, wa, x, source):
    kind = x['kind']
    actual = wa.alerts(cur, kind)
    public = wa.rpc(cur, 'erp_cp7_get_alerts_v1', ('{}',), x['owner'])
    selected = {}
    for subject in x['subjects']:
        assert subject in actual, ('WA_ALL_KINDS_ALERT_MISSING', kind, subject)
        a, src = actual[subject], source[subject]
        d = a['detail']
        visible = [r for r in public['rows'] if r['kind'] == kind and r['subject_key'] == subject and r['state'] == 'OPEN']
        assert len(visible) == 1 and visible[0]['id'] == a['id'] and visible[0]['detail'] == d, (
            'WA_ALL_KINDS_PUBLIC_ALERT_DIFFERS', kind, subject)
        if kind in OTHER:
            assert d == _other_detail(src), ('WA_ALL_KINDS_OTHER_DETAIL_NOT_EXACT_NATIVE_SOURCE', kind, subject)
            assert d['domain'] == kind and d['source_id'] == src['source_id'] and d['source_hash'] == src['source_hash'], d
            assert d['label'] == src['label'] and d['state'] == x['source_state'] == src['state'], d
            assert d['remaining_state'] == src['financial_source']['remaining']['state'], d
            assert d['remaining'] == src['financial_source']['remaining'].get('value'), d
            assert d['due_date'] == src['financial_source']['recorded_due_date'], d
            if x['amount'] is None:
                assert d['remaining_state'] == 'UNKNOWN' and d['remaining'] is None, d
            else:
                assert d['remaining_state'] == 'KNOWN' and D(d['remaining']) == D(x['amount']), d
            if 'reason' in x:
                assert d['reason'] == x['reason'] == src['reason'], d
            if kind in ('OPENING_AR', 'OPENING_AP'):
                assert d['due_date'] is None, d
        elif kind in ANALYSIS:
            assert d['run_id'] == str(x['run']['run']) and d['target_key'] == src['target_key'], d
            assert d['label'] == src['label'] and d['data_as_of'] == src['data_as_of'], d
            number, detail = ('need_now_pcs', 'need_now_pcs') if kind == 'PRODUCTION_GAP' else ('snapshot_value', 'value')
            assert d[detail] == src['numbers'][number] and D(d[detail]) == D(x['amount']), d
            if kind == 'FABRIC_NEED':
                assert d['unit'] == x['condition']['value']['unit'], d
                assert d['material_id'] == src['numbers']['material']['material_id'] and d['material_name'], d
        else:
            assert _semantic(dict(subject_key=subject, title=a['title'], detail=d, party_names=a['party_names'])) == src, (
                'WA_ALL_KINDS_ALERT_NOT_CURRENT_NATIVE_SOURCE', kind)
            if kind == 'FG_AT_REORDER_POINT':
                assert (D(d['free_pcs']), D(d['reorder_point_pcs']), d['wip_status'], D(d['wip_pcs']), d['basis']) == (
                    x['free'], x['point'], 'COMPLETE', 0, 'FORMULA'), d
            elif kind == 'ACCESSORY_AT_REORDER_POINT':
                assert (D(d['free_qty']), D(d['reorder_point_qty']), d['basis'], d['safety_qty'], d['service_level'], D(d['lead_days'])) == (
                    180, 250, 'ESTIMATE', None, None, 20), d
            else:
                assert D(d['open_balance' if kind == 'AR_DUE' else 'remaining']) == D(x['amount']), d
        if 'due' in x:
            assert d['due_date'] == x['due'], d
        selected[subject] = a
    return selected


def _unchanged(cur, wa, x):
    wa.b.api.admin(cur)
    assert wa.b.boundary.snapshot(cur) == x['boundary'], 'WA_ALL_KINDS_NATIVE_BUSINESS_BOUNDARY_CHANGED'
    source = _native_source(cur, wa, x)
    assert source == x['native_source'], ('WA_ALL_KINDS_NATIVE_SOURCE_CHANGED', x['kind'])
    if x['kind'] in ANALYSIS:
        run = x['run']['run']
        document, pages, _ = wa.remv2.staged.fetch(cur, run, x['owner'])
        assert document == x['original'] and pages['identity_hash'] == x['original_identity'], 'WA_ALL_KINDS_ORIGINAL_CHANGED'
        wa.b.api.admin(cur)
        assert wa.one(cur, 'select count(*) from cp7_reminder_native.staged_claims where run_id=%s', (run,)) == 0, 'WA_ALL_KINDS_LOCAL_CLAIM_CREATED'
        assert wa.one(cur, 'select count(*) from cp7_reminder_native.staged_rechecks where run_id=%s', (run,)) == 0, 'WA_ALL_KINDS_LOCAL_RECHECK_RECORDED'
    wa.b.api.admin(cur)
    assert wa.b.boundary.snapshot(cur) == x['boundary'], 'WA_ALL_KINDS_SOURCE_READ_CHANGED_NATIVE_BUSINESS'
    return True


def _prepare(cur, tools, today, wa, kind):
    _disposable(cur, tools, wa)
    assert wa.one(cur, 'select count(*) from cp7_alert_native.dispatches') == 0, 'WA_ALL_KINDS_COPY_NOT_FRESH'
    prior_users = {r[0] for r in cur.execute('select id::text from erp.app_users')}
    cfg = wa.setup(cur, kinds=[kind], detail='DETAILED', max_items=20, repeat_minutes=0,
                   digest_times=[], quiet_enabled=False, analysis_every_minutes=0)
    wa.b.api.admin(cur)
    assert cfg['user'] not in prior_users, 'WA_ALL_KINDS_SETTINGS_OWNER_NOT_FRESH'
    assert wa.one(cur, 'select base_url from cp7_alert_native.transport where id') == wa.FAKE, 'WA_ALL_KINDS_NOT_FAKE_TRANSPORT'
    assert wa.one(cur, 'select count(*) from net.http_request_queue') == 0, 'WA_ALL_KINDS_COPY_QUEUE_NOT_EMPTY'
    x = _fixture(cur, today, wa, kind, cfg['owner'])
    x['boundary'] = wa.b.boundary.snapshot(cur)
    x['native_source'] = _native_source(cur, wa, x)
    if kind in ANALYSIS:
        assert wa.drain(cur)[-1] == 'ANALYSIS_CHECKED', 'WA_ALL_KINDS_ANALYSIS_NOT_CHECKED'
    else:
        out = wa.tick(cur, 'collect_tick')
        assert out['outcome'] == 'COLLECTED' and kind in out['kinds'] and not out['kinds'][kind].get('error'), out
    x['alerts'] = _assert_alerts(cur, wa, x, x['native_source'])
    target_outboxes = []
    for a in x['alerts'].values():
        boxes = wa.outbox(cur, a['id'])
        assert len(boxes) == 1 and boxes[0]['round'] == 0 and boxes[0]['state'] == 'PENDING', boxes
        o = boxes[0]
        assert o['kind'] == kind and o['episode'] == str(a['episode']) and o['attempts'] == 0 and o['dispatch'] is None, o
        target_outboxes.append(o['id'])
    x['target_outboxes'] = sorted(target_outboxes)
    # A single selected kind must fit the real send batch and the final body.
    # Refuse a source overflow rather than skipping its undispatched targets.
    wa.b.api.admin(cur)
    eligible = cur.execute("select id from cp7_alert_native.outbox where state='PENDING' and alert_kind=%s order by id", (kind,)).fetchall()
    x['eligible_outboxes'] = [r[0] for r in eligible]
    assert 0 < len(eligible) <= 20 and set(target_outboxes) <= set(x['eligible_outboxes']), 'WA_ALL_KINDS_SELECTED_BATCH_OVERFLOW'
    if kind in ANALYSIS:
        assert x['eligible_outboxes'] == x['target_outboxes'], 'WA_ALL_KINDS_UNEXPECTED_ANALYSIS_TARGET'
    if kind in OTHER:
        # Accepted payroll fixtures also create comparison payrolls. Every
        # dispatched comparison row must bind to the same actual Native source,
        # although the explicit fixture amount oracle applies to our target.
        selected = cur.execute('select a.subject_key,a.detail from cp7_alert_native.outbox o '
                               'join cp7_alert_native.alerts a on a.id=o.item_id '
                               'where o.id=any(%s::bigint[])', (x['eligible_outboxes'],)).fetchall()
        assert len(selected) == len(eligible), 'WA_ALL_KINDS_SELECTED_NATIVE_LINK_MISSING'
        for subject, detail in selected:
            src = x['native_source'][subject]
            assert detail == _other_detail(src), ('WA_ALL_KINDS_COMPARISON_DETAIL_NOT_EXACT_NATIVE_SOURCE', kind, subject)
    _unchanged(cur, wa, x)
    return x


def _body(body, x):
    assert isinstance(body, str) and 0 < len(body) <= 1000, 'WA_ALL_KINDS_BODY_MISSING_OR_OVERFLOW'
    assert HEADINGS[x['kind']] in body and body.endswith('Buka ERP > Reminder'), body
    for fragment in x['body_fragments']:
        assert fragment in body, ('WA_ALL_KINDS_SOURCE_FRAGMENT_LOST', x['kind'], fragment, body)
    # The fake server intentionally refuses FAIL. Never count its refused
    # receipt or alter the source label to make this transport proof pass.
    assert 'FAIL' not in body, ('WA_ALL_KINDS_FIXTURE_TEXT_WOULD_REFUSE', x['kind'])
    kind = x['kind']
    d = next(iter(x['alerts'].values()))['detail']
    if kind == 'ACCESSORY_AT_REORDER_POINT':
        assert ': sisa 180 %s, minimum 250 %s' % (d['unit_code'], d['unit_code']) in body, body
    elif kind in ('AR_DUE', 'AP_DUE'):
        assert ': Rp' + x['amount'] + ', jatuh tempo ' in body, body
        assert d['number' if kind == 'AR_DUE' else 'purchase_number'] in body, body
    elif kind == 'FABRIC_NEED':
        assert d['material_name'] + ' untuk ' + d['label'] + ': 176 ' + d['unit'] in body, body
    elif kind in OTHER:
        # Each actual target's Native label and expected value must survive
        # left(item_line,120), independently of dispatch-item linkage.
        for a in x['alerts'].values():
            d = a['detail']
            value = ('nilai belum diketahui' if x['amount'] is None else
                     'Rp17.312,9' if kind == 'LAUNDRY_AP' else 'Rp' + x['amount'])
            assert d['label'] + ': ' + value in body, ('WA_ALL_KINDS_TARGET_VALUE_NOT_IN_BODY', kind, body)
        if x['amount'] is None:
            assert 'Rp0' not in body, body
        if kind == 'LAUNDRY_OPENING_UNINVOICED':
            assert 'Rp70.000' not in body, body


def _links(cur, wa, did):
    wa.b.api.admin(cur)
    return cur.execute('select o.id,o.alert_kind,o.item_kind,o.item_id::text,o.item_episode,o.round,o.state,o.attempts,o.dispatch_id '
                       'from cp7_alert_native.dispatch_items i join cp7_alert_native.outbox o on o.id=i.outbox_id '
                       'where i.dispatch_id=%s order by o.id', (did,)).fetchall()


def _send(cur, tools, wa, x):
    _disposable(cur, tools, wa)  # Queue cannot be consumed until this transaction commits.
    assert wa.one(cur, 'select count(*) from net.http_request_queue') == 0, 'WA_ALL_KINDS_UNEXPECTED_QUEUED_REQUEST'
    sent = wa.tick(cur, 'send_tick')
    assert sent['outcome'] == 'SENT', sent
    d = wa.dispatch(cur, sent['dispatch_id'])
    assert d['kind'] == 'INSTANT' and d['status'] == 'QUEUED', d
    requests = wa.queued(cur)
    # Never include the decoded request/key in an assertion or case receipt.
    assert len(requests) == 1, 'WA_ALL_KINDS_NOT_ONE_GENUINE_QUEUED_REQUEST'
    req = requests[0]
    assert (req['id'] == d['net'] and req['base'] == wa.FAKE and req['phone'] == wa.PHONE
            and req['apikey'] == wa.KEY and req['text'] == d['body']), 'WA_ALL_KINDS_QUEUED_DESTINATION_OR_BODY_MISMATCH'
    _body(d['body'], x)
    links = _links(cur, wa, d['id'])
    assert [r[0] for r in links] == x['eligible_outboxes'], 'WA_ALL_KINDS_DISPATCH_ITEMS_NOT_COMPLETE_SELECTED_BATCH'
    assert set(x['target_outboxes']) <= {r[0] for r in links}, 'WA_ALL_KINDS_TARGET_NOT_DISPATCHED'
    assert all((r[1], r[2], r[5], r[6], r[7], r[8]) == (x['kind'], 'ALERT', 0, 'DISPATCHED', 1, d['id']) for r in links), links
    # Read-only proof AFTER the send, BEFORE its immediate COMMIT. All source
    # business writes finished in _prepare's earlier committed transaction.
    _unchanged(cur, wa, x)
    return d


def _accepted(cur, wa, x, did):
    d = wa.dispatch(cur, did)
    assert (d['kind'], d['status'], d['http']) == ('INSTANT', 'PROVIDER_ACCEPTED', 200), d
    assert wa.KEY not in d['text'] and '***' in d['text'], 'WA_ALL_KINDS_PROVIDER_KEY_NOT_MASKED'
    links = _links(cur, wa, did)
    assert [r[0] for r in links] == x['eligible_outboxes'], 'WA_ALL_KINDS_ACCEPTED_LINK_SET_CHANGED'
    assert all((r[1], r[2], r[5], r[6], r[7], r[8]) == (x['kind'], 'ALERT', 0, 'ACCEPTED', 1, did) for r in links), links
    current = _assert_alerts(cur, wa, x, _native_source(cur, wa, x))
    for subject, a in current.items():
        assert (a['id'], a['episode']) == (x['alerts'][subject]['id'], x['alerts'][subject]['episode']), a
    _body(d['body'], x)
    _unchanged(cur, wa, x)
    assert wa.one(cur, 'select count(*) from cp7_alert_native.dispatches') == 1, 'WA_ALL_KINDS_DUPLICATE_DISPATCH'
    assert wa.one(cur, 'select count(*) from net.http_request_queue') == 0, 'WA_ALL_KINDS_QUEUE_NOT_DRAINED'
    return d


def _case(tools, today, wa, kind):
    transport = wa.accessory_transport
    x = transport._committed(tools, lambda cur: _prepare(cur, tools, today, wa, kind))
    before = len(wa.fake_log())
    # Worker was observed off this copy. Queue + source proof COMMIT first;
    # then start the existing worker, which reads only the disposable copy.
    d = transport._committed(tools, lambda cur: _send(cur, tools, wa, x))
    with transport._provider_worker(tools, wa):
        assert transport._wait_answer(tools, d['id']), ('WA_ALL_KINDS_REAL_FAKE_PROVIDER_NO_ANSWER', kind)
        transport._committed(tools, lambda cur: wa.tick(cur, 'send_tick'))  # Normal real-response reconciliation.
        accepted = transport._committed(tools, lambda cur: _accepted(cur, wa, x, d['id']))
        receipts = wa.fake_log()[before:]
        assert len(receipts) == 1, ('WA_ALL_KINDS_NOT_EXACTLY_ONE_REAL_RECEIPT', kind, len(receipts))
        receipt = receipts[0]
        assert (receipt['path'], receipt['phone'], receipt['key_ok'], receipt['status']) == (
            '/whatsapp.php', wa.PHONE, True, 200), receipt
        assert receipt['text'] == accepted['body'] == d['body'], 'WA_ALL_KINDS_FAKE_RECEIPT_NOT_STORED_BODY'
        final = transport._committed(tools, lambda cur: wa.tick(cur, 'send_tick'))
        assert final['outcome'] in ('WAITING', 'IDLE'), final
        transport._committed(tools, lambda cur: _accepted(cur, wa, x, d['id']))
        assert wa.fake_log()[before:] == receipts, ('WA_ALL_KINDS_SECOND_TICK_DUPLICATE_RECEIPT', kind)
    return dict(status='PASS', kind=kind, actual_Native_targets=len(x['subjects']),
                actual_dispatched_items=len(x['eligible_outboxes']), real_fake_provider_receipts=1,
                selected_kind_only=True, actual_phone_key_and_body_match=True,
                target_value_or_UNKNOWN_in_actual_body=True, real_response_status='PROVIDER_ACCEPTED',
                accepted_round=0, attempts=1, next_tick_no_duplicate=True,
                business_source_unchanged_after_send_before_commit=True,
                business_source_unchanged_after_provider_and_final_tick=True,
                Original_identity_unchanged=x['kind'] in ANALYSIS,
                no_local_preview_claim_or_recorded_recheck=x['kind'] in ANALYSIS)


def races(tools, today, wa):
    """Registration is pure; no fixture/connection until the runner calls a case."""
    return [(case_id, lambda kind=kind: _case(tools, today, wa, kind))
            for case_id, kind in zip(RACE_IDS, KINDS)]
