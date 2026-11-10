"""Prepared upstream Native callbacks; importing this runs no ERP operation.

Physical production, QC BS, rework/redye completion and parent reversal all
use the admitted original commands. Only target/process masters are fixture
setup. The owning component must preflight these callbacks and retain the
complete sequence prefixes and outer backup/restore before counting a case.
"""
from decimal import Decimal, ROUND_HALF_UP
import inspect
import json
import uuid

IDS = (
    'SKU_AUTOMATIC_NATIVE_REWORK_PENDING_AVERAGE_REPLAY_AND_PARENT_INVERSE',
    'SKU_AUTOMATIC_NATIVE_REDYE_UNKNOWN_AVERAGE_REPLAY_AND_PARENT_INVERSE',
    'SKU_AUTOMATIC_NATIVE_ZERO_GOOD_PARENT_HAS_NO_CONVERSION',
    'SKU_AUTOMATIC_NATIVE_LATE_TARGET_REFUSAL_ROLLS_BACK_PARENT_AND_CHILD',
)


def source_contract(fixture, modules):
    """Bind the real caller APIs before the owning runtime opens its cases."""
    calls = (
        (fixture.prepare, (None, None, None), {'special': True}),
        (fixture.post_good, (None, None, None), {'good_qty': 6, 'bs_qty': 4}),
        (fixture.actual_time, (None, None), {}),
        (modules.bd.sized_product, (None, None, None), {}),
        (modules.bd.chain.bs_action, (None, None, None, None), {'key': None}),
        (modules.bd.chain.version, (None, None, None), {}),
    )
    for operation, args, kwargs in calls:
        inspect.signature(operation).bind(*args, **kwargs)
    return dict(status='NATIVE_AUTOMATIC_CALLER_APIS_BOUND_NOT_EXECUTED', calls=len(calls),
                original_AFUI_physical_constructor=True, actual_ERP_cases=0)


def context(product):
    # Automatic -> money -> moving -> admitted current Mandor assembly. Its
    # domain modules were admitted before installing the additional stages;
    # re-running the narrow Afui verifier after their DDL would be incorrect.
    mandor = product.parent().parent().parent()
    fixture, modules = mandor.fixture, mandor.domain_modules
    if modules is None:
        raise ValueError('SKU_AUTOMATIC_ADMITTED_CURRENT_MANDOR_DOMAIN_REQUIRED')
    source_contract(fixture, modules)
    return fixture, modules


def one(cur, sql, *params):
    row = cur.execute(sql, params).fetchone()
    if row is None:
        raise ValueError('SKU_AUTOMATIC_REQUIRED_NATIVE_OBSERVATION_MISSING')
    return row[0]


def quantity(cur, lot):
    return int(one(cur, 'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s', lot))


