"""Expected-first Native fractional-HPP qualification proposal.

Pure registration only: this module never connects, installs, commits or runs a
case on import. The existing closed cp7_ow04_probe owns the disposable database,
candidate verification, transaction, per-case savepoint and restoration gate.

All economic facts use existing Native/CP7 writers. Only fresh masters, the
opening DRAFT inputs and the labelled disposable period are administrative.
The genuine Native opening-HPP correction accepts an unconstrained numeric
argument: its 24-digit one-third input writes total1.000000/basis3 and records
the real correction. Its stored unit is six decimals; this explicit fixture
asserts both quantities instead of pretending the stored unit is exact1/3.

Existing cost10 source/expected modules are imported unchanged, never patched.
"""
from collections import Counter
from datetime import datetime, time, timedelta
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
import copy
import json
import re
import uuid

import cp6_bb_probe as bb
import cp6_bd_probe as bd
import cp7_fg_adjustment_cases as adjustment
import cp7_sales_draft_cases as drafts
import cp7_ow04_initial_settlement_cases as initial
import cp7_ow04_native_source_fixture as nf

b, source, cmd, auth = nf.b, nf.source, nf.cmd, nf.auth
EXPECTED_SHA = 'f53001d8ec87289a7fc7ca1a6f69752f994480418256923133329e6395a37d4c'
IDS = (
    'OW04_HPP_NONPO_SECOND_RETURN_CARRY',
    'OW04_HPP_PO_SECOND_RETURN_CARRY',
    'OW04_HPP_NONPO_OTHER_POSITIVE',
    'OW04_HPP_NONPO_OTHER_NEGATIVE',
    'OW04_HPP_PO_OTHER_POSITIVE',
    'OW04_HPP_PO_OTHER_NEGATIVE',
    'OW04_HPP_TWO_LOTS_ONE_PO',
    'OW04_HPP_TWO_LOTS_SAME_NONPO_PRODUCT',
    'OW04_HPP_NONPO_FG_ZERO_HPP_JOURNAL',
    'OW04_HPP_PO_FG_ZERO_REOPENED_HPP_JOURNAL',
    'OW04_HPP_POSITIVE_SNAPSHOT_ZERO_VECTOR_REFUSED',
    'OW04_HPP_NATIVE_RECOST_STALE_QUOTE_REFUSED',
    'OW04_HPP_TWO_ALLOCATIONS_SAME_LOT_GROUPED',
    'OW04_HPP_DEBITS_PER_GROUP_BEFORE_NETTING',
)
VECTOR_KEYS = ('hpp_total_cost', 'fg_value', 'cogs_value', 'other_out_value')
PRIVATE_SCHEMAS = ('cp7_credit', 'cp7_sales', 'ow04_ordinal_wrapper',
                   'ow04_source_proposal', 'ow04_pure_kernel')
SCOPES = ('initial_return_work', 'source_mutation_scope', 'execution_context',
          'return_native_scope', 'return_command_scope', 'posting_scope',
          'initial_refund_posting_scope', 'opening_return_hpp_work_v1')
HPP_KEYS = ('FG_INVENTORY', 'COGS', 'OTHER_EXPENSE', 'OTHER_INCOME')


def expected():
    raw = Path(__file__).with_name('EXPECTED.json').read_bytes()
    assert sha256(raw).hexdigest() == EXPECTED_SHA, 'OW04_HPP_FROZEN_EXPECTED_CHANGED'
    value = json.loads(raw)
    assert value['expected_case_count'] == len(IDS) == 14
    assert tuple(row['id'] for row in value['cases']) == IDS
    assert tuple(value['vector_order']) == VECTOR_KEYS
    return value


def _decimal_text(value):
    """Only diagnostic presentation; no float enters a financial assertion."""
    return format(D(value), 'f')


def _clock(f, day, hour, microsecond=123456):
    return datetime.combine(f['dates'][day], time(hour, 0, 0, microsecond), nf.ERP_ZONE)


def _unit_for(total):
    values = expected()['fixture_policy']
    return {
        D('1.000000'): values['native_opening_correction_unit_for_total_1'],
        D('0.010000'): values['native_opening_correction_unit_for_total_0_01'],
        D('2.000000'): values['native_opening_correction_unit_for_total_2'],
    }[D(total)]


def _snapshot_unit(total):
    values = expected()['fixture_policy']
    return {
        D('1.000000'): values['unit_snapshot_for_total_1'],
        D('0.010000'): values['unit_snapshot_for_total_0_01'],
        D('2.000000'): values['unit_snapshot_for_total_2'],
    }[D(total)]


def _require_installed(cur):
    initial._require_installed(cur)
    signatures = (
        'erp.post_opening_balance(uuid)',
        'erp.post_opening_hpp_correction(uuid,numeric,text,date)',
        'erp.complete_initial_import_wip_v1(jsonb)',
        'erp.compute_po_hpp_gl_targets_v2620d(uuid)',
        'erp.compute_po_hpp_gl_book_v2620e(uuid)',
        'erp.compute_non_po_product_hpp_targets_v2620f(uuid)',
        'erp.compute_non_po_product_hpp_book_v2620f(uuid)',
        'public.erp_cp7_save_fg_adjustment_v1(text,jsonb,uuid,text)',
        'cp7_credit.assert_initial_return_closed_v1(uuid)',
    )
    b.api.admin(cur)
    for signature in signatures:
        assert cur.execute('select to_regprocedure(%s) is not null',
                           (signature,)).fetchone()[0], ('OW04_HPP_REQUIRED_NATIVE_MISSING', signature)


def _hpp_rows(cur, lots):
    b.api.admin(cur)
    return cur.execute('select l.id::text,l.po_id::text,l.product_id::text,l.lot_origin,'
        'h.id::text,h.qty_basis_pcs,h.total_cost,h.hpp_per_pcs '
        'from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current '
        'where l.id=any(%s::uuid[])order by l.produced_at,l.id', (list(lots),)).fetchall()


