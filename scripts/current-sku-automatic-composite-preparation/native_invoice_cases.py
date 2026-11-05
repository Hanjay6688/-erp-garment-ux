"""Real Native automatic completion followed by lawful supplier recosts.

PO accounting is checked in its actual PO scope. The non-PO product book
helper would return the wrong scope here and must not supply an oracle.
No callback runs at import; the combined owner supplies the admitted modules.
"""
from decimal import Decimal, ROUND_HALF_UP
import inspect
import json

IDS = (
    'SKU_AUTOMATIC_NATIVE_REWORK_PO_LATE_INVOICE_INVERSE_AND_NO_REVIVAL',
    'SKU_AUTOMATIC_NATIVE_REDYE_PO_LATE_INVOICE_INVERSE_AND_NO_REVIVAL',
)


def source_contract(modules):
    calls = (
        (modules.invoice.payload, (None, '1000', '3.50'), {}),
        (modules.invoice.finalize, (None, None), {'p': None}),
        (modules.invoice.reverse, (None, None, None), {}),
        (modules.bc.internal, (None, 'process_cost_recalc_queue', 100), {}),
    )
    for operation, args, kwargs in calls:
        inspect.signature(operation).bind(*args, **kwargs)
    return dict(original_invoice_helper_shapes=len(calls), actual_ERP_cases=0)


def roots(cur, f, *, active_child):
    rows = cur.execute(
        'select l.id::text,l.initial_qty_pcs,h.qty_basis_pcs,h.total_cost,h.hpp_per_pcs '
        'from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current '
        "where l.po_id=%s and l.lot_origin='PRODUCTION' order by l.id", (f['po'],)).fetchall()
    expected = {f['lot']: 6}
    if active_child:
        expected[f['source']] = 2
    if {row[0]: row[1] for row in rows} != expected:
        raise ValueError('SKU_AUTOMATIC_INVOICE_EXACT_ACTIVE_NATIVE_ROOTS_REQUIRED')
    for _, qty, basis, total, unit in rows:
        if (basis != qty or any(value is None or not Decimal(str(value)).is_finite()
                                for value in (total, unit)) or Decimal(str(total)) < 0):
            raise ValueError('SKU_AUTOMATIC_INVOICE_PRESENT_NATIVE_ROOT_AMOUNTS_REQUIRED')
    return rows


def observe(cur, f, native, *, active_child):
    if native.one(cur, 'select count(*) from cp7_sku_conversion.cost_events_v3 where root_lot_id in(%s,%s)',
                  f['lot'], f['source']):
        raise ValueError('SKU_AUTOMATIC_INVOICE_BASE_ONLY_FIXTURE_REQUIRED')
    current = roots(cur, f, active_child=active_child)
    expected = sum(Decimal(str(row[3])) for row in current).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    books = {}
    for key in ('FG_INVENTORY', 'COGS'):
        books[key] = Decimal(str(native.one(cur,
            'select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l '
            'join erp.accounting_account_mappings m on m.account_id=l.account_id '
            'where m.mapping_key=%s and l.po_id=%s', key, f['po'])))
    if books != {'FG_INVENTORY': expected, 'COGS': Decimal(0)}:
        raise ValueError('SKU_AUTOMATIC_NATIVE_PO_ROOT_TOTAL_MUST_EQUAL_ACTUAL_PO_FG_GL:'
                         + json.dumps(dict(expected=str(expected), actual={k: str(v) for k, v in books.items()})))
    if (native.quantity(cur, f['lot']) != 6 or native.quantity(cur, f['source']) != 0
            or native.quantity(cur, f['destination']) != (2 if active_child else 0)):
        raise ValueError('SKU_AUTOMATIC_INVOICE_CHANGED_PHYSICAL_QUANTITIES')
    events = cur.execute(
        'select side,product_id::text,root_lot_id::text,sum(units_delta) '
        'from cp7_sku_conversion.component_events_v2 where group_id=%s '
        "and source_type='SKU_CONVERSION' and phase='POST' group by side,product_id,root_lot_id", (f['child'],)).fetchall()
    expected_events = {
        ('SOURCE', f['product'], f['lot']): Decimal('-1.5'),
        ('SOURCE', f['product'], f['source']): Decimal('1.5'),
        ('TARGET', f['target'], f['lot']): Decimal('1.5'),
        ('TARGET', f['target'], f['source']): Decimal('0.5'),
        ('TARGET', f['target'], f['destination']): Decimal('-2'),
    }
    if len(events) != 5 or {(side, product, root): units for side, product, root, units in events} != expected_events:
        raise ValueError('SKU_AUTOMATIC_INVOICE_EXACT_INDEPENDENT_TWO_OF_EIGHT_ROOT_CUSTODY_REQUIRED')
    if not active_child:
        net = cur.execute(
            'select side,product_id,root_lot_id,sum(units_delta) '
            'from cp7_sku_conversion.component_events_v2 where group_id=%s '
            "and source_type='SKU_CONVERSION' group by side,product_id,root_lot_id", (f['child'],)).fetchall()
        if len(net) != 5 or any(row[3] != 0 for row in net):
            raise ValueError('SKU_AUTOMATIC_INVOICE_PARENT_INVERSE_DID_NOT_ZERO_ECONOMIC_CUSTODY')
    return dict(native_roots=[[str(value) for value in row] for row in current],
                independent_native_root_total=str(expected), actual_PO_GL={k: str(v) for k, v in books.items()},
                independent_two_of_eight_custody_exact=True, after_inverse_custody_zero=not active_child)