def prepare(cur, today, product, *, redye=False):
    fixture, modules = context(product)
    f = fixture.prepare(cur, today, modules, special=True)
    fixture.post_good(cur, modules, f, good_qty=6, bs_qty=4)
    modules.bc.api.admin(cur)
    rows = cur.execute("select id::text,qty_pcs from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",
                       (f['po'], f['product'])).fetchall()
    if len(rows) != 1 or rows[0][1] != 4:
        raise ValueError('SKU_AUTOMATIC_GENUINE_QC_FOUR_BS_REQUIRED')
    bs = rows[0][0]
    chain = modules.bd.chain
    chain.bs_action(cur, 'CLASSIFY_BS', dict(bs_case_id=bs, cause_source='UNKNOWN',
        components=[dict(work_component_id=chain.production.COMPONENT, completed_before_bs_qty=4)],
        change_reason='Native completed component retained for four QC BS'), chain.version(cur, 'bs_cases', bs))
    modules.bc.api.admin(cur)
    target = modules.bd.sized_product(cur, chain.base.SIZE, 'AUTO-' + uuid.uuid4().hex[:12])
    bom = one(cur, 'select id::text from erp.accessory_bom_versions where product_id=%s and is_active order by effective_from desc,id desc limit 1', f['product'])
    sent = fixture.actual_time(cur, today)
    order = dict(rework_number='AUTO-' + uuid.uuid4().hex[:20], bs_case_id=bs,
        destination_type='LAUNDRY', contractor_id=None, vendor_id=f['vendor'], qty_sent=4,
        physical_sent_at=sent.isoformat(), status='IN_PROGRESS', return_fg_location_id=chain.base.LOCATION,
        accessory_bom_version_id=bom, accessory_bom_item_ids=[], components=[])
    payload = dict(order=order, target_product_id=target, reason='Native automatic target from actual QC BS')
    action = 'SAVE_REWORK'
    if redye:
        process = str(uuid.uuid4())
        cur.execute('insert into erp.wash_processes(id,process_code,process_name,is_active) values(%s,%s,%s,true)',
                    (process, 'AUTO-' + uuid.uuid4().hex[:12], 'Isolated automatic redye unknown rate'))
        payload.update(wash_process_id=process, price_status='UNKNOWN')
        action = 'SAVE_REDYE'
    # The same ordinary public action used by the manual Native fixture; its
    # SAVE_REWORK/SAVE_REDYE branches create only a draft/in-progress order.
    modules.bc.api.admin(cur)
    chain.production.owner(cur)
    saved = cur.execute('select public.erp_save_product_conversion_action_v1(%s,%s::jsonb,%s)',
                        (action, json.dumps(payload), uuid.uuid4())).fetchone()[0]
    modules.bc.api.admin(cur)
    f.update(bs=bs, target=target, rework=saved['rework_id'], redye=redye)
    return fixture, modules, f


def completion(cur, today, fixture, modules, f, good):
    chain = modules.bd.chain
    payload = dict(rework_order_id=f['rework'], qty_good=good, qty_bs=4-good,
                   completed_at=fixture.actual_time(cur, today).isoformat(),
                   return_fg_location_id=chain.base.LOCATION,
                   change_reason='Native automatic completion at genuine current physical time')
    return payload, chain.version(cur, 'rework_orders', f['rework']), str(uuid.uuid4())


def parent_inverse(cur, modules, f):
    chain = modules.bd.chain
    result = chain.bs_action(cur, 'REVERSE_REWORK_COMPLETION',
        dict(rework_order_id=f['rework'], change_reason='Native automatic parent inverse'),
        chain.version(cur, 'rework_orders', f['rework']))
    modules.bc.api.admin(cur)
    if one(cur, 'select status from erp.rework_orders where id=%s', f['rework']) != 'CANCELLED':
        raise ValueError('SKU_AUTOMATIC_NATIVE_PARENT_INVERSE_REQUIRED')
    return result


