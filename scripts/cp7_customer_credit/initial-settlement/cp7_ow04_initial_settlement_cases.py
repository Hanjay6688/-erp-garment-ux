"""Twelve unexecuted Native settlement cases; outside-only test proposal.

No connection, installation or fixture operation runs during registration. The
closed Native harness owns the cursor, transaction and serialization of periods.
Only the supplied UI quote/settle wire contract is called. Disposable account
masters are explicit fixtures, never imported balances or business documents.
"""
from collections import Counter
from datetime import datetime, time
from decimal import Decimal as D
from pathlib import Path
import copy
import hashlib
import json
import re
import uuid

import cp7_ow04_native_source_fixture as native

EXPECTED_SHA = 'acb42395ea5e679c0b059be56ecceadc6b0cd5d5de70686f4c089ad9b5e95888'
QUOTE = 'public.erp_cp7_get_sales_return_settlement_quote_v1(jsonb)'
SETTLE = 'public.erp_cp7_settle_sales_return_v1(jsonb,uuid,text)'
PAID = ('1000.00', '900.00')
PROFILES = ('OPEN', 'CLOSED', 'REOPENED')
MODES = ('CREDIT', 'REFUND')
NATIVE_IDS = tuple('OW04_INITIAL_' + paid.split('.')[0] + '_' + profile + '_' + mode
                   for paid in PAID for profile in PROFILES for mode in MODES)
TABLES = ('return_families', 'return_family_members', 'cohorts',
          'recognition_plans', 'plan_support_events', 'recognition_components',
          'component_parts', 'component_journals', 'consumption_events')
SHA = re.compile(r'^[0-9a-f]{64}$')
MONEY = re.compile(r'^(0|[1-9][0-9]*)\.[0-9]{2}$')


def expected():
    data = Path(__file__).with_name('EXPECTED.json').read_bytes()
    assert hashlib.sha256(data).hexdigest() == EXPECTED_SHA, 'OW04_INITIAL_EXPECTED_CHANGED'
    result = json.loads(data)
    assert tuple(c['id'] for c in result['cases']) == NATIVE_IDS
    return result


def _closed(value, keys):
    assert isinstance(value, dict) and set(value) == set(keys), ('OW04_INITIAL_WIRE_FIELDS', keys)
    return value


def _sha(value):
    assert isinstance(value, str) and SHA.fullmatch(value), 'OW04_INITIAL_FULL_SHA_REQUIRED'


def _uuid(value):
    assert isinstance(value, str) and str(uuid.UUID(value)) == value, 'OW04_INITIAL_UUID_REQUIRED'


def _require_installed(cur):
    native.b.api.admin(cur)
    for signature in (QUOTE, SETTLE):
        if not cur.execute('select to_regprocedure(%s) is not null', (signature,)).fetchone()[0]:
            raise RuntimeError('OW04_INITIAL_REQUIRED_API_NOT_INSTALLED: ' + signature)
    for table in TABLES:
        if not cur.execute('select to_regclass(%s) is not null', ('cp7_credit.' + table,)).fetchone()[0]:
            raise RuntimeError('OW04_INITIAL_REQUIRED_LEDGER_NOT_INSTALLED: cp7_credit.' + table)