def invoice(cur, modules, f, today, price):
    document = dict(f['accessory'], receipt=dict(purchase_id=f['accessory']['purchase']),
                    tag=f['accessory']['code'], day=today)
    payload = modules.invoice.payload(document, '1000', price)
    payload.update(invoice_date=str(today), received_at=modules.bc.local_at(today, 8), due_date=str(today))
    result = modules.invoice.finalize(cur, document, p=payload)
    modules.bc.internal(cur, 'process_cost_recalc_queue', 100)
    modules.bc.api.admin(cur)
    return document, result


def undo(cur, modules, document, result):
    reply = modules.invoice.reverse(cur, document, result['invoice_id'])
    modules.bc.internal(cur, 'process_cost_recalc_queue', 100)
    modules.bc.api.admin(cur)
    return reply


def run(cur, today, product, business, native, *, redye=False):
    fixture, modules, f = native.prepare(cur, today, product, redye=redye)
    source_contract(modules)
    payload, version, request = native.completion(cur, today, fixture, modules, f, 2)
    posted = modules.bd.chain.bs_action(cur, 'COMPLETE_REWORK', payload, version, key=request)
    modules.bc.api.admin(cur)
    row = cur.execute(
        'select c.id::text,a.source_lot_id::text,a.destination_lot_id::text,a.qty_pcs '
        'from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id '
        'join erp.product_conversion_allocations a on a.conversion_id=c.id '
        "where s.rework_id=%s and c.status='POSTED'", (f['rework'],)).fetchall()
    if len(row) != 1 or row[0][3] != 2:
        raise ValueError('SKU_AUTOMATIC_INVOICE_ONE_ACTUAL_TWO_GOOD_CHILD_REQUIRED')
    child, f['source'], f['destination'], _ = row[0]
    f['child'] = child
    immutable = business.n.immutable(cur, [child])
    admission = native.one(cur,
        "select to_jsonb(a) from cp7_sku_conversion.automatic_admissions_v5 a where conversion_id=%s and phase='POST'", child)
    initial = observe(cur, f, native, active_child=True)
    document, first = invoice(cur, modules, f, today, '3.50')
    changed = observe(cur, f, native, active_child=True)
    if changed['independent_native_root_total'] == initial['independent_native_root_total']:
        raise ValueError('SKU_AUTOMATIC_INVOICE_MUST_ACTUALLY_CHANGE_NATIVE_ROOT_COST')
    if business.n.immutable(cur, [child]) != immutable:
        raise ValueError('SKU_AUTOMATIC_INVOICE_MUTATED_ORIGINAL_NATIVE_CONVERSION_FACTS')
    held = business.n.capture(cur)
    if modules.bd.chain.bs_action(cur, 'COMPLETE_REWORK', payload, version, key=request) != posted:
        raise ValueError('SKU_AUTOMATIC_INVOICE_REPLAY_REPLACED_ORIGINAL_RESPONSE')
    replay = business.n.unchanged(cur, held, 'AUTOMATIC_INVOICE_PARENT_REPLAY')
    first_inverse = undo(cur, modules, document, first)
    restored = observe(cur, f, native, active_child=True)
    if restored['independent_native_root_total'] != initial['independent_native_root_total']:
        raise ValueError('SKU_AUTOMATIC_LAWFUL_INVOICE_INVERSE_DID_NOT_RESTORE_SOURCE_AMOUNT')
    document, second = invoice(cur, modules, f, today, '4.00')
    before_parent_inverse = observe(cur, f, native, active_child=True)
    native.parent_inverse(cur, modules, f)
    after_parent_inverse = observe(cur, f, native, active_child=False)
    if native.one(cur, 'select status from erp.product_conversions where id=%s', child) != 'REVERSED':
        raise ValueError('SKU_AUTOMATIC_INVOICE_PARENT_INVERSE_MUST_REVERSE_CHILD')
    if native.one(cur,
            "select to_jsonb(a) from cp7_sku_conversion.automatic_admissions_v5 a where conversion_id=%s and phase='POST'", child) != admission:
        raise ValueError('SKU_AUTOMATIC_INVOICE_IMMUTABLE_POST_ADMISSION_CHANGED')
    frozen = business.n.immutable(cur, [child])
    second_inverse = undo(cur, modules, document, second)
    after_invoice_inverse = observe(cur, f, native, active_child=False)
    _, third = invoice(cur, modules, f, today, '5.00')
    later = observe(cur, f, native, active_child=False)
    if business.n.immutable(cur, [child]) != frozen:
        raise ValueError('SKU_AUTOMATIC_LATER_COST_REVIVED_OR_CHANGED_REVERSED_CHILD')
    if native.one(cur, 'select count(*) from cp7_sku_conversion.automatic_context_v5'):
        raise ValueError('SKU_AUTOMATIC_INVOICE_TEMPORARY_CONTEXT_LEAK')
    return dict(status='PASS', mode='REDYE' if redye else 'REWORK', initial=initial,
                after_first_invoice=changed, actual_parent_replay=replay,
                first_lawful_invoice_inverse=first_inverse, source_restored=restored,
                second_invoice=second, before_parent_inverse=before_parent_inverse,
                after_parent_inverse=after_parent_inverse, second_lawful_invoice_inverse=second_inverse,
                after_second_invoice_inverse=after_invoice_inverse, later_invoice=third,
                later_active_root_cost=later, reversed_child_never_revived=True,
                original_post_admission_immutable=True, actual_Auth_HTTP_cases=0,
                complete_outer_restore_and_all_five_required=True, production_go=False)


def cases(cur, today, product, business, native):
    return [(IDS[0], lambda: run(cur, today, product, business, native)),
            (IDS[1], lambda: run(cur, today, product, business, native, redye=True))]