def _assert_source_hpp(cur, group, total):
    rows = _hpp_rows(cur, group['lots'])
    assert len(rows) == len(group['lots'])
    for lot, po, product, origin, version, basis, raw_total, unit in rows:
        assert (po, product, origin, basis, raw_total, unit) == (
            group['po'], group['product'], 'PRODUCTION' if group['kind'] == 'PO' else 'OPENING',
            3, D(total), D(_snapshot_unit(total))), ('OW04_HPP_GENUINE_SOURCE_WRONG', rows)
        assert version and lot in group['lots']
    return rows


def _nonpo(cur, f, total, number):
    """Retained BE opening DRAFT -> real Native post/correction, no posted DML."""
    b.api.admin(cur)
    product, _ = source.fg.ax.owner_only_model_product(cur,
        effective_from=_clock(f, 'D-2', 0))
    opening = str(uuid.uuid4())
    cur.execute('insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by)'
        "values(%s,%s,%s,'DRAFT',%s)",
        (opening, 'OW04H-'+uuid.uuid4().hex[:18], f['dates']['D-1'], source.fg.base.OPERATOR_APP))
    items = []
    for _ in range(number):
        ident = str(cur.execute('insert into erp.opening_balance_items('
            'opening_id,balance_type,product_id,location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method)'
            "values(%s,'FINISHED_GOODS',%s,%s,3,0,'GRADE_A','MANUAL')returning id",
            (opening, product, f['location'])).fetchone()[0])
        items.append(ident)
    bd.internal(cur, 'post_opening_balance', opening)
    b.api.admin(cur)
    lots = [str(row[0]) for row in cur.execute('select m.lot_id from erp.fg_stock_movements m '
        "where m.source_type='OPENING_BALANCE_ITEM'and m.source_id=any(%s::uuid[])"
        "and m.movement_type='OPENING'order by m.physical_at,m.lot_id", (items,)).fetchall()]
    assert len(lots) == number
    corrections = []
    for lot in lots:
        corrections.append(str(bd.internal(cur, 'post_opening_hpp_correction', lot,
            D(_unit_for(total)), 'OW04 explicit one-third opening source value; retained Native correction',
            f['dates']['D-1'])))
    group = dict(kind='NONPO', product=str(product), po=None, lots=lots,
        source=dict(classification='ADMINISTRATIVE_DRAFT_THEN_GENUINE_NATIVE_OPENING_AND_CORRECTION',
                    opening=opening, opening_items=items, corrections=corrections,
                    exact_numeric_input=_unit_for(total)))
    _assert_source_hpp(cur, group, total)
    return group


def _po(cur, f, today, total, number):
    """Actual import WIP continuation owns source value and creates each lot."""
    rows = bb.production_rows(stage='SEWING')
    quantity = 3 * number
    amount = format(D(total) * number, '.2f')
    rows['OPEN_PO'][0]['target_qty_pcs'] = str(quantity)
    rows['OPENING_BALANCE_ITEM'][0].update(qty=str(quantity), amount=amount)
    rows['OPENING_BALANCE_ITEM'][0].pop('unit_cost')
    rows['OPENING_CONTROL'][0].update(qty=str(quantity), amount=amount)
    fx = bb.production_post(cur, today, rows, cutover_days=10)
    outputs = []
    for n in range(number):
        day = f['dates']['D-2'] if number == 2 and n == 0 else f['dates']['D-1']
        outputs.append(bb.complete(cur, fx, day, 3))
    b.api.admin(cur)
    product = str(cur.execute('select id from erp.products where sku=%s',
                              (fx['code']+'P',)).fetchone()[0])
    lots = [row['lot_id'] for row in outputs]
    group = dict(kind='PO', product=product, po=fx['po'], lots=lots,
        source=dict(classification='GENUINE_NATIVE_IMPORTED_WIP_CONTINUATION_NOT_FRESH_MANUFACTURE',
            batch=fx['batch'], cutoff=str(fx['cutover']), source_qty=quantity,
            source_amount=amount, accessory_cost_included=True, outputs=outputs))
    f['location'] = fx['fg']
    _assert_source_hpp(cur, group, total)
    return group


def _other_out(cur, f, group):
    one = dict(f, product=group['product'], lot=group['lots'][0])
    p = adjustment.payload(cur, one, '-1')
    p['physical_at'] = _clock(f, 'D-1', 9).isoformat()
    p['reason'] = 'OW04 actual prior counted one-piece loss'
    p['notes'] = 'Native prior OTHER outflow, no stock or HPP facts fabricated'
    draft = adjustment.command(cur, 'SAVE', p)
    posted = adjustment.action(cur, 'POST', draft)
    group['source']['other_out_adjustment'] = posted
    b.api.admin(cur)
    rows = cur.execute('select m.movement_type,m.source_type,m.qty_signed,m.reversal_of_id '
        'from erp.fg_stock_movements m join erp.fg_adjustment_items i on i.id=m.source_id '
        "where i.adjustment_id=%s and m.source_type='FG_ADJUSTMENT_ITEM'", (posted['adjustment_id'],)).fetchall()
    assert rows == [('ADJUSTMENT', 'FG_ADJUSTMENT_ITEM', -1, None)]