def _credit_master(cur):
    """ADMINISTRATIVE_DISPOSABLE_MASTER_FIXTURE: no funding is fabricated."""
    native.b.api.admin(cur)
    code = 'OW04C-' + uuid.uuid4().hex[:18]
    ident = str(cur.execute(
        'insert into erp.chart_accounts(account_code,account_name,account_type,report_group,'
        'normal_balance,is_postable,is_active) '
        "values(%s,'OW04 explicitly selected customer credit','LIABILITY','CURRENT_LIABILITIES','CREDIT',true,true) returning id",
        (code,)).fetchone()[0])
    # This is a master fixture, with no opening/import or unexplained balance.
    ok = cur.execute(
        "select a.account_type='LIABILITY' and a.normal_balance='CREDIT' and a.is_active and a.is_postable "
        'and not exists(select 1 from erp.journal_lines l where l.account_id=a.id) '
        'and not exists(select 1 from erp.cash_accounts c where c.coa_account_id=a.id) '
        'and not exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id) '
        'and not exists(select 1 from erp.initial_import_prepayments p where p.coa_account_id=a.id) '
        'and not exists(select 1 from erp.bb_customer_credits_v1 b where b.coa_account_id=a.id) '
        'from erp.chart_accounts a where a.id=%s', (ident,)).fetchone()
    assert ok == (True,), 'OW04_INITIAL_MASTER_NOT_EMPTY_OR_ELIGIBLE_SHAPE'
    return dict(id=ident, code=code, classification='ADMINISTRATIVE_DISPOSABLE_MASTER_FIXTURE',
                before=native._array(cur, 'erp.chart_accounts', 'id=%s', (ident,)))


def _ledger_snapshot(cur):
    native.b.api.admin(cur)
    # Fixed tables only; this is disposable test evidence, not a product reader.
    return {table: native._array(cur, 'cp7_credit.' + table, 'true', ()) for table in TABLES}


def _input(x, gold, credit):
    p = copy.deepcopy(x['return_payload'])
    # Normalize only user-entered draft values to the existing UI cent format.
    for line in p['items']:
        line['refund_amount'] = format(D(line['refund_amount']), '.2f')
    draft_keys = ('return_number', 'physical_at', 'notes', 'items', 'change_reason')
    draft = {key: p[key] for key in draft_keys}
    physical = None
    if gold['mode'] == 'REFUND':
        # Independent explicit physical cash INPUT, not a journal-date override.
        physical = datetime.combine(datetime.fromisoformat(x['dates']['D2']).date(),
                                    time(13, 0, 0, 654321), native.ERP_ZONE).isoformat()
    choice = dict(mode=gold['mode'], credit_account_id=credit['id'],
                  cash_account_id=x['f']['bank'] if gold['mode'] == 'REFUND' else None,
                  refund_physical_at=physical,
                  reference='OW04 explicit full refund' if gold['mode'] == 'REFUND' else None)
    return dict(sale_id=p['sale_id'], expected_version=x['return_version'],
                review_token=p['review_token'], return_payload=draft, settlement=choice)


def _assert_account(value, ident):
    _closed(value, ('id', 'code', 'name', 'facts_sha256'))
    assert value['id'] == ident and value['code'] and value['name']
    _sha(value['facts_sha256'])