def forward_inverse(cur, today, product, business, *, redye=False):
    fixture, modules, f = prepare(cur, today, product, redye=redye)
    payload, version, request = completion(cur, today, fixture, modules, f, 2)
    chain = modules.bd.chain
    posted = chain.bs_action(cur, 'COMPLETE_REWORK', payload, version, key=request)
    modules.bc.api.admin(cur)
    source = one(cur, 'select good_fg_lot_id::text from erp.rework_orders where id=%s', f['rework'])
    children = cur.execute("select c.id::text,c.status,s.origin_kind,a.source_lot_id::text,a.destination_lot_id::text,a.qty_pcs,a.original_hpp_per_pcs "
        "from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id "
        "join erp.product_conversion_allocations a on a.conversion_id=c.id where s.rework_id=%s", (f['rework'],)).fetchall()
    if len(children) != 1:
        raise ValueError('SKU_AUTOMATIC_EXACT_ONE_NATIVE_CHILD_REQUIRED')
    child, status, origin, actual_source, destination, qty, physical_hpp = children[0]
    if (status != 'POSTED' or origin != ('REDYE' if redye else 'REWORK') or actual_source != source
            or qty != 2 or quantity(cur, source) != 0 or quantity(cur, destination) != 2 or quantity(cur, f['lot']) != 6):
        raise ValueError('SKU_AUTOMATIC_NATIVE_SOURCE_AND_GOOD_PHYSICAL_EFFECT_NOT_EXACT')
    pending = one(cur, 'select pending_reason_count from erp.get_hpp_completeness(%s)', f['po'])
    if pending <= 0:
        raise ValueError('SKU_AUTOMATIC_FIXTURE_MUST_RETAIN_REAL_PO_PENDING_COST')
    roots = cur.execute('select l.id::text,l.initial_qty_pcs,h.hpp_per_pcs from erp.fg_lots l '
        'join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.id in(%s,%s) order by l.id',
        (f['lot'], source)).fetchall()
    if len(roots) != 2 or sorted(row[1] for row in roots) != [2, 6]:
        raise ValueError('SKU_AUTOMATIC_TWO_REAL_PO_BASE_COMPONENTS_REQUIRED')
    prices = [Decimal(str(row[2])) for row in roots]
    if any(not price.is_finite() for price in prices) or len(set(prices)) != 2:
        raise ValueError('SKU_AUTOMATIC_DISTINCT_PRESENT_NATIVE_LOT_PRICES_REQUIRED')
    if one(cur, 'select count(*) from cp7_sku_conversion.base_money_events_v4 where root_lot_id in(%s,%s)', f['lot'], source):
        raise ValueError('SKU_AUTOMATIC_PO_ORACLE_MUST_NOT_USE_NONPO_CENT_CUSTODY')
    # These two production roots have no extra conversion-cost source. Observe
    # that prerequisite rather than silently treating a present cost as zero.
    extra = one(cur, 'select count(*) from cp7_sku_conversion.cost_events_v3 where root_lot_id in(%s,%s)', f['lot'], source)
    if extra:
        raise ValueError('SKU_AUTOMATIC_INDEPENDENT_BASE_ONLY_FIXTURE_REQUIRED')
    pool = sum(Decimal(row[1]) * Decimal(str(row[2])) for row in roots).quantize(Decimal('.000001'), rounding=ROUND_HALF_UP)
    expected = (pool * Decimal(2) / Decimal(8)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    legacy = one(cur, 'select to_jsonb(g) from cp7_sku_conversion.legacy_groups_v4 g where group_id=%s', child)
    preview = legacy['original_preview']
    if (Decimal(preview['cost']['source_value']) != expected or preview['valuation_provisional'] is not True
            or preview['source_value_state'] != 'PROVISIONAL'):
        raise ValueError('SKU_AUTOMATIC_INDEPENDENT_CURRENT_NATIVE_WEIGHTED_AVERAGE_REQUIRED')
    post_proof = one(cur, "select to_jsonb(a) from cp7_sku_conversion.automatic_admissions_v5 a where conversion_id=%s and phase='POST'", child)
    held = business.n.capture(cur)
    if chain.bs_action(cur, 'COMPLETE_REWORK', payload, version, key=request) != posted:
        raise ValueError('SKU_AUTOMATIC_NATIVE_PARENT_REPLAY_RESPONSE_CHANGED')
    replay = business.n.unchanged(cur, held, 'AUTOMATIC_PARENT_REPLAY')
    parent_inverse(cur, modules, f)
    if quantity(cur, source) != 0 or quantity(cur, destination) != 0 or quantity(cur, f['lot']) != 6:
        raise ValueError('SKU_AUTOMATIC_PARENT_PHYSICAL_INVERSE_NOT_EXACT')
    if one(cur, "select to_jsonb(a) from cp7_sku_conversion.automatic_admissions_v5 a where conversion_id=%s and phase='POST'", child) != post_proof:
        raise ValueError('SKU_AUTOMATIC_IMMUTABLE_POST_ADMISSION_CHANGED')
    if one(cur, 'select count(*) from cp7_sku_conversion.automatic_admissions_v5 where conversion_id=%s', child) != 2:
        raise ValueError('SKU_AUTOMATIC_POST_AND_INVERSE_PROVENANCE_REQUIRED')
    if one(cur, 'select count(*) from cp7_sku_conversion.automatic_context_v5'):
        raise ValueError('SKU_AUTOMATIC_TEMPORARY_CONTEXT_LEAK')
    return dict(status='PASS', mode=origin, rework=f['rework'], child=child,
                actual_upstream_native_completion=True, actual_parent_inverse=True,
                distinct_native_root_prices=[str(value) for value in prices], source_pool_qty=8,
                independent_expected_transfer=str(expected), actual_physical_hpp=str(physical_hpp),
                pending_reason_count=int(pending), replay=replay, actual_Auth_HTTP_cases=0,
                complete_outer_restore_and_all_five_still_required=True, production_go=False)


def zero_good(cur, today, product, business):
    fixture, modules, f = prepare(cur, today, product)
    payload, version, request = completion(cur, today, fixture, modules, f, 0)
    modules.bd.chain.bs_action(cur, 'COMPLETE_REWORK', payload, version, key=request)
    modules.bc.api.admin(cur)
    result = cur.execute('select status,cost_posted,good_fg_lot_id from erp.rework_orders where id=%s', (f['rework'],)).fetchone()
    if result != ('COMPLETED', True, None):
        raise ValueError('SKU_AUTOMATIC_ZERO_GOOD_ORIGINAL_PARENT_PATH_REQUIRED')
    if one(cur, 'select count(*) from erp.be_conversion_sources_v1 where rework_id=%s', f['rework']):
        raise ValueError('SKU_AUTOMATIC_ZERO_GOOD_CANNOT_CREATE_CHILD')
    parent_inverse(cur, modules, f)
    if quantity(cur, f['lot']) != 6:
        raise ValueError('SKU_AUTOMATIC_ZERO_GOOD_CHANGED_OTHER_PHYSICAL_STOCK')
    return dict(status='PASS', actual_zero_good_parent_completion_and_inverse=True,
                child_conversions=0, actual_Auth_HTTP_cases=0, production_go=False)


def late_refusal(cur, today, product, business, sequence_prefix):
    fixture, modules, f = prepare(cur, today, product)
    modules.bc.api.admin(cur)
    cur.execute('update erp.products set is_active=false where id=%s', (f['target'],))
    payload, version, request = completion(cur, today, fixture, modules, f, 2)
    before = business.n.capture(cur)
    cur.execute('savepoint automatic_native_late_target')
    error = None
    try:
        try:
            modules.bd.chain.bs_action(cur, 'COMPLETE_REWORK', payload, version, key=request)
        except Exception as caught:
            error = dict(sqlstate=getattr(caught, 'sqlstate', None), message=str(caught))
    finally:
        cur.execute('rollback to savepoint automatic_native_late_target')
        cur.execute('release savepoint automatic_native_late_target')
    if error is None or error['sqlstate'] != 'P0001' or 'BE_TARGET_NOT_ACTIVE' not in error['message']:
        raise ValueError('SKU_AUTOMATIC_EXACT_LATE_NATIVE_TARGET_REFUSAL_REQUIRED:' + str(error))
    after = business.n.capture(cur)
    rollback = sequence_prefix.strict_rollback(
        dict(catalog=before['catalog'], data=before['data_and_sequences']),
        dict(catalog=after['catalog'], data=after['data_and_sequences']))
    return dict(status='PASS', exact_Native_late_refusal=error, all22_and_all_table_rows_restored=True,
                sequence_prefix=rollback['sequence_prefix'], per_savepoint_sequence_restore_claim=False,
                full_sequence_restore_owned_by='FULL_OUTER_BACKUP_RESTORE',
                target_inactive_is_master_fixture_only=True, actual_Auth_HTTP_cases=0, production_go=False)


def cases(cur, today, product, business, sequence_prefix):
    return [(IDS[0], lambda: forward_inverse(cur, today, product, business)),
            (IDS[1], lambda: forward_inverse(cur, today, product, business, redye=True)),
            (IDS[2], lambda: zero_good(cur, today, product, business)),
            (IDS[3], lambda: late_refusal(cur, today, product, business, sequence_prefix))]