def _post_sale(cur, f, gold):
    if gold['profile'] == 'REOPENED':
        source.fg.ax.boundary.historical.prior.set_open_period(cur, f['dates']['D2'])
    hold = None
    if gold['lots'] == 2 and gold['kind'] in ('PO', 'NONPO'):
        hold = dict(f, tag=f['tag']+'-H')
        drafts.create(cur, hold, drafts.payload(hold, '2', '20.00'))
    payload = drafts.payload(f, gold['sale_qty'], '20.00')
    if gold['duplicate_sale_lines']:
        payload['items'][0]['qty_pcs'] = '1'
        payload['items'].append(copy.deepcopy(payload['items'][0]))
    elif gold['kind'] == 'TWO_NONPO_PRODUCTS':
        payload['items'][0]['qty_pcs'] = '2'
        payload['items'].append(dict(payload['items'][0],
            product_id=f['groups'][1]['product'], qty_pcs='1'))
    drafts.create(cur, f, payload)
    p, version = cmd.review(cur, f)
    cmd.command(cur, 'POST', p, version)
    if hold:
        p, version = cmd.review(cur, hold)
        cmd.command(cur, 'CANCEL', p, version)
        assert source.read(cur, hold)['detail']['status'] == 'CANCELLED'
        assert source.read(cur, hold)['detail']['reserved_qty'] == '0'
        f['holding_draft'] = hold['sale']
    f['allocations'] = nf.returns.read(cur, f)['page']['rows']
    assert len(f['allocations']) == gold['allocation_count']
    if gold['lots'] == 2 and gold['kind'] in ('PO', 'NONPO'):
        assert len({x['lot_id'] for x in f['allocations']}) == 2
        assert all(x['allocated_qty'] == '1' for x in f['allocations'])
    elif gold['kind'] == 'TWO_NONPO_PRODUCTS':
        assert len({x['lot_id'] for x in f['allocations']}) == 2
        assert {x['product_id']: x['allocated_qty'] for x in f['allocations']} == {
            f['groups'][0]['product']: '2', f['groups'][1]['product']: '1'}
    if gold['duplicate_sale_lines']:
        assert len({x['lot_id'] for x in f['allocations']}) == 1
        assert len({x['sale_item_id'] for x in f['allocations']}) == 2
    p, version = nf.payments.payment_payload(cur, f,
        format(D(gold['sale_qty'])*D('20.00'), '.2f'))
    p['payment_date'] = f['at']['payment'].isoformat()
    f['payment'] = cmd.command(cur, 'PAYMENT', p, version)['payment_id']
    if gold['profile'] == 'REOPENED':
        prior_filings = nf.period.filings(cur)
        workspace = nf.period.read(cur, f['dates']['D2'])
        nf.period.command(cur, 'REOPEN', nf.period.intent(workspace, 'REOPEN', str(f['dates']['D-2'])))
        assert nf.period.filings(cur) == prior_filings
        assert cur.execute('select erp.resolve_accounting_transaction_date(%s)',
                           (f['dates']['D2'],)).fetchone()[0] == f['dates']['D2']


def _return_legacy(cur, f, amount, *, prior=False):
    p, version = nf.returns.payload(cur, f, qty='1', refund='0.00', destination=f['location'])
    p['physical_at'] = (_clock(f, 'D1', 12) if prior else f['at']['returned']).isoformat()
    p['items'] = []
    selected = f['allocations'][:1] if prior else f['allocations']
    each = format(D(amount)/len(selected), '.2f')
    assert D(each) * len(selected) == D(amount)
    for allocation in selected:
        p['items'].append(dict(allocation_id=allocation['allocation_id'], location_id=f['location'],
            qty_pcs='1', quality_grade='GRADE_A', refund_amount=each,
            notes='Actual selected original allocation; no caller HPP'))
    return p, version


def _fixture(cur, today, gold):
    b.api.admin(cur)
    cur.execute("set local timezone='UTC'")
    dates, at = nf._calendar(cur)
    source.fg.ax.boundary.historical.prior.set_open_period(cur, dates['D-2'])
    f = dict(dates=dates, at=at, location=str(source.fg.base.LOCATION),
        tag='OW04H-'+uuid.uuid4().hex[:18], sale_at=at['sale'].isoformat())
    if gold['kind'] == 'PO':
        f['groups'] = [_po(cur, f, today, gold['lot_total'], gold['lots'])]
        # The import helper changes only this disposable period; restore the
        # declared posting input after all genuine WIP output has completed.
        source.fg.ax.boundary.historical.prior.set_open_period(cur, dates['D-2'])
    elif gold['kind'] == 'TWO_NONPO_PRODUCTS':
        f['groups'] = [_nonpo(cur, f, gold['lot_total'], 1), _nonpo(cur, f, gold['lot_total'], 1)]
    else:
        f['groups'] = [_nonpo(cur, f, gold['lot_total'], gold['lots'])]
    f['product'] = f['groups'][0]['product']
    f['lots'] = [lot for group in f['groups'] for lot in group['lots']]
    f['lot'] = f['lots'][0]
    f['sku'] = cur.execute('select sku from erp.products where id=%s', (f['product'],)).fetchone()[0]
    f['destination'] = f['location']
    f['customer'] = str(source.fg.base.create_customer(cur, f['tag']))
    f['bank'] = str(source.bc.bank_account(cur, f['tag']+'B'))
    if gold['adjustment_qty'] != '0':
        for group in f['groups']:
            _other_out(cur, f, group)
    _post_sale(cur, f, gold)
    if gold['prior_zero_value_return']:
        p, version = _return_legacy(cur, f, '0.00', prior=True)
        f['prior_return'] = cmd.command(cur, 'RETURN', p, version)['return_id']
        rows = nf._array(cur, 'cp7_credit.return_family_members', 'return_id=%s', (f['prior_return'],))
        assert len(rows['document']) == 1
    f['payment_before'] = nf.payment_snapshot(cur, f['payment'])
    for group in f['groups']:
        _assert_source_hpp(cur, group, gold['lot_total'])
    return f