def _assert_quote(cur, q, query, x, gold, credit):
    _closed(q, ('contract_version', 'kind', 'read_only', 'business_DML', 'captured_at',
                'input_echo', 'source', 'binding', 'has_recognition_effect', 'current_credit_amount',
                'components', 'return_projection', 'totals', 'credit_account', 'cash_account',
                'refund_projection', 'capabilities', 'readiness'))
    assert (q['contract_version'], q['kind'], q['read_only'], q['business_DML']) == (
        'cp7.sales-return-settlement-quote.v1', 'QUOTE', True, False), q
    datetime.fromisoformat(q['captured_at'].replace('Z', '+00:00'))
    assert q['input_echo'] == query, 'OW04_INITIAL_QUOTE_INPUT_ECHO_CHANGED'
    s = _closed(q['source'], ('sale_id', 'sale_number', 'customer_id', 'customer_name', 'row_version', 'review_token'))
    assert (s['sale_id'], s['customer_id'], s['row_version'], s['review_token']) == (
        x['f']['sale'], x['f']['customer'], query['expected_version'], query['review_token'])
    assert s['sale_number'] and s['customer_name']
    binding = _closed(q['binding'], ('immutable_source_sha256', 'current_state_sha256', 'draft_sha256',
        'choice_sha256', 'projection_sha256', 'authority_sha256', 'period_sha256', 'dependency_sha256', 'quote_sha256'))
    for value in binding.values():
        _sha(value)
    assert q['readiness'] == dict(state='READY', issues=[]), q['readiness']
    caps = _closed(q['capabilities'], ('record_return', 'recognize_credit', 'refund_cash'))
    assert all(isinstance(value, bool) for value in caps.values())
    assert caps['record_return'] is True and caps['recognize_credit'] is True
    assert q['has_recognition_effect'] is True and q['current_credit_amount'] == gold['current_credit_amount']
    assert q['totals'] == dict(before=gold['before'], after=gold['after']), q['totals']
    assert len(q['components']) == 1
    c = _closed(q['components'][0], ('component_key', 'economic_date', 'book_date', 'signed_amount', 'support_sha256'))
    _sha(c['component_key']); _sha(c['support_sha256'])
    assert (c['economic_date'], c['book_date'], c['signed_amount']) == (
        x['dates']['D2'], x['dates'][gold['return_pair'][1]], gold['current_credit_amount']), c
    p = _closed(q['return_projection'], ('economic_date', 'prior_causal', 'journal_effect', 'planned_book_date',
        'return_amount', 'hpp_amount', 'receivable_account_id'))
    assert (p['economic_date'], p['planned_book_date'], p['journal_effect'], p['return_amount'], p['hpp_amount']) == (
        x['dates']['D2'], x['dates'][gold['return_pair'][1]], 'JOURNAL_EXPECTED', '200.00', '10.00'), p
    assert p['receivable_account_id'] == native.cmd.mapping(cur, 'AR_CUSTOMER')
    prior = _closed(p['prior_causal'], ('contract_version', 'scope', 'state', 'causal_book_floor', 'proof_sha256'))
    assert (prior['contract_version'], prior['scope'], prior['state'], prior['causal_book_floor']) == (
        'ow04.prior-causal-book-proof.v1', 'PRIOR_CAUSAL_SALE_RETURN', 'DATED', x['dates'][gold['prior_causal_book_floor']])
    _sha(prior['proof_sha256'])
    _assert_account(q['credit_account'], credit['id'])
    assert q['credit_account']['code'] == credit['code']
    if gold['mode'] == 'CREDIT':
        assert q['cash_account'] is None and q['refund_projection'] is None
    else:
        _assert_account(q['cash_account'], x['f']['bank'])
        cash_code = cur.execute('select cash_account_code from erp.cash_accounts where id=%s', (x['f']['bank'],)).fetchone()[0]
        assert q['cash_account']['code'] == cash_code
        assert q['capabilities']['refund_cash'] is True
        r = _closed(q['refund_projection'], ('amount', 'physical_at', 'economic_date', 'book_date', 'safe_capacity', 'capacity_sha256'))
        assert (r['amount'], r['physical_at'], r['economic_date'], r['book_date']) == (
            gold['refund_amount'], query['settlement']['refund_physical_at'], x['dates']['D2'], x['dates'][gold['refund_pair'][1]]), r
        assert MONEY.fullmatch(r['safe_capacity']) and D(r['safe_capacity']) >= D(gold['refund_amount'])
        _sha(r['capacity_sha256'])


def _envelope(query, quote):
    c = query['settlement']
    choice = dict(mode=c['mode'], credit_account_id=c['credit_account_id'])
    if c['mode'] == 'REFUND':
        choice.update(cash_account_id=c['cash_account_id'], refund_physical_at=c['refund_physical_at'], reference=c['reference'])
    document = dict(copy.deepcopy(query['return_payload']), sale_id=query['sale_id'],
                    review_token=query['review_token'], settlement=choice, quote_sha256=quote['binding']['quote_sha256'])
    # Exact existing SALES recovery shape; plan facts never enter the payload.
    return dict(document=document, expected_version=query['expected_version'])


def _settle(cur, envelope, request):
    native.auth.actor(cur)
    result = cur.execute('select public.erp_cp7_settle_sales_return_v1(%s::jsonb,%s::uuid,%s::text)',
        (json.dumps(envelope['document']), request, envelope['expected_version'])).fetchone()[0]
    native.b.api.admin(cur)
    return result