def _target_book(cur, group):
    b.api.admin(cur)
    if group['kind'] == 'PO':
        target = nf._raw(cur, 'select to_jsonb(t) from erp.compute_po_hpp_gl_targets_v2620d(%s)t', (group['po'],))
        book_raw = nf._raw(cur, 'select to_jsonb(t) from erp.compute_po_hpp_gl_book_v2620e(%s)t', (group['po'],))
        # Native's PO book reader exposes ONLY FG/COGS/OTHER. Derive H from
        # those actual book balances; target and cache are not book authority.
        book = nf._raw(cur, "select to_jsonb(t)||jsonb_build_object('hpp_total_cost',"
            't.fg_value+t.cogs_value+t.other_out_value)'
            'from erp.compute_po_hpp_gl_book_v2620e(%s)t', (group['po'],))
        cache = nf._array(cur, 'erp.po_hpp_gl_state', 'po_id=%s', (group['po'],))
        assert len(cache['document']) == 1
        assert tuple(D(str(cache['document'][0][key])) for key in VECTOR_KEYS) == tuple(
            D(str(target['document'][key])) for key in VECTOR_KEYS)
    else:
        target = nf._raw(cur, 'select to_jsonb(t) from erp.compute_non_po_product_hpp_targets_v2620f(%s)t', (group['product'],))
        book = nf._raw(cur, 'select to_jsonb(t) from erp.compute_non_po_product_hpp_book_v2620f(%s)t', (group['product'],))
        book_raw = book
        cache = None
    tv = tuple(D(str(target['document'][key])) for key in VECTOR_KEYS)
    bv = tuple(D(str(book['document'][key])) for key in VECTOR_KEYS)
    assert tv == bv, ('OW04_HPP_NATIVE_TARGET_BOOK_DISAGREE', group, tv, bv)
    return dict(target=target, book_raw=book_raw, book=book, cache=cache, vector=[format(x, '.2f') for x in tv])


def _vectors(cur, f, wanted):
    states = [_target_book(cur, group) for group in f['groups']]
    assert [row['vector'] for row in states] == wanted, ('OW04_HPP_LITERAL_TARGET_WRONG', wanted, states)
    return states


def _owned(cur, f, wanted):
    b.api.admin(cur)
    # All held drafts are already CANCELLED. No active reservation can masquerade
    # as the requested physical state; current sum equals Native owned quantity.
    active = cur.execute('select count(*)from erp.fg_stock_movements m '
        "where m.lot_id=any(%s::uuid[])and m.movement_type='SALE_RESERVE'"
        'and not exists(select 1 from erp.fg_stock_movements r where r.reversal_of_id=m.id)',
        (f['lots'],)).fetchone()[0]
    assert active == 0
    quantities = []
    for lot in f['lots']:
        summed, cached = cur.execute('select coalesce(sum(m.qty_signed),0),l.cached_qty_pcs '
            'from erp.fg_lots l left join erp.fg_stock_movements m on m.lot_id=l.id '
            'where l.id=%s group by l.cached_qty_pcs', (lot,)).fetchone()
        assert summed == cached
        quantities.append(int(summed))
    assert quantities == wanted, ('OW04_HPP_OWNED_WRONG', quantities, wanted)
    return quantities


def _private(cur):
    b.api.admin(cur)
    names = cur.execute('select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace '
        "where n.nspname=any(%s::text[])and c.relkind in('r','p')order by n.nspname,c.relname",
        (list(PRIVATE_SCHEMAS),)).fetchall()
    result = {}
    for schema, table in names:
        assert re.fullmatch('[a-z_][a-z_0-9]*', schema) and re.fullmatch('[a-z_][a-z_0-9]*', table)
        identity = schema+'.'+table  # actual fixed-schema catalog names, never API input
        result[identity] = nf._array(cur, identity, 'true', ())
    return result


def _observe(cur, f):
    return dict(boundary=b.boundary.snapshot(cur), private=_private(cur),
        source_sale=nf._array(cur, 'erp.sales_headers', 'id=%s', (f['sale'],)),
        payments=nf.payment_snapshot(cur, f['payment']),
        hpp=nf._array(cur, 'erp.hpp_versions', 'lot_id=any(%s::uuid[])', (f['lots'],)),
        stock=nf._array(cur, 'erp.fg_stock_movements', 'lot_id=any(%s::uuid[])', (f['lots'],)))


def _preserved(cur, f):
    b.api.admin(cur)
    ids = [str(row[0]) for row in cur.execute('select id from erp.journal_entries').fetchall()]
    stock = nf._array(cur, 'erp.fg_stock_movements', 'lot_id=any(%s::uuid[])', (f['lots'],))
    return dict(journals={ident: nf.journal(cur, ident) for ident in ids},
        items=nf._array(cur, 'erp.sales_items', 'sale_id=%s', (f['sale'],)),
        allocations=nf._raw(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')"
            'from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s', (f['sale'],)),
        products=nf._array(cur, 'erp.products', 'id=any(%s::uuid[])', ([g['product'] for g in f['groups']],)),
        hpp=nf._array(cur, 'erp.hpp_versions', 'lot_id=any(%s::uuid[])', (f['lots'],)),
        lots={lot: nf._raw(cur, "select to_jsonb(l)-array['cached_qty_pcs','is_open']from erp.fg_lots l where id=%s", (lot,)) for lot in f['lots']},
        stock={row['id']: nf._array(cur, 'erp.fg_stock_movements', 'id=%s', (row['id'],)) for row in stock['document']},
        private=_private(cur), accounts=cmd.accounts(cur))


def _assert_preserved(cur, f, before):
    b.api.admin(cur)
    assert nf.payment_snapshot(cur, f['payment']) == f['payment_before'], 'OW04_HPP_ORIGINAL_PAYMENT_CHANGED'
    for ident, row in before['journals'].items():
        assert nf.journal(cur, ident) == row, ('OW04_HPP_ORIGINAL_JOURNAL_CHANGED', ident)
    assert nf._array(cur, 'erp.sales_items', 'sale_id=%s', (f['sale'],)) == before['items']
    assert nf._raw(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')"
        'from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s',
        (f['sale'],)) == before['allocations']
    assert nf._array(cur, 'erp.products', 'id=any(%s::uuid[])',
        ([g['product'] for g in f['groups']],)) == before['products']
    assert nf._array(cur, 'erp.hpp_versions', 'lot_id=any(%s::uuid[])', (f['lots'],)) == before['hpp']
    for lot, row in before['lots'].items():
        assert nf._raw(cur, "select to_jsonb(l)-array['cached_qty_pcs','is_open']from erp.fg_lots l where id=%s", (lot,)) == row
    for ident, row in before['stock'].items():
        assert nf._array(cur, 'erp.fg_stock_movements', 'id=%s', (ident,)) == row
    after_private = _private(cur)
    for table, raw in before['private'].items():
        # A new request/family can append rows. Every existing private fact must
        # remain byte-value-equivalent, including earlier real EMPTY families.
        after_rows = after_private[table]['document']
        assert all(row in after_rows for row in raw['document']), ('OW04_HPP_EXISTING_PRIVATE_FACT_CHANGED', table)


def _query(cur, f, gold, credit):
    payload, version = _return_legacy(cur, f, gold['return_amount'])
    choice = dict(mode=gold['mode'], credit_account_id=credit['id'] if gold['mode'] else None,
                  cash_account_id=None, refund_physical_at=None, reference=None)
    return dict(sale_id=f['sale'], expected_version=version, review_token=payload['review_token'],
        return_payload={key: value for key, value in payload.items() if key not in ('sale_id', 'review_token')},
        settlement=choice)


def _envelope(query, quote):
    if query['settlement']['mode']:
        return initial._envelope(query, quote)  # unchanged actual wire helper
    document = dict(copy.deepcopy(query['return_payload']), sale_id=query['sale_id'],
        review_token=query['review_token'], settlement=None, quote_sha256=quote['binding']['quote_sha256'])
    return dict(document=document, expected_version=query['expected_version'])


def _quote(cur, f, gold, query, *, old=False):
    before = _observe(cur, f)
    quote = nf.call_quote(cur, query)
    assert _observe(cur, f) == before, 'OW04_HPP_QUOTE_WROTE_BUSINESS_OR_PRIVATE_FACTS'
    assert (quote['contract_version'], quote['kind'], quote['read_only'], quote['business_DML']) == (
        'cp7.sales-return-settlement-quote.v1', 'QUOTE', True, False)
    assert quote['input_echo'] == query
    assert quote['readiness'] == dict(state='READY', issues=[])
    assert quote['source']['row_version'] == query['expected_version']
    assert quote['source']['review_token'] == query['review_token']
    for value in quote['binding'].values():
        initial._sha(value)
    pair = gold.get('return_pair', expected()['return_pair_default'])
    projection = quote['return_projection']
    assert (projection['economic_date'], projection['planned_book_date'], projection['journal_effect'],
            projection['return_amount'], projection['hpp_amount']) == (
        str(f['dates'][pair[0]]), str(f['dates'][pair[1]]), 'JOURNAL_EXPECTED', gold['return_amount'],
        gold['old_hpp_amount'] if old else gold['hpp_amount']), projection
    amount = D(gold['return_amount'])
    assert quote['current_credit_amount'] == (gold['return_amount'] if gold['mode'] else '0.00')
    assert quote['has_recognition_effect'] is bool(gold['mode'])
    gross = format(D(gold['sale_qty'])*20, '.2f')
    totals_before = dict(gross_total=gross, return_total='0.00', net_total=gross,
        payments_received=gross, credit_applied='0.00', credit_recognized='0.00',
        effective_paid=gross, receivable_remaining='0.00')
    totals_after = dict(totals_before, return_total=gold['return_amount'],
        net_total=format(D(gross)-amount, '.2f'),
        credit_recognized=gold['return_amount'] if gold['mode'] else '0.00',
        effective_paid=format(D(gross)-amount, '.2f'))
    assert quote['totals'] == dict(before=totals_before, after=totals_after)
    if gold['mode']:
        initial._assert_account(quote['credit_account'], query['settlement']['credit_account_id'])
        assert len(quote['components']) == 1
        component = quote['components'][0]
        assert (component['economic_date'], component['book_date'], component['signed_amount']) == (
            str(f['dates'][pair[0]]), str(f['dates'][pair[1]]), gold['return_amount'])
    else:
        assert quote['credit_account'] is None and quote['components'] == []
    assert quote['cash_account'] is None and quote['refund_projection'] is None
    return quote


def _wanted_journal(cur, f, gold):
    lines = []
    def add(key, amount, po=None, product=None):
        amount = D(amount)
        if amount:
            lines.append((cmd.mapping(cur, key), max(amount, D(0)), max(-amount, D(0)),
                          f['customer'], po, product, None, None))
    add('SALES_REVENUE', gold['return_amount'])
    add('AR_CUSTOMER', -D(gold['return_amount']))
    for group, vector in zip(f['groups'], gold['delta'], strict=True):
        po = group['po']
        product = group['product'] if po is None else None
        add('FG_INVENTORY', vector[0], po, product)
        add('COGS', vector[1], po, product)
        add('OTHER_EXPENSE' if D(vector[2]) > 0 else 'OTHER_INCOME', vector[2], po, product)
    return Counter(lines)