def _assert_outcome(result, request, envelope, quote, mode):
    _closed(result, ('contract_version', 'kind', 'action', 'request_id', 'sale_id', 'return_id', 'return_status',
        'row_version', 'family_ordinal', 'credit_id', 'refund_event_id', 'quote_sha256', 'projection_sha256',
        'actual_manifest_sha256', 'projection_actual_proof_sha256', 'production_go'))
    assert (result['contract_version'], result['kind'], result['action'], result['request_id'], result['sale_id'],
        result['return_status'], result['family_ordinal'], result['production_go']) == (
        'cp7.sales-return-settlement-outcome.v1', 'COMMITTED_OUTCOME', 'RETURN_SETTLEMENT', str(request),
        envelope['document']['sale_id'], 'POSTED', '1', False), result
    for key in ('request_id', 'return_id', 'credit_id'):
        _uuid(result[key])
    assert re.fullmatch(r'[1-9][0-9]{0,18}', result['row_version'])
    for key in ('quote_sha256', 'projection_sha256', 'actual_manifest_sha256', 'projection_actual_proof_sha256'):
        _sha(result[key])
    assert result['quote_sha256'] == envelope['document']['quote_sha256']
    assert result['projection_sha256'] == quote['binding']['projection_sha256']
    if mode == 'REFUND':
        _uuid(result['refund_event_id'])
    else:
        assert result['refund_event_id'] is None


def _journal_matches(cur, ident, source_type, source_id, pair, amounts, customer):
    raw = native.journal(cur, ident); document = raw['document']; h = document['header']
    assert h is not None and (h['source_type'], h['source_id'], h['status'], h['economic_date'], h['transaction_date'], h['reversal_of_id']) == (
        source_type, source_id, 'POSTED', pair[0], pair[1], None), h
    actual = Counter((line['account_id'], D(str(line['debit'])), D(str(line['credit'])), line['customer_id']) for line in document['lines'])
    wanted = Counter((account, max(amount, D(0)), max(-amount, D(0)), customer) for account, amount in amounts)
    assert actual == wanted, ('OW04_INITIAL_ACTUAL_JOURNAL_LINES_CHANGED', ident, actual, wanted)
    return raw