def _assert_actual(cur, f, gold, query, quote, envelope, request, result, before):
    b.api.admin(cur)
    initial._closed(result, ('contract_version', 'kind', 'action', 'request_id', 'sale_id', 'return_id',
        'return_status', 'row_version', 'family_ordinal', 'credit_id', 'refund_event_id', 'quote_sha256',
        'projection_sha256', 'actual_manifest_sha256', 'projection_actual_proof_sha256', 'production_go'))
    assert (result['contract_version'], result['kind'], result['action'], result['request_id'],
        result['sale_id'], result['return_status'], result['family_ordinal'], result['production_go']) == (
        'cp7.sales-return-settlement-outcome.v1', 'COMMITTED_OUTCOME', 'RETURN_SETTLEMENT', str(request),
        f['sale'], 'POSTED', gold['family_ordinal'], False)
    for key in ('request_id', 'return_id'):
        initial._uuid(result[key])
    for key in ('quote_sha256', 'projection_sha256', 'actual_manifest_sha256', 'projection_actual_proof_sha256'):
        initial._sha(result[key])
    assert result['quote_sha256'] == envelope['document']['quote_sha256'] == quote['binding']['quote_sha256']
    assert result['projection_sha256'] == quote['binding']['projection_sha256']
    assert result['refund_event_id'] is None
    if gold['mode']:
        initial._uuid(result['credit_id'])
    else:
        assert result['credit_id'] is None
    rows = cur.execute("select id::text from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s",
                       (result['return_id'],)).fetchall()
    assert len(rows) == 1, ('OW04_HPP_RETURN_JOURNAL_REQUIRED_EVEN_WITH_FG_ZERO', rows)
    journal_id = rows[0][0]
    raw = nf.journal(cur, journal_id)
    header = raw['document']['header']
    pair = gold.get('return_pair', expected()['return_pair_default'])
    assert (header['source_type'], header['source_id'], header['status'], header['economic_date'],
            header['transaction_date'], header['reversal_of_id']) == (
        'SALES_RETURN', result['return_id'], 'POSTED', str(f['dates'][pair[0]]), str(f['dates'][pair[1]]), None)
    lines = cur.execute('select account_id::text,debit,credit,customer_id::text,po_id::text,product_id::text,'
        'vendor_id::text,contractor_id::text from erp.journal_lines where journal_entry_id=%s', (journal_id,)).fetchall()
    assert Counter(lines) == _wanted_journal(cur, f, gold), ('OW04_HPP_NATIVE_SIGNED_LINES_WRONG', lines, gold)
    assert sum(row[1] for row in lines) == sum(row[2] for row in lines)
    # The scalar sums each group's debit side. OTHER +/- rows in separate
    # groups remain separate dimensions, so cross-group netting cannot hide it.
    scalar = sum((max(D(v), D(0)) for vector in gold['delta'] for v in vector), D(0))
    assert format(scalar, '.2f') == gold['hpp_amount'] == quote['return_projection']['hpp_amount']
    after_targets = _vectors(cur, f, gold['after'])
    _owned(cur, f, gold['owned_after'])
    _assert_preserved(cur, f, before)
    main = cur.execute('select status,physical_at=%s::timestamptz from erp.sales_returns where id=%s',
                       (query['return_payload']['physical_at'], result['return_id'])).fetchone()
    assert main == ('POSTED', True)
    items = nf._array(cur, 'erp.sales_return_items', 'return_id=%s', (result['return_id'],))
    selected = {row['allocation_id']: row for row in query['return_payload']['items']}
    allocation_lots = {row['allocation_id']: row['lot_id'] for row in f['allocations']}
    current_units = {row[0]: row[7] for row in _hpp_rows(cur, f['lots'])}
    assert len(items['document']) == len(selected)
    new_movements = []
    for item in items['document']:
        original = selected[item['sale_stock_allocation_id']]
        assert (item['lot_id'], item['location_id'], item['quality_grade'], item['qty_pcs'], D(str(item['refund_amount']))) == (
            allocation_lots[item['sale_stock_allocation_id']], f['location'], 'GRADE_A', 1, D(original['refund_amount']))
        assert D(str(item['unit_hpp_snapshot'])) == current_units[item['lot_id']]
        movement = nf._array(cur, 'erp.fg_stock_movements',
            "source_type='SALES_RETURN_ITEM'and source_id=%s", (item['id'],))
        assert len(movement['document']) == 1
        m = movement['document'][0]
        assert (m['movement_type'], m['lot_id'], m['qty_signed'], m['location_id'], m['quality_grade'],
                m['customer_id'], m['reversal_of_id']) == (
            'SALE_RETURN', item['lot_id'], 1, f['location'], 'GRADE_A', f['customer'], None)
        assert D(str(m['unit_hpp_snapshot'])) == current_units[item['lot_id']]
        assert cur.execute('select physical_at=%s::timestamptz from erp.fg_stock_movements where id=%s',
                           (query['return_payload']['physical_at'], m['id'])).fetchone() == (True,)
        new_movements.append(m['id'])
    stock_ids = {str(row[0]) for row in cur.execute('select id from erp.fg_stock_movements '
        'where lot_id=any(%s::uuid[])', (f['lots'],)).fetchall()}
    assert stock_ids == set(before['stock']) | set(new_movements)
    wanted_global = {}
    for account, debit, credit, *_ in _wanted_journal(cur, f, gold).elements():
        wanted_global[account] = wanted_global.get(account, D(0)) + debit - credit
    # Recognition offsets only the new Native AR credit; original funding is
    # immutable. Cash does not change for CREDIT or HPP-only EMPTY settlement.
    if gold['mode']:
        ar = cmd.mapping(cur, 'AR_CUSTOMER')
        wanted_global[ar] = wanted_global.get(ar, D(0)) + D(gold['return_amount'])
        liability = query['settlement']['credit_account_id']
        wanted_global[liability] = -D(gold['return_amount'])
    wanted_global = {key: value for key, value in wanted_global.items() if value}
    assert cmd.delta(before['accounts'], cmd.accounts(cur)) == wanted_global
    materialization = nf._array(cur, 'cp7_credit.initial_return_materializations', 'request_id=%s', (request,))
    assert len(materialization['document']) == 1
    mat = materialization['document'][0]
    assert (mat['source_return_id'], str(mat['family_ordinal']), mat['quote_sha256'], mat['projection_sha256'],
            mat['cohort_id'], mat['origin']) == (
        result['return_id'], gold['family_ordinal'], result['quote_sha256'], result['projection_sha256'],
        result['credit_id'], 'REVIEWED_SETTLEMENT')
    assert mat['projection']['hpp']['hpp_amount'] == gold['hpp_amount']
    assert mat['projection_actual_proof_sha256'] == result['projection_actual_proof_sha256']
    assert mat['actual_kernel']['net_current_k'] == (gold['return_amount'] if gold['mode'] else '0.00')
    cur.execute('select cp7_credit.assert_initial_return_closed_v1(%s)', (mat['operation_id'],))
    detail = source.read(cur, f)['detail']
    gross = D(gold['sale_qty']) * 20
    assert detail['status'] == 'PAID'
    assert {key: D(detail['financial'][key]) for key in (
        'gross_total', 'return_total', 'net_total', 'paid_total', 'open_balance')} == dict(
        gross_total=gross, return_total=D(gold['return_amount']),
        net_total=gross-D(gold['return_amount']), paid_total=gross-D(gold['return_amount']), open_balance=D(0))
    assert cur.execute("select sum(amount)from erp.sales_payments where sale_id=%s and status='POSTED'",
                       (f['sale'],)).fetchone()[0] == gross
    assert cur.execute("select count(*)from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=%s",
                       (f['sale'],)).fetchone()[0] == 0
    new_journals = {str(row[0]) for row in cur.execute('select id from erp.journal_entries').fetchall()} - set(before['journals'])
    if gold['mode']:
        recognition_ids = {str(row[0]) for row in cur.execute('select cj.journal_id from cp7_credit.component_journals cj '
            'join cp7_credit.component_parts p on p.id=cj.part_id join cp7_credit.recognition_components c on c.id=p.component_id '
            'join cp7_credit.recognition_plans rp on rp.id=c.plan_id where rp.cohort_id=%s', (result['credit_id'],)).fetchall()}
        assert len(recognition_ids) == 1
    else:
        recognition_ids = set()
    assert new_journals == {journal_id} | recognition_ids
    for table in SCOPES:
        assert cur.execute('select count(*)from cp7_credit.'+table).fetchone()[0] == 0, table
    assert cur.execute('select count(*)from cp7_sales.command_context').fetchone()[0] == 0
    return dict(native_return_journal=raw, materialization=materialization, after_targets=after_targets,
                return_items=items, movement_ids=new_movements, recognition_journal_ids=sorted(recognition_ids))


def _refuse_unchanged(cur, f, operation, code):
    before = _observe(cur, f)
    error = auth.refused(cur, operation, code)
    assert error == code, ('OW04_HPP_EXACT_REFUSAL_CHANGED', error, code)
    assert _observe(cur, f) == before, ('OW04_HPP_REFUSAL_LEFT_PARTIAL_EFFECT', code)
    return error


def _opening_failure_controls(cur, f, query, envelope):
    """Labelled disposable cache/trigger/work-scope fault injection only.

    No economic fixture or monetary expected is rewritten. Each injection is
    rolled back before the genuine Native settlement and before source verify.
    """
    controls = {}
    b.api.admin(cur)
    prior_return = cur.execute('select id from erp.sales_returns where sale_id=%s order by id limit 1',
                               (f['sale'],)).fetchone()[0]
    for old, new in ((None, 'POSTED'), ('DRAFT', None), ('POSTED', 'REVERSED'), ('DRAFT', 'DRAFT')):
        assert cur.execute('select cp7_credit.defer_opening_return_hpp_v1(%s,%s,%s)',
                           (prior_return, old, new)).fetchone() == (False,)
    assert cur.execute("select cp7_credit.defer_opening_return_hpp_v1(%s,'DRAFT','POSTED')",
                       (prior_return,)).fetchone() == (False,)
    controls['unowned_and_nonexact_transitions_do_not_defer'] = True
    with nf.isolated(cur):
        # Same money and same HPP version; changing only the activation cache
        # must still invalidate the complete reviewed source binding.
        cur.execute("update erp.opening_lot_hpp_gl_state set updated_at=updated_at-interval '1 microsecond'where lot_id=%s",
                    (f['lot'],))
        changed = nf.call_quote(cur, query)
        assert changed['binding']['quote_sha256'] != envelope['document']['quote_sha256']
        controls['cache_only_stale_quote_refusal'] = _refuse_unchanged(cur, f,
            lambda: initial._settle(cur, envelope, uuid.uuid4()), 'CP7_CREDIT_COMPLETE_QUOTE_CHANGED')
    with nf.isolated(cur):
        # Fail only the diagnostic write AFTER the actual Native journal.
        # The owning SQL statement must roll back stock, journal, family and
        # request together; no receipt from a partial transaction is accepted.
        cur.execute("create function pg_temp.ow04_refuse_opening_diagnostic()returns trigger language plpgsql as $$"
            "begin if not exists(select 1 from erp.journal_entries j join cp7_credit.opening_return_hpp_work_v1 w "
            "on j.source_id=w.return_id where j.source_type='SALES_RETURN'and w.backend_pid=pg_backend_pid()"
            "and w.transaction_id=txid_current())then raise exception 'OW04_TEST_DIAGNOSTIC_BEFORE_NATIVE_JOURNAL';end if;"
            "raise exception 'OW04_TEST_OPENING_DIAGNOSTIC_WRITE_REFUSED';end $$", prepare=False)
        cur.execute('create trigger ow04_test_opening_diagnostic_refusal before update on erp.opening_lot_hpp_gl_state '
            'for each row execute function pg_temp.ow04_refuse_opening_diagnostic()', prepare=False)
        controls['diagnostic_failure_atomic_rollback'] = _refuse_unchanged(cur, f,
            lambda: initial._settle(cur, envelope, uuid.uuid4()), 'OW04_TEST_OPENING_DIAGNOSTIC_WRITE_REFUSED')
    with nf.isolated(cur):
        def leak():
            cur.execute('insert into cp7_credit.opening_return_hpp_work_v1 values(%s,pg_backend_pid(),txid_current(),%s,%s::uuid[])',
                (prior_return, json.dumps(dict(kind='LABELLED_DISPOSABLE_LEAK_INJECTION')), [f['lot']]))
            cur.execute('update cp7_credit.opening_return_hpp_work_v1 set backend_pid=backend_pid+1 where return_id=%s',
                        (prior_return,))
            cur.execute('set constraints all immediate')
        controls['updated_work_witness_cannot_escape_deferred_closure'] = _refuse_unchanged(cur, f,
            leak, 'CP7_CREDIT_OPENING_HPP_DEFERRED_SCOPE_LEAK')
    return controls