def _assert_actual(cur, x, gold, credit, result, request, original_rows):
    native.b.api.admin(cur); f = x['f']; k = D(gold['current_credit_amount'])
    native.assert_first_settlement_gl(cur, x, gold['mode'], credit['id'])
    source = native.source_manifest(cur, x)
    for ident, raw in x['source_before']['journals'].items():
        assert native.journal(cur, ident) == raw, ('OW04_INITIAL_ORIGINAL_JOURNAL_REWRITTEN', ident)
    for key in ('items', 'allocations', 'product', 'found_receipt'):
        assert source[key] == x['source_before'][key], ('OW04_INITIAL_ORIGINAL_SOURCE_REWRITTEN', key)
    # Native post_fg_movement legitimately changes only these lot cache fields.
    assert native._raw(cur, "select to_jsonb(t)-array['cached_qty_pcs','is_open'] from erp.fg_lots t where id=%s",
                       (f['lot'],)) == x['lot_identity_before'], 'OW04_INITIAL_ORIGINAL_LOT_IDENTITY_REWRITTEN'
    assert cur.execute('select cached_qty_pcs,is_open from erp.fg_lots where id=%s', (f['lot'],)).fetchone() == (6, True)
    for ident, raw in original_rows.items():
        assert native._array(cur, 'erp.fg_stock_movements', 'id=%s', (ident,)) == raw
    assert cur.execute('select sum(qty_signed),sum(qty_signed*unit_hpp_snapshot) from erp.fg_stock_movements where lot_id=%s',
                       (f['lot'],)).fetchone() == (6, D('60.00')), 'OW04_INITIAL_FG_VALUE_CHANGED'
    assert cur.execute('select count(*) from erp.sales_returns where sale_id=%s', (f['sale'],)).fetchone()[0] == 1
    assert cur.execute("select status='POSTED' and physical_at=%s::timestamptz from erp.sales_returns where id=%s",
                       (x['physical']['returned'], result['return_id'])).fetchone() == (True,)
    returned_items = native._array(cur, 'erp.sales_return_items', 'return_id=%s', (result['return_id'],))
    ri = returned_items['document']; assert len(ri) == 1
    movements = native._array(cur, 'erp.fg_stock_movements', "source_type='SALES_RETURN_ITEM' and source_id=%s", (ri[0]['id'],))
    assert len(movements['document']) == 1
    m = movements['document'][0]
    assert (m['movement_type'], m['product_id'], m['lot_id'], m['location_id'], m['quality_grade'], D(str(m['qty_signed'])),
        D(str(m['unit_hpp_snapshot'])), m['customer_id'], m['reversal_of_id']) == (
        'SALE_RETURN', f['product'], f['lot'], f['destination'], 'GRADE_A', 1, D('10.00'), f['customer'], None)
    assert cur.execute('select physical_at=%s::timestamptz from erp.fg_stock_movements where id=%s',
                       (x['physical']['returned'], m['id'])).fetchone() == (True,)
    assert {row['id'] for row in source['stock']['document']} == set(original_rows) | {m['id']}, 'OW04_INITIAL_UNEXPLAINED_FG_MOVEMENT'
    assert native.source.read(cur, f)['detail']['row_version'] == result['row_version']
    family_rows = native._array(cur, 'cp7_credit.return_families', 'family_root_sale_id=%s', (f['sale'],))
    assert len(family_rows['document']) == 1
    family = family_rows['document'][0]
    assert (family['first_return_id'], str(family['family_ordinal']), family['assignment_kind'], family['request_id']) == (
        result['return_id'], result['family_ordinal'], 'NEW_POST', str(request))
    members = native._array(cur, 'cp7_credit.return_family_members', 'family_id=%s', (family['id'],))
    assert len(members['document']) == 1
    member = members['document'][0]
    assert (member['return_id'], member['member_kind'], member['request_id']) == (result['return_id'], 'ORIGINAL', str(request))
    cohorts = native._array(cur, 'cp7_credit.cohorts', 'family_id=%s', (family['id'],))
    assert len(cohorts['document']) == 1
    h = cohorts['document'][0]
    assert (h['id'], h['source_sale_id'], h['source_return_id'], h['customer_id'], h['credit_account_id'], h['initial_mode'],
        D(str(h['initial_net_amount'])), h['request_id']) == (
        result['credit_id'], f['sale'], result['return_id'], f['customer'], credit['id'], gold['mode'], k, str(request))
    ar = native.cmd.mapping(cur, 'AR_CUSTOMER'); pair = tuple(x['dates'][day] for day in gold['return_pair'])
    assert h['ar_account_id'] == ar
    assert member['source_journal_id'] == h['source_return_journal_id']
    native_return = _journal_matches(cur, h['source_return_journal_id'], 'SALES_RETURN', result['return_id'], pair,
        ((native.cmd.mapping(cur, 'SALES_REVENUE'), D('200.00')), (ar, D('-200.00')),
         (native.cmd.mapping(cur, 'FG_INVENTORY'), D('10.00')), (native.cmd.mapping(cur, 'COGS'), D('-10.00'))), f['customer'])
    plans = native._array(cur, 'cp7_credit.recognition_plans', 'cohort_id=%s', (h['id'],))
    assert len(plans['document']) == 1
    p = plans['document'][0]
    assert (p['id'], p['plan_kind'], D(str(p['net_amount'])), p['has_recognition_effect'],
        p['expected_component_count'], p['expected_part_count'], p['request_id']) == (
        h['initial_plan_id'], 'INITIAL', k, True, 1, 1, str(request))
    support = native._array(cur, 'cp7_credit.plan_support_events', 'plan_id=%s', (p['id'],))
    # Source UUIDs and signed amounts come from actual stored journals, never
    # from projected semantic keys or the new recognition/refund journal.
    wanted_support = Counter((e['id'], 'BEFORE', e['kind'], D(e['amount']), e['economic_date'], e['transaction_date'])
                             for e in x['source_events_before'])
    wanted_support[(h['source_return_journal_id'], 'ADDED', 'NET', D('-200.00'), *pair)] += 1
    actual_support = Counter((e['journal_id'], e['phase'], e['kind'], D(str(e['amount'])), e['economic_date'], e['transaction_date'])
                             for e in support['document'])
    assert actual_support == wanted_support, 'OW04_INITIAL_SUPPORT_NOT_EXACT_NATIVE_SALE_PAYMENT_RETURN'
    components = native._array(cur, 'cp7_credit.recognition_components', 'plan_id=%s', (p['id'],))
    assert len(components['document']) == 1
    component = components['document'][0]
    assert (component['economic_date'], component['transaction_date'], D(str(component['amount']))) == (*pair, k)
    parts = native._array(cur, 'cp7_credit.component_parts', 'component_id=%s', (component['id'],))
    assert len(parts['document']) == 1 and D(str(parts['document'][0]['amount'])) == k
    part = parts['document'][0]
    links = native._array(cur, 'cp7_credit.component_journals', 'part_id=%s', (part['id'],))
    assert len(links['document']) == 1
    recognition = _journal_matches(cur, links['document'][0]['journal_id'], 'CP7_CUSTOMER_CREDIT_RECOGNITION', part['id'], pair,
        ((ar, k), (credit['id'], -k)), f['customer'])
    events = native._array(cur, 'cp7_credit.consumption_events', 'cohort_id=%s', (h['id'],))
    assert len(events['document']) == gold['refund_event_count']
    refund = None
    if gold['mode'] == 'REFUND':
        e = events['document'][0]
        assert (e['id'], e['event_kind'], D(str(e['amount'])), e['economic_date'], e['transaction_date'],
            e['target_sale_id'], e['cash_account_id'], e['restores_event_id'], e['request_id']) == (
            result['refund_event_id'], 'REFUND', k, *tuple(x['dates'][day] for day in gold['refund_pair']),
            None, f['bank'], None, str(request))
        refund = _journal_matches(cur, e['journal_id'], 'CP7_CUSTOMER_CREDIT_REFUND', e['id'],
            tuple(x['dates'][day] for day in gold['refund_pair']), ((credit['id'], k), (native.payments.bank_account(cur, f), -k)), f['customer'])
    expected_journals = {native_return['document']['header']['id'], recognition['document']['header']['id']}
    if refund is not None:
        expected_journals.add(refund['document']['header']['id'])
    current_journals = {str(row[0]) for row in cur.execute('select id from erp.journal_entries').fetchall()}
    assert current_journals - x['journal_ids_before'] == expected_journals, 'OW04_INITIAL_UNEXPLAINED_ADDITIONAL_JOURNAL'
    assert cur.execute("select count(*) from cp7_credit.consumption_events where event_kind='APPLY' and target_sale_id=%s", (f['sale'],)).fetchone()[0] == 0
    # P and I come from their distinct actual sources. Consumption never reduces I.
    assert cur.execute("select sum(amount) from erp.sales_payments where sale_id=%s and status='POSTED'", (f['sale'],)).fetchone()[0] == D(gold['paid'])
    actual_i = cur.execute('select sum(l.debit-l.credit) from cp7_credit.component_journals cj '
        'join cp7_credit.component_parts pp on pp.id=cj.part_id join cp7_credit.recognition_components cc on cc.id=pp.component_id '
        'join cp7_credit.recognition_plans rp on rp.id=cc.plan_id join erp.journal_lines l on l.journal_entry_id=cj.journal_id '
        'where rp.cohort_id=%s and l.account_id=%s and l.customer_id=%s', (h['id'], ar, f['customer'])).fetchone()[0]
    assert actual_i == k and D(gold['paid']) - actual_i == D('800.00')
    assert cur.execute('select coalesce(sum(ce.amount),0) from cp7_credit.consumption_events ce where ce.cohort_id=%s',
                       (h['id'],)).fetchone()[0] == D(gold['refund_amount'])
    return dict(source=source, family=family_rows, members=members, cohorts=cohorts, plans=plans, support=support, components=components,
                parts=parts, part_journals=links, consumptions=events, native_return_journal=native_return,
                recognition_journal=recognition, refund_journal=refund, return_items=returned_items, return_movement=movements)