def _run(cur, today, gold):
    _require_installed(cur)
    with nf.isolated(cur):
        f = _fixture(cur, today, gold)
        credit = initial._credit_master(cur)
        query = _query(cur, f, gold, credit)
        _owned(cur, f, gold['owned_before'])
        old_quote = None
        refusal = None
        request = uuid.uuid4()
        if 'recost_total' in gold:
            _vectors(cur, f, gold['before_old_quote'])
            old_quote = _quote(cur, f, gold, query, old=True)
            stale_envelope = _envelope(query, old_quote)
            prior = _hpp_rows(cur, f['lots'])
            recost = bd.internal(cur, 'post_opening_hpp_correction', f['lot'],
                D(_unit_for(gold['recost_total'])), 'OW04 genuine Native recost after the reviewed quote', f['dates']['D1'])
            _assert_source_hpp(cur, f['groups'][0], gold['recost_total'])
            current = _hpp_rows(cur, f['lots'])
            assert current[0][4] != prior[0][4]
            # The source mutation is lawful setup. Baseline the attempted
            # settlement AFTER it, so a correct refusal cannot hide recost loss.
            refusal = _refuse_unchanged(cur, f,
                lambda: initial._settle(cur, stale_envelope, request), gold['refusal'])
            f['source_recost'] = dict(correction_id=str(recost), before=prior, after=current)
        before_targets = _vectors(cur, f, gold['before'])
        if 'hpp_amount' not in gold:
            refusal_quote = _refuse_unchanged(cur, f, lambda: nf.call_quote(cur, query), gold['refusal'])
            # No approved quote can exist for the rejected source. This digest
            # is deliberately non-authoritative and is used ONLY to prove the
            # same projection refusal precedes mutations on the write route.
            denied_envelope = _envelope(query, dict(binding=dict(quote_sha256='0'*64)))
            refusal_settle = _refuse_unchanged(cur, f,
                lambda: initial._settle(cur, denied_envelope, request), gold['refusal'])
            cur.execute('set constraints all immediate')
            return dict(status='PASS', native_executed=True, production_go=False, expected_id=gold['id'],
                classification='ACTUAL_NATIVE_REFUSAL_ONLY_WHEN_RUN', source_groups=f['groups'],
                expected_sha256=EXPECTED_SHA, before_targets=before_targets,
                refused_quote=refusal_quote, refused_unapproved_write=refusal_settle,
                exact_snapshot_unchanged=True, deferred_constraints_forced=True)
        quote = _quote(cur, f, gold, query)
        if old_quote:
            assert quote['binding']['quote_sha256'] != old_quote['binding']['quote_sha256']
            assert quote['binding']['projection_sha256'] != old_quote['binding']['projection_sha256']
        envelope = _envelope(query, quote)
        opening_controls = _opening_failure_controls(cur, f, query, envelope) if gold['id'] == IDS[0] else None
        frozen = copy.deepcopy(envelope)
        before = _preserved(cur, f)
        result = initial._settle(cur, envelope, request)
        actual = _assert_actual(cur, f, gold, query, quote, envelope, request, result, before)
        committed = _observe(cur, f)
        assert initial._settle(cur, envelope, request) == result
        assert envelope == frozen
        assert _observe(cur, f) == committed, 'OW04_HPP_REPLAY_CREATED_SECOND_EFFECT'
        assert nf.payment_snapshot(cur, f['payment']) == f['payment_before']
        cur.execute('set constraints all immediate')
        return dict(status='PASS', native_executed=True, production_go=False, expected_id=gold['id'],
            classification='ACTUAL_NATIVE_FRACTIONAL_HPP_ONLY_WHEN_RUN', expected_sha256=EXPECTED_SHA,
            fixture_calendar_binding=nf.calendar_binding(), period_setup='ADMINISTRATIVE_DISPOSABLE_PERIOD_INPUT',
            source_groups=f['groups'], source_recost=f.get('source_recost'), before_targets=before_targets,
            frozen_literal_delta=gold['delta'], quote=quote, outcome=result, actual=actual,
            old_quote=old_quote, stale_refusal=refusal,
            opening_failure_controls=opening_controls,
            original_payment_and_all_prior_journals_byte_equal=True,
            replay_same_outcome=True, replay_additional_effects=0, deferred_constraints_forced=True)


def cases(cur, today):
    """No database calls here; all fourteen cases execute under the old harness."""
    return [(gold['id'], lambda gold=gold: _run(cur, today, gold)) for gold in expected()['cases']]