def _run(cur, today, gold):
    _require_installed(cur)
    with native.isolated(cur):
        x = native.prepared(cur, today, gold['paid'], gold['profile'])
        credit = _credit_master(cur)
        query = _input(x, gold, credit)
        x['lot_identity_before'] = native._raw(cur,
            "select to_jsonb(t)-array['cached_qty_pcs','is_open'] from erp.fg_lots t where id=%s", (x['f']['lot'],))
        x['journal_ids_before'] = {str(row[0]) for row in cur.execute('select id from erp.journal_entries').fetchall()}
        original_rows = {r['id']: native._array(cur, 'erp.fg_stock_movements', 'id=%s', (r['id'],))
                         for r in x['source_before']['stock']['document']}
        before = dict(boundary=native.b.boundary.snapshot(cur), source=native.source_manifest(cur, x), ledger=_ledger_snapshot(cur))
        quote = native.call_quote(cur, query)
        assert before == dict(boundary=native.b.boundary.snapshot(cur), source=native.source_manifest(cur, x), ledger=_ledger_snapshot(cur)), 'OW04_INITIAL_QUOTE_WROTE_BUSINESS_FACTS'
        _assert_quote(cur, quote, query, x, gold, credit)
        envelope = _envelope(query, quote)
        frozen_envelope = copy.deepcopy(envelope)
        request = uuid.uuid4()
        result = _settle(cur, envelope, request)
        _assert_outcome(result, request, envelope, quote, gold['mode'])
        actual = _assert_actual(cur, x, gold, credit, result, request, original_rows)
        complete = dict(boundary=native.b.boundary.snapshot(cur), source=native.source_manifest(cur, x), ledger=_ledger_snapshot(cur))
        replay = _settle(cur, envelope, request)
        assert replay == result and envelope == frozen_envelope, 'OW04_INITIAL_REPLAY_CHANGED_OUTCOME_OR_ENVELOPE'
        assert complete == dict(boundary=native.b.boundary.snapshot(cur), source=native.source_manifest(cur, x), ledger=_ledger_snapshot(cur)), 'OW04_INITIAL_REPLAY_CREATED_ANOTHER_EFFECT'
        native.assert_payment_unchanged(cur, x)
        # Stored actual book D3 must survive REOPENED's ordinary resolver D2.
        assert x['current_return_resolver'] == x['dates'][gold['ordinary_return_resolver']]
        # The fixture rolls back its inner savepoint on exit. Force every
        # pending FK and factual closure trigger now, so rollback cannot hide
        # a transaction that would fail at COMMIT. Existing oracles stay intact.
        cur.execute('set constraints all immediate')
        return dict(status='PASS', classification='ACTUAL_NATIVE_INITIAL_SETTLEMENT_CASE_WHEN_RUN',
            source_fixture_id=x['fixture_id'], mode=gold['mode'], period_fixture=x['period_setup'],
            credit_master_fixture=credit, source_before=x['source_before'], payment_before=x['payment_before'],
            expected_id=gold['id'], request_envelope=dict(domain='SALES', action='RETURN_SETTLEMENT',
                id=str(request), payload=envelope, expectedVersion=None),
            actual_quote=quote, actual_outcome=result, actual_facts=actual,
            replay_same_outcome=True, replay_additional_effects=0, original_payment_byte_equal=True,
            original_sale_and_payment_journals_byte_equal=True,
            deferred_constraints_forced_before_fixture_rollback=True,
            native_executed=True, production_go=False)


def cases(cur, today):
    """Pure registration of 12 savepoint cases; no DB call until invocation."""
    rows = expected()['cases']
    return [(gold['id'], lambda gold=gold: _run(cur, today, gold)) for gold in rows]
